from extraction import affiner_extraction

def test_extraction_pdf():
    # Remplacez par le chemin vers votre fichier test.pdf
    resultat = affiner_extraction("test.pdf")
    
    print("\n--- Résultats de l'extraction ---")
    for cle, valeur in resultat.items():
        print(f"{cle}: {valeur}")
        
    # Assertions pour valider que le regex trouve bien les données
    assert resultat["num_caso"] != "Non trouvé"
    assert "126" in resultat["parcelle"]  # Vérification basée sur votre PDF
    assert "Bernadette NKE AVA" in resultat["requerant"]