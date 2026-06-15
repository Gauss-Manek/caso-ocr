import re
import easyocr
import numpy as np
from pdf2image import convert_from_path

# Initialisation du lecteur
reader = easyocr.Reader(['fr', 'en'], gpu=False)

def affiner_extraction(file_path):
    """
    Extrait le texte via OCR et applique des regex spécifiques 
    pour structurer les données.
    """
    texte_complet = ""
    
    try:
        pages = convert_from_path(file_path, dpi=300)
        for page in pages:
            image_np = np.array(page)
            resultats = reader.readtext(image_np, detail=0)
            # Utilisation de \n pour mieux gérer les sauts de ligne
            texte_complet += " ".join(resultats) + " "
            
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier : {e}")
        return {"error": str(e)}

    # Initialisation des données
    data = {
        "num_caso": "Non trouvé", 
        "parcelle": "Non trouvé", 
        "section": "Non trouvé",
        "commune": "Non trouvé", 
        "requerant": "Non trouvé",
        "date_debut": "Non trouvé",
        "date_fin": "Non trouvé"
    }
    
    # Nettoyage : normalisation des espaces pour faciliter les regex
    texte_propre = re.sub(r'\s+', ' ', texte_complet)

    # 1. num_caso : De « BP » à « CERTIFICAT »
    match_caso = re.search(r"BP\s*(.*?)\s*CERTIFICAT", texte_propre, re.IGNORECASE)
    if match_caso:
        data["num_caso"] = match_caso.group(1).strip()

    # 2. Zones basées sur « d'attribution de la parcelle » à « , formulée »
    # On capture tout le bloc pour extraire les sous-parties
    bloc_zone = re.search(r"d'attribution de la parcelle(.*?),\s*formulée", texte_propre, re.IGNORECASE)
    if bloc_zone:
        contenu = bloc_zone.group(1)
        # Ces patterns dépendent de la structure précise entre "parcelle" et "formulée"
        # Adapté selon vos besoins :
        data["parcelle"] = contenu.strip() 
        data["section"] = contenu.strip()
        data["commune"] = contenu.strip()

    # 3. Requerant : De « , formulée le » à « a été affichée »
    match_req = re.search(r",\s*formulée\s*le\s*(.*?)\s*a\s*été\s*affichée", texte_propre, re.IGNORECASE)
    if match_req:
        data["requerant"] = match_req.group(1).strip()

    # 4. Dates : De « a été affichée » à « , par et n'a été »
    match_dates = re.search(r"a\s*été\s*affichée\s*(.*?),\s*par\s*et\s*n'a\s*été", texte_propre, re.IGNORECASE)
    if match_dates:
        # On suppose ici que les deux dates sont dans la même chaîne capturée
        data["date_debut"] = match_dates.group(1).strip()
        data["date_fin"] = match_dates.group(1).strip()

    return data