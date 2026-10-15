import os
import json
import uuid
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
from database import get_connection, init_db

app = FastAPI(title="AutoCote - Recherche de Véhicules & Cote Marché", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
uploads_dir = os.path.join(static_dir, "uploads")
os.makedirs(uploads_dir, exist_ok=True)

@app.on_event("startup")
def startup_event():
    init_db()

class VehiculeCreate(BaseModel):
    marque: str
    modele: str
    version: Optional[str] = ""
    annee: int
    prix: float
    prix_marche_estime: Optional[float] = None
    kilometrage: int
    carburant: str
    boite: str
    couleur: Optional[str] = "Non précisée"
    wilaya: str
    papiers: Optional[str] = "Carte Grise (Safia)"
    sbigha: Optional[str] = "00 Peinture (Tôle d'origine)"
    vendeur_nom: str
    vendeur_type: Optional[str] = "Particulier"
    vendeur_tel: str
    vendeur_whatsapp: Optional[str] = None
    vendeur_email: Optional[str] = None
    reference_annonce: Optional[str] = None
    photo_principale: str
    photos_liste: Optional[List[str]] = []
    description: Optional[str] = ""

# API: Upload de vraies photos depuis l'ordinateur
@app.post("/api/upload")
async def upload_photos(fichiers: List[UploadFile] = File(...)):
    urls = []
    for f in fichiers:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp", ".avif"]:
            ext = ".jpg"
        nom_fichier = f"{uuid.uuid4().hex[:12]}{ext}"
        chemin_sauvegarde = os.path.join(uploads_dir, nom_fichier)
        
        contenu = await f.read()
        with open(chemin_sauvegarde, "wb") as out:
            out.write(contenu)
            
        urls.append(f"/static/uploads/{nom_fichier}")
        
    return {"urls": urls}

# API: Liste des marques avec statistiques
@app.get("/api/marques")
def get_marques():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT marque, COUNT(*) as nb_vehicules, MIN(prix) as min_prix, MAX(prix) as max_prix
        FROM vehicules
        GROUP BY marque
        ORDER BY nb_vehicules DESC, marque ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [{"marque": r["marque"], "count": r["nb_vehicules"], "min_prix": r["min_prix"], "max_prix": r["max_prix"]} for r in rows]

# API: Modèles pour une marque donnée
@app.get("/api/modeles")
def get_modeles(marque: str = Query(..., description="Marque sélectionnée")):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT modele, COUNT(*) as nb_vehicules, MIN(prix) as min_prix, MAX(prix) as max_prix, MIN(annee) as min_annee, MAX(annee) as max_annee
        FROM vehicules
        WHERE LOWER(marque) = LOWER(?)
        GROUP BY modele
        ORDER BY nb_vehicules DESC, modele ASC
    """, (marque,))
    rows = cursor.fetchall()
    conn.close()
    return [{
        "modele": r["modele"],
        "count": r["nb_vehicules"],
        "min_prix": r["min_prix"],
        "max_prix": r["max_prix"],
        "min_annee": r["min_annee"],
        "max_annee": r["max_annee"]
    } for r in rows]

# API: Années disponibles pour un modèle
@app.get("/api/annees")
def get_annees(marque: str = Query(...), modele: str = Query(...)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT annee, COUNT(*) as count, AVG(prix) as prix_moyen
        FROM vehicules
        WHERE LOWER(marque) = LOWER(?) AND LOWER(modele) = LOWER(?)
        GROUP BY annee
        ORDER BY annee DESC
    """, (marque, modele))
    rows = cursor.fetchall()
    conn.close()
    return [{
        "annee": r["annee"],
        "count": r["count"],
        "prix_moyen": round(r["prix_moyen"], 2)
    } for r in rows]

