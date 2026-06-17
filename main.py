import os
# Évite le conflit de DLL OpenMP sous Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import easyocr
from routers import caso

# Initialisation de l'application
app = FastAPI(
    title="CASO OCR API",
    description="API d'extraction utilisant EasyOCR et FastAPI",
    version="1.0.0"
)

# Configuration CORS pour autoriser les requêtes depuis votre interface (Live Server, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION FICHIERS STATIQUES ---
# Assurez-vous que le dossier 'uploads' existe bien à la racine de votre projet
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# Monte le dossier 'uploads' sur la route '/static'
app.mount("/static", StaticFiles(directory="uploads"), name="static")
# ----------------------------------------

# Chargement unique du modèle pour optimiser les performances
print("Chargement des modèles EasyOCR...")
reader = easyocr.Reader(['fr', 'en'], gpu=False)
print("Modèles prêts !")

# Inclusion du routeur
app.include_router(caso.router)

@app.get("/")
def read_root():
    return {"status": "online", "engine": "EasyOCR"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)