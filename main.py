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
        <title>SaaS Chiffrage Devis BTP (DA)</title>
        <style>
            body { font-family: sans-serif; background: #f8fafc; margin: 0; padding: 20px; color: #1e293b; }
            .container { max-width: 1100px; margin: 0 auto; }
            .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; }
            .btn { background: #0284c7; color: white; border: none; padding: 10px 18px; border-radius: 6px; cursor: pointer; font-weight: bold; }
            .btn-excel { background: #16a34a; display: none; margin-top: 15px; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { border: 1px solid #cbd5e1; padding: 8px; text-align: left; }
            th { background: #f1f5f9; }
            input { width: 95%; padding: 4px; }
            #status { margin-top: 10px; font-weight: bold; color: #d97706; }
            .total-box { margin-top: 15px; font-size: 1.2em; font-weight: bold; color: #0284c7; text-align: right; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h2>🏗️ Logiciel de Chiffrage Devis BTP (Dinars Algériens - DA)</h2>
                <p>Importez votre devis vierge (PDF / Image) pour chiffrer automatiquement :</p>
                <input type="file" id="devisFile" accept="image/*,application/pdf">
                <button class="btn" onclick="analyserEtChiffrer()">Lancer le Chiffrage</button>
                <div id="status"></div>
            </div>

            <div class="card">
                <h3>📋 Bordereau des Prix Unités (DA)</h3>
                <div id="containerTable">Aucun document importé.</div>
                <div id="totalGeneral" class="total-box"></div>
                <button id="btnExcel" class="btn btn-excel" onclick="exporterExcel()">📥 Exporter en Excel (.xlsx)</button>
            </div>
        </div>

        <script>
            let currentPostes = [];

            async function analyserEtChiffrer() {
                const fileInput = document.getElementById('devisFile');
                const statusDiv = document.getElementById('status');
                
                if (!fileInput.files[0]) {
                    alert("Veuillez sélectionner un fichier PDF ou Image.");
                    return;
                }

                const formData = new FormData();
                formData.append('file', fileInput.files[0]);

                statusDiv.innerText = "⏳ Extraction Gemini par partie d'édifice & application des tarifs BTP (DA)...";

                try {
                    const response = await fetch('/chiffrer-devis-vierge', { method: 'POST', body: formData });
                    const data = await response.json();
                    statusDiv.innerText = "";

                    if (data.succes) {
                        currentPostes = data.donnees;
                        afficherTableau(currentPostes);
                    } else {
                        alert("Erreur : " + data.erreur);
                    }
                } catch (err) {
                    statusDiv.innerText = "";
                    alert("Erreur serveur : " + err);
                }
            }

            function afficherTableau(postes) {
                let html = `
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 20%;">Partie Édifice / Lot</th>
                                <th style="width: 35%;">Désignation des Travaux</th>
                                <th style="width: 8%;">Qté</th>
                                <th style="width: 7%;">Unité</th>
                                <th style="width: 13%;">P.U HT (DA)</th>
                                <th style="width: 17%;">Montant HT (DA)</th>
                            </tr>
                        </thead>
                        <tbody>
                `;

                let totalGeneral = 0;

                postes.forEach((p, index) => {
                    const totalLigne = (p.quantite || 0) * (p.prix_unitaire_ht || 0);
                    totalGeneral += totalLigne;

                    html += `
                        <tr>
                            <td><input type="text" value="${p.lot || ''}" onchange="updatePoste(${index}, 'lot', this.value)"></td>
                            <td><input type="text" value="${p.designation}" onchange="updatePoste(${index}, 'designation', this.value)"></td>
                            <td><input type="number" value="${p.quantite}" onchange="updatePoste(${index}, 'quantite', this.value)"></td>
                            <td><input type="text" value="${p.unite}" onchange="updatePoste(${index}, 'unite', this.value)"></td>
                            <td><input type="number" step="0.01" value="${p.prix_unitaire_ht}" onchange="updatePoste(${index}, 'prix_unitaire_ht', this.value)"></td>
                            <td><strong>${totalLigne.toLocaleString('fr-FR', {minimumFractionDigits: 2})} DA</strong></td>
                        </tr>
                    `;
                });

                html += `</tbody></table>`;
                document.getElementById('containerTable').innerHTML = html;
                document.getElementById('totalGeneral').innerText = "TOTAL GÉNÉRAL HT : " + totalGeneral.toLocaleString('fr-FR', {minimumFractionDigits: 2}) + " DA";
                document.getElementById('btnExcel').style.display = 'block';
            }

            function updatePoste(index, field, value) {
                if (field === 'quantite' || field === 'prix_unitaire_ht') {
                    currentPostes[index][field] = parseFloat(value) || 0;
                    currentPostes[index]['montant_ht'] = currentPostes[index]['quantite'] * currentPostes[index]['prix_unitaire_ht'];
                } else {
                    currentPostes[index][field] = value;
                }
                afficherTableau(currentPostes);
            }

            async function exporterExcel() {
                if (!currentPostes || currentPostes.length === 0) return;

                try {
                    const response = await fetch('/exporter-excel', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(currentPostes)
                    });

                    if (!response.ok) {
                        alert("Erreur lors de l'exportation.");
                        return;
                    }

                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = "Devis_Chiffre_BTP_DA.xlsx";
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                } catch (err) {
                    alert("Erreur technique : " + err);
                }
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