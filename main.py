import os
import io
import re
import json
import time
import asyncio
from typing import List, Optional
from dotenv import load_dotenv

# Chargement automatique des variables d'environnement (.env)
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

# SDK Gemini moderne (google-genai) avec repli vers legacy (google.generativeai)
try:
    from google import genai
    from google.genai import types as genai_types
    HAS_NEW_GENAI = True
except ImportError:
    HAS_NEW_GENAI = False

import google.generativeai as legacy_genai
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

# Client Supabase pour la gestion des utilisateurs, devis et crédits BaridiMob
try:
    from supabase import create_client
except ImportError:
    create_client = None

app = FastAPI(
    title="Logiciel Devis BTP Algérie",
    description="Solution IA spécialisée dans le métré, le chiffrage par lots et l'exportation Excel/PDF aux normes algériennes (DZD).",
    version="2.1.0"
)

# Configuration CORS pour autoriser l'accès depuis n'importe quelle origine (PWA, mobile, local, Render)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Gestion du pool de clés API Gemini (Rotation intelligente) ---
current_key_index = 0

def get_api_keys_pool(client_key: str = None):
    """Récupère l'ensemble des clés Gemini disponibles, en priorisant la clé fournie par le client si présente."""
    keys = []
    if client_key and isinstance(client_key, str) and client_key.strip():
        keys.append(client_key.strip())

    for k, v in os.environ.items():
        k_upper = k.upper()
        if k_upper.startswith("GEMINI_KEY") or k_upper.startswith("GEMINI_API_KEY"):
            val = (v or "").strip()
            if val and val not in keys:
                keys.append(val)
    return keys

# Modèles Gemini par ordre d'efficacité pour le BTP (Testés en production)
MODELS_PRIORITY = [
    "gemini-3.5-flash",       # Modèle de référence : Ultra rapide (2-4s), haute fidélité métreur BTP
    "gemini-3.5-flash-lite",  # Très rapide (1s), ultra économique, quota distinct
    "gemini-3.1-flash-lite",  # Backup haute disponibilité
    "gemini-3.8-flash",       # Modèle supérieur
    "gemini-3-flash-preview", # Fallback
]

# --- Connexion Supabase résiliente ---
def get_supabase_client():
    """Initialise le client Supabase si configuré dans .env."""
    if not create_client:
        return None
    url = (os.environ.get("SUPABASE_URL") or "").strip()
    key = (os.environ.get("SUPABASE_KEY") or "").strip()
    if url and key:
        try:
            return create_client(url, key)
        except Exception:
            return None
    return None

# ============================================================
# PROMPT EXPERT MÉTREUR BTP, HYDRAULIQUE & TRAVAUX PUBLICS ALGÉRIE
# ============================================================
SYSTEM_PROMPT = """
Tu es un expert métreur-vérificateur senior spécialisé dans le Bâtiment (BTP), l'Hydraulique et les Travaux Publics (VRD) en Algérie.
Ton rôle est d'analyser ce document (page de devis, bordereau des prix unitaires BPU, devis quantitatif estimatif DQE issu d'une photo WhatsApp, d'un scan ou d'un fichier PDF mono ou multi-pages).

RÈGLE CARDINALE DE FIDÉLITÉ 1:1 AU BORDEREAU CLIENT :
1. CONFORMITÉ STRICTE LIGNE PAR LIGNE : Le bordereau final doit être la réplique exacte du document source.
2. INTERDICTION FORMELLE DE FUSIONNER OU DÉDUPLIQUER : Même si un article porte la même désignation ou se répète plusieurs fois dans le document (dans un même lot ou entre des sous-lots différents), TU DOIS IMPÉRATIVEMENT TRANSCRIRE CHAQUE LIGNE COMME UNE ENTRÉE DISTINCTE avec son numéro d'ordre séquentiel et sa quantité propre. Ne jamais regrouper ou éliminer de lignes.
3. RESPECT DE L'ORDRE DU BORDEREAU : Conserver fidèlement la séquence et la pagination du document client. Le client doit pouvoir réutiliser directement ce bordereau chiffré sans aucune divergence.

OBJECTIFS MÉTREUR :
1. Détecter et regrouper les travaux par LOTS BTP/VRD/HYDRAULIQUE explicites en majuscules (ex: "LOT 01: TERRASSEMENTS", "LOT 02: GROS-OEUVRE & BÉTON ARMÉ", "LOT 03: MAÇONNERIE", "LOT 04: ÉTANCHÉITÉ", "LOT 05: REVÊTEMENTS", "LOT 06: HYDRAULIQUE & ASSAINISSEMENT", "LOT 07: VOIRIE & TRAVAUX PUBLICS", etc.).
2. Si un prix unitaire ou une quantité est inscrit(e) sur le document, le recopier scrupuleusement.
3. Si le bordereau est vierge (sans prix), chiffrer chaque article selon le barème de référence algérien (DZD) :
   - Fouilles en rigole/tranchée : 900 à 1400 DZD/m3, fouille pleine masse : 500 à 800 DZD/m3
   - Béton armé pour semelles/longrines : 30000 à 38000 DZD/m3, poteaux/poutres en élévation : 34000 à 42000 DZD/m3
   - Plancher corps creux 16+4 : 3800 à 4500 DZD/m2, dallage BA 12cm : 2200 à 2600 DZD/m2
   - Maçonnerie 12T+8T : 2600 à 3200 DZD/m2, simple 12T : 1400 à 1800 DZD/m2, parpaings 20cm : 1600 à 2000 DZD/m2
   - Enduit ciment int : 800 à 1100 DZD/m2, ext étanche : 1100 à 1500 DZD/m2, plâtre : 700 à 900 DZD/m2
   - Étanchéité multicouche 36S : 2000 à 2500 DZD/m2, paxalu : 2200 à 2800 DZD/m2
   - Dalle de sol : 2800 à 3600 DZD/m2, grès cérame 60x60 : 4200 à 5500 DZD/m2, faïence : 2800 à 3500 DZD/m2
   - Conduites PEHD AEP : DN63 1000-1400 DZD/ml, DN90 1500-2000 DZD/ml, DN110 2200-2800 DZD/ml
   - Tuyaux PVC Assainissement : DN200 2400-3000 DZD/ml, DN250 3200-4000 DZD/ml, DN315 4800-5800 DZD/ml
   - Regards visite BA 100x100 : 28000 à 36000 DZD/U, tampon fonte D400 : 22000 à 28000 DZD/U
   - Décapage chaussée : 150 à 220 DZD/m2, couche de tuf : 2200 à 2800 DZD/m3, GNT 0/40 : 3000 à 3800 DZD/m3
   - Enrobé à chaud BB 0/10 (6cm) : 1900 à 2400 DZD/m2, bordures T2 : 1400 à 1800 DZD/ml, pavés autobloquants : 2000 à 2600 DZD/m2
4. Numéroter les articles (1, 2, 3...) séquentiellement par lot.
5. Standardiser les unités : m3, m2, ml, kg, tonne, U, ens, f, j.

FORMAT DE RÉPONSE STRICT (JSON PUR, AUCUN MARKDOWN, AUCUN TEXTE AUTOUR) :
{
  "client": "Nom du maître d'ouvrage ou client si présent, sinon ''",
  "projet": "Intitulé du projet ou chantier si présent, sinon ''",
  "articles": [
    {
      "lot": "LOT 01: GROS-OEUVRE",
      "n": 1,
      "d": "Béton armé pour semelles dosé à 350 kg/m3",
      "u": "m3",
      "q": 25.5,
      "pu": 34000.0
    }
  ]
}
"""

