import os
import json
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import google.generativeai as genai
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

app = FastAPI(title="Logiciel Devis BTP - Extraction Gemini & Export Excel DZD")

# Configurer la clé Gemini depuis les variables d'environnement Render
GEMINI_KEY = os.environ.get("GEMINI_KEY_1") or os.environ.get("GEMINI_API_KEY")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

# Prompts pour l'analyse des devis BTP
SYSTEM_PROMPT = """
Vous êtes un expert en métré et devis BTP.
Analysez l'image ou le document PDF fourni et extrayez la liste de tous les articles/prestation du devis.

Retournez EXCLUSIVEMENT un objet JSON valide suivant exactement ce schéma (aucun texte avant ou après, pas de balises markdown) :
{
  "titre_devis": "Titre ou Référence du Devis",
  "client": "Nom du client si disponible",
  "items": [
    {
      "designation": "Description des travaux ou fourniture",
      "unite": "m2, m3, ml, kg, ens, u, etc.",
      "quantite": 0.0,
      "prix_unitaire_ht": 0.0
    }
  ]
}
"""


def parse_gemini_response(response_text: str) -> dict:
    """Nettoie la réponse texte de Gemini pour extraire le JSON valide."""
    clean_text = response_text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    if clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    clean_text = clean_text.strip()
    return json.loads(clean_text)


def create_excel_dzd(devis_data: dict) -> io.BytesIO:
    """Génère un fichier Excel professionnel aux normes algériennes (TVA 19% + DZD)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Devis BTP"
    ws.views.sheetView[0].showGridLines = True

    # Couleurs & Styles
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    bold_font = Font(name="Calibri", size=11, bold=True)
    normal_font = Font(name="Calibri", size=11)
    
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    
    # Format numérique monétaire DZD
    dzd_format = '#,##0.00 "DZD"'

    # En-tête du document
    ws['A1'] = "DEVIS BTP / FACTURE PROFORMA"
    ws['A1'].font = Font(name="Calibri", size=16, bold=True, color="1F4E78")
    
    titre = devis_data.get("titre_devis", "Devis BTP")
    client = devis_data.get("client", "Client")
    ws['A3'] = f"Référence / Objet : {titre}"
    ws['A3'].font = bold_font
    ws['A4'] = f"Client : {client}"
    ws['A4'].font = bold_font

    # Entêtes du tableau
    headers = ["N°", "Désignation des travaux", "Unité", "Quantité", "P.U HT (DZD)", "Montant HT (DZD)"]
    start_row = 6
    
    for col_num, header_title in enumerate(headers, 1):
        cell = ws.cell(row=start_row, column=col_num)
        cell.value = header_title
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center" if col_num in [1, 3] else "left", vertical="center")

    items = devis_data.get("items", [])
    current_row = start_row + 1

    # Injection des lignes du devis
    for idx, item in enumerate(items, 1):
        ws.cell(row=current_row, column=1, value=idx).alignment = Alignment(horizontal="center")
        ws.cell(row=current_row, column=2, value=item.get("designation", ""))
        ws.cell(row=current_row, column=3, value=item.get("unite", "")).alignment = Alignment(horizontal="center")
        
        qty_cell = ws.cell(row=current_row, column=4, value=float(item.get("quantite", 0)))
        qty_cell.number_format = "#,##0.00"
        
        pu_cell = ws.cell(row=current_row, column=5, value=float(item.get("prix_unitaire_ht", 0)))
        pu_cell.number_format = dzd_format
        
        # Formule pour le Total HT de la ligne
        total_cell = ws.cell(row=current_row, column=6, value=f"=D{current_row}*E{current_row}")
        total_cell.number_format = dzd_format

        for col_num in range(1, 7):
            c = ws.cell(row=current_row, column=col_num)
            c.font = normal_font
            c.border = thin_border

        current_row += 1

    # Totaux (Total HT, TVA 19%, Total TTC)
    totaux_start = current_row + 1
    
    # Total HT
    ws.cell(row=totaux_start, column=5, value="Total HT :").font = bold_font
    tht_cell = ws.cell(row=totaux_start, column=6, value=f"=SUM(F{start_row + 1}:F{current_row - 1})")
    tht_cell.font = bold_font
    tht_cell.number_format = dzd_format

    # TVA 19%
    ws.cell(row=totaux_start + 1, column=5, value="TVA (19%) :").font = bold_font
    tva_cell = ws.cell(row=totaux_start + 1, column=6, value=f"=F{totaux_start}*0.19")
    tva_cell.font = bold_font
    tva_cell.number_format = dzd_format

    # Total TTC
    ws.cell(row=totaux_start + 2, column=5, value="Total TTC :").font = Font(name="Calibri", size=12, bold=True, color="1F4E78")
    ttc_cell = ws.cell(row=totaux_start + 2, column=6, value=f"=F{totaux_start}+F{totaux_start + 1}")
    ttc_cell.font = Font(name="Calibri", size=12, bold=True, color="1F4E78")
    ttc_cell.number_format = dzd_format

    # Ajustement automatique de la largeur des colonnes
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)
    ws.column_dimensions['B'].width = 45  # Plus large pour la désignation

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


@app.get("/")
def root():
    return {"status": "ok", "message": "API Logiciel Devis BTP - Operational"}


@app.post("/extract-devis/")
async def extract_devis(file: UploadFile = File(...)):
    """Reçoit une image ou un PDF, extrait les données via Gemini et renvoie le JSON."""
    if not GEMINI_KEY:
        raise HTTPException(status_code=500, detail="Clé GEMINI_KEY_1 non configurée sur Render.")

    try:
        content = await file.read()
        mime_type = file.content_type or "image/jpeg"

        # Utilisation du modèle stable 'gemini-1.5-flash'
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        image_part = {
            "mime_type": mime_type,
            "data": content
        }

        response = model.generate_content([SYSTEM_PROMPT, image_part])
        parsed_json = parse_gemini_response(response.text)
        
        return {"success": True, "data": parsed_json}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'extraction : {str(e)}")


@app.post("/generate-excel/")
async def generate_excel_endpoint(devis_data: dict):
    """Reçoit le JSON du devis et génère le fichier Excel DZD avec TVA 19%."""
    try:
        excel_stream = create_excel_dzd(devis_data)
        filename = "Devis_BTP_19percent.xlsx"
        
        return StreamingResponse(
            excel_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de génération Excel : {str(e)}")