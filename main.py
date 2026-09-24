import os
import time
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_api_keys_pool():
    keys = []
    for key, value in os.environ.items():
        if key.startswith("GEMINI_KEY_") or key == "GEMINI_API_KEY":
            if value and value.strip():
                keys.append(value.strip())
    return keys

MODELS_PRIORITY = [
    'gemini-3.6-flash',
    'gemini-1.5-flash',
    'gemini-1.5-pro'
]

@app.get("/")
def read_root():
    keys_count = len(get_api_keys_pool())
    return {
        "status": "ok", 
        "message": f"Serveur BTP Chiffrage opérationnel avec un pool de {keys_count} clé(s) API."
    }

@app.post("/chiffrer-devis")
async def chiffrer_devis(
    file: UploadFile = File(None),
    texte_descriptif: str = Form(None)
):
    try:
        keys_pool = get_api_keys_pool()
        if not keys_pool:
            raise HTTPException(
                status_code=500, 
                detail="Aucune clé API disponible. Veuillez configurer GEMINI_KEY_1 dans Render."
            )

        prompt_base = (
            "Tu es un expert métreur et chiffreur BTP en Algérie.\n"
            "Analyse le document/texte fourni et génère un **Devis Quantitatif et Estimatif (DQE) COMPLET sans jamais t'arrêter en cours de route**.\n\n"
            "Format STRICT de réponse attendu (HTML) :\n"
            "1. Une courte introduction d'une ligne.\n"
            "2. Un tableau HTML complet structuré comme suit :\n"
            "<table class='devis-table'>\n"
            "  <thead>\n"
            "    <tr><th>N°</th><th>Désignation des Travaux</th><th>Unité</th><th>Qté</th><th>P.U (DZD)</th><th>Montant HT (DZD)</th></tr>\n"
            "  </thead>\n"
            "  <tbody>\n"
            "    <!-- Lignes de travaux - Sois concis dans la désignation pour aller jusqu'au dernier article -->\n"
            "  </tbody>\n"
            "</table>\n\n"
            "3. Le récapitulatif financier final :\n"
            "- Total Général HT (DZD)\n"
            "- TVA (19%) (DZD)\n"
            "- Total Général TTC (DZD)\n\n"
            "IMPORTANT : Ne coupe JAMAIS la réponse. Va obligatoirement jusqu'au dernier article et affiche le Total TTC."
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

        # Configuration pour autoriser la taille maximale de réponse (8192 tokens)
        generation_config = genai.GenerationConfig(
            max_output_tokens=8192,
            temperature=0.2
        )

        last_exception = None

        for api_key in keys_pool:
            genai.configure(api_key=api_key)

            for model_name in MODELS_PRIORITY:
                try:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        generation_config=generation_config
                    )
                    response = model.generate_content(contents_list, stream=True)

                    def generate_stream():
                        for chunk in response:
                            if hasattr(chunk, 'text') and chunk.text:
                                yield chunk.text

                    return StreamingResponse(generate_stream(), media_type="text/html; charset=utf-8")

                except Exception as inner_e:
                    last_exception = inner_e
                    err_msg = str(inner_e).lower()
                    print(f"Échec Modèle {model_name} : {err_msg}")
                    
                    if "429" in err_msg or "quota" in err_msg:
                        continue
                    else:
                        break

        raise HTTPException(
            status_code=429, 
            detail="Le service est très sollicité. Veuillez réimporter votre document dans quelques secondes."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))