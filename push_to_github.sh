#!/bin/bash

# Configuration
REPO_URL="https://github.com/Gauss-Manek/caso-ocr.git"
BRANCH="main"

echo "Initialisation du dépôt Git..."
git init

echo "Ajout des fichiers..."
# On ajoute tous les fichiers, en excluant les dossiers temporaires/cache Python si nécessaire
git add .

echo "Commit initial..."
git commit -m "Initial commit: Ajout du projet OCR CASO"

echo "Configuration de la branche..."
git branch -M $BRANCH

echo "Ajout du dépôt distant..."
git remote add origin $REPO_URL

echo "Poussée vers GitHub..."
git push -u origin $BRANCH

echo "Opération terminée avec succès."