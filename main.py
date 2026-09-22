import os
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Configuration de la clé API Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY introuvable dans les variables d'environnement")

genai.configure(api_key=api_key)

# Modèle Gemini 2.0 Flash
model = genai.GenerativeModel('gemini-2.0-flash')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Serveur BTP Chiffrage opérationnel"}

@app.get("/models")
def list_models():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return {"available_models": models}
    except Exception as e:
        return {"error": str(e)}

@app.post("/chiffrer-devis")
async def chiffrer_devis(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        
        content_type = file.content_type if file.content_type else "image/jpeg"
        
        image_part = {
            "mime_type": content_type,
            "data": contents
        }
        
        prompt = (
            "Tu es un expert métreur et chiffreur en bâtiment (BTP) en Algérie. "
            "Examine attentivement ce document (devis/métré/plan). "
            "1. Extrais et liste le texte et les désignations des travaux détectés. "
            "2. Génère un tableau de chiffrage détaillé avec : Désignation, Unité, Quantité, Prix Unitaire (DZD), et Prix Total (DZD). "
            "3. Indique le Montant Total Hors Taxe (HT), la TVA (19%), et le Montant TTC en Dinars Algériens (DZD). "
            "Sois très précis et structure la réponse de manière professionnelle."
        )

        response = model.generate_content([prompt, image_part], stream=True)

        def generate_stream():
            for chunk in response:
                if hasattr(chunk, 'text') and chunk.text:
                    yield chunk.text

        return StreamingResponse(generate_stream(), media_type="text/plain; charset=utf-8")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))