import os
import logging
import time
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from google.genai.errors import APIError
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="API Devis BTP", version="1.7.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

supabase_client: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)


class DevisRequest(BaseModel):
    description: str


def call_gemini_with_fallback(contents):
    """
    Appelle Gemini avec réessais en cas d'erreur 503 et bascule de modèle si nécessaire.
    """
    if not gemini_client:
        raise HTTPException(status_code=500, detail="Client Gemini non disponible.")

    models_to_try = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.5-pro"]
    
    for model_name in models_to_try:
        for attempt in range(2):
            try:
                logging.info(f"Tentative de génération avec {model_name} (essai {attempt + 1})...")
                response = gemini_client.models.generate_content(
                    model=model_name,
                    contents=contents
                )
                return response.text
            except APIError as e:
                if e.code in [503, 429]:
                    logging.warning(f"Surcharge détectée sur {model_name} (Code {e.code}). Pause de 2s...")
                    time.sleep(2)
                    continue
                else:
                    logging.error(f"Erreur API avec {model_name}: {str(e)}")
                    break
            except Exception as e:
                logging.error(f"Erreur inattendue avec {model_name}: {str(e)}")
                break

    raise HTTPException(
        status_code=503, 
        detail="Les serveurs d'IA sont actuellement très sollicités. Veuillez réespayer dans quelques instants."
    )


def get_catalogue_prix_supabase() -> str:
    if not supabase_client:
        return "Aucune base de prix externe disponible."
    try:
        response = supabase_client.table("prix_unitaires").select(
            "code_article, categorie, designation, unite, prix_unitaire_ht"
        ).execute()
        articles = response.data
        if not articles:
            return "La table des prix unitaires est vide."
        catalogue_text = "CATALOGUE DES PRIX UNITAIRES DE RÉFÉRENCE EN DINARS ALGÉRIENS (SUPABASE) :\n"
        for art in articles:
            catalogue_text += (
                f"- [{art.get('code_article', 'N/A')}] {art.get('designation')} "
                f"({art.get('categorie', 'Général')}) : {art.get('prix_unitaire_ht')} DA HT / {art.get('unite')}\n"
            )
        return catalogue_text
    except Exception as e:
        logging.error(f"Erreur Supabase : {str(e)}")
        return "Impossible de charger la base de prix officielle pour le moment."


@app.get("/", response_class=HTMLResponse)
def read_root():
    return """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Logiciel de Devis BTP</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 15px; max-width: 900px; color: #333; background-color: #f4f6f9; }
        .box { border: 1px solid #e0e0e0; padding: 20px; border-radius: 8px; background: #fff; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        textarea { width: 100%; height: 100px; padding: 10px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        button { background-color: #007bff; color: white; padding: 12px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; margin-top: 10px; font-weight: bold; }
        button:hover { background-color: #0056b3; }
        .btn-whatsapp { background-color: #25D366; color: white; }
        .btn-whatsapp:hover { background-color: #128C7E; }
        .btn-secondary { background-color: #6c757d; font-size: 13px; padding: 6px 12px; margin-top: 5px; }
        #preview-container { margin-top: 15px; display: none; text-align: center; background: #eaeff2; padding: 15px; border: 2px dashed #25D366; border-radius: 8px; }
        #preview-img { max-width: 100%; max-height: 550px; border-radius: 5px; border: 1px solid #ccc; }
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
        
        <div class="box">
            <h3>1. Importer un document client (Photo / Document WhatsApp)</h3>
            <p style="font-size: 13px; color: #666;">Sélectionnez la photo ou le fichier PDF reçu sur WhatsApp :</p>
            <input type="file" id="fileInput" accept="image/*,application/pdf,.webp"><br>
            
            <div id="preview-container">
                <p style="margin-top:0; font-weight:bold; color: #075e54;">📄 Document / Photo WhatsApp chargé :</p>
                <img id="preview-img" style="display:none;" />
                <iframe id="preview-pdf" style="display:none;"></iframe>
                <div id="image-controls" style="display:none; margin-top: 10px;">
                    <button type="button" class="btn-secondary" id="btnRotate">🔄 Tourner l'image (90°)</button>
                </div>
            </div>

            <button type="button" class="btn-whatsapp" id="btnChiffrerAuto">🚀 Lancer le chiffrage automatique</button>
        </div>

        <div class="box">
            <h3>2. Ou saisissez/complétez la description des travaux :</h3>
            <textarea id="description" placeholder="Ex: Réalisation de 50 m² de faux plafond BA13 et 120 m² de peinture vinylique..."></textarea><br>
            <button type="button" id="btnChiffrerTexte">Chiffrer via le texte</button>
        </div>

        <button id="btnPrint" style="display:none; background-color: #17a2b8;" onclick="window.print()">📄 Imprimer / Sauvegarder en PDF</button>
    </div>

    <div id="resultat">En attente d'un document ou d'une description...</div>

    <script>
        let rotationAngle = 0;

        document.addEventListener("DOMContentLoaded", function() {
            const fileInput = document.getElementById('fileInput');
            const btnRotate = document.getElementById('btnRotate');
            const btnChiffrerAuto = document.getElementById('btnChiffrerAuto');
            const btnChiffrerTexte = document.getElementById('btnChiffrerTexte');

            fileInput.addEventListener('change', afficherApercu);
            btnRotate.addEventListener('click', tournerImage);
            btnChiffrerAuto.addEventListener('click', lancerChiffrageAutomatique);
            btnChiffrerTexte.addEventListener('click', genererDevisTexte);
        });

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
            img.style.transform = "rotate(" + rotationAngle + "deg)";
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

        async function lancerChiffrageAutomatique() {
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            const resDiv = document.getElementById('resultat');
            const btnPrint = document.getElementById('btnPrint');

            if (!file) {
                alert("Veuillez d'abord sélectionner un fichier ou une photo WhatsApp.");
                return;
            }

            resDiv.innerText = "Analyse de la forme et du contenu du document par l'IA...";
            btnPrint.style.display = "none";

            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch('/generate-devis-file', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();

                if (data.status === 'success') {
                    resDiv.innerText = data.devis;
                    btnPrint.style.display = "inline-block";
                } else {
                    resDiv.innerText = "Erreur : " + (data.detail || "Échec de l'analyse du document");
                }
            } catch (err) {
                resDiv.innerText = "Erreur lors de l'envoi du fichier au serveur.";
            }
        }
    </script>
</body>
</html>"""


