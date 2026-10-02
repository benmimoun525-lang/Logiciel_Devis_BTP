import os
import json
import random
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

app = FastAPI(title="Logiciel Devis BTP - Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chargement intelligent des clés GEMINI_KEY_X
def get_gemini_keys():
    keys = []
    for k, v in os.environ.items():
        if (k.startswith("GEMINI_KEY_") or k == "GEMINI_API_KEY") and v.strip():
            keys.append(v.strip())
    return list(set(keys))

API_KEYS = get_gemini_keys()

def configure_random_key():
    if not API_KEYS:
        raise HTTPException(status_code=500, detail="Aucune clé GEMINI_KEY configurée sur Render.")
    selected_key = random.choice(API_KEYS)
    genai.configure(api_key=selected_key)
    return selected_key

def get_gemini_model():
    configure_random_key()
    # Modèles actifs supportés
    for model_name in ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash-latest"]:
        try:
            return genai.GenerativeModel(model_name)
        except Exception:
            continue
    return genai.GenerativeModel("gemini-2.5-flash")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Serveur BTP opérationnel</h1>")

@app.get("/status")
async def get_status():
    return {
        "status": "ok",
        "message": f"Serveur BTP opérationnel ({len(API_KEYS)} clés API détectées).",
        "keys_count": len(API_KEYS)
    }

@app.post("/chiffrer-page")
async def chiffrer_page(
    file: UploadFile = File(None),
    texte_descriptif: str = Form(""),
    page_num: int = Form(1)
):
    if not file and not texte_descriptif.strip():
        raise HTTPException(status_code=400, detail="Veuillez fournir un fichier ou un descriptif textuel.")

    model = get_gemini_model()
    prompt = """
    Tu es un métreur expert en BTP algérien. 
    Analyse ce document/descriptif et extrait la liste des articles avec leurs prix sous forme de tableau JSON strict.
    
    Structure JSON attendue (sans balises markdown extra, uniquement le tableau JSON) :
    [
      {
        "lot": "Nom du lot (ex: Maçonnerie, Béton, Peinture)",
        "n": 1,
        "d": "Désignation claire des travaux",
        "u": "Unité (m², m³, kg, u, ens)",
        "q": 10.0,
        "pu": 1500.0
      }
    ]
    Si le prix unitaire n'est pas précisé, estime-le selon les tarifs moyens BTP en DZD.
    """

    try:
        contents = [prompt]
        
        if file:
            file_bytes = await file.read()
            mime_type = file.content_type or "image/jpeg"
            
            if "pdf" in mime_type:
                temp_filename = f"temp_{file.filename}"
                with open(temp_filename, "wb") as f_out:
                    f_out.write(file_bytes)
                uploaded_file = genai.upload_file(temp_filename)
                contents.append(uploaded_file)
            else:
                contents.append({"mime_type": mime_type, "data": file_bytes})

        if texte_descriptif.strip():
            contents.append(f"Consignes supplémentaires : {texte_descriptif}")

        response = model.generate_content(contents)
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        
        return {"raw_json": raw_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'extraction Gemini : {str(e)}")

@app.post("/exporter-excel")
async def exporter_excel(data: dict):
    nom_client = data.get("nom_client", "Projet_BTP")
    articles = data.get("articles", [])

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Devis BTP"

    ws['A1'] = "DEVIS ESTIMATIF BTP"
    ws['A1'].font = Font(size=16, bold=True, color="1E3A8A")
    ws['A2'] = f"Client / Projet : {nom_client}"
    ws['A2'].font = Font(size=11, italic=True)

    headers = ["N°", "Lot", "Désignation des Travaux", "Unité", "Quantité", "P.U HT (DZD)", "Montant HT (DZD)"]
    ws.append([])
    ws.append(headers)

    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    row_idx = 5
    start_row = row_idx

    for art in articles:
        ws.cell(row=row_idx, column=1, value=art.get("n", row_idx - 4))
        ws.cell(row=row_idx, column=2, value=art.get("lot", "Général"))
        ws.cell(row=row_idx, column=3, value=art.get("d", ""))
        ws.cell(row=row_idx, column=4, value=art.get("u", "u"))
        ws.cell(row=row_idx, column=5, value=art.get("q", 0))
        ws.cell(row=row_idx, column=6, value=art.get("pu", 0))
        ws.cell(row=row_idx, column=7, value=f"=E{row_idx}*F{row_idx}")
        row_idx += 1

    end_row = row_idx - 1

    ws.cell(row=row_idx + 1, column=6, value="TOTAL HT (DZD) :").font = Font(bold=True)
    ws.cell(row=row_idx + 1, column=7, value=f"=SUM(G{start_row}:G{end_row})").font = Font(bold=True)

    ws.cell(row=row_idx + 2, column=6, value="TVA (19%) :").font = Font(bold=True)
    ws.cell(row=row_idx + 2, column=7, value=f"=G{row_idx + 1}*0.19").font = Font(bold=True)

    ws.cell(row=row_idx + 3, column=6, value="TOTAL TTC (DZD) :").font = Font(bold=True, color="1E3A8A")
    ws.cell(row=row_idx + 3, column=7, value=f"=G{row_idx + 1}+G{row_idx + 2}").font = Font(bold=True, color="1E3A8A")

    file_path = f"Devis_{nom_client}.xlsx"
    wb.save(file_path)

    return FileResponse(file_path, filename=file_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
