import os
import io
import re
import json
import time
from dotenv import load_dotenv

# Charger immédiatement les variables du fichier .env
load_dotenv()

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
import google.generativeai as genai

app = FastAPI(title="Logiciel Chiffrage Devis BTP", version="2.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

current_key_index = 0
working_model_cache = None  # Mémorise le modèle rapide validé pour supprimer les temps d'attente

def get_api_keys_pool():
    """Récupère toutes les clés Gemini disponibles dans l'environnement sans doublons."""
    keys = []
    for key, value in os.environ.items():
        k_upper = key.upper()
        if k_upper.startswith("GEMINI_KEY") or k_upper.startswith("GEMINI_API_KEY"):
            val_clean = (value or "").strip()
            if val_clean and val_clean not in keys:
                keys.append(val_clean)
    return keys

# Modèles rapides et fiables pour l'analyse BTP multi-pages
MODELS_PRIORITY = [
    'gemini-2.5-flash',
    'gemini-2.0-flash',
    'gemini-1.5-flash',
    'gemini-flash-latest',
    'gemini-2.5-flash-lite',
    'gemini-3.8-flash',
    'gemini-3.5-flash'
]

# --- Conversion des nombres en toutes lettres pour devis algérien ---
def nombre_en_lettres(n: float) -> str:
    """Convertit un montant numérique en lettres françaises (norme BTP Algérie)."""
    entier = int(abs(n))
    centimes = int(round((abs(n) - entier) * 100))

    if entier == 0:
        texte_entier = "zéro"
    else:
        unites = ['', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf']
        dizaines = ['', 'dix', 'vingt', 'trente', 'quarante', 'cinquante', 'soixante', 'soixante-dix', 'quatre-vingt', 'quatre-vingt-dix']
        particuliers = {
            11: 'onze', 12: 'douze', 13: 'treize', 14: 'quatorze', 15: 'quinze', 16: 'seize',
            71: 'soixante-et-onze', 72: 'soixante-douze', 73: 'soixante-treize', 74: 'soixante-quatorze',
            75: 'soixante-quinze', 76: 'soixante-seize', 77: 'soixante-dix-sept', 78: 'soixante-dix-huit', 79: 'soixante-dix-neuf',
            80: 'quatre-vingts', 91: 'quatre-vingt-onze', 92: 'quatre-vingt-douze', 93: 'quatre-vingt-treize',
            94: 'quatre-vingt-quatorze', 95: 'quatre-vingt-quinze', 96: 'quatre-vingt-seize', 97: 'quatre-vingt-dix-sept',
            98: 'quatre-vingt-dix-huit', 99: 'quatre-vingt-dix-neuf'
        }

        def _inf_cent(val):
            if val in particuliers:
                return particuliers[val]
            d, u = divmod(val, 10)
            if d == 0:
                return unites[u]
            if d == 1:
                return ['dix', 'onze', 'douze', 'treize', 'quatorze', 'quinze', 'seize', 'dix-sept', 'dix-huit', 'dix-neuf'][u]
            if u == 1 and d not in (8, 9):
                return f"{dizaines[d]}-et-un"
            if u == 0:
                return dizaines[d]
            return f"{dizaines[d]}-{unites[u]}"

        def _inf_mille(val):
            c, r = divmod(val, 100)
            res = ""
            if c == 1:
                res = "cent"
            elif c > 1:
                res = f"{unites[c]} cent" + ("s" if r == 0 else "")
            if r > 0:
                sub = _inf_cent(r)
                res = f"{res} {sub}".strip()
            return res

        parts = []
        milliards, r = divmod(entier, 1000000000)
        millions, r = divmod(r, 1000000)
        mille, unites_val = divmod(r, 1000)

        if milliards:
            parts.append(f"{_inf_mille(milliards)} milliard" + ("s" if milliards > 1 else ""))
        if millions:
            parts.append(f"{_inf_mille(millions)} million" + ("s" if millions > 1 else ""))
        if mille:
            if mille == 1:
                parts.append("mille")
            else:
                parts.append(f"{_inf_mille(mille)} mille")
        if unites_val:
            parts.append(_inf_mille(unites_val))

        texte_entier = " ".join(parts).strip()

    texte_final = f"{texte_entier} Dinars Algériens"
    if centimes > 0:
        texte_final += f" et {centimes} centimes"
    else:
        texte_final += " et zéro centime"

    return texte_final.capitalize()

# --- Distribution de l'interface Web (sur PC et Smartphone) ---
@app.get("/")
def serve_index():
    """Sert l'application web principale sur PC et Smartphone."""
    # Recherche du fichier index.html dans le dossier courant ou dossier du script
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "index.html"),
        os.path.join(os.getcwd(), "index.html"),
        "index.html"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
    return {"status": "ok", "message": "Serveur BTP opérationnel, mais index.html est introuvable."}

@app.get("/index.html")
def serve_index_html():
    return serve_index()

@app.get("/manifest.json")
def serve_manifest():
    manifest_path = os.path.join(os.path.dirname(__file__), "manifest.json")
    if os.path.exists(manifest_path):
        return FileResponse(manifest_path, media_type="application/manifest+json")
    raise HTTPException(status_code=404, detail="Manifest non trouvé")

@app.get("/sw.js")
def serve_sw():
    sw_path = os.path.join(os.path.dirname(__file__), "sw.js")
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Service Worker non trouvé")

@app.get("/api/status")
def read_status():
    keys = get_api_keys_pool()
    return {
        "status": "ok",
        "keys_count": len(keys),
        "working_model": working_model_cache,
        "message": f"Serveur BTP prêt avec {len(keys)} clé(s) configurée(s)."
    }

# --- Fonction de récupération d'urgence pour JSON incomplets ou tronqués ---
def extraire_articles_partiels(texte: str):
    """Permet de récupérer tous les articles valides même si le JSON a été coupé par la taille de la page."""
    articles = []
    # Recherche de tous les blocs { ... } contenant au minimum 'd' ou 'designation'
    pattern = re.compile(r'\{[^{}]*"(?:d|designation)"[^{}]*\}', re.DOTALL)
    matches = pattern.findall(texte)
    for m in matches:
        try:
            item = json.loads(m)
            if "d" in item or "designation" in item:
                articles.append(item)
        except Exception:
            continue
    return articles

# --- Traitement IA Page par Page (Ultra-Stable pour Gros Devis Multi-Pages) ---
@app.post("/chiffrer-page")
async def chiffrer_page(
    file: UploadFile = File(None),
    texte_descriptif: str = Form(None),
    page_num: int = Form(1)
):
    global current_key_index, working_model_cache
    try:
        keys_pool = get_api_keys_pool()
        if not keys_pool:
            raise HTTPException(status_code=500, detail="Aucune clé API Gemini configurée dans le fichier .env.")

        # PROMPT EXPERT MÉTREUR BTP ALGÉRIE ULTRA-ROBUSTE
        prompt_expert = (
            f"Tu es un expert métreur-vérificateur senior spécialisé dans le BTP en Algérie.\n"
            f"Analyse CETTE PAGE (Page {page_num}) d'un bordereau de prix / devis BTP (DQE).\n\n"
            "MISSION :\n"
            "1. Détecte si le nom du client ou l'intitulé du projet est mentionné sur le document.\n"
            "2. Extrait fidèlement chaque prestation ou article de travaux visible sur la page (sans en oublier aucun).\n"
            "3. Classe chaque article dans son LOT approprié (ex: 'LOT 01: TERRASSEMENTS', 'LOT 02: GROS-OEUVRE', 'LOT 03: MAÇONNERIE', 'LOT 04: ÉTANCHÉITÉ', 'LOT 05: REVÊTEMENTS', 'LOT 06: MENUISERIE', 'LOT 07: PLOMBERIE', 'LOT 08: ÉLECTRICITÉ', 'LOT 09: PEINTURE', etc.).\n"
            "4. Si un prix unitaire H.T. (pu) est déjà écrit sur le document, REPRENDS-LE FIDÈLEMENT.\n"
            "   Si le devis est vierge de prix, ESTIME un prix unitaire HT réaliste en Dinars Algériens (DZD) selon les tarifs récents du BTP en Algérie.\n\n"
            "FORMAT DE RÉPONSE OBLIGATOIRE (JSON PUR SANS MARKDOWN NI TEXTE EN DEHORS) :\n"
            "{\n"
            "  \"client\": \"Nom du client détecté ou vide\",\n"
            "  \"projet\": \"Nom du projet ou chantier détecté ou vide\",\n"
            "  \"articles\": [\n"
            "    {\n"
            "      \"lot\": \"LOT 01: TERRASSEMENTS\",\n"
            "      \"n\": 1,\n"
            "      \"d\": \"Fouille en pleine masse dans terrain de toute nature y compris évacuation\",\n"
            "      \"u\": \"m3\",\n"
            "      \"q\": 120.5,\n"
            "      \"pu\": 950.0\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        contents_list = [prompt_expert]
        if texte_descriptif and texte_descriptif.strip():
            contents_list.append(f"\n--- CONSIGNES DU CLIENT ---\n{texte_descriptif.strip()}")

        if file:
            file_bytes = await file.read()
            if file_bytes:
                content_type = file.content_type or "image/jpeg"
                contents_list.append({"mime_type": content_type, "data": file_bytes})

        total_keys = len(keys_pool)
        last_error = ""

        # Ordre des modèles optimisé : prioriser le modèle en cache s'il fonctionne
        modeles_a_tester = list(MODELS_PRIORITY)
        if working_model_cache and working_model_cache in modeles_a_tester:
            modeles_a_tester.remove(working_model_cache)
            modeles_a_tester.insert(0, working_model_cache)

        for attempt in range(total_keys):
            selected_key_idx = (current_key_index + attempt) % total_keys
            api_key = keys_pool[selected_key_idx]
            genai.configure(api_key=api_key)

            for model_name in modeles_a_tester:
                try:
                    model = genai.GenerativeModel(model_name=model_name)
                    
                    # Tentative avec mode JSON structuré natif
                    try:
                        response = model.generate_content(
                            contents_list,
                            generation_config={
                                "max_output_tokens": 8192,
                                "temperature": 0.1,
                                "response_mime_type": "application/json"
                            }
                        )
                    except Exception:
                        response = model.generate_content(
                            contents_list,
                            generation_config={
                                "max_output_tokens": 8192,
                                "temperature": 0.1
                            }
                        )

                    raw_text = (response.text or "").strip()
                    if not raw_text:
                        continue

                    # Nettoyage JSON
                    clean_json = raw_text
                    if "```json" in clean_json:
                        clean_json = clean_json.split("```json", 1)[1]
                    if "```" in clean_json:
                        clean_json = clean_json.split("```", 1)[0]
                    clean_json = clean_json.strip()

                    parsed_data = None
                    try:
                        parsed_data = json.loads(clean_json)
                    except Exception:
                        # Sauvetage par recherche d'accolades ou de crochets
                        s_obj = clean_json.find('{')
                        e_obj = clean_json.rfind('}')
                        if s_obj != -1 and e_obj != -1:
                            try:
                                parsed_data = json.loads(clean_json[s_obj:e_obj+1])
                            except Exception:
                                pass
                        if not parsed_data:
                            s_arr = clean_json.find('[')
                            e_arr = clean_json.rfind(']')
                            if s_arr != -1 and e_arr != -1:
                                try:
                                    parsed_data = json.loads(clean_json[s_arr:e_arr+1])
                                except Exception:
                                    pass

                    detected_client = ""
                    detected_project = ""
                    raw_articles = []

                    if isinstance(parsed_data, dict):
                        detected_client = str(parsed_data.get("client") or "").strip()
                        detected_project = str(parsed_data.get("projet") or "").strip()
                        raw_articles = parsed_data.get("articles") or []
                    elif isinstance(parsed_data, list):
                        raw_articles = parsed_data
                    else:
                        # Sauvetage d'urgence par regex : aucun article n'est perdu
                        raw_articles = extraire_articles_partiels(clean_json)

                    articles_valides = []
                    for item in raw_articles:
                        if isinstance(item, dict) and ("d" in item or "designation" in item):
                            lot_nom = str(item.get("lot") or "TRAVAUX GÉNÉRAUX").strip()
                            desig = str(item.get("d") or item.get("designation") or "Article BTP").strip()
                            unit = str(item.get("u") or item.get("unite") or "U").strip()
                            try:
                                qte = float(str(item.get("q", 1)).replace(',', '.').replace(' ', '') or 1.0)
                            except Exception:
                                qte = 1.0
                            try:
                                pu = float(str(item.get("pu", 0)).replace(',', '.').replace(' ', '') or 0.0)
                            except Exception:
                                pu = 0.0

                            num = int(item.get("n") or (len(articles_valides) + 1))
                            articles_valides.append({
                                "lot": lot_nom,
                                "n": num,
                                "d": desig,
                                "u": unit,
                                "q": round(qte, 3),
                                "pu": round(pu, 2),
                                "total": round(qte * pu, 2)
                            })

                    # Mémoriser la clé et le modèle fonctionnel
                    working_model_cache = model_name
                    current_key_index = selected_key_idx

                    return JSONResponse(content={
                        "page": page_num,
                        "client": detected_client,
                        "projet": detected_project,
                        "raw_json": json.dumps(articles_valides, ensure_ascii=False),
                        "articles": articles_valides,
                        "model_used": model_name
                    })

                except Exception as inner_e:
                    last_error = str(inner_e)
                    err_lower = last_error.lower()
                    if "404" in err_lower or "not found" in err_lower:
                        continue
                    elif "429" in err_lower or "quota" in err_lower or "resource_exhausted" in err_lower:
                        break  # Clé saturée, passer à la clé suivante
                    else:
                        continue

        raise HTTPException(
            status_code=500,
            detail=f"Erreur d'analyse IA : {last_error or 'Toutes les clés ou modèles sont momentanément occupés.'}"
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Exportation Professionnelle Excel par Lots ---
@app.post("/exporter-excel")
async def exporter_excel(payload: dict = Body(...)):
    try:
        nom_client = payload.get("nom_client", "Client").strip() or "Client"
        nom_projet = payload.get("nom_projet", "").strip() or f"Chantier {nom_client}"
        num_devis = payload.get("num_devis", "DEV-" + time.strftime("%Y%m%d")).strip()
        date_devis = payload.get("date_devis", time.strftime("%d/%m/%Y")).strip()
        taux_tva = float(payload.get("taux_tva", 19.0))
        remise_pct = float(payload.get("remise_pct", 0.0))
        entreprise = payload.get("entreprise", {})
        articles = payload.get("articles", [])

        if not articles:
            raise HTTPException(status_code=400, detail="Aucun article à exporter.")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Devis Estimatif BTP"
        ws.views.sheetView[0].showGridLines = True

        # Styles typographiques et palettes
        c_bleu_nuit = "1E3A8A"     # Titres et en-tête principal
        c_bleu_lot = "DBEAFE"      # Bannière de lot
        c_bleu_total = "EFF6FF"    # Cadre des totaux
        c_gris_bord = "94A3B8"     # Bordures légères

        font_titre = Font(name="Calibri", size=15, bold=True, color=c_bleu_nuit)
        font_sub = Font(name="Calibri", size=10, bold=False, color="475569")
        font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        font_lot = Font(name="Calibri", size=11, bold=True, color=c_bleu_nuit)
        font_subtotal = Font(name="Calibri", size=10, bold=True, color="1E3A8A")
        font_bold = Font(name="Calibri", size=10, bold=True)
        font_normal = Font(name="Calibri", size=10)

        fill_header = PatternFill(start_color=c_bleu_nuit, end_color=c_bleu_nuit, fill_type="solid")
        fill_lot = PatternFill(start_color=c_bleu_lot, end_color=c_bleu_lot, fill_type="solid")
        fill_subtotal = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        fill_total = PatternFill(start_color=c_bleu_total, end_color=c_bleu_total, fill_type="solid")

        thin_side = Side(style='thin', color=c_gris_bord)
        thick_side = Side(style='medium', color=c_bleu_nuit)
        double_side = Side(style='double', color=c_bleu_nuit)

        border_cell = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
        border_subtotal = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thick_side)
        border_grand_total = Border(left=thin_side, right=thin_side, top=thick_side, bottom=double_side)

        # 1. En-tête Entreprise (Gauche) et Client/Devis (Droite)
        ent_nom = entreprise.get("nom", "ENTREPRISE TRAVAUX BTP").upper()
        ent_tel = entreprise.get("tel", "")
        ent_adr = entreprise.get("adresse", "")
        ent_nif = entreprise.get("nif", "")
        ent_rc = entreprise.get("rc", "")

        ws['A1'] = ent_nom
        ws['A1'].font = font_titre
        
        info_lines = []
        if ent_adr: info_lines.append(f"Adresse : {ent_adr}")
        if ent_tel: info_lines.append(f"Tél : {ent_tel}")
        if ent_nif or ent_rc: info_lines.append(f"NIF : {ent_nif} | RC : {ent_rc}")
        if not info_lines: info_lines = ["Entreprise Générale de Bâtiment et Travaux Publics"]

        ws['A2'] = info_lines[0]
        ws['A2'].font = font_sub
        if len(info_lines) > 1:
            ws['A3'] = info_lines[1]
            ws['A3'].font = font_sub
        if len(info_lines) > 2:
            ws['A4'] = info_lines[2]
            ws['A4'].font = font_sub

        # Bloc Devis & Client (Colonnes E & F)
        ws['E1'] = f"DEVIS ESTIMATIF N° {num_devis}"
        ws['E1'].font = font_lot
        ws['E1'].alignment = Alignment(horizontal="right")
        ws['E2'] = f"Date : {date_devis}"
        ws['E2'].font = font_sub
        ws['E2'].alignment = Alignment(horizontal="right")
        ws['E3'] = f"Client : {nom_client}"
        ws['E3'].font = font_bold
        ws['E3'].alignment = Alignment(horizontal="right")
        ws['E4'] = f"Projet : {nom_projet}"
        ws['E4'].font = font_sub
        ws['E4'].alignment = Alignment(horizontal="right")

        start_table_row = 6
        headers = ["N°", "Désignation des Travaux", "Unité", "Quantité", "P.U HT (DZD)", "Montant HT (DZD)"]
        for col_idx, h in enumerate(headers, start=1):
            c = ws.cell(row=start_table_row, column=col_idx, value=h)
            c.fill = fill_header
            c.font = font_header
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = border_cell

        current_row = start_table_row + 1
        dernier_lot = ""
        lot_start_row = current_row
        lots_subtotals_cells = []

        # Regrouper les articles par lot
        for idx, art in enumerate(articles):
            lot_nom = str(art.get("lot") or "TRAVAUX GÉNÉRAUX").strip()

            if dernier_lot and lot_nom != dernier_lot:
                sub_row = current_row
                ws.merge_cells(start_row=sub_row, start_column=1, end_row=sub_row, end_column=5)
                lbl_c = ws.cell(row=sub_row, column=1, value=f"SOUS-TOTAL {dernier_lot.upper()} (H.T) :")
                lbl_c.font = font_subtotal
                lbl_c.fill = fill_subtotal
                lbl_c.alignment = Alignment(horizontal="right", vertical="center", indent=1)

                val_c = ws.cell(row=sub_row, column=6, value=f"=SUM(F{lot_start_row}:F{sub_row-1})")
                val_c.font = font_subtotal
                val_c.fill = fill_subtotal
                val_c.number_format = '#,##0.00'
                val_c.alignment = Alignment(horizontal="right", vertical="center")

                for c_idx in range(1, 7):
                    ws.cell(row=sub_row, column=c_idx).border = border_subtotal

                lots_subtotals_cells.append((dernier_lot, f"F{sub_row}"))
                current_row += 1

            if lot_nom != dernier_lot:
                ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
                lot_cell = ws.cell(row=current_row, column=1, value=f"--- {lot_nom.upper()} ---")
                lot_cell.font = font_lot
                lot_cell.fill = fill_lot
                lot_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
                for c_idx in range(1, 7):
                    ws.cell(row=current_row, column=c_idx).border = border_cell

                dernier_lot = lot_nom
                current_row += 1
                lot_start_row = current_row

            num = art.get("n", idx + 1)
            desig = art.get("d", "Prestation")
            unite = art.get("u", "U")
            qte = float(art.get("q", 1) or 1.0)
            pu = float(art.get("pu", 0) or 0.0)

            c1 = ws.cell(row=current_row, column=1, value=num)
            c1.alignment = Alignment(horizontal="center", vertical="center")
            c1.font = font_normal

            c2 = ws.cell(row=current_row, column=2, value=desig)
            c2.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            c2.font = font_normal

            c3 = ws.cell(row=current_row, column=3, value=unite)
            c3.alignment = Alignment(horizontal="center", vertical="center")
            c3.font = font_normal

            c4 = ws.cell(row=current_row, column=4, value=qte)
            c4.number_format = '#,##0.00'
            c4.alignment = Alignment(horizontal="right", vertical="center")
            c4.font = font_normal

            c5 = ws.cell(row=current_row, column=5, value=pu)
            c5.number_format = '#,##0.00'
            c5.alignment = Alignment(horizontal="right", vertical="center")
            c5.font = font_normal

            c6 = ws.cell(row=current_row, column=6, value=f"=D{current_row}*E{current_row}")
            c6.number_format = '#,##0.00'
            c6.alignment = Alignment(horizontal="right", vertical="center")
            c6.font = font_normal

            for c_idx in range(1, 7):
                ws.cell(row=current_row, column=c_idx).border = border_cell

            current_row += 1

        if dernier_lot:
            sub_row = current_row
            ws.merge_cells(start_row=sub_row, start_column=1, end_row=sub_row, end_column=5)
            lbl_c = ws.cell(row=sub_row, column=1, value=f"SOUS-TOTAL {dernier_lot.upper()} (H.T) :")
            lbl_c.font = font_subtotal
            lbl_c.fill = fill_subtotal
            lbl_c.alignment = Alignment(horizontal="right", vertical="center", indent=1)

            val_c = ws.cell(row=sub_row, column=6, value=f"=SUM(F{lot_start_row}:F{sub_row-1})")
            val_c.font = font_subtotal
            val_c.fill = fill_subtotal
            val_c.number_format = '#,##0.00'
            val_c.alignment = Alignment(horizontal="right", vertical="center")

            for c_idx in range(1, 7):
                ws.cell(row=sub_row, column=c_idx).border = border_subtotal

            lots_subtotals_cells.append((dernier_lot, f"F{sub_row}"))
            current_row += 1

        # 2. Tableau Récapitulatif Général des Lots
        recap_start_row = current_row + 1
        ws.merge_cells(start_row=recap_start_row, start_column=2, end_row=recap_start_row, end_column=6)
        rc_header = ws.cell(row=recap_start_row, column=2, value="RÉCAPITULATIF GÉNÉRAL DES LOTS")
        rc_header.fill = fill_header
        rc_header.font = font_header
        rc_header.alignment = Alignment(horizontal="center", vertical="center")
        current_row = recap_start_row + 1

        recap_items_rows = []
        for nom_lot, ref_cell in lots_subtotals_cells:
            ws.merge_cells(start_row=current_row, start_column=2, end_row=current_row, end_column=5)
            lc = ws.cell(row=current_row, column=2, value=nom_lot.upper())
            lc.font = font_bold
            lc.alignment = Alignment(horizontal="left", vertical="center", indent=1)

            vc = ws.cell(row=current_row, column=6, value=f"={ref_cell}")
            vc.font = font_bold
            vc.number_format = '#,##0.00'
            vc.alignment = Alignment(horizontal="right", vertical="center")

            for c_idx in range(2, 7):
                ws.cell(row=current_row, column=c_idx).border = border_cell

            recap_items_rows.append(current_row)
            current_row += 1

        recap_sum_formula = "+".join([f"F{r}" for r in recap_items_rows]) if recap_items_rows else f"SUM(F{start_table_row+1}:F{current_row-1})"

        # 3. Totaux Financiers (Total HT, Remise, TVA, TTC)
        tot_ht_row = current_row
        ws.merge_cells(start_row=tot_ht_row, start_column=2, end_row=tot_ht_row, end_column=5)
        l_ht = ws.cell(row=tot_ht_row, column=2, value="TOTAL GÉNÉRAL H.T :")
        l_ht.font = font_bold
        l_ht.alignment = Alignment(horizontal="right", vertical="center")
        v_ht = ws.cell(row=tot_ht_row, column=6, value=f"={recap_sum_formula}")
        v_ht.font = font_bold
        v_ht.number_format = '#,##0.00 "DZD"'
        v_ht.alignment = Alignment(horizontal="right", vertical="center")
        for c_idx in range(2, 7):
            ws.cell(row=tot_ht_row, column=c_idx).border = border_cell
        current_row += 1

        active_ht_ref = f"F{tot_ht_row}"

        if remise_pct > 0:
            remise_row = current_row
            ws.merge_cells(start_row=remise_row, start_column=2, end_row=remise_row, end_column=5)
            l_rem = ws.cell(row=remise_row, column=2, value=f"REMISE EXCEPTIONNELLE ({remise_pct}%) :")
            l_rem.font = font_normal
            l_rem.alignment = Alignment(horizontal="right", vertical="center")
            v_rem = ws.cell(row=remise_row, column=6, value=f"=F{tot_ht_row}*{remise_pct/100:.4f}")
            v_rem.number_format = '#,##0.00 "DZD"'
            v_rem.alignment = Alignment(horizontal="right", vertical="center")
            for c_idx in range(2, 7):
                ws.cell(row=remise_row, column=c_idx).border = border_cell
            current_row += 1

            net_ht_row = current_row
            ws.merge_cells(start_row=net_ht_row, start_column=2, end_row=net_ht_row, end_column=5)
            l_net = ws.cell(row=net_ht_row, column=2, value="TOTAL H.T NET :")
            l_net.font = font_bold
            l_net.alignment = Alignment(horizontal="right", vertical="center")
            v_net = ws.cell(row=net_ht_row, column=6, value=f"=F{tot_ht_row}-F{remise_row}")
            v_net.font = font_bold
            v_net.number_format = '#,##0.00 "DZD"'
            v_net.alignment = Alignment(horizontal="right", vertical="center")
            for c_idx in range(2, 7):
                ws.cell(row=net_ht_row, column=c_idx).border = border_cell
            current_row += 1
            active_ht_ref = f"F{net_ht_row}"

        tva_row = current_row
        ws.merge_cells(start_row=tva_row, start_column=2, end_row=tva_row, end_column=5)
        l_tva = ws.cell(row=tva_row, column=2, value=f"T.V.A ({taux_tva:g}%) :")
        l_tva.font = font_bold
        l_tva.alignment = Alignment(horizontal="right", vertical="center")
        v_tva = ws.cell(row=tva_row, column=6, value=f"={active_ht_ref}*{taux_tva/100:.4f}")
        v_tva.font = font_bold
        v_tva.number_format = '#,##0.00 "DZD"'
        v_tva.alignment = Alignment(horizontal="right", vertical="center")
        for c_idx in range(2, 7):
            ws.cell(row=tva_row, column=c_idx).border = border_cell
        current_row += 1

        ttc_row = current_row
        ws.merge_cells(start_row=ttc_row, start_column=2, end_row=ttc_row, end_column=5)
        l_ttc = ws.cell(row=ttc_row, column=2, value="TOTAL GÉNÉRAL T.T.C :")
        l_ttc.font = font_titre
        l_ttc.fill = fill_total
        l_ttc.alignment = Alignment(horizontal="right", vertical="center")
        v_ttc = ws.cell(row=ttc_row, column=6, value=f"={active_ht_ref}+F{tva_row}")
        v_ttc.font = font_titre
        v_ttc.fill = fill_total
        v_ttc.number_format = '#,##0.00 "DZD"'
        v_ttc.alignment = Alignment(horizontal="right", vertical="center")
        for c_idx in range(2, 7):
            ws.cell(row=ttc_row, column=c_idx).border = border_grand_total
        current_row += 2

        # 4. Somme en toutes lettres
        total_ht_estime = sum([float(a.get("q", 1) or 1) * float(a.get("pu", 0) or 0) for a in articles])
        if remise_pct > 0:
            total_ht_estime *= (1 - remise_pct / 100)
        total_ttc_estime = total_ht_estime * (1 + taux_tva / 100)
        somme_lettres = nombre_en_lettres(total_ttc_estime)

        lettres_row = current_row
        ws.merge_cells(start_row=lettres_row, start_column=1, end_row=lettres_row, end_column=6)
        ws.cell(
            row=lettres_row,
            column=1,
            value=f"Arrêté le présent devis estimatif à la somme de : {somme_lettres} Toutes Taxes Comprises."
        ).font = font_bold
        ws.cell(row=lettres_row, column=1).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        current_row += 3

        # 5. Signatures et Cachets
        sig_row = current_row
        ws.merge_cells(start_row=sig_row, start_column=1, end_row=sig_row, end_column=3)
        s1 = ws.cell(row=sig_row, column=1, value="Pour l'Entreprise (Cachet et Signature)")
        s1.font = font_bold
        s1.alignment = Alignment(horizontal="center", vertical="center")

        ws.merge_cells(start_row=sig_row, start_column=4, end_row=sig_row, end_column=6)
        s2 = ws.cell(row=sig_row, column=4, value="Le Client (Bon pour accord)")
        s2.font = font_bold
        s2.alignment = Alignment(horizontal="center", vertical="center")

        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 58
        ws.column_dimensions['C'].width = 10
        ws.column_dimensions['D'].width = 14
        ws.column_dimensions['E'].width = 18
        ws.column_dimensions['F'].width = 24

        output_stream = io.BytesIO()
        wb.save(output_stream)
        output_stream.seek(0)

        nom_fichier_clean = re.sub(r'[^a-zA-Z0-9_-]', '_', nom_client)[:30] or "Devis"
        filename = f"Devis_BTP_{nom_fichier_clean}_{num_devis}.xlsx"

        return StreamingResponse(
            output_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))