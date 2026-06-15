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

# Configuration CORS pour autoriser les requêtes depuis votre interface (Live Server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chargement unique du modèle pour optimiser les performances
print("Chargement des modèles EasyOCR...")
reader = easyocr.Reader(['fr', 'en'], gpu=False)
print("Modèles prêts !")

# Inclusion du routeur
# Assurez-vous que le fichier routers/caso.py utilise bien 'router = APIRouter()'
app.include_router(caso.router)

@app.get("/")
def read_root():
    return {"status": "online", "engine": "EasyOCR"}

if __name__ == "__main__":
    import uvicorn
    # Suppression de la virgule erronée
    uvicorn.run(app, host="0.0.0.0", port=8000)