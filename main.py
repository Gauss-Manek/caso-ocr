import os
# Contournement indispensable pour éviter le plantage "libiomp5md.dll" lié à OpenMP/Intel MKL sous Windows/Conda
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import easyocr
from pdf2image import convert_from_bytes
from PIL import Image

# Initialisation de l'application FastAPI
app = FastAPI(
    title="CASO OCR API",
    description="API d'extraction de texte utilisant EasyOCR et FastAPI",
    version="1.0.0"
)

# Initialisation du lecteur EasyOCR (chargé une seule fois en mémoire au démarrage)
# Nous configurons la langue française ('fr') et anglaise ('en')
print("Chargement des modèles EasyOCR en mémoire...")
reader = easyocr.Reader(['fr', 'en'], gpu=False)
print("Modèles EasyOCR prêts !")

@app.get("/")
def read_root():
    """
    Route d'accueil pour vérifier que l'API est en ligne.
    """
    return {"status": "online", "engine": "EasyOCR", "languages": ["fr", "en"]}

@app.post("/ocr")
async def perform_ocr(file: UploadFile = File(...)):
    """
    Route principale pour analyser un document (Image ou PDF) et en extraire le texte.
    """
    filename = file.filename.lower()
    file_bytes = await file.read()
    
    extracted_results = []

    # --- TRAITEMENT DES DOCUMENTS PDF ---
    if filename.endswith(".pdf"):
        try:
            # Conversion des pages du PDF en images PIL (utilise Poppler en arrière-plan)
            images = convert_from_bytes(file_bytes)
            
            for i, page_image in enumerate(images):
                # Conversion de l'image PIL en octets pour qu'EasyOCR puisse la lire
                img_byte_arr = io.BytesIO()
                page_image.save(img_byte_arr, format='JPEG')
                img_bytes = img_byte_arr.getvalue()
                
                # Extraction du texte pour la page courante
                # detail=0 permet d'obtenir directement une liste de textes simples
                text_lines = reader.readtext(img_bytes, detail=0)
                full_text = " ".join(text_lines)
                
                extracted_results.append({
                    "page": i + 1,
                    "text": full_text
                })
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Erreur lors du traitement du fichier PDF : {str(e)}"
            )

    # --- TRAITEMENT DES IMAGES ---
    elif filename.endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
        try:
            # Utilisation directe des octets de l'image par EasyOCR
            text_lines = reader.readtext(file_bytes, detail=0)
            full_text = " ".join(text_lines)
            
            extracted_results.append({
                "page": 1,
                "text": full_text
            })
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Erreur lors du traitement de l'image : {str(e)}"
            )
            
    else:
        raise HTTPException(
            status_code=400, 
            detail="Format de fichier non supporté. Veuillez fournir un fichier PDF ou une Image (PNG, JPG, JPEG, TIFF, BMP)."
        )

    return JSONResponse(content={
        "filename": file.filename,
        "results": extracted_results
    })