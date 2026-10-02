import os
import io
import time
import tempfile
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
import google.generativeai as genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

current_key_index = 0

def get_api_keys_pool():
    keys = []
    for key, value in os.environ.items():
        if key.startswith("GEMINI_KEY_") or key in ("GEMINI_API_KEY", "GEMINI_KEY", "GEMINI_API_KEYS"):
            if value and value.strip():
                keys.append(value.strip())
    return keys

# Modèles Gemini officiels et valides par ordre de priorité
MODELS_PRIORITY = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']

@app.get("/")
def afficher_interface():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return JSONResponse(content={"status": "ok", "message": "Serveur BTP opérationnel."})

@app.get("/status")
def read_status():
    keys_count = len(get_api_keys_pool())
    return {"status": "ok", "message": f"Serveur BTP opérationnel ({keys_count} clés API détectées)."}

@app.post("/chiffrer-page")
async def chiffrer_page(
    file: UploadFile = File(None),
    texte_descriptif: str = Form(None),
    page_num: int = Form(1)
):
    global current_key_index
    tmp_file_path = None
    
    try:
        keys_pool = get_api_keys_pool()
        if not keys_pool:
            raise HTTPException(
                status_code=500, 
                detail="Aucune clé API configurée sur Render. Ajoutez GEMINI_API_KEY dans les variables d'environnement."
            )

        prompt_base = (
            f"Tu es un expert métreur BTP en Algérie.\n"
            f"Analyse CETTE PAGE (Page {page_num}) d'un devis chiffré par LOTS.\n"
            "Extrait tous les articles en identifiant clairement les LOTS (ex: 'Lot 01: Terrassement') et la numérotation des articles qui recommence à 1 pour chaque lot.\n\n"
            "FORMAT DE RÉPONSE STRICT (JSON UNIQUEMENT) :\n"
            "[\n"
            "  {\"lot\": \"Nom du Lot ou de la Section\", \"n\": 1, \"d\": \"Désignation précise\", \"u\": \"m3\", \"q\": 10, \"pu\": 12000}\n"
            "]\n\n"
            "CONSIGNES :\n"
            "- Si la page commence par un nouveau lot, indique-le dans le champ 'lot'.\n"
            "- 'n' = Numéro de l'article dans son lot (recommence à 1 par lot).\n"
            "- 'pu' = Estime un Prix Unitaire HT réaliste en DZD pour le marché algérien.\n"
            "- RÈGLE ABSOLUE : Renvoie UNIQUEMENT le tableau JSON, aucun texte avant, aucun texte après."
        )

        contents_list = [prompt_base]
        if texte_descriptif and texte_descriptif.strip():
            contents_list.append(f"\n--- DESCRIPTIF ---\n{texte_descriptif.strip()}")

        if file:
            file_bytes = await file.read()
            if file_bytes:
                filename = (file.filename or "").lower()
                content_type = (file.content_type or "").lower()
                
                # Rejet explicite des fichiers Word (.docx)
                if filename.endswith(('.doc', '.docx')) or "word" in content_type:
                    raise HTTPException(
                        status_code=400, 
                        detail="Les fichiers Word (.docx) ne sont pas supportés directement par l'IA. Veuillez les convertir en PDF ou envoyer une image."
                    )
                
                # Traitement des fichiers PDF via l'API File de Google Gemini
                if filename.endswith('.pdf') or "pdf" in content_type:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(file_bytes)
                        tmp_file_path = tmp_file.name
                
                # Traitement des images (JPG, PNG, WEBP, etc.)
                else:
                    mime = content_type if "image" in content_type else "image/jpeg"
                    contents_list.append({"mime_type": mime, "data": file_bytes})

        total_keys = len(keys_pool)
        last_error = ""

        for attempt in range(total_keys):
            selected_key_idx = (current_key_index + attempt) % total_keys
            active_key = keys_pool[selected_key_idx]
            genai.configure(api_key=active_key)
            key_failed_due_to_quota = False

            # Transfert du PDF à l'API File Gemini si présent
            gemini_file_part = None
            if tmp_file_path:
                try:
                    gemini_file_part = genai.upload_file(tmp_file_path, mime_type="application/pdf")
                except Exception as upload_err:
                    last_error = f"Erreur Upload PDF: {str(upload_err)}"
                    continue

            current_contents = list(contents_list)
            if gemini_file_part:
                current_contents.append(gemini_file_part)

            for model_name in MODELS_PRIORITY:
                try:
                    # Essai prioritaire sur le modèle 2.0 / 2.5 flash, puis bascule automatique
try:
    model = genai.GenerativeModel("gemini-2.0-flash")
except Exception:
    model = genai.GenerativeModel("gemini-2.5-flash")
                    response = model.generate_content(
                        current_contents,
                        generation_config={"max_output_tokens": 4096, "temperature": 0.0}
                    )

                    raw_text = response.text or "[]"
                    clean_json = raw_text.replace("```json", "").replace("```", "").strip()

                    current_key_index = (selected_key_idx + 1) % total_keys
                    time.sleep(0.5)

                    # Nettoyage du fichier distant chez Gemini
                    if gemini_file_part:
                        try:
                            genai.delete_file(gemini_file_part.name)
                        except Exception:
                            pass

                    return JSONResponse(content={"page": page_num, "raw_json": clean_json})

                except Exception as inner_e:
                    err_msg = str(inner_e).lower()
                    last_error = f"Modèle {model_name}: {str(inner_e)}"
                    if "429" in err_msg or "quota" in err_msg or "resource_exhausted" in err_msg:
                        key_failed_due_to_quota = True
                        break
                    else:
                        continue

            if key_failed_due_to_quota:
                time.sleep(1)
                continue

        raise HTTPException(status_code=500, detail=f"Erreur d'extraction Gemini : {last_error}")

    except HTTPException as http_e:
        raise http_e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur : {str(e)}")
    finally:
        # Suppression du fichier temporaire local
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.remove(tmp_file_path)
            except Exception:
                pass
