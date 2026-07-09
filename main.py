# -*- coding: utf-8 -*-
import math
import sqlite3
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException

# Initialisation de l'application FastAPI
app = FastAPI(title="API Commerciale QGIS - Base de Données")

DB_FILE = "abonnements.db"

def initialiser_base_de_donnees():
    """Crée la table SQLite et insère les clés de production de test."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS licences (
            cle TEXT PRIMARY KEY,
            nom_client TEXT NOT NULL,
            statut TEXT NOT NULL,
            date_expiration TEXT NOT NULL
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM licences")
    if cursor.fetchone() == 0:
        utilisateurs_test = [
            ("PRO-2026", "Utilisateur Premium", "actif", "2026-12-31"),
            ("EXPIRE-2025", "Client En Retard", "actif", "2025-05-01"),
            ("FRAUDE-XYZ", "Entreprise Bloquée", "suspendu", "2027-01-01")
        ]
        cursor.executemany("INSERT INTO licences VALUES (?, ?, ?, ?)", utilisateurs_test)
        conn.commit()
    conn.close()

# Initialisation automatique au démarrage du serveur Cloud
initialiser_base_de_donnees()

def calculer_haversine(lat1, lon1, lat2, lon2):
    """Formule mathématique de calcul de distance orthodromique réelle sur Terre."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    return round(R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))), 3)

# Configure la racine pour accepter à la fois les requêtes GET et HEAD du robot de Render
@app.get("/")
@app.head("/")
def page_daccueil():
    """Route d'accueil requise pour le suivi de santé (Health Check) de Render."""
    return {
        "status": "online", 
        "message": "Bienvenue sur l'API de calcul sécurisée pour votre plugin QGIS"
    }

# Route de calcul universelle acceptant GET et POST (avec et sans slash final) via l'URL
@app.get("/api/v1/calculer-distance")
@app.get("/api/v1/calculer-distance/")
@app.post("/api/v1/calculer-distance")
@app.post("/api/v1/calculer-distance/")
def api_calculer_distance(cle_licence: str, lat1: float, lon1: float, lat2: float, lon2: float):
    licence = cle_licence
    
    # Interrogation sécurisée de la base SQLite
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT nom_client, statut, date_expiration FROM licences WHERE cle = ?", (licence,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=403, detail="Accès refusé : Clé introuvable.")
        
    nom_client, statut, date_expiration = row
    
    if statut != "actif":
        raise HTTPException(status_code=403, detail="Accès refusé : Cet abonnement a été suspendu.")
        
    date_limite = datetime.strptime(date_expiration, "%Y-%m-%d")
    if datetime.now() > date_limite:
        raise HTTPException(status_code=403, detail=f"Accès refusé : Abonnement expiré le {date_expiration}.")
    
    # Exécution de l'algorithme métier protégé sur le Cloud
    distance_km = calculer_haversine(lat1, lon1, lat2, lon2)
    
    return {
        "status": "success",
        "client": nom_client,
        "expiration": date_expiration,
        "resultats": {
            "distance_km": distance_km, 
            "distance_metres": round(distance_km * 1000, 1)
        }
    }

if __name__ == "__main__":
    import uvicorn
    # Récupération automatique du port injecté par Render (Défaut 10000)
    port_cloud = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port_cloud)