# API: Cote et baromètre du marché
@app.get("/api/cote-marche")
def get_cote_marche(
    marque: str = Query(...),
    modele: Optional[str] = Query(None),
    annee: Optional[int] = Query(None)
):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT prix, prix_marche_estime, kilometrage FROM vehicules WHERE LOWER(marque) = LOWER(?)"
    params = [marque]
    
    if modele:
        query += " AND LOWER(modele) = LOWER(?)"
        params.append(modele)
    if annee:
        query += " AND annee = ?"
        params.append(annee)
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return {
            "trouve": False,
            "message": "Pas assez de données pour établir une cote précise."
        }
    
    prix_list = [r["prix"] for r in rows]
    estime_list = [r["prix_marche_estime"] for r in rows if r["prix_marche_estime"]]
    
    avg_prix = sum(prix_list) / len(prix_list)
    min_prix = min(prix_list)
    max_prix = max(prix_list)
    
    cote_officielle = (sum(estime_list) / len(estime_list)) if estime_list else avg_prix
    
    fourchette_basse = round(cote_officielle * 0.93)
    fourchette_haute = round(cote_officielle * 1.07)
    
    return {
        "trouve": True,
        "nb_echantillons": len(rows),
        "cote_marche": round(cote_officielle),
        "prix_moyen": round(avg_prix),
        "fourchette_basse": fourchette_basse,
        "fourchette_haute": fourchette_haute,
        "prix_min_constate": min_prix,
        "prix_max_constate": max_prix
    }

# API: Recherche filtrée des annonces
@app.get("/api/vehicules")
def search_vehicules(
    marque: Optional[str] = None,
    modele: Optional[str] = None,
    annee: Optional[int] = None,
    annee_min: Optional[int] = None,
    annee_max: Optional[int] = None,
    prix_min: Optional[float] = None,
    prix_max: Optional[float] = None,
    km_max: Optional[int] = None,
    carburant: Optional[str] = None,
    boite: Optional[str] = None,
    wilaya: Optional[str] = None,
    search: Optional[str] = None,
    tri: Optional[str] = "bonne_affaire"
):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM vehicules WHERE 1=1"
    params = []
    
    if marque and marque.strip():
        query += " AND LOWER(marque) = LOWER(?)"
        params.append(marque.strip())
        
    if modele and modele.strip():
        query += " AND LOWER(modele) = LOWER(?)"
        params.append(modele.strip())
        
    if annee:
        query += " AND annee = ?"
        params.append(annee)
    else:
        if annee_min:
            query += " AND annee >= ?"
            params.append(annee_min)
        if annee_max:
            query += " AND annee <= ?"
            params.append(annee_max)
            
    if prix_min is not None:
        query += " AND prix >= ?"
        params.append(prix_min)
        
    if prix_max is not None:
        query += " AND prix <= ?"
        params.append(prix_max)
        
    if km_max is not None:
        query += " AND kilometrage <= ?"
        params.append(km_max)
        
    if carburant and carburant.strip():
        query += " AND LOWER(carburant) LIKE LOWER(?)"
        params.append(f"%{carburant.strip()}%")
        
    if boite and boite.strip():
        query += " AND LOWER(boite) LIKE LOWER(?)"
        params.append(f"%{boite.strip()}%")
        
    if wilaya and wilaya.strip():
        query += " AND LOWER(wilaya) LIKE LOWER(?)"
        params.append(f"%{wilaya.strip()}%")
        
    if search and search.strip():
        query += " AND (LOWER(marque) LIKE LOWER(?) OR LOWER(modele) LIKE LOWER(?) OR LOWER(description) LIKE LOWER(?))"
        kw = f"%{search.strip()}%"
        params.extend([kw, kw, kw])
        
    if tri == "prix_asc":
        query += " ORDER BY prix ASC"
    elif tri == "prix_desc":
        query += " ORDER BY prix DESC"
    elif tri == "km_asc":
        query += " ORDER BY kilometrage ASC"
    elif tri == "annee_desc":
        query += " ORDER BY annee DESC"
    elif tri == "bonne_affaire":
        query += " ORDER BY (prix_marche_estime - prix) DESC"
    else:
        query += " ORDER BY id DESC"
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for r in rows:
        d = dict(r)
        
        # Décoder la liste des photos réelles
        photos = []
        if d.get("photos_liste"):
            try:
                photos = json.loads(d["photos_liste"])
            except Exception:
                photos = [d["photo_principale"]]
        if not photos:
            photos = [d["photo_principale"]]
        d["photos"] = photos
        
        # Qualification financière
        ecart = d["prix"] - d["prix_marche_estime"]
        ratio = (ecart / d["prix_marche_estime"]) * 100
        
        if ratio <= -4:
            d["statut_prix"] = "Bonne Affaire"
            d["statut_badge_class"] = "bg-emerald-500 text-white"
            d["statut_detail"] = f"-{abs(round(ratio))}% sous la cote"
        elif ratio >= 4:
            d["statut_prix"] = "Au-dessus du marché"
            d["statut_badge_class"] = "bg-amber-500 text-white"
            d["statut_detail"] = f"+{round(ratio)}% au-dessus"
        else:
            d["statut_prix"] = "Prix du Marché"
            d["statut_badge_class"] = "bg-blue-600 text-white"
            d["statut_detail"] = "Conforme à la cote"
            
        result.append(d)
        
    return result

