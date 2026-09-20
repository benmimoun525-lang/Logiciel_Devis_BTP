import os
import io
import json
import time
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Body, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from google.genai.errors import APIError
from supabase import create_client, Client

load_dotenv()

# Initialisation des clients
ai_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(api_version='v1beta')
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("⚠️ SUPABASE_URL et SUPABASE_KEY doivent être définies dans .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="SaaS Chiffrage BTP - Algérie (DA)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROMPT_EXTRACTION_VIERGE = """
Tu es un métreur expert en BTP en Algérie.
Analyse ce devis, bordereau de prix ou CPT/DQE.

Pour chaque article, identifie la partie de l'édifice (lot/chapitre) dans laquelle il se trouve (ex: Fondations, Superstructure, Maçonnerie, Étanchéité).
Rassemble le contexte complet pour que la désignation soit explicite (ex: si l'article dit juste "Béton armé" dans la section "Semelles", la désignation finale doit être "Béton armé dosé à 350 kg/m3 pour semelles de fondation").

Extrais une liste JSON stricte contenant :
- "lot": La partie de l'édifice / chapitre (ex: Fondations & Infrastructure)
- "designation": La description complète et contextualisée de l'article
- "quantite": La quantité demandée (nombre, 0 si absente)
- "unite": L'unité de mesure (m2, m3, ml, kg, ens, u, etc.)

Renvoie UNIQUEMENT un tableau JSON valide.
"""

def trouver_prix_unitaire_supabase(designation_extraite: str, lot_extrait: str = "") -> float:
    """Recherche le prix unitaire en tenant compte du contexte de l'édifice."""
    try:
        res = supabase.table("articles_prix").select("prix_unitaire_ht, designation, categorie").execute()
        catalogue = res.data
        
        if not catalogue or not designation_extraite:
            return 0.0

        texte_complet = f"{lot_extrait} {designation_extraite}".lower()
        
        mots_inutiles = {
            "pour", "avec", "dans", "sans", "sous", "sur", "les", "des", "une", 
            "d'un", "d'une", "pose", "fourniture", "et", "de", "du", "la", "le", 
            "en", "au", "aux", "y", "compris", "toutes", "servitudes", "exécution"
        }
        
        mots_clef = [m for m in texte_complet.replace("'", " ").replace(",", " ").split() if len(m) > 2 and m not in mots_inutiles]

        if not mots_clef:
            return 0.0

        meilleur_prix = 0.0
        max_score = 0

        for article in catalogue:
            desig_art = f"{article.get('categorie', '')} {article['designation']}".lower()
            
            score = sum(1 for m in mots_clef if m in desig_art)

            if score > max_score:
                max_score = score
                meilleur_prix = float(article["prix_unitaire_ht"])

        return meilleur_prix if max_score >= 1 else 0.0
    except Exception as e:
        print(f"❌ Erreur Supabase : {e}")
        return 0.0

@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Logiciel de Devis BTP (Dinars Algériens)</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 15px; max-width: 900px; color: #333; background-color: #f4f6f9; }
            .box { border: 1px solid #e0e0e0; padding: 20px; border-radius: 8px; background: #fff; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
            textarea { width: 100%; height: 100px; padding: 10px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
            button { background-color: #007bff; color: white; padding: 12px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; margin-top: 10px; font-weight: bold; }
            button:hover { background-color: #0056b3; }
            .btn-whatsapp { background-color: #25D366; color: white; }
            .btn-whatsapp:hover { background-color: #128C7E; }
            .btn-secondary { background-color: #6c757d; font-size: 13px; padding: 6px 12px; margin-top: 5px; }
            
            /* Zone d'aperçu du document WhatsApp */
            #preview-container { margin-top: 15px; display: none; text-align: center; background: #eaeff2; padding: 15px; border: 2px dashed #25D366; border-radius: 8px; }
            #preview-img { max-width: 100%; max-height: 550px; border-radius: 5px; border: 1px solid #ccc; transition: transform 0.3s ease; }
            #preview-pdf { width: 100%; height: 500px; border: none; }

            #resultat { margin-top: 20px; white-space: pre-wrap; background: #fff; padding: 20px; border: 1px solid #ddd; border-radius: 5px; font-family: monospace; font-size: 14px; }
            
            @media print {
                .no-print { display: none !important; }
                body { margin: 0; padding: 0; background: #fff; }
                #resultat { border: none; padding: 0; font-family: Arial, sans-serif; }
            }
        </style>
    </head>
    <body>
        <div class="no-print">
            <h2>📱 Logiciel de chiffrage devis BTP (Dinars Algériens)</h2>
            
            <!-- SECTION IMPORT DOCUMENT WHATSAPP -->
            <div class="box">
                <h3>1. Importer un document client (Photo / Document WhatsApp)</h3>
                <p style="font-size: 13px; color: #666;">Sélectionnez directement la photo ou le fichier PDF reçu sur WhatsApp :</p>
                <input type="file" id="fileInput" accept="image/*,application/pdf,.webp" onchange="afficherApercu(event)"><br>
                
                <!-- Zone d'aperçu automatique pour WhatsApp -->
                <div id="preview-container">
                    <p style="margin-top:0; font-weight:bold; color: #075e54;">📄 Document / Photo WhatsApp chargé :</p>
                    <img id="preview-img" style="display:none;" />
                    <iframe id="preview-pdf" style="display:none;"></iframe>
                    
                    <div id="image-controls" style="display:none; margin-top: 10px;">
                        <button class="btn-secondary" onclick="tournerImage()">🔄 Tourner l'image (90°)</button>
                    </div>
                </div>

                <button class="btn-whatsapp" onclick="lancerChiffrageAutomatique()">🚀 Lancer le chiffrage automatique</button>
            </div>

            <!-- SECTION DESCRIPTION MANUELLE -->
            <div class="box">
                <h3>2. Ou saisissez/complétez la description des travaux :</h3>
                <textarea id="description" placeholder="Ex: Réalisation de 50 m² de faux plafond BA13 et 120 m² de peinture vinylique..."></textarea><br>
                <button onclick="genererDevisTexte()">Chiffrer via le texte</button>
            </div>

            <button id="btnPrint" style="display:none; background-color: #17a2b8;" onclick="window.print()">📄 Imprimer / Sauvegarder en PDF</button>
        </div>

        <div id="resultat">En attente d'un document ou d'une description...</div>

        <script>
            let rotationAngle = 0;

            function afficherApercu(event) {
                const file = event.target.files[0];
                const container = document.getElementById('preview-container');
                const img = document.getElementById('preview-img');
                const pdf = document.getElementById('preview-pdf');
                const controls = document.getElementById('image-controls');

                if (!file) {
                    container.style.display = 'none';
                    return;
                }

                container.style.display = 'block';
                rotationAngle = 0;
                img.style.transform = 'rotate(0deg)';
                const fileURL = URL.createObjectURL(file);

                if (file.type.startsWith('image/') || file.name.endsWith('.webp')) {
                    pdf.style.display = 'none';
                    img.src = fileURL;
                    img.style.display = 'inline-block';
                    controls.style.display = 'block';
                } else if (file.type === 'application/pdf') {
                    img.style.display = 'none';
                    controls.style.display = 'none';
                    pdf.src = fileURL;
                    pdf.style.display = 'block';
                }
            }

            function tournerImage() {
                const img = document.getElementById('preview-img');
                rotationAngle = (rotationAngle + 90) % 360;
                img.style.transform = `rotate(${rotationAngle}deg)`;
            }

            async function genererDevisTexte() {
                const desc = document.getElementById('description').value;
                const resDiv = document.getElementById('resultat');
                const btnPrint = document.getElementById('btnPrint');
                
                if (!desc) { alert('Veuillez entrer une description des travaux.'); return; }

                resDiv.innerText = "Génération du devis en cours via Gemini et Supabase...";
                btnPrint.style.display = "none";

                try {
                    const response = await fetch('/generate-devis', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ description: desc })
                    });
                    const data = await response.json();

                    if (data.status === 'success') {
                        resDiv.innerText = data.devis;
                        btnPrint.style.display = "inline-block";
                    } else {
                        resDiv.innerText = "Erreur : " + (data.detail || "Échec de la génération");
                    }
                } catch (err) {
                    resDiv.innerText = "Erreur de connexion avec le serveur.";
                }
            }

            function lancerChiffrageAutomatique() {
                const fileInput = document.getElementById('fileInput');
                if (!fileInput.files[0]) {
                    alert('Veuillez d\'abord sélectionner un fichier ou une photo WhatsApp.');
                    return;
                }
                alert('Traitement du document WhatsApp par analyse visuelle Gemini en cours d\'intégration...');
            }
        </script>
    </body>
    </html>
    """

@app.post("/chiffrer-devis-vierge")
async def chiffrer_devis_vierge(file: UploadFile = File(...)):
    try:
        content = await file.read()
        
        max_retries = 3
        retry_delay = 2
        response = None

        for attempt in range(max_retries):
            try:
                response = ai_client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[
                        types.Part.from_bytes(data=content, mime_type=file.content_type),
                        PROMPT_EXTRACTION_VIERGE
                    ]
                )
                break
            except APIError as e:
                if e.code == 503 and attempt < max_retries - 1:
                    print(f"⚠️ Serveur Gemini saturé (503). Tentative {attempt + 1}/{max_retries} dans {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise e

        if not response or not response.text:
            return {"succes": False, "erreur": "L'IA n'a renvoyé aucune réponse."}

        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        lignes_vierges = json.loads(raw_text)
        
        lignes_chiffrees = []
        for ligne in lignes_vierges:
            pu_bdd = trouver_prix_unitaire_supabase(
                ligne.get("designation", ""), 
                ligne.get("lot", "")
            )
            qte = float(ligne.get("quantite", 0))
            
            lignes_chiffrees.append({
                "lot": ligne.get("lot", "Général"),
                "designation": ligne.get("designation", ""),
                "quantite": qte,
                "unite": ligne.get("unite", ""),
                "prix_unitaire_ht": pu_bdd,
                "montant_ht": round(qte * pu_bdd, 2)
            })
        
        return {"succes": True, "donnees": lignes_chiffrees}

    except APIError as e:
        if e.code == 503:
            return {
                "succes": False, 
                "erreur": "Le service de Google Gemini est momentanément très sollicité. Veuillez réessayer dans quelques secondes."
            }
        return {"succes": False, "erreur": f"Erreur API Gemini : {e.message}"}
    except Exception as e:
        return {"succes": False, "erreur": f"Erreur serveur : {str(e)}"}

@app.post("/exporter-excel")
async def exporter_excel(postes: list = Body(...)):
    try:
        if not postes:
            return {"succes": False, "erreur": "Aucune donnée reçue."}

        df = pd.DataFrame(postes)
        
        colonnes_map = {
            "lot": "Partie de l'Édifice / Lot",
            "designation": "Désignation des travaux",
            "quantite": "Quantité",
            "unite": "Unité",
            "prix_unitaire_ht": "Prix Unitaire HT (DA)",
            "montant_ht": "Montant Total HT (DA)"
        }
        df = df.rename(columns=colonnes_map)

        total_ht = float(df["Montant Total HT (DA)"].sum()) if "Montant Total HT (DA)" in df.columns else 0.0
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Devis Quantitatif DA')
            sheet = writer.sheets['Devis Quantitatif DA']
            sheet.append([])
            sheet.append(["TOTAL GÉNÉRAL HT (DA)", "", "", "", "", total_ht])

        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=Devis_Chiffre_BTP_DA.xlsx"
            }
        )
    except Exception as e:
        return {"succes": False, "erreur": str(e)}