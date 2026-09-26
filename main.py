import os
import io
import time
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

current_key_index = 0

def get_api_keys_pool():
    keys = []
    for key, value in os.environ.items():
        if key.startswith("GEMINI_KEY_") or key == "GEMINI_API_KEY":
            if value and value.strip():
                keys.append(value.strip())
    return keys

MODELS_PRIORITY = ['gemini-3.8-flash', 'gemini-1.5-flash']

@app.get("/")
def read_root():
    keys_count = len(get_api_keys_pool())
    return {"status": "ok", "message": f"Serveur BTP opérationnel ({keys_count} clés). Mode : Devis par lots + Aperçu visuel."}

@app.post("/chiffrer-page")
async def chiffrer_page(
    file: UploadFile = File(None),
    texte_descriptif: str = Form(None),
    page_num: int = Form(1)
):
    global current_key_index
    try:
        keys_pool = get_api_keys_pool()
        if not keys_pool:
            raise HTTPException(status_code=500, detail="Aucune clé API configurée.")

        # PROMPT ADAPTÉ AUX LOTS BTP
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
                content_type = file.content_type or "image/jpeg"
                contents_list.append({"mime_type": content_type, "data": file_bytes})

        total_keys = len(keys_pool)
        last_error = ""

        for attempt in range(total_keys):
            selected_key_idx = (current_key_index + attempt) % total_keys
            genai.configure(api_key=keys_pool[selected_key_idx])
            key_failed_due_to_quota = False

            for model_name in MODELS_PRIORITY:
                try:
                    model = genai.GenerativeModel(model_name=model_name)
                    response = model.generate_content(
                        contents_list,
                        generation_config={"max_output_tokens": 4096, "temperature": 0.0}
                    )

                    raw_text = response.text or "[]"
                    clean_json = raw_text.replace("```json", "").replace("```", "").strip()

                    current_key_index = (selected_key_idx + 1) % total_keys
                    time.sleep(1)

                    return JSONResponse(content={"page": page_num, "raw_json": clean_json})

                except Exception as inner_e:
                    err_msg = str(inner_e).lower()
                    last_error = err_msg
                    if "429" in err_msg or "quota" in err_msg:
                        key_failed_due_to_quota = True
                        break
                    else:
                        continue

            if key_failed_due_to_quota:
                time.sleep(1)
                continue

        raise HTTPException(status_code=429, detail=f"Détail de l'erreur : {last_error}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/exporter-excel")
async def exporter_excel(payload: dict = Body(...)):
    try:
        nom_client = payload.get("nom_client", "Client")
        articles = payload.get("articles", [])

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Devis par Lots"

        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        lot_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
        lot_font = Font(name="Calibri", size=11, bold=True, color="1E3A8A")
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

        ws['A1'] = f"DEVIS ESTIMATIF PAR LOTS : {nom_client}"
        ws['A1'].font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
        
        headers = ["N°", "Désignation des Travaux", "Unité", "Quantité", "P.U HT (DZD)", "Montant HT (DZD)"]
        ws.append([]) 
        ws.append(headers) 
        
        for col_num in range(1, 7):
            cell = ws.cell(row=3, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        start_row = 4
        current_row = start_row
        dernier_lot = ""

        for art in articles:
            lot_nom = art.get("lot", "Général")
            
            # Si un nouveau lot apparaît, on insère une ligne de séparation stylisée
            if lot_nom != dernier_lot:
                ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
                lot_cell = ws.cell(row=current_row, column=1, value=f"--- {lot_nom.upper()} ---")
                lot_cell.font = lot_font
                lot_cell.fill = lot_fill
                lot_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
                
                for c in range(1, 7):
                    ws.cell(row=current_row, column=c).border = thin_border
                
                dernier_lot = lot_nom
                current_row += 1

            num = art.get("n", 1)
            des = art.get("d", "Article")
            uni = art.get("u", "U")
            qte = float(art.get("q", 1) or 1)
            pu = float(art.get("pu", 0) or 0)

            ws.cell(row=current_row, column=1, value=num).alignment = Alignment(horizontal="center")
            ws.cell(row=current_row, column=2, value=des)
            ws.cell(row=current_row, column=3, value=uni).alignment = Alignment(horizontal="center")
            
            ws.cell(row=current_row, column=4, value=qte).number_format = '#,##0.00'
            ws.cell(row=current_row, column=5, value=pu).number_format = '#,##0.00'
            
            # Formule Excel pour le montant de la ligne
            ws.cell(row=current_row, column=6, value=f"=D{current_row}*E{current_row}").number_format = '#,##0.00'

            for c in range(1, 7):
                ws.cell(row=current_row, column=c).border = thin_border
            
            current_row += 1

        total_row = current_row + 1

        # Totaux généraux avec formules Excel
        ws.cell(row=total_row, column=5, value="TOTAL HT :").font = Font(bold=True)
        ws.cell(row=total_row, column=6, value=f"=SUM(F{start_row}:F{current_row-1})").font = Font(bold=True)
        ws.cell(row=total_row, column=6).number_format = '#,##0.00 DZD'

        ws.cell(row=total_row+1, column=5, value="TVA (19%) :")
        ws.cell(row=total_row+1, column=6, value=f"=F{total_row}*0.19")
        ws.cell(row=total_row+1, column=6).number_format = '#,##0.00 DZD'

        ws.cell(row=total_row+2, column=5, value="TOTAL TTC :").font = Font(bold=True, color="1E3A8A")
        ws.cell(row=total_row+2, column=6, value=f"=F{total_row}+F{total_row+1}").font = Font(bold=True, color="1E3A8A")
        ws.cell(row=total_row+2, column=6).number_format = '#,##0.00 DZD'

        ws.column_dimensions['A'].width = 6
        ws.column_dimensions['B'].width = 60
        ws.column_dimensions['C'].width = 8
        ws.column_dimensions['D'].width = 12
        ws.column_dimensions['E'].width = 18
        ws.column_dimensions['F'].width = 22

        output_stream = io.BytesIO()
        wb.save(output_stream)
        output_stream.seek(0)

        nom_fichier_propre = nom_client.replace(' ', '_').replace('/', '_')
        return StreamingResponse(
            output_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={'Content-Disposition': f'attachment; filename="Devis_Par_Lots_{nom_fichier_propre}.xlsx"'}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))