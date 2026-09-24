import os
import time
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY introuvable dans les variables d'environnement")

genai.configure(api_key=api_key)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODELS_PRIORITY = [
    'gemini-3.6-flash',
    'gemini-1.5-flash',
    'gemini-1.5-pro'
]

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Serveur BTP Chiffrage opérationnel"}

@app.post("/chiffrer-devis")
async def chiffrer_devis(
    file: UploadFile = File(None),
    texte_descriptif: str = Form(None)
):
    try:
        prompt_base = (
            "Tu es un expert métreur et chiffreur BTP en Algérie.\n"
            "Analyse le document/texte fourni et génère un **Devis Quantitatif et Estimatif (DQE)**.\n\n"
            "Format STRICT de réponse attendu (HTML) :\n"
            "1. Une courte introduction résumant les travaux détectés.\n"
            "2. Un tableau HTML complet structuré comme suit :\n"
            "<table class='devis-table'>\n"
            "  <thead>\n"
            "    <tr><th>N°</th><th>Désignation des Travaux</th><th>Unité</th><th>Qté</th><th>P.U (DZD)</th><th>Montant HT (DZD)</th></tr>\n"
            "  </thead>\n"
            "  <tbody>\n"
            "    <!-- Lignes de travaux -->\n"
            "  </tbody>\n"
            "</table>\n\n"
            "3. Le récapitulatif financier sous forme de tableau ou bloc structuré :\n"
            "- Total Général HT (DZD)\n"
            "- TVA (19%) (DZD)\n"
            "- Total Général TTC (DZD)\n\n"
            "Sois précis, professionnel et utilise des prix réalistes du marché BTP algérien en DZD."
        )

        contents_list = [prompt_base]

        if texte_descriptif and texte_descriptif.strip():
            contents_list.append(f"\n--- DESCRIPTIF / TEXTE DU CLIENT ---\n{texte_descriptif.strip()}")

        if file:
            file_bytes = await file.read()
            if file_bytes:
                content_type = file.content_type or "image/jpeg"
                contents_list.append({
                    "mime_type": content_type,
                    "data": file_bytes
                })

        if len(contents_list) == 1:
            raise HTTPException(status_code=400, detail="Veuillez fournir un fichier ou saisir du texte.")

        for model_name in MODELS_PRIORITY:
            for attempt in range(2):
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(contents_list, stream=True)

                    def generate_stream():
                        for chunk in response:
                            if hasattr(chunk, 'text') and chunk.text:
                                yield chunk.text

                    return StreamingResponse(generate_stream(), media_type="text/html; charset=utf-8")

                except Exception as inner_e:
                    err_msg = str(inner_e).lower()
                    if "429" in err_msg or "quota" in err_msg:
                        time.sleep(3)
                        continue
                    else:
                        break

        raise HTTPException(
            status_code=429, 
            detail="Quota temporairement atteint. Veuillez réimporter le document dans 30 secondes."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))