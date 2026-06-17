from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import List
import shutil
import os
from extraction import affiner_extraction

# Nouveaux imports pour la sécurité
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from auth import SECRET_KEY, ALGORITHM, verify_password, create_access_token

router = APIRouter()

# --- CONFIGURATION DB ---
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/caso_ocr_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Configuration du mécanisme d'authentification
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Fonction de dépendance pour vérifier le token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token invalide")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.execute(
        text("SELECT password_hash FROM users WHERE username = :u"), 
        {"u": username}
    ).fetchone()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")

    token = create_access_token(data={"sub": username})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/upload-multiple/")
async def upload_multiple(
    files: List[UploadFile] = File(...),
    current_user: str = Depends(get_current_user), # Sécurisé par le token
    db: Session = Depends(get_db)
):
    results = []
    
    for file in files:
        temp_path = f"temp_{file.filename}"
        try:
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            data = affiner_extraction(temp_path)
            
            if "error" in data:
                results.append({"filename": file.filename, "status": "error", "message": data["error"]})
                continue

            query = text("""
                INSERT INTO caso_data (
                    num_caso, parcelle, section, commune, 
                    requerant, date_debut, date_fin, utilisateur, statut
                ) VALUES (:num_caso, :parcelle, :section, :commune, 
                          :requerant, :date_debut, :date_fin, :utilisateur, 'en_attente')
            """)
            
            db.execute(query, {
                "num_caso": data.get("num_caso"),
                "parcelle": data.get("parcelle"),
                "section": data.get("section"),
                "commune": data.get("commune"),
                "requerant": data.get("requerant"),
                "date_debut": data.get("date_debut"),
                "date_fin": data.get("date_fin"),
                "utilisateur": current_user
            })
            db.commit()
            results.append({"filename": file.filename, "status": "saved"})
            
        except Exception as e:
            db.rollback()
            results.append({"filename": file.filename, "status": "error", "message": str(e)})
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    return {"message": "Traitement terminé", "details": results}

@router.post("/valider-document/{caso_id}")
async def valider_document(
    caso_id: int, 
    validateur: str = Form(...), 
    db: Session = Depends(get_db)
):
    # 1. Récupération du document en attente
    doc = db.execute(
        text("SELECT num_caso FROM caso_data WHERE id = :id"), 
        {"id": caso_id}
    ).fetchone()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable.")

    # 2. Vérification de doublon sur les documents déjà VALIDÉS
    conflit = db.execute(text(
        "SELECT COUNT(*) FROM caso_data WHERE num_caso = :num AND statut = 'valide'"
    ), {"num": doc.num_caso}).scalar()
    
    if conflit > 0:
        raise HTTPException(status_code=400, detail="Doublon détecté : ce cas est déjà validé.")
    
    # 3. Passage au statut validé
    db.execute(text(
        "UPDATE caso_data SET statut = 'valide', valide_par = :v WHERE id = :id"
    ), {"v": validateur, "id": caso_id})
    db.commit()
    
    return {"status": "success", "message": f"Document {caso_id} validé par {validateur}."}