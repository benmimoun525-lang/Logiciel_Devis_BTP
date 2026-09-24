import os
import time
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

@app.post("/chiffrer-page")
async def chiffrer_page(
    file: UploadFile = File(None),
    texte_descriptif: str = Form(None),
    page_num: int = Form(1),
    start_index: int = Form(1)
):
    try:
        keys_pool = get_api_keys_pool()
        if not keys_pool:
            raise HTTPException(
                status_code=500, 
                detail="Aucune clé API disponible. Veuillez configurer GEMINI_KEY_1 dans Render."
            )

        prompt_base = (
            f"Tu es un expert métreur et chiffreur BTP en Algérie.\n"
            f"Analyse CETTE PAGE de document (Page {page_num}) et extrait TOUS les articles présents sur cette page sans en omettre aucun.\n"
            f"Commence la numérotation des articles à partir du N° {start_index}.\n\n"
            "FORMAT DE RÉPONSE STRICT (JSON UNIQUEMENT, SANS BALISES HTML NI BLOCKS MARKDOWN) :\n"
            "Renvoie uniquement un tableau JSON :\n"
            "[\n"
            f"  {{\"n\": {start_index}, \"d\": \"Désignation précise de l'article\", \"u\": \"m3\", \"q\": 10, \"pu\": 12000}}\n"
            "]\n\n"
            "CONSIGNES :\n"
            "- Ne fusionne aucun poste sur cette page.\n"
            "- Estime un Prix Unitaire 'pu' réaliste en DZD pour le marché algérien si non spécifié.\n"
            "- Ne renvoie AUCUN autre texte, uniquement le tableau JSON."
        )

        contents_list = [prompt_base]

        if texte_descriptif and texte_descriptif.strip():
            contents_list.append(f"\n--- DESCRIPTIF DE LA PAGE {page_num} ---\n{texte_descriptif.strip()}")

        if file:
            file_bytes = await file.read()
            if file_bytes:
                content_type = file.content_type or "image/jpeg"
                contents_list.append({
                    "mime_type": content_type,
                    "data": file_bytes
                })

        generation_config = genai.GenerationConfig(
            max_output_tokens=4096,
            temperature=0.0
        )

        for api_key in keys_pool:
            genai.configure(api_key=api_key)

            for model_name in MODELS_PRIORITY:
                try:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        generation_config=generation_config
                    )
                    response = model.generate_content(contents_list)

                    raw_text = response.text or "[]"
                    clean_json = raw_text.replace("```json", "").replace("```", "").strip()

                    return JSONResponse(content={"page": page_num, "raw_json": clean_json})

                except Exception as inner_e:
                    err_msg = str(inner_e).lower()
                    print(f"Échec Modèle {model_name} : {err_msg}")
                    if "429" in err_msg or "quota" in err_msg:
                        continue
                    else:
                        break

        raise HTTPException(
            status_code=429, 
            detail="Canaux occupés. Veuillez retenter dans quelques secondes."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))