# ============================================================
# CONVERSION NOMBRES EN LETTRES (Normes BTP Algérie en DZD)
# ============================================================
def nombre_en_lettres(montant: float) -> str:
    """Convertit un montant numérique en toutes lettres en Dinars Algériens."""
    entier = int(abs(montant))
    centimes = int(round((abs(montant) - entier) * 100))

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
            if val in particuliers: return particuliers[val]
            d, u = divmod(val, 10)
            if d == 0: return unites[u]
            if d == 1: return ['dix', 'onze', 'douze', 'treize', 'quatorze', 'quinze', 'seize', 'dix-sept', 'dix-huit', 'dix-neuf'][u]
            if u == 1 and d not in (8, 9): return f"{dizaines[d]}-et-un"
            if u == 0: return dizaines[d]
            return f"{dizaines[d]}-{unites[u]}"

        def _inf_mille(val):
            c, r = divmod(val, 100)
            res = ""
            if c == 1: res = "cent"
            elif c > 1: res = f"{unites[c]} cent" + ("s" if r == 0 else "")
            if r > 0:
                sub = _inf_cent(r)
                res = f"{res} {sub}".strip()
            return res

        parts = []
        milliards, r = divmod(entier, 1000000000)
        millions, r = divmod(r, 1000000)
        mille, unites_val = divmod(r, 1000)

        if milliards: parts.append(f"{_inf_mille(milliards)} milliard" + ("s" if milliards > 1 else ""))
        if millions: parts.append(f"{_inf_mille(millions)} million" + ("s" if millions > 1 else ""))
        if mille:
            if mille == 1: parts.append("mille")
            else: parts.append(f"{_inf_mille(mille)} mille")
        if unites_val: parts.append(_inf_mille(unites_val))
        texte_entier = " ".join(parts).strip()

    texte_final = f"{texte_entier} Dinars Algériens"
    if centimes > 0:
        texte_final += f" et {centimes} centimes"
    else:
        texte_final += " et zéro centime"
    return texte_final.capitalize()

# ============================================================
# NETTOYAGE & VALIDATION DU JSON GEMINI
# ============================================================
def clean_and_parse_json(raw_text: str) -> dict:
    """Nettoie minutieusement la chaîne retournée par l'IA pour extraire un objet ou tableau JSON valide."""
    text = raw_text.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1]
    if "```" in text:
        text = text.split("```", 1)[0]
    text = text.strip()

    start_arr = text.find('[')
    start_obj = text.find('{')

    if start_obj != -1 and (start_arr == -1 or start_obj < start_arr):
        end_obj = text.rfind('}')
        if end_obj != -1:
            clean = text[start_obj:end_obj + 1]
            return json.loads(clean)
    elif start_arr != -1:
        end_arr = text.rfind(']')
        if end_arr != -1:
            clean = text[start_arr:end_arr + 1]
            articles = json.loads(clean)
            return {"client": "", "projet": "", "articles": articles}

    return json.loads(text)