# API: Détail d'un véhicule
@app.get("/api/vehicules/{vehicule_id}")
def get_vehicule_detail(vehicule_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vehicules WHERE id = ?", (vehicule_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Véhicule introuvable")
        
    d = dict(row)
    photos = []
    if d.get("photos_liste"):
        try:
            photos = json.loads(d["photos_liste"])
        except Exception:
            photos = [d["photo_principale"]]
    if not photos:
        photos = [d["photo_principale"]]
    d["photos"] = photos

    ecart = d["prix"] - d["prix_marche_estime"]
    ratio = (ecart / d["prix_marche_estime"]) * 100
    if ratio <= -4:
        d["statut_prix"] = "Bonne Affaire"
        d["statut_badge_class"] = "bg-emerald-500 text-white"
    elif ratio >= 4:
        d["statut_prix"] = "Au-dessus du marché"
        d["statut_badge_class"] = "bg-amber-500 text-white"
    else:
        d["statut_prix"] = "Prix du Marché"
        d["statut_badge_class"] = "bg-blue-600 text-white"
        
    return d

# API: Ajouter une annonce avec support multi-photos
@app.post("/api/vehicules")
def create_vehicule(vehicule: VehiculeCreate):
    conn = get_connection()
    cursor = conn.cursor()
    
    ref = vehicule.reference_annonce
    if not ref:
        import time
        ref = f"OK-{vehicule.marque[:3].upper()}-{vehicule.annee}-{int(time.time()) % 10000}"
        
    cote = vehicule.prix_marche_estime
    if not cote:
        cursor.execute("SELECT AVG(prix) as m FROM vehicules WHERE LOWER(marque) = LOWER(?) AND LOWER(modele) = LOWER(?)", 
                       (vehicule.marque, vehicule.modele))
        r = cursor.fetchone()
        cote = r["m"] if r and r["m"] else vehicule.prix
        
    photos_json = json.dumps(vehicule.photos_liste if vehicule.photos_liste else [vehicule.photo_principale])
    
    try:
        cursor.execute("""
        INSERT INTO vehicules (
            marque, modele, version, annee, prix, prix_marche_estime, kilometrage,
            carburant, boite, couleur, wilaya, papiers, sbigha, vendeur_nom, vendeur_type,
            vendeur_tel, vendeur_whatsapp, vendeur_email, reference_annonce,
            photo_principale, photos_liste, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vehicule.marque, vehicule.modele, vehicule.version, vehicule.annee, vehicule.prix,
            cote, vehicule.kilometrage, vehicule.carburant, vehicule.boite,
            vehicule.couleur, vehicule.wilaya, vehicule.papiers, vehicule.sbigha,
            vehicule.vendeur_nom, vehicule.vendeur_type, vehicule.vendeur_tel, vehicule.vendeur_whatsapp,
            vehicule.vendeur_email, ref, vehicule.photo_principale, photos_json, vehicule.description
        ))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return {"success": True, "id": new_id, "reference": ref}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))

# API: Supprimer un véhicule
@app.delete("/api/vehicules/{vehicule_id}")
def delete_vehicule(vehicule_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vehicules WHERE id = ?", (vehicule_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Véhicule supprimé"}

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Interface web en cours de chargement..."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8050, reload=True)
