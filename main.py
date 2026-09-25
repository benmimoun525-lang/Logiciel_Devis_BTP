import os
import io
import time
import json
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import google.generativeai as genai

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
            "FORMAT DE RÉPONSE STRICT (JSON UNIQUEMENT) :\n"
            "[\n"
            f"  {{\"n\": {start_index}, \"d\": \"Désignation précise de l'article\", \"u\": \"m3\", \"q\": 10, \"pu\": 12000}}\n"
            "]\n\n"
            "CONSIGNES :\n"
            "- Ne fusionne aucun poste sur cette page.\n"
            "- Estime un Prix Unitaire 'pu' réaliste en DZD pour le marché algérien si non spécifié.\n"
            "- Renvoie UNIQUEMENT le tableau JSON sans aucun texte additionnel."
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

        # Forcer la génération JSON native
        generation_config = genai.GenerationConfig(
            max_output_tokens=4096,
            temperature=0.0,
            response_mime_type="application/json"
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
                        time.sleep(2)
                        continue
                    else:
                        break

        raise HTTPException(
            status_code=429, 
            detail="Canaux occupés ou quotas atteints. Réessai en cours..."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/exporter-excel")
async def exporter_excel(payload: dict = Body(...)):
    try:
        nom_client = payload.get("nom_client", "Client")
        tel_client = payload.get("tel_client", "-")
        chantier = payload.get("chantier", "-")
        articles = payload.get("articles", [])

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "DQE Estimatif"

        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        bold_font = Font(name="Calibri", size=11, bold=True)
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        ws['A1'] = "DEVIS QUANTITATIF ET ESTIMATIF (DQE)"
        ws['A1'].font = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
        
        ws['A3'] = f"Client : {nom_client}"
        ws['A4'] = f"Téléphone : {tel_client}"
        ws['A5'] = f"Chantier : {chantier}"

        headers = ["N°", "Désignation des Travaux", "Unité", "Quantité", "P.U (DZD)", "Montant HT (DZD)"]
        ws.append([])
        ws.append(headers)
        
        for col_num in range(1, 7):
            cell = ws.cell(row=7, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        start_row = 8
        total_ht = 0

        for idx, art in enumerate(articles):
            row_idx = start_row + idx
            num = art.get("n", idx + 1)
            des = art.get("d", "Article")
            uni = art.get("u", "U")
            qte = float(art.get("q", 1))
            pu = float(art.get("pu", 0))
            montant = qte * pu
            total_ht += montant

            ws.append([num, des, uni, qte, pu, montant])

            ws.cell(row=row_idx, column=1).alignment = Alignment(horizontal="center")
            ws.cell(row=row_idx, column=3).alignment = Alignment(horizontal="center")
            ws.cell(row=row_idx, column=4).number_format = '#,##0.00'
            ws.cell(row=row_idx, column=5).number_format = '#,##0.00'
            ws.cell(row=row_idx, column=6).number_format = '#,##0.00'

            for c in range(1, 7):
                ws.cell(row=row_idx, column=c).border = thin_border

        last_row = start_row + len(articles)
        tva = total_ht * 0.19
        total_ttc = total_ht + tva

        ws.cell(row=last_row + 1, column=5, value="Total Général HT :").font = bold_font
        ws.cell(row=last_row + 1, column=6, value=total_ht).font = bold_font
        ws.cell(row=last_row + 1, column=6).number_format = '#,##0.00 DZD'

        ws.cell(row=last_row + 2, column=5, value="TVA (19%) :")
        ws.cell(row=last_row + 2, column=6, value=tva)
        ws.cell(row=last_row + 2, column=6).number_format = '#,##0.00 DZD'

        ws.cell(row=last_row + 3, column=5, value="Total Général TTC :").font = Font(name="Calibri", size=12, bold=True, color="1E3A8A")
        ws.cell(row=last_row + 3, column=6, value=total_ttc).font = Font(name="Calibri", size=12, bold=True, color="1E3A8A")
        ws.cell(row=last_row + 3, column=6).number_format = '#,##0.00 DZD'

        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 50
        ws.column_dimensions['C'].width = 10
        ws.column_dimensions['D'].width = 15
        ws.column_dimensions['E'].width = 18
        ws.column_dimensions['F'].width = 22

        output_stream = io.BytesIO()
        wb.save(output_stream)
        output_stream.seek(0)

        filename = f"Devis_DQE_{nom_client.replace(' ', '_')}.xlsx"
        headers_resp = {
            'Content-Disposition': f'attachment; filename="{filename}"'
        }

        return StreamingResponse(
            output_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers_resp
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))