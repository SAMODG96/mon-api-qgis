# -*- coding: utf-8 -*-
import math
import sqlite3
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="API Commerciale QGIS - Base de Données")

DB_FILE = "abonnements.db"

def initialiser_base_de_donnees():
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

initialiser_base_de_donnees()

class DemandeCalculDistance(BaseModel):
    cle_licence: str
    lat1: float
    lon1: float
    lat2: float
    lon2: float

def calculer_haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi, delta_lambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    return round(R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))), 3)

# Double enregistrement des routes pour accepter les requêtes avec ou sans slash final
@app.post("/api/v1/calculer-distance")
@app.post("/api/v1/calculer-distance/")
def api_calculer_distance(donnees: DemandeCalculDistance):
    licence = donnees.cle_licence
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT nom_client, statut, date_expiration FROM licences WHERE cle = ?", (licence,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=403, detail="Accès refusé : Clé introuvable.")
        
    nom_client, statut, date_expiration = row
    
    if statut != "actif":
        raise HTTPException(status_code=403, detail="Accès refusé : Abonnement suspendu.")
        
    date_limite = datetime.strptime(date_expiration, "%Y-%m-%d")
    if datetime.now() > date_limite:
        raise HTTPException(status_code=403, detail=f"Accès refusé : Expire le {date_expiration}.")
    
    distance_km = calculer_haversine(donnees.lat1, donnees.lon1, donnees.lat2, donnees.lon2)
    
    return {
        "status": "success",
        "client": nom_client,
        "expiration": date_expiration,
        "resultats": {"distance_km": distance_km, "distance_metres": round(distance_km * 1000, 1)}
    }

if __name__ == "__main__":
    import uvicorn
    # CORRECTION : Récupère automatiquement le port 10000 imposé par Render
    port_cloud = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port_cloud)
