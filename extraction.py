import re
import easyocr
import numpy as np
from pdf2image import convert_from_path
import json # Ajoutez cet import

# Initialisation du lecteur
reader = easyocr.Reader(['fr', 'en'], gpu=False)

def affiner_extraction(file_path):
    """
    Extrait le texte via OCR et applique les patterns regex définis 
    pour structurer les données.
    """
    texte_complet = ""
    
    try:
        pages = convert_from_path(file_path, dpi=300)
        for page in pages:
            image_np = np.array(page)
            resultats = reader.readtext(image_np, detail=0)
            # Concaténation propre pour éviter les coupures de mots
            texte_complet += " ".join(resultats) + " "
            
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier : {e}")
        return {"error": str(e)}

    # Nettoyage : normalisation des espaces
    texte_propre = re.sub(r'\s+', ' ', texte_complet)

    # Définition des patterns
    patterns = {
        "parcelle": r"de la parcelle (.*?),",
        "section": r"de la section (.*?) du plan cadastral",
        "commune": r"du plan cadastral (.*?)(?:,|$)",
        "requerant": r"formulée Le (.*?) a été affiché",
        "date_debut": r"a été affiché du\s+(.*?)\s+au",
        "date_fin": r"a été affiché (.*?)\s+inclus,",
    }

    # Initialisation du dictionnaire de résultats
    data = {cle: "Non trouvé" for cle in patterns.keys()}
    
    # Ajout manuel du cas particulier "num_caso" si nécessaire
    data["num_caso"] = "Non trouvé"
    match_caso = re.search(r"BP\s*(.*?)\s*CERTIFICAT", texte_propre, re.IGNORECASE)
    if match_caso:
        data["num_caso"] = match_caso.group(1).strip()

    # Extraction dynamique via les patterns
    for cle, motif in patterns.items():
        match = re.search(motif, texte_propre, re.IGNORECASE)
        if match:
            data[cle] = match.group(1).strip()
    data["extraction_ocr"] = texte_propre
    data["ocr_raw_json"] = json.dumps(data)
    

    return data