@app.post("/generate-devis")
async def generate_devis(request: DevisRequest):
    catalogue_prix = get_catalogue_prix_supabase()
    prompt = f"""
Tu es un métré et économiste de la construction BTP expert sur le marché algérien.
Ta mission est de générer un devis estimatif précis et structuré en DINARS ALGÉRIENS (DA).

---
{catalogue_prix}
---

CONSIGNES STRICTES :
1. TOUS LES PRIX DOIVENT ÊTRE EXPRIMÉS EN DINARS ALGÉRIENS (DA).
2. Pour chaque prestation requise, vérifie si l'article existe dans le CATALOGUE DES PRIX ci-dessus.
3. Si l'article figure dans le catalogue, réutilise son prix unitaire HT en DA et son unité.
4. Si un article est absent, estime son prix unitaire en DA selon les tarifs actuels du marché BTP en Algérie avec la mention "(Prix estimé du marché DA)".
5. Présente le résultat sous forme de tableau (Désignation, Quantité, Unité, PU HT DA, Total HT DA).
6. Calcule ensuite : Total Général HT (DA), TVA (19%) (DA), Total TTC (DA).

DESCRIPTION DU BESOIN CLIENT :
{request.description}
"""
    try:
        devis_genere = call_gemini_with_fallback(prompt)
        if supabase_client:
            supabase_client.table("devis").insert({
                "description_initiale": request.description,
                "devis_genere": devis_genere
            }).execute()
        return {"status": "success", "devis": devis_genere}
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-devis-file")
async def generate_devis_file(file: UploadFile = File(...)):
    catalogue_prix = get_catalogue_prix_supabase()
    file_bytes = await file.read()

    mime_type = file.content_type or "image/jpeg"
    if file.filename.endswith(".webp"):
        mime_type = "image/webp"

    prompt = f"""
Tu es un expert métré et métreur-vérificateur BTP en Algérie.
Analyse visuellement le document fourni (photo manuscrite, document scanné, ou capture WhatsApp).

---
RÈGLE D'OR DE RESTITUTION VISUELLE ET STRUCTURELLE :
- RESPECTE STRICTEMENT LA FORME DU DOCUMENT REÇU.
- Si le document d'origine est un TABLEAU : restitué sous forme de TABLEAU complet en conservant toutes ses colonnes initiales et en complétant/ajoutant les colonnes de chiffrage en Dinars Algériens (DA) : Désignation, Quantité, Unité, Prix Unitaire HT (DA), Total HT (DA).
- Si le document d me parvient sous forme de LISTE / TEXTE / PARAGRAPHE : conserve la structure en liste/sections telle qu'elle apparaît, tout en ajoutant les détails du chiffrage.
---

{catalogue_prix}

CONSIGNES DE CHIFFRAGE BTP (ALGERIE) :
1. TOUS LES PRIX DOIVENT ÊTRE EXPRIMÉS EN DINARS ALGÉRIENS (DA).
2. Si un article est présent dans le CATALOGUE SUPABASE, utilise son prix unitaire exact.
3. Si un article est absent du catalogue, calcule une estimation au prix du marché BTP algérien actuel et indique "(Prix estimé DA)".
4. Calcule systématiquement en fin de document : Total Général HT (DA), TVA 19% (DA), et Total TTC (DA).
"""

    try:
        image_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
        devis_genere = call_gemini_with_fallback([image_part, prompt])

        if supabase_client:
            supabase_client.table("devis").insert({
                "description_initiale": f"Fichier analysé : {file.filename}",
                "devis_genere": devis_genere
            }).execute()

        return {"status": "success", "devis": devis_genere}
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logging.error(f"Erreur traitement fichier : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur d'analyse visuelle par l'IA : {str(e)}")