# ============================================================
# GÉNÉRATEUR EXCEL PROFESSIONNEL MULTI-LOTS DZD
# ============================================================
def create_excel_multilots(payload: dict) -> io.BytesIO:
    """Génère un classeur Excel professionnel avec sous-totaux par lots, formules et récapitulatif."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Devis Estimatif BTP"
    ws.views.sheetView[0].showGridLines = True

    c_bleu_titre = "1E3A8A"
    c_bleu_banniere = "1E3A8A"
    c_bleu_lot = "DBEAFE"
    c_gris_table = "F8FAFC"
    c_gris_bord = "CBD5E1"

    font_titre_ent = Font(name="Calibri", size=14, bold=True, color=c_bleu_titre)
    font_sub_ent = Font(name="Calibri", size=9, color="475569")
    font_devis_titre = Font(name="Calibri", size=12, bold=True, color=c_bleu_titre)
    font_header_tab = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_lot = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_subtotal = Font(name="Calibri", size=10, bold=True, color=c_bleu_titre)
    font_bold = Font(name="Calibri", size=10, bold=True)
    font_normal = Font(name="Calibri", size=10)
    font_total_grand = Font(name="Calibri", size=12, bold=True, color=c_bleu_titre)

    fill_header = PatternFill(start_color=c_bleu_banniere, end_color=c_bleu_banniere, fill_type="solid")
    fill_lot = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    fill_subtotal = PatternFill(start_color=c_bleu_lot, end_color=c_bleu_lot, fill_type="solid")
    fill_total = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")

    thin_border = Border(
        left=Side(style="thin", color=c_gris_bord),
        right=Side(style="thin", color=c_gris_bord),
        top=Side(style="thin", color=c_gris_bord),
        bottom=Side(style="thin", color=c_gris_bord)
    )
    thick_bottom = Border(
        left=Side(style="thin", color=c_gris_bord),
        right=Side(style="thin", color=c_gris_bord),
        top=Side(style="thin", color=c_gris_bord),
        bottom=Side(style="medium", color=c_bleu_titre)
    )
    double_bottom = Border(
        left=Side(style="thin", color=c_gris_bord),
        right=Side(style="thin", color=c_gris_bord),
        top=Side(style="thin", color=c_gris_bord),
        bottom=Side(style="double", color=c_bleu_titre)
    )

    dzd_format = '#,##0.00 "DZD"'
    qte_format = '#,##0.00'

    ent = payload.get("entreprise", {})
    nom_client = (payload.get("nom_client") or "Client").strip()
    nom_projet = (payload.get("nom_projet") or f"Chantier {nom_client}").strip()
    num_devis = (payload.get("num_devis") or "DEV-" + time.strftime("%Y%m%d")).strip()
    date_devis = (payload.get("date_devis") or time.strftime("%d/%m/%Y")).strip()
    email_client = (payload.get("email_client") or "").strip()
    tel_client = (payload.get("tel_client") or "").strip()
    taux_tva = float(payload.get("taux_tva", 19.0))
    remise_pct = float(payload.get("remise_pct", 0.0))
    articles_bruts = payload.get("articles", [])

    # 1. En-tête Entreprise
    ws.merge_cells("A1:C1")
    ws["A1"] = (ent.get("nom") or "ENTREPRISE TRAVAUX BTP").upper()
    ws["A1"].font = font_titre_ent

    coord_lines = []
    if ent.get("adresse"): coord_lines.append(f"Adresse : {ent.get('adresse')}")
    tel_email = []
    if ent.get("tel"): tel_email.append(f"Tél : {ent.get('tel')}")
    if ent.get("email"): tel_email.append(f"Email : {ent.get('email')}")
    if tel_email: coord_lines.append(" | ".join(tel_email))
    if ent.get("nif") or ent.get("rc"): coord_lines.append(f"NIF : {ent.get('nif', '')}  |  RC : {ent.get('rc', '')}")
    if not coord_lines: coord_lines = ["Entreprise Générale de Bâtiment et Travaux Publics"]

    for idx, l in enumerate(coord_lines[:3], start=2):
        ws.merge_cells(f"A{idx}:C{idx}")
        ws[f"A{idx}"] = l
        ws[f"A{idx}"].font = font_sub_ent

    # 2. En-tête Devis & Client (à droite)
    ws.merge_cells("D1:F1")
    ws["D1"] = f"DEVIS ESTIMATIF N° {num_devis}"
    ws["D1"].font = font_devis_titre
    ws["D1"].alignment = Alignment(horizontal="right")

    ws.merge_cells("D2:F2")
    ws["D2"] = f"Date : {date_devis}"
    ws["D2"].font = font_bold
    ws["D2"].alignment = Alignment(horizontal="right")

    ws.merge_cells("D3:F3")
    ws["D3"] = f"Client : {nom_client}"
    ws["D3"].font = font_bold
    ws["D3"].alignment = Alignment(horizontal="right")

    ws.merge_cells("D4:F4")
    ws["D4"] = f"Projet : {nom_projet}"
    ws["D4"].font = font_sub_ent
    ws["D4"].alignment = Alignment(horizontal="right")

    coord_client_list = []
    if email_client: coord_client_list.append(f"Email : {email_client}")
    if tel_client: coord_client_list.append(f"Tél : {tel_client}")
    if coord_client_list:
        ws.merge_cells("D5:F5")
        ws["D5"] = " | ".join(coord_client_list)
        ws["D5"].font = font_sub_ent
        ws["D5"].alignment = Alignment(horizontal="right")

    ws.column_dimensions["A"].width = 7
    ws.column_dimensions["B"].width = 56
    ws.column_dimensions["C"].width = 9
    ws.column_dimensions["D"].width = 13
    ws.column_dimensions["E"].width = 17
    ws.column_dimensions["F"].width = 23

    lots_dict = {}
    for art in articles_bruts:
        l_nom = (art.get("lot") or "TRAVAUX GÉNÉRAUX").strip().upper()
        lots_dict.setdefault(l_nom, []).append(art)

    current_row = 7 if coord_client_list else 6
    lots_subtotals_refs = []

    for lot_nom, liste_art in lots_dict.items():
        ws.merge_cells(f"A{current_row}:F{current_row}")
        c_lot = ws.cell(row=current_row, column=1, value=f"--- {lot_nom} ---")
        c_lot.fill = fill_lot
        c_lot.font = font_lot
        c_lot.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[current_row].height = 22
        current_row += 1

        headers = ["N°", "Désignation des Travaux", "Unité", "Quantité", "P.U HT (DZD)", "Montant HT (DZD)"]
        for col_idx, h in enumerate(headers, start=1):
            hc = ws.cell(row=current_row, column=col_idx, value=h)
            hc.fill = fill_header
            hc.font = font_header_tab
            hc.border = thin_border
            hc.alignment = Alignment(horizontal="center" if col_idx in [1, 3] else "left", vertical="center")
        current_row += 1

        lot_first_art_row = current_row
        for idx, art in enumerate(liste_art, start=1):
            q = float(art.get("q") or 1.0)
            pu = float(art.get("pu") or 0.0)

            ws.cell(row=current_row, column=1, value=idx).alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=current_row, column=2, value=art.get("d", "Article")).alignment = Alignment(wrap_text=True, vertical="center")
            ws.cell(row=current_row, column=3, value=art.get("u", "U")).alignment = Alignment(horizontal="center", vertical="center")

            qc = ws.cell(row=current_row, column=4, value=q)
            qc.number_format = qte_format
            qc.alignment = Alignment(horizontal="right", vertical="center")

            puc = ws.cell(row=current_row, column=5, value=pu)
            puc.number_format = dzd_format
            puc.alignment = Alignment(horizontal="right", vertical="center")

            totc = ws.cell(row=current_row, column=6, value=f"=D{current_row}*E{current_row}")
            totc.number_format = dzd_format
            totc.alignment = Alignment(horizontal="right", vertical="center")

            for c in range(1, 7):
                ws.cell(row=current_row, column=c).border = thin_border
                ws.cell(row=current_row, column=c).font = font_normal

            current_row += 1

        lot_last_art_row = current_row - 1

        ws.merge_cells(f"A{current_row}:E{current_row}")
        st_lbl = ws.cell(row=current_row, column=1, value=f"SOUS-TOTAL {lot_nom} (H.T) :")
        st_lbl.font = font_subtotal
        st_lbl.fill = fill_subtotal
        st_lbl.alignment = Alignment(horizontal="right", vertical="center", indent=1)

        st_val = ws.cell(row=current_row, column=6, value=f"=SUM(F{lot_first_art_row}:F{lot_last_art_row})")
        st_val.font = font_subtotal
        st_val.fill = fill_subtotal
        st_val.number_format = dzd_format
        st_val.alignment = Alignment(horizontal="right", vertical="center")

        for c in range(1, 7):
            ws.cell(row=current_row, column=c).border = thick_bottom

        lots_subtotals_refs.append((lot_nom, f"F{current_row}"))
        current_row += 2

    # 3. Tableau Récapitulatif Général des Lots
    recap_start_row = current_row
    ws.merge_cells(f"B{recap_start_row}:F{recap_start_row}")
    rc_h = ws.cell(row=recap_start_row, column=2, value="RÉCAPITULATIF GÉNÉRAL DES LOTS")
    rc_h.fill = fill_header
    rc_h.font = font_header_tab
    rc_h.alignment = Alignment(horizontal="center", vertical="center")
    current_row += 1

    recap_val_rows = []
    for l_nom, ref in lots_subtotals_refs:
        ws.merge_cells(f"B{current_row}:E{current_row}")
        l_cell = ws.cell(row=current_row, column=2, value=l_nom)
        l_cell.font = font_bold
        l_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)

        v_cell = ws.cell(row=current_row, column=6, value=f"={ref}")
        v_cell.font = font_bold
        v_cell.number_format = dzd_format
        v_cell.alignment = Alignment(horizontal="right", vertical="center")

        for c in range(2, 7):
            ws.cell(row=current_row, column=c).border = thin_border
        recap_val_rows.append(current_row)
        current_row += 1

    recap_formula = "+".join([f"F{r}" for r in recap_val_rows]) if recap_val_rows else "0"

    # 4. Totaux Financiers
    tot_ht_row = current_row
    ws.merge_cells(f"B{tot_ht_row}:E{tot_ht_row}")
    ws.cell(row=tot_ht_row, column=2, value="TOTAL GÉNÉRAL H.T :").font = font_bold
    ws.cell(row=tot_ht_row, column=2).alignment = Alignment(horizontal="right", vertical="center")

    tot_ht_val = ws.cell(row=tot_ht_row, column=6, value=f"={recap_formula}")
    tot_ht_val.font = font_bold
    tot_ht_val.number_format = dzd_format
    tot_ht_val.alignment = Alignment(horizontal="right", vertical="center")
    for c in range(2, 7): ws.cell(row=tot_ht_row, column=c).border = thin_border
    current_row += 1

    active_ht_ref = f"F{tot_ht_row}"

    if remise_pct > 0:
        rem_row = current_row
        ws.merge_cells(f"B{rem_row}:E{rem_row}")
        ws.cell(row=rem_row, column=2, value=f"REMISE ({remise_pct:g}%) :").font = font_normal
        ws.cell(row=rem_row, column=2).alignment = Alignment(horizontal="right", vertical="center")

        rem_val = ws.cell(row=rem_row, column=6, value=f"=F{tot_ht_row}*{remise_pct/100:.4f}")
        rem_val.font = font_normal
        rem_val.number_format = dzd_format
        rem_val.alignment = Alignment(horizontal="right", vertical="center")
        for c in range(2, 7): ws.cell(row=rem_row, column=c).border = thin_border
        current_row += 1

        net_ht_row = current_row
        ws.merge_cells(f"B{net_ht_row}:E{net_ht_row}")
        ws.cell(row=net_ht_row, column=2, value="TOTAL H.T NET :").font = font_bold
        ws.cell(row=net_ht_row, column=2).alignment = Alignment(horizontal="right", vertical="center")

        net_val = ws.cell(row=net_ht_row, column=6, value=f"=F{tot_ht_row}-F{rem_row}")
        net_val.font = font_bold
        net_val.number_format = dzd_format
        net_val.alignment = Alignment(horizontal="right", vertical="center")
        for c in range(2, 7): ws.cell(row=net_ht_row, column=c).border = thin_border
        current_row += 1
        active_ht_ref = f"F{net_ht_row}"

    tva_row = current_row
    ws.merge_cells(f"B{tva_row}:E{tva_row}")
    ws.cell(row=tva_row, column=2, value=f"T.V.A ({taux_tva:g}%) :").font = font_bold
    ws.cell(row=tva_row, column=2).alignment = Alignment(horizontal="right", vertical="center")

    tva_val = ws.cell(row=tva_row, column=6, value=f"={active_ht_ref}*{taux_tva/100:.4f}")
    tva_val.font = font_bold
    tva_val.number_format = dzd_format
    tva_val.alignment = Alignment(horizontal="right", vertical="center")
    for c in range(2, 7): ws.cell(row=tva_row, column=c).border = thin_border
    current_row += 1

    ttc_row = current_row
    ws.merge_cells(f"B{ttc_row}:E{ttc_row}")
    lbl_ttc = ws.cell(row=ttc_row, column=2, value="TOTAL GÉNÉRAL T.T.C :")
    lbl_ttc.font = font_total_grand
    lbl_ttc.fill = fill_total
    lbl_ttc.alignment = Alignment(horizontal="right", vertical="center")

    ttc_val = ws.cell(row=ttc_row, column=6, value=f"={active_ht_ref}+F{tva_row}")
    ttc_val.font = font_total_grand
    ttc_val.fill = fill_total
    ttc_val.number_format = dzd_format
    ttc_val.alignment = Alignment(horizontal="right", vertical="center")
    for c in range(2, 7): ws.cell(row=ttc_row, column=c).border = double_bottom
    current_row += 2

    # 5. Mention en toutes lettres
    total_ht_est = sum([float(a.get("q", 1) or 1) * float(a.get("pu", 0) or 0) for a in articles_bruts])
    if remise_pct > 0: total_ht_est *= (1 - remise_pct / 100)
    total_ttc_est = total_ht_est * (1 + taux_tva / 100)

    lettres_row = current_row
    ws.merge_cells(f"A{lettres_row}:F{lettres_row}")
    ws.cell(
        row=lettres_row,
        column=1,
        value=f"Arrêté le présent devis estimatif à la somme de : {nombre_en_lettres(total_ttc_est)} Toutes Taxes Comprises."
    ).font = font_bold
    ws.cell(row=lettres_row, column=1).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    current_row += 3

    # 6. Signatures et Cachets
    sig_row = current_row
    ws.merge_cells(f"A{sig_row}:C{sig_row+3}")
    s1 = ws.cell(row=sig_row, column=1, value="Pour l'Entreprise\n(Signature et Cachet)")
    s1.font = font_bold
    s1.alignment = Alignment(horizontal="center", vertical="top", wrap_text=True)
    s1.border = Border(left=Side(style="medium"), right=Side(style="medium"), top=Side(style="medium"), bottom=Side(style="medium"))

    ws.merge_cells(f"D{sig_row}:F{sig_row+3}")
    s2 = ws.cell(row=sig_row, column=4, value="Le Client\n(Bon pour accord - Signature)")
    s2.font = font_bold
    s2.alignment = Alignment(horizontal="center", vertical="top", wrap_text=True)
    s2.border = Border(left=Side(style="medium"), right=Side(style="medium"), top=Side(style="medium"), bottom=Side(style="medium"))

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

# ============================================================
# ENDPOINTS API & INTERFACE WEB
# ============================================================

@app.get("/")
def serve_index():
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"status": "ok", "message": "Serveur BTP opérationnel."}

@app.get("/manifest.json")
def serve_manifest():
    manifest_path = os.path.join(os.path.dirname(__file__), "manifest.json")
    if os.path.exists(manifest_path):
        return FileResponse(manifest_path, media_type="application/manifest+json")
    raise HTTPException(status_code=404, detail="manifest.json non trouvé")

@app.get("/sw.js")
def serve_sw():
    sw_path = os.path.join(os.path.dirname(__file__), "sw.js")
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="sw.js non trouvé")

@app.get("/bpu_algerie.json")
def serve_bpu_json():
    bpu_path = os.path.join(os.path.dirname(__file__), "bpu_algerie.json")
    if os.path.exists(bpu_path):
        return FileResponse(bpu_path, media_type="application/json")
    raise HTTPException(status_code=404, detail="bpu_algerie.json non trouvé")

@app.get("/status")
@app.get("/api/status")
def api_status():
    keys = get_api_keys_pool()
    return {
        "status": "ok",
        "keys_count": len(keys),
        "models_priority": MODELS_PRIORITY,
        "message": f"Serveur opérationnel avec {len(keys)} clé(s) Gemini."
    }

@app.get("/api/bpu")
def get_bpu(categorie: str = None, q: str = None):
    """Retourne les articles de la base de données des prix unitaires récents (BTP, Hydraulique, VRD)."""
    bpu_path = os.path.join(os.path.dirname(__file__), "bpu_algerie.json")
    if not os.path.exists(bpu_path):
        return []
    with open(bpu_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if categorie and categorie.strip() and categorie.strip().upper() != "TOUS":
        cat_lower = categorie.strip().lower()
        data = [item for item in data if item.get("categorie", "").lower() == cat_lower]
    if q and q.strip():
        query = q.strip().lower()
        data = [
            item for item in data 
            if query in item.get("designation", "").lower() 
            or query in item.get("lot", "").lower() 
            or query in item.get("description", "").lower()
            or query in item.get("code", "").lower()
        ]
    return data

def call_gemini_sync(api_key: str, model_name: str, contents_parts: list) -> str:
    """Appelle l'API Gemini de façon synchrone en utilisant en priorité le nouveau SDK google-genai."""
    if HAS_NEW_GENAI:
        client = genai.Client(api_key=api_key)
        parts = []
        for item in contents_parts:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "data" in item:
                parts.append(genai_types.Part.from_bytes(data=item["data"], mime_type=item.get("mime_type", "image/jpeg")))
        
        response = client.models.generate_content(
            model=model_name,
            contents=parts,
            config=genai_types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=8192
            )
        )
        return response.text or "{}"

    # Repli sur le SDK historique google.generativeai
    legacy_genai.configure(api_key=api_key)
    mod = legacy_genai.GenerativeModel(model_name)
    response = mod.generate_content(
        contents_parts,
        generation_config={"max_output_tokens": 8192, "temperature": 0.1}
    )
    return response.text or "{}"

