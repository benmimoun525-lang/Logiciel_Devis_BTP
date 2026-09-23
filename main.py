import os
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

# gemini-3.6-flash est désormais le modèle principal recommandé
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
            "Tu es un expert métreur et chiffreur en bâtiment (BTP) en Algérie. "
            "Examine les éléments fournis (document/image ou texte descriptif). "
            "1. Extrais et liste clairement l'ensemble du texte, métrés et désignations de travaux détectés. "
            "2. Génère un tableau de chiffrage détaillé : Désignation, Unité, Quantité, Prix Unitaire (DZD), et Prix Total (DZD). "
            "3. Indique le Montant Total Hors Taxe (HT), la TVA (19%), et le Montant TTC en Dinars Algériens (DZD). "
            "Sois très précis et synthétique."
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

        # Essai des modèles par ordre de priorité avec capture globale des erreurs
        for model_name in MODELS_PRIORITY:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(contents_list, stream=True)

                def generate_stream():
                    for chunk in response:
                        if hasattr(chunk, 'text') and chunk.text:
                            yield chunk.text

                return StreamingResponse(generate_stream(), media_type="text/plain; charset=utf-8")

            except Exception as e:
                # Si le modèle renvoie 404, 429 ou toute autre indisponibilité, on essaye le suivant
                print(f"Échec avec le modèle {model_name}: {e}")
                continue

        raise HTTPException(
            status_code=500, 
            detail="Impossible de contacter le service AI. Veuillez re-tester dans un moment."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))