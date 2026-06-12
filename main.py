import os
# Évite le conflit de DLL OpenMP sous Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import easyocr
from routers import caso

app = FastAPI(
    title="CASO OCR API",
    description="API d'extraction utilisant EasyOCR et FastAPI",
    version="1.0.0"
)

# Configuration CORS pour autoriser ton interface web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chargement unique du modèle (évite de le recharger à chaque requête)
print("Chargement des modèles EasyOCR...")
reader = easyocr.Reader(['fr', 'en'], gpu=False)
print("Modèles prêts !")

# Inclusion du routeur métier
app.include_router(caso.router)

@app.get("/")
def read_root():
    return {"status": "online", "engine": "EasyOCR"}