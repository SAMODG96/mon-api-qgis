# -*- coding: utf-8 -*-
import math
import sqlite3
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException

app = FastAPI(title="API Commerciale QGIS - Production")

# SÉCURITÉ CLOUD : Utilisation du dossier /tmp de Linux pour autoriser l'écriture
DB_FILE = "/tmp/abonnements.db"

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
    
    # Nettoyage et réinsertion propre à chaque démarrage pour le mode Test
    cursor.execute("DELETE FROM licences")
    utilisateurs_test = [
        ("PRO-2026", "Utilisateur Premium", "actif", "2026-12-31"),
        ("EXPIRE-2025", "Client En Retard", "actif", "2025-05-01"),
        ("FRAUDE-XYZ", "Entreprise Bloquée", "suspendu", "2027-01-01")
    ]
    cursor.executemany("INSERT INTO licences VALUES (?, ?, ?, ?)", utilisateurs_test)
    conn.commit()
    conn.close()
    print("Base de données initialisée avec succès dans /tmp")

# Initialisation automatique au démarrage du serveur Cloud
initialiser_base_de_donnees()

def calculer_haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    return round(R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))), 3)

@app.get("/")
@app.head("/")
def page_daccueil():
    return {"status": "online", "message": "API QGIS active"}

@app.get("/api/v1/calculer-distance")
@app.get("/api/v1/calculer-distance/")
def api_calculer_distance(cle_licence: str, lat1: float, lon1: float, lat2: float, lon2: float):
    licence = cle_licence.strip()
    
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
    port_cloud = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port_cloud)
