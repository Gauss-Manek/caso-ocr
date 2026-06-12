from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import shutil
import os
from extraction import affiner_extraction

# --- CONFIGURATION DB ---
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/caso_ocr_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class LoginRequest(BaseModel):
    username: str
    password: str

# --- ROUTES ---

@router.post("/login")
async def login(credentials: LoginRequest, db=Depends(get_db)):
    query = text("SELECT username, role FROM users WHERE username = :user AND password_hash = :password")
    user = db.execute(query, {"user": credentials.username, "password": credentials.password}).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Identifiants incorrects.")
    return {"username": user[0], "role": user[1]}

@router.get("/caso/")
def get_all_caso(db=Depends(get_db)):
    result = db.execute(text("SELECT * FROM caso_data ORDER BY id DESC")).fetchall()
    return [dict(row._mapping) for row in result]

@router.post("/valider-caso/")
async def valider_caso(
    document_id: int = Form(...),
    num_caso: str = Form(...),
    parcelle: str = Form(...),
    section: str = Form(...),
    commune: str = Form(...),
    date_debut: str = Form(...),
    date_fin: str = Form(...),
    requerant: str = Form(...),
    current_user: str = Form(...),
    db=Depends(get_db)
):
    query = text("""
        INSERT INTO caso_data (document_id, num_caso, parcelle, section, commune, date_debut, date_fin, requerant)
        VALUES (:doc_id, :nc, :p, :s, :c, :dd, :df, :r)
    """)
    db.execute(query, {
        "doc_id": document_id, "nc": num_caso, "p": parcelle, "s": section,
        "c": commune, "dd": date_debut, "df": date_fin, "r": requerant
    })
    db.commit()
    return {"message": "Fiche validée et intégrée avec succès"}

@router.put("/caso/{id}")
def update_caso(id: int, data: dict, current_user: str = Form(...), db=Depends(get_db)):
    # Vérification du rôle admin
    role = db.execute(text("SELECT role FROM users WHERE username = :u"), {"u": current_user}).scalar()
    if role != 'admin':
        raise HTTPException(status_code=401, detail="Droits insuffisants pour modifier.")
    
    query = text("""
        UPDATE caso_data SET num_caso=:nc, parcelle=:p, section=:s, commune=:c, requerant=:r WHERE id=:id
    """)
    db.execute(query, {**data, "id": id})
    db.commit()
    return {"message": "Mis à jour avec succès"}

@router.delete("/caso/{id}")
def delete_caso(id: int, current_user: str, db=Depends(get_db)):
    role = db.execute(text("SELECT role FROM users WHERE username = :u"), {"u": current_user}).scalar()
    if role != 'admin':
        raise HTTPException(status_code=401, detail="Droits insuffisants pour supprimer.")
    
    db.execute(text("DELETE FROM caso_data WHERE id = :id"), {"id": id})
    db.commit()
    return {"message": "Supprimé"}