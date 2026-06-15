from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_upload_et_validation():
    files = {"files": ("test.pdf", open("test.pdf", "rb"), "application/pdf")}
    data = {"current_user": "test_admin"}
    
    response = client.post("/upload-multiple/", files=files, data=data)
    
    # --- AJOUTEZ CECI ---
    if response.status_code != 200 or response.json()["details"][0]["status"] == "error":
        print("\n--- ERREUR DÉTAILLÉE ---")
        print(response.json()) 
    # --------------------
    
    assert response.status_code == 200
    assert response.json()["details"][0]["status"] == "saved"