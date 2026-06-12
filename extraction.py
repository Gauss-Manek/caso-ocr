import re

def affiner_extraction(texte_complet):
    data = {
        "num_caso": "Non trouvé", 
        "parcelle": "Non trouvé", 
        "section": "Non trouvé",
        "commune": "Non trouvé", 
        "date_debut": "Non trouvé", 
        "date_fin": "Non trouvé", 
        "requerant": "Non trouvé"
    }
    
    # Extraction du numéro CASO
    match_caso = re.search(r"(?:N[°\?]|N°)\s*([\d\s]+)", texte_complet, re.IGNORECASE)
    if match_caso:
        data["num_caso"] = match_caso.group(1).strip()
        
    # Extraction des données cadastrales (parcelle, section, commune)
    match_parcelle = re.search(r"parcelle\s*n[°\?]?\s*([\w\d]+)\s+de\s+la\s+section\s+([\w\d]+)\s+du\s+plan\s+cadastral\s+d['\s]([\w\s]+?),", texte_complet, re.IGNORECASE)
    if match_parcelle:
        data["parcelle"] = match_parcelle.group(1).strip()
        data["section"] = match_parcelle.group(2).strip()
        data["commune"] = match_parcelle.group(3).strip()
        
    # Extraction des dates d'affichage
    match_dates = re.search(r"affichée\s+du\s+(.*?)\s+au\s+(.*?)\s+inclus", texte_complet, re.IGNORECASE)
    if match_dates:
        data["date_debut"] = match_dates.group(1).strip()
        data["date_fin"] = match_dates.group(2).strip()
        
    # CORRECTION : Ajout de \. et $ pour intercepter la fin de phrase ou de chaîne
    match_req = re.search(r"par\s+(Madame|Monsieur.*?)(?:\.|;|\d|\bet\b|$)", texte_complet, re.IGNORECASE)
    if match_req:
        data["requerant"] = match_req.group(1).strip()
        
    return data