@app.post("/chiffrer-page")
async def chiffrer_page(
    file: UploadFile = File(None),
    files: Optional[List[UploadFile]] = File(None),
    texte_descriptif: str = Form(None),
    page_num: int = Form(1),
    telephone: str = Form(None),
    gemini_key: str = Form(None),
    strategie_prix: str = Form("moins_disant"),
    region: str = Form("centre")
):
    global current_key_index

    keys_pool = get_api_keys_pool(client_key=gemini_key)
    if not keys_pool:
        raise HTTPException(
            status_code=500,
            detail="Aucune clé Gemini configurée. Veuillez ajouter votre clé Gemini dans l'interface ou dans les paramètres du serveur."
        )

    # Directives contextuelles selon la stratégie commerciale et la région
    instructions_strategie = ""
    if strategie_prix == "moins_disant":
        instructions_strategie += (
            "\n--- STRATÉGIE TARIFAIRE : MOINS-DISANT (APPEL D'OFFRES / SOUMISSION COMPÉTITIVE) ---\n"
            "Le client souhaite une offre agressive et compétitive pour remporter le marché public ou privé.\n"
            "Pour chaque article sans prix mentionné, applique le PRIX PLANCHER RÉALISTE (la borne inférieure du barème BPU algérien),\n"
            "tout en restant dans un cadre économiquement viable pour l'entrepreneur sans être anormalement bas.\n"
        )
    elif strategie_prix == "marge":
        instructions_strategie += (
            "\n--- STRATÉGIE TARIFAIRE : MARGE SÉCURISÉE (CLIENT PRIVÉ / TRAVAUX COMPLEXES) ---\n"
            "Applique des prix unitaires situés dans la tranche haute du marché algérien (marge de confort sécurisée).\n"
        )
    else:  # prix moyen
        instructions_strategie += (
            "\n--- STRATÉGIE TARIFAIRE : PRIX MOYEN DU MARCHÉ (STANDARD ALGÉRIE) ---\n"
            "Applique les prix unitaires médians constatés sur les chantiers et mercuriales de prix en Algérie.\n"
        )

    if region == "sud":
        instructions_strategie += (
            "\n--- ZONE GÉOGRAPHIQUE : SUD ALGÉRIEN & HAUTS-PLATEAUX ---\n"
            "Tenir compte de la majoration d'éloignement et du transport des matériaux/agrégats (+8% à +15% sur les bétons et enrobés).\n"
        )

    contents_list = [SYSTEM_PROMPT + instructions_strategie]
    if texte_descriptif and isinstance(texte_descriptif, str) and texte_descriptif.strip():
        contents_list.append(f"\n--- NOTES DU CLIENT ---\n{texte_descriptif.strip()}")

    # Collecte de tous les fichiers envoyés (page unique ou ensemble de pages découpées/images)
    fichiers_a_traiter = []
    if files:
        if isinstance(files, list):
            fichiers_a_traiter.extend(files)
        else:
            fichiers_a_traiter.append(files)
    if file and file not in fichiers_a_traiter:
        fichiers_a_traiter.append(file)

    for f_item in fichiers_a_traiter:
        if f_item:
            file_bytes = await f_item.read()
            if file_bytes:
                content_type = f_item.content_type or "image/jpeg"
                if f_item.filename and f_item.filename.lower().endswith(".pdf"):
                    content_type = "application/pdf"
                contents_list.append({"mime_type": content_type, "data": file_bytes})

    total_keys = len(keys_pool)
    last_error = ""

    for attempt in range(total_keys):
        key_idx = (current_key_index + attempt) % total_keys
        api_key = keys_pool[key_idx]

        for model_name in MODELS_PRIORITY:
            try:
                # Exécution asynchrone non-bloquante pour ne jamais geler le serveur
                raw_text = await asyncio.to_thread(call_gemini_sync, api_key, model_name, contents_list)
                parsed = clean_and_parse_json(raw_text or "{}")
                articles = parsed.get("articles", []) if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])

                articles_propres = []
                for idx, art in enumerate(articles, start=1):
                    if isinstance(art, dict):
                        lot_nom = str(art.get("lot") or "TRAVAUX GÉNÉRAUX").strip().upper()
                        desig = str(art.get("d") or "Prestation BTP").strip()
                        unite = str(art.get("u") or "U").strip()
                        try:
                            qte = float(str(art.get("q", 1)).replace(',', '.').replace(' ', '') or 1.0)
                        except Exception:
                            qte = 1.0
                        try:
                            pu = float(str(art.get("pu", 0)).replace(',', '.').replace(' ', '') or 0.0)
                        except Exception:
                            pu = 0.0

                        articles_propres.append({
                            "lot": lot_nom,
                            "n": int(art.get("n") or idx),
                            "d": desig,
                            "u": unite,
                            "q": round(qte, 3),
                            "pu": round(pu, 2),
                            "total": round(qte * pu, 2)
                        })

                current_key_index = (key_idx + 1) % total_keys

                # Décompte automatique du crédit page dans Supabase
                credits_restants = None
                sb = get_supabase_client()
                if sb and telephone and isinstance(telephone, str):
                    try:
                        tel_clean = re.sub(r'[^0-9+]', '', telephone)
                        c_res = sb.table("clients").select("id, credits_pages").eq("telephone", tel_clean).execute()
                        if c_res.data and len(c_res.data) > 0:
                            solde = c_res.data[0].get("credits_pages", 0)
                            if solde > 0:
                                solde -= 1
                                sb.table("clients").update({"credits_pages": solde}).eq("id", c_res.data[0]["id"]).execute()
                            credits_restants = solde
                    except Exception:
                        pass

                return {
                    "success": True,
                    "page": page_num,
                    "client": parsed.get("client", "") if isinstance(parsed, dict) else "",
                    "projet": parsed.get("projet", "") if isinstance(parsed, dict) else "",
                    "articles": articles_propres,
                    "raw_json": json.dumps(articles_propres, ensure_ascii=False),
                    "model_used": model_name,
                    "credits_restants": credits_restants
                }

            except Exception as inner_e:
                last_error = str(inner_e)
                # Basculer immédiatement sur le modèle suivant de la liste sans bloquer
                continue

    raise HTTPException(
        status_code=429,
        detail=f"Toutes les clés et modèles Gemini sont temporairement indisponibles. Détail : {last_error}"
    )

