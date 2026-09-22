import os
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import google.generativeai as genai

app = FastAPI(title="Logiciel Devis BTP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("ATTENTION : GEMINI_API_KEY non trouvée dans les variables d'environnement !")
else:
    genai.configure(api_key=GEMINI_API_KEY)

PROMPT_BTP = """
Tu es un expert métreur et chiffreur du bâtiment (BTP) en Algérie.
Analyse le document/descriptif fourni ci-joint et génère un chiffrage détaillé et structuré.

Pour chaque poste de travaux trouve :
1. La désignation précise des travaux
2. L'unité (m², m³, forfait, ens, ml, kg...)
3. La quantité estimée
4. Le prix unitaire moyen estimé en Dinars Algériens (DZD)
5. Le montant total HT (DZD)

Termine impérativement par le récapitulatif :
- Total HT (DZD)
- TVA (19%)
- Total TTC (DZD)

Présente le résultat sous forme d'un tableau Markdown clair, lisible et professionnel.
"""

async def generer_chiffrage_stream(fichier_bytes: bytes, mime_type: str):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        contents = [
            {"mime_type": mime_type, "data": fichier_bytes},
            PROMPT_BTP
        ]

        response = model.generate_content(contents, stream=True)

        for chunk in response:
            if chunk.text:
                yield chunk.text
                await asyncio.sleep(0.01)

    except Exception as e:
        yield f"\n\n[ERREUR SERVEUR : {str(e)}]"

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Serveur BTP Chiffrage opérationnel"}

@app.post("/chiffrer-devis")
async def chiffrer_devis(file: UploadFile = File(...)):
    mime_type = file.content_type or "application/octet-stream"
    fichier_bytes = await file.read()
    if not fichier_bytes:
        raise HTTPException(status_code=400, detail="Le fichier envoyé est vide.")

    return StreamingResponse(
        generer_chiffrage_stream(fichier_bytes, mime_type),
        media_type="text/plain; charset=utf-8"
    )