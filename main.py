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
            "Ta mission : Extraire et chiffrer l'INTÉGRALITÉ des articles du document sans AUCUNE omission, synthèse ou regroupement.\n"
            "Si le document contient 83 articles ou plus, tu dois TOUS les lister du N°1 au dernier N°.\n\n"
            "Format STRICT de réponse attendu (HTML compact) :\n"
            "1. Une ligne d'intro : <p>Devis DQE détaillé complet.</p>\n"
            "2. Le tableau HTML :\n"
            "<table class='devis-table'>\n"
            "<thead><tr><th>N°</th><th>Désignation</th><th>Unité</th><th>Qté</th><th>P.U (DZD)</th><th>Montant HT</th></tr></thead>\n"
            "<tbody>\n"
            "<!-- Lignes de 1 jusqu'à la fin. Garde les désignations précises mais sans blabla superflu pour tenir sur la totalité. -->\n"
            "</tbody>\n"
            "</table>\n\n"
            "3. Bloc financier final en bas du tableau :\n"
            "<p><strong>Total Général HT :</strong> [Montant] DZD<br>\n"
            "<strong>TVA (19%) :</strong> [Montant] DZD<br>\n"
            "<strong>Total Général TTC :</strong> [Montant] DZD</p>\n\n"
            "RÈGLE D'OR : Traite l'intégralité des 83+ articles et termine IMPÉRATIVEMENT par le Total TTC."
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

        # Configuration maximale pour très grands métrés
        generation_config = genai.GenerationConfig(
            max_output_tokens=8192,
            temperature=0.0
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