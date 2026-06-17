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
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token invalide")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

# --- LOGIN ---
@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.execute(text("SELECT password_hash FROM users WHERE username = :u"), {"u": form_data.username}).fetchone()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    return {"access_token": create_access_token(data={"sub": form_data.username}), "token_type": "bearer"}

# --- UPLOAD MULTIPLE ---
@router.post("/upload-multiple/")
async def upload_multiple(files: List[UploadFile] = File(...), current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    BASE_DIR = Path(__file__).resolve().parent
    UPLOAD_DIR = BASE_DIR / "uploads"
    
    for file in files:
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Insertion document
        doc_id = db.execute(text("INSERT INTO documents (filename, uploaded_by) VALUES (:fn, :u) RETURNING id"), 
                           {"fn": file.filename, "u": current_user}).scalar()
        db.commit()
        
        # OCR
        data = affiner_extraction(str(file_path))
        db.execute(text("""
            INSERT INTO caso_data (doc_id, num_caso, parcelle, section, commune, requerant, date_debut, date_fin, statut)
            VALUES (:did, :nc, :p, :s, :c, :r, :dd, :df, 'en_attente')
        """), {"did": doc_id, **data})
        db.commit()
    
    return {"message": "Upload et OCR terminés"}

# --- GET TOUS DOCUMENTS (MODIFIÉ) ---
@router.get("/tous-les-documents/")
async def get_tous_documents(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    # Requête mise à jour avec d.created_at
    docs = db.execute(text("""
        SELECT c.id, d.filename, c.num_caso, c.parcelle, c.section, c.commune, 
               c.requerant, c.date_debut, c.date_fin, c.statut, d.created_at 
        FROM caso_data c 
        JOIN documents d ON c.doc_id = d.id
        ORDER BY d.created_at DESC
    """)).fetchall()
    
    return [dict(row._mapping) for row in docs]

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
    validateur: str = Form(...),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        db.execute(text("""
            UPDATE caso_data 
            SET num_caso=:nc, parcelle=:p, section=:s, commune=:c, 
                requerant=:r, date_debut=:dd, date_fin=:df, 
                statut='valide', valide_par=:v 
            WHERE id = :id
        """), {"nc": num_caso, "p": parcelle, "s": section, "c": commune, "r": requerant, "dd": date_debut, "df": date_fin, "v": validateur, "id": caso_id})
        db.commit()
        return {"message": "Validé"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))