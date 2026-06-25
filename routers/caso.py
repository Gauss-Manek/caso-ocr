from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import List
import shutil
import os
from pathlib import Path
from extraction import affiner_extraction
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from auth import SECRET_KEY, ALGORITHM, verify_password, create_access_token
import bcrypt

##################
def safe_truncate(text, length=100):
    if text is None: return "Non trouvé"
    return str(text)[:length]
##################

router = APIRouter()

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/caso_ocr_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") is None:
            raise HTTPException(status_code=401, detail="Token invalide")
        return payload  # On retourne tout le payload pour avoir accès au rôle
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")
    

def check_admin(user: dict = Depends(get_current_user)):
    # On convertit le rôle en minuscule pour comparer avec la base
    role = user.get("role", "").lower()
    if role != "admin": 
        raise HTTPException(
            status_code=403, 
            detail="Accès réservé aux administrateurs"
        )
    return user

@router.post("/ajouter-utilisateur/")
async def ajouter_utilisateur(
    username: str = Form(...), 
    password: str = Form(...), 
    role: str = Form("Utilisateur"),
    db: Session = Depends(get_db),
    admin: dict = Depends(check_admin) # <--- La sécurité est appliquée ici
):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        db.execute(text("INSERT INTO users (username, password_hash, role) VALUES (:u, :p, :r)"), 
                   {"u": username, "p": hashed, "r": role})
        db.commit()
        return {"message": "Utilisateur créé avec succès"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Erreur lors de la création")

# --- LOGIN ---
@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Récupérer le hash ET le rôle
    user = db.execute(text("SELECT password_hash, role FROM users WHERE username = :u"), {"u": form_data.username}).fetchone()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    
    # Inclusion du rôle dans le token
    return {
        "access_token": create_access_token(data={"sub": form_data.username, "role": user.role}), 
        "token_type": "bearer"
    }

# --- UPLOAD MULTIPLE ---
@router.post("/upload-multiple/")
async def upload_multiple(files: List[UploadFile] = File(...), current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    BASE_DIR = Path(__file__).resolve().parent.parent
    UPLOAD_DIR = BASE_DIR / "uploads"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Extraction sécurisée du nom d'utilisateur
    username = current_user.get("sub") 
    
    for file in files:
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Insertion document : on utilise 'username' (str) et non 'current_user' (dict)
        doc_id = db.execute(text("INSERT INTO documents (filename, uploaded_by) VALUES (:fn, :u) RETURNING id"), 
                           {"fn": file.filename, "u": username}).scalar()
        db.commit()
        
        # OCR
        extracted_data = affiner_extraction(str(file_path)) 
        
        # Insertion dans caso_data
        db.execute(text("""
            INSERT INTO caso_data (document_id, num_caso, parcelle, section, commune, 
                                   requerant, date_debut, date_fin, extraction_ocr)
            VALUES (:did, :nc, :p, :s, :c, :r, :dd, :df, :raw)
        """), {
            "did": doc_id,
            "nc": safe_truncate(extracted_data.get("num_caso")),
            "p": safe_truncate(extracted_data.get("parcelle")),
            "s": safe_truncate(extracted_data.get("section")),
            "c": safe_truncate(extracted_data.get("commune")),
            "r": safe_truncate(extracted_data.get("requerant")),
            "dd": safe_truncate(extracted_data.get("date_debut")),
            "df": safe_truncate(extracted_data.get("date_fin")),
            "raw": extracted_data.get("extraction_ocr")
        })
        db.commit()
    return {"message": "Upload et OCR terminés"}
# --- VALIDER DOCUMENT ---
@router.post("/valider-document/{caso_id}")
async def valider_document(
    caso_id: int, 
    num_caso: str = Form(...),
    parcelle: str = Form(...),
    section: str = Form(...),
    commune: str = Form(...),
    requerant: str = Form(...),
    date_debut: str = Form(...),
    date_fin: str = Form(...),
    extraction_ocr: str = Form(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # 1. Vérifier le statut actuel
    doc_result = db.execute(
        text("SELECT statut FROM caso_data WHERE id = :id"), 
        {"id": caso_id}
    ).fetchone()

    if not doc_result:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    
    statut_actuel = doc_result[0]

    # 2. Sécurité : Règle métier
    if statut_actuel == 'valide' and current_user.get("role") != "Administrateur":
        raise HTTPException(
            status_code=403, 
            detail="Ce document est déjà validé. Seul un administrateur peut le modifier."
        )

    # 3. Mise à jour avec commit explicite
    try:
        db.execute(text("""
            UPDATE caso_data 
            SET num_caso=:nc, parcelle=:p, section=:s, commune=:c, 
                requerant=:r, date_debut=:dd, date_fin=:df, 
                extraction_ocr=:raw, 
                statut='valide'
            WHERE id = :id
        """), {
            "id": caso_id,
            "nc": num_caso, "p": parcelle, "s": section, "c": commune,
            "r": requerant, "dd": date_debut, "df": date_fin,
            "raw": extraction_ocr
        })
        
        # IMPORTANT : db.commit() doit être appelé pour finaliser l'écriture
        db.commit() 
        return {"message": "Validation réussie"}
        
    except Exception as e:
        db.rollback() # Annule en cas d'erreur pour garder la base cohérente
        # Remplacement de raise...() avec erreur de syntaxe par une exception propre
        raise HTTPException(status_code=500, detail=f"Erreur serveur : {str(e)}")
    
    
# Pensez aussi à mettre à jour /tous-les-documents/ pour sélectionner extraction_ocr
@router.get("/tous-les-documents/")
async def get_tous_documents(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):    
    docs = db.execute(text("""
        SELECT c.id AS id, d.filename, c.num_caso, c.parcelle, c.section, c.commune, 
               c.requerant, c.date_debut, c.date_fin, c.statut, d.created_at,
               c.extraction_ocr 
        FROM caso_data c 
        JOIN documents d ON c.document_id = d.id
        ORDER BY d.created_at DESC
    """)).fetchall()
    return [dict(row._mapping) for row in docs]

# --- CRUD USERS ---

@router.get("/users/")
async def get_users(db: Session = Depends(get_db), admin: dict = Depends(check_admin)):
    # On sélectionne les colonnes réelles de votre table
    users = db.execute(text("SELECT id, username, role, is_active FROM users")).fetchall()
    return [dict(row._mapping) for row in users]

@router.post("/users/")
async def create_user(
    username: str = Form(...), 
    password: str = Form(...), 
    role: str = Form("correcteur"), 
    db: Session = Depends(get_db),
    admin: dict = Depends(check_admin)
):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        # Utilisation de password_hash et is_active
        db.execute(text("""
            INSERT INTO users (username, password_hash, role, is_active) 
            VALUES (:u, :p, :r, true)
        """), {"u": username, "p": hashed, "r": role})
        db.commit()
        return {"message": "Utilisateur créé"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db), admin: dict = Depends(check_admin)):
    db.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
    db.commit()
    return {"message": "Utilisateur supprimé"}

@router.put("/users/{user_id}")
async def update_user(
    user_id: int, 
    data: dict, # On utilise 'dict' au lieu de 'UserUpdateSchema'
    db: Session = Depends(get_db), 
    admin: dict = Depends(check_admin)
):
    # Récupération des données du dictionnaire
    username = data.get("username")
    password = data.get("password")
    
    # Logique de mise à jour
    if password and password.strip() != "":
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.execute(text("UPDATE users SET username = :u, password_hash = :p WHERE id = :id"), 
                   {"u": username, "p": hashed, "id": user_id})
    else:
        db.execute(text("UPDATE users SET username = :u WHERE id = :id"), 
                   {"u": username, "id": user_id})
    
    db.commit()
    return {"message": "Utilisateur mis à jour avec succès"}