@app.post("/exporter-excel")
async def exporter_excel(payload: dict = Body(...)):
    try:
        articles = payload.get("articles", [])
        if not articles:
            raise HTTPException(status_code=400, detail="Aucun article à exporter.")

        excel_stream = create_excel_multilots(payload)
        nom_client = re.sub(r'[^a-zA-Z0-9_-]', '_', payload.get("nom_client", "Client"))[:25] or "Client"
        num_devis = re.sub(r'[^a-zA-Z0-9_-]', '_', payload.get("num_devis", "DEV-01"))[:20] or "DEV-01"
        filename = f"Devis_BTP_{nom_client}_{num_devis}.xlsx"

        return StreamingResponse(
            excel_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de génération Excel : {str(e)}")

# ============================================================
# ENDPOINTS SUPABASE : CLIENTS, DEVIS & PAIEMENTS BARIDIMOB
# ============================================================

@app.post("/api/clients/connexion")
async def client_connexion(payload: dict = Body(...)):
    telephone_brut = (payload.get("telephone") or "").strip()
    nom_complet = (payload.get("nom_complet") or "").strip() or "Artisan BTP"
    wilaya = (payload.get("wilaya") or "Alger").strip()
    
    tel_clean = re.sub(r'[^0-9+]', '', telephone_brut)
    if not tel_clean or len(tel_clean) < 8:
        raise HTTPException(status_code=400, detail="Numéro de téléphone algérien invalide.")
        
    sb = get_supabase_client()
    if not sb:
        return {
            "success": True,
            "mode": "local",
            "client": {
                "id": "local_user",
                "telephone": tel_clean,
                "nom_complet": nom_complet,
                "credits_pages": 10,
                "type_abonnement": "gratuit"
            }
        }
        
    try:
        res = sb.table("clients").select("*").eq("telephone", tel_clean).execute()
        if res.data and len(res.data) > 0:
            client = res.data[0]
            return {"success": True, "nouveau": False, "client": client}
        else:
            new_client = {
                "nom_complet": nom_complet,
                "telephone": tel_clean,
                "wilaya": wilaya,
                "type_abonnement": "gratuit",
                "credits_pages": 5
            }
            ins = sb.table("clients").insert(new_client).execute()
            created = ins.data[0] if ins.data else new_client
            return {"success": True, "nouveau": True, "client": created}
    except Exception as e:
        return {
            "success": True,
            "mode": "fallback_local",
            "message": f"Supabase en attente d'initialisation SQL ({str(e)}).",
            "client": {
                "id": "local_user",
                "telephone": tel_clean,
                "nom_complet": nom_complet,
                "credits_pages": 5,
                "type_abonnement": "gratuit"
            }
        }

@app.get("/api/clients/profil/{telephone}")
async def get_client_profil(telephone: str):
    tel_clean = re.sub(r'[^0-9+]', '', telephone)
    sb = get_supabase_client()
    if not sb:
        return {"success": True, "client": {"telephone": tel_clean, "credits_pages": 10, "type_abonnement": "gratuit"}}
    try:
        res = sb.table("clients").select("*").eq("telephone", tel_clean).execute()
        if res.data and len(res.data) > 0:
            return {"success": True, "client": res.data[0]}
        return {"success": False, "detail": "Client non trouvé"}
    except Exception as e:
        return {"success": False, "detail": str(e)}

@app.post("/api/devis/sauvegarder")
async def sauvegarder_devis_cloud(payload: dict = Body(...)):
    sb = get_supabase_client()
    if not sb:
        return {"success": False, "detail": "Base de données Cloud non connectée. Le devis est conservé localement."}
    try:
        tel = re.sub(r'[^0-9+]', '', payload.get("telephone", ""))
        client_id = payload.get("client_id")
        
        if not client_id and tel:
            c_res = sb.table("clients").select("id").eq("telephone", tel).execute()
            if c_res.data:
                client_id = c_res.data[0]["id"]
                
        devis_data = {
            "client_id": client_id,
            "num_devis": payload.get("num_devis", "DEV-01"),
            "nom_client": payload.get("nom_client", "Client"),
            "nom_projet": payload.get("nom_projet", ""),
            "date_devis": payload.get("date_devis", time.strftime("%d/%m/%Y")),
            "taux_tva": float(payload.get("taux_tva", 19)),
            "remise_pct": float(payload.get("remise_pct", 0)),
            "total_ht": float(payload.get("total_ht", 0)),
            "total_ttc": float(payload.get("total_ttc", 0)),
            "articles": payload.get("articles", []),
            "nb_pages": int(payload.get("nb_pages", 1)),
            "statut": payload.get("statut", "chiffre")
        }
        res = sb.table("devis").insert(devis_data).execute()
        return {"success": True, "devis_id": res.data[0]["id"] if res.data else None}
    except Exception as e:
        return {"success": False, "detail": str(e)}

@app.get("/api/devis/historique/{telephone}")
async def historique_devis_cloud(telephone: str):
    sb = get_supabase_client()
    if not sb:
        return {"success": True, "devis": []}
    try:
        tel = re.sub(r'[^0-9+]', '', telephone)
        c_res = sb.table("clients").select("id").eq("telephone", tel).execute()
        if not c_res.data:
            return {"success": True, "devis": []}
        client_id = c_res.data[0]["id"]
        
        d_res = sb.table("devis").select("id, num_devis, nom_client, nom_projet, date_devis, total_ht, total_ttc, nb_pages, created_at").eq("client_id", client_id).order("created_at", desc=True).limit(50).execute()
        return {"success": True, "devis": d_res.data or []}
    except Exception as e:
        return {"success": False, "detail": str(e), "devis": []}

@app.get("/api/devis/charger/{devis_id}")
async def charger_devis_cloud(devis_id: str):
    sb = get_supabase_client()
    if not sb:
        raise HTTPException(status_code=404, detail="Supabase non connecté")
    try:
        res = sb.table("devis").select("*").eq("id", devis_id).execute()
        if res.data and len(res.data) > 0:
            return {"success": True, "devis": res.data[0]}
        raise HTTPException(status_code=404, detail="Devis non trouvé")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/devis/{devis_id}")
async def supprimer_devis_cloud(devis_id: str):
    sb = get_supabase_client()
    if not sb:
        return {"success": True}
    try:
        sb.table("devis").delete().eq("id", devis_id).execute()
        return {"success": True}
    except Exception as e:
        return {"success": False, "detail": str(e)}

@app.post("/api/paiements/baridimob")
async def declarer_paiement_baridimob(payload: dict = Body(...)):
    sb = get_supabase_client()
    tel = re.sub(r'[^0-9+]', '', payload.get("telephone", ""))
    formule = payload.get("formule", "pack_50")
    montant = float(payload.get("montant_dzd", 4000))
    numero_trans = (payload.get("numero_transaction") or "").strip()
    recu_img = (payload.get("recu_image_url") or "").strip()
    
    if not tel:
        raise HTTPException(status_code=400, detail="Numéro de téléphone requis.")
        
    if not sb:
        return {
            "success": True,
            "message": "Notification de paiement BaridiMob transmise ! Validation par votre conseiller sous peu."
        }
        
    try:
        c_res = sb.table("clients").select("id").eq("telephone", tel).execute()
        client_id = c_res.data[0]["id"] if c_res.data else None
        if not client_id:
            c_ins = sb.table("clients").insert({"telephone": tel, "nom_complet": "Client BaridiMob"}).execute()
            client_id = c_ins.data[0]["id"] if c_ins.data else None
            
        data = {
            "client_id": client_id,
            "telephone_client": tel,
            "formule": formule,
            "montant_dzd": montant,
            "numero_transaction": numero_trans,
            "recu_image_url": recu_img,
            "statut": "en_attente"
        }
        ins = sb.table("paiements_baridimob").insert(data).execute()
        return {
            "success": True,
            "paiement_id": ins.data[0]["id"] if ins.data else None,
            "message": "Preuve de paiement BaridiMob reçue ! Vos crédits seront activés dès vérification du virement."
        }
    except Exception as e:
        return {"success": False, "detail": str(e)}

ADMIN_PIN = (os.environ.get("ADMIN_PIN") or "7788").strip()

@app.get("/api/admin/stats")
async def admin_stats(pin: str = None):
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Code PIN Administrateur incorrect.")
    sb = get_supabase_client()
    keys = get_api_keys_pool()
    stats = {
        "keys_count": len(keys),
        "models_priority": MODELS_PRIORITY,
        "clients_total": 0,
        "devis_total": 0,
        "paiements_en_attente": 0
    }
    if sb:
        try:
            c_res = sb.table("clients").select("id", count="exact").execute()
            stats["clients_total"] = c_res.count if hasattr(c_res, "count") and c_res.count is not None else len(c_res.data or [])
            d_res = sb.table("devis").select("id", count="exact").execute()
            stats["devis_total"] = d_res.count if hasattr(d_res, "count") and d_res.count is not None else len(d_res.data or [])
            p_res = sb.table("paiements_baridimob").select("id", count="exact").eq("statut", "en_attente").execute()
            stats["paiements_en_attente"] = p_res.count if hasattr(p_res, "count") and p_res.count is not None else len(p_res.data or [])
        except Exception:
            pass
    return {"success": True, "stats": stats}

@app.get("/api/admin/paiements")
async def admin_liste_paiements(pin: str = None):
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Code PIN Administrateur incorrect.")
    sb = get_supabase_client()
    if not sb:
        return {"success": True, "paiements": []}
    try:
        res = sb.table("paiements_baridimob").select("*").order("created_at", desc=True).limit(50).execute()
        return {"success": True, "paiements": res.data or []}
    except Exception as e:
        return {"success": False, "detail": str(e), "paiements": []}

@app.post("/api/admin/valider-paiement")
async def admin_valider_paiement(payload: dict = Body(...)):
    pin = payload.get("pin")
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Code PIN Administrateur incorrect.")
    paiement_id = payload.get("paiement_id")
    action = payload.get("action", "valider")
    sb = get_supabase_client()
    if not sb:
        return {"success": False, "detail": "Supabase non connecté"}
    try:
        p_res = sb.table("paiements_baridimob").select("*").eq("id", paiement_id).execute()
        if not p_res.data:
            raise HTTPException(status_code=404, detail="Paiement introuvable")
        p = p_res.data[0]
        
        if action == "valider":
            formule = p.get("formule", "")
            client_id = p.get("client_id")
            
            credits_attribues = 50
            if "100" in formule: credits_attribues = 100
            elif "devis" in formule or "par_devis" in formule: credits_attribues = 10
            elif "mensuel" in formule: credits_attribues = 150
            
            c_res = sb.table("clients").select("credits_pages").eq("id", client_id).execute()
            actuel = c_res.data[0].get("credits_pages", 0) if c_res.data else 0
            nouveau = actuel + credits_attribues
            
            sb.table("clients").update({"credits_pages": nouveau, "type_abonnement": formule}).eq("id", client_id).execute()
            sb.table("paiements_baridimob").update({"statut": "valide", "valide_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}).eq("id", paiement_id).execute()
            return {"success": True, "message": f"Paiement validé ! {credits_attribues} crédits ajoutés au solde du client."}
        else:
            sb.table("paiements_baridimob").update({"statut": "rejete"}).eq("id", paiement_id).execute()
            return {"success": True, "message": "Paiement rejeté."}
    except Exception as e:
        return {"success": False, "detail": str(e)}

@app.post("/api/admin/crediter-client")
async def admin_crediter_client(payload: dict = Body(...)):
    pin = payload.get("pin")
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Code PIN Administrateur incorrect.")
    telephone = re.sub(r'[^0-9+]', '', payload.get("telephone", ""))
    credits_a_ajouter = int(payload.get("credits", 50))
    formule = payload.get("formule", "pack_credits")
    
    if not telephone:
        raise HTTPException(status_code=400, detail="Numéro de téléphone requis.")
        
    sb = get_supabase_client()
    if not sb:
        return {"success": False, "detail": "Supabase non connecté"}
        
    try:
        c_res = sb.table("clients").select("id, credits_pages").eq("telephone", telephone).execute()
        if not c_res.data:
            # Créer le client s'il n'existe pas encore
            new_client = {
                "telephone": telephone,
                "nom_complet": "Client BTP",
                "credits_pages": credits_a_ajouter,
                "type_abonnement": formule
            }
            sb.table("clients").insert(new_client).execute()
            return {"success": True, "message": f"Nouveau client créé avec {credits_a_ajouter} crédits."}
        else:
            client_id = c_res.data[0]["id"]
            actuel = c_res.data[0].get("credits_pages", 0)
            nouveau = actuel + credits_a_ajouter
            sb.table("clients").update({"credits_pages": nouveau, "type_abonnement": formule}).eq("id", client_id).execute()
            return {"success": True, "message": f"{credits_a_ajouter} crédits ajoutés avec succès ! Nouveau solde : {nouveau} pages."}
    except Exception as e:
        return {"success": False, "detail": str(e)}

@app.post("/extract-devis/")
async def extract_devis_legacy(file: UploadFile = File(...)):
    return await chiffrer_page(file=file)

@app.post("/generate-excel/")
async def generate_excel_legacy(devis_data: dict = Body(...)):
    return await exporter_excel(payload=devis_data)