import os
import io
import re
import json
import time
import hashlib
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

# Modèles Gemini par ordre d'efficacité, de vitesse et de compatibilité universelle
MODELS_PRIORITY = [
    "gemini-2.0-flash",       # Modèle de production standard universel et très rapide
    "gemini-2.5-flash",       # Modèle hybride haute précision
    "gemini-1.5-flash",       # Fallback universel 100% garanti sur toutes les clés Google AI Studio
    "gemini-2.0-flash-lite",  # Fallback rapide
    "gemini-2.5-flash-lite",  # Modèle haute vitesse
    "gemini-1.5-pro",         # Secours haute précision
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
    if not raw_text or not raw_text.strip():
        return {"client": "", "projet": "", "articles": []}

    text = raw_text.strip()
    # Nettoyage des balises Markdown
    text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
    text = text.strip()

    # 1. Tentative directe
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return {"client": "", "projet": "", "articles": data}
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 2. Extraction du bloc {...}
    start_obj = text.find('{')
    end_obj = text.rfind('}')
    if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
        clean = text[start_obj:end_obj + 1]
        clean_sanitized = re.sub(r',\s*([\]}])', r'\1', clean)
        try:
            data = json.loads(clean_sanitized)
            if isinstance(data, list):
                return {"client": "", "projet": "", "articles": data}
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    # 3. Extraction du bloc [...]
    start_arr = text.find('[')
    end_arr = text.rfind(']')
    if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
        clean = text[start_arr:end_arr + 1]
        clean_sanitized = re.sub(r',\s*([\]}])', r'\1', clean)
        try:
            articles = json.loads(clean_sanitized)
            if isinstance(articles, list):
                return {"client": "", "projet": "", "articles": articles}
        except Exception:
            pass

    # 4. Fallback de sauvetage par Regex article par article
    articles_secours = []
    regex_obj = re.compile(r'\{[^{}]*"(?:d|designation)"[^{}]*\}', re.DOTALL)
    for m in regex_obj.finditer(text):
        bloc = m.group(0)
        try:
            bloc_clean = re.sub(r',\s*\}', '}', bloc)
            art = json.loads(bloc_clean)
            if isinstance(art, dict):
                articles_secours.append(art)
        except Exception:
            pass

    if articles_secours:
        return {"client": "", "projet": "", "articles": articles_secours}

    return {"client": "", "projet": "", "articles": []}

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

    # 7. Feuille 2 : DOSSIER COMPLET BTP — PLANNING & DÉLAI D'EXÉCUTION DES TRAVAUX
    try:
        ws_plan = wb.create_sheet(title="Planning & Délai Travaux")
        ws_plan.views.sheetView[0].showGridLines = True

        c_vert_entete = "047857"
        c_vert_sub = "D1FAE5"
        fill_plan_head = PatternFill(start_color=c_vert_entete, end_color=c_vert_entete, fill_type="solid")
        fill_plan_sub = PatternFill(start_color=c_vert_sub, end_color=c_vert_sub, fill_type="solid")
        fill_gantt_corps = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
        fill_gantt_fin = PatternFill(start_color="10B981", end_color="10B981", fill_type="solid")

        # Titre général du Dossier Complet BTP
        ws_plan.merge_cells("A1:K1")
        t_plan = ws_plan["A1"]
        t_plan.value = "⭐ DOSSIER COMPLET BTP — PLANNING PRÉVISIONNEL & DÉLAI D'EXÉCUTION"
        t_plan.font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
        t_plan.fill = fill_plan_head
        t_plan.alignment = Alignment(horizontal="center", vertical="center")
        ws_plan.row_dimensions[1].height = 28

        # Sous-titre réglementaire algérien
        ws_plan.merge_cells("A2:K2")
        t_sub = ws_plan["A2"]
        t_sub.value = "Conforme aux prescriptions du Décret présidentiel n° 15-247 portant réglementation des marchés publics en Algérie"
        t_sub.font = Font(name="Calibri", size=9, italic=True, color="065F46")
        t_sub.fill = fill_plan_sub
        t_sub.alignment = Alignment(horizontal="center", vertical="center")
        ws_plan.row_dimensions[2].height = 18

        # Paramètres calculés
        nb_lots_detectes = len(lots_dict) if lots_dict else 5
        delai_mois = int(payload.get("delai_mois") or max(2, min(12, round(1 + nb_lots_detectes * 0.75))))
        delai_jours = delai_mois * 30
        date_demarrage = payload.get("date_demarrage") or date_devis

        # Cartouche Informations Chantier & Délai
        ws_plan.merge_cells("A4:C4")
        ws_plan["A4"] = f"Client : {nom_client}"
        ws_plan["A4"].font = font_bold

        ws_plan.merge_cells("A5:C5")
        ws_plan["A5"] = f"Projet : {nom_projet}"
        ws_plan["A5"].font = font_sub_ent

        ws_plan.merge_cells("A6:C6")
        ws_plan["A6"] = f"Réf. Devis DQE : N° {num_devis} du {date_devis}"
        ws_plan["A6"].font = font_sub_ent

        ws_plan.merge_cells("D4:G4")
        ws_plan["D4"] = f"Date de Démarrage (Notification OS) : {date_demarrage}"
        ws_plan["D4"].font = font_bold

        ws_plan.merge_cells("D5:G5")
        ws_plan["D5"] = f"Délai Contractuel Global : {delai_mois} MOIS ({delai_jours} Jours calendaires)"
        ws_plan["D5"].font = Font(name="Calibri", size=11, bold=True, color="047857")

        ws_plan.merge_cells("D6:G6")
        ws_plan["D6"] = "Régime hebdomadaire : 6 Jours / Semaine (Vendredi chômé)"
        ws_plan["D6"].font = font_sub_ent

        # Tableau des Phases & Gantt
        plan_headers = ["Phase", "Désignation du Lot / Corps d'État", "Durée Estimée", "Début Estimé", "Fin Estimée"]
        nb_colonnes_gantt = max(8, min(16, delai_mois * 2))
        for s_idx in range(1, nb_colonnes_gantt + 1):
            plan_headers.append(f"S{s_idx}")

        p_row = 8
        for col_idx, h_text in enumerate(plan_headers, start=1):
            cell_h = ws_plan.cell(row=p_row, column=col_idx, value=h_text)
            cell_h.font = font_header_tab
            cell_h.fill = fill_header if col_idx <= 5 else PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
            cell_h.alignment = Alignment(horizontal="center", vertical="center")
            cell_h.border = thin_border
        ws_plan.row_dimensions[p_row].height = 24

        ws_plan.column_dimensions["A"].width = 9
        ws_plan.column_dimensions["B"].width = 38
        ws_plan.column_dimensions["C"].width = 16
        ws_plan.column_dimensions["D"].width = 18
        ws_plan.column_dimensions["E"].width = 18
        for s_idx in range(1, nb_colonnes_gantt + 1):
            ws_plan.column_dimensions[get_column_letter(5 + s_idx)].width = 5

        liste_lots_noms = list(lots_dict.keys())
        if not liste_lots_noms:
            liste_lots_noms = [
                "LOT 01: TERRASSEMENTS & FOUILLES",
                "LOT 02: GROS-OEUVRE & INFRASTRUCTURE",
                "LOT 03: MAÇONNERIE & ENDUITS",
                "LOT 04: CORPS D'ÉTAT SECONDAIRES (CES)",
                "LOT 05: REVÊTEMENTS & FINITIONS"
            ]

        nb_total_phases = len(liste_lots_noms)
        for idx_phase, lot_nom in enumerate(liste_lots_noms, start=1):
            p_row += 1
            duree_phase_jours = max(15, round((delai_jours * 0.8) / max(1, nb_total_phases - 0.5)))
            s_start = max(1, round(1 + (idx_phase - 1) * (nb_colonnes_gantt - 3) / max(1, nb_total_phases)))
            s_span = max(2, min(5, round(nb_colonnes_gantt / 2.5)))
            s_end = min(nb_colonnes_gantt, s_start + s_span - 1)

            c1 = ws_plan.cell(row=p_row, column=1, value=f"PH-{idx_phase:02d}")
            c1.alignment = Alignment(horizontal="center", vertical="center")
            c1.font = font_bold
            c1.border = thin_border

            c2 = ws_plan.cell(row=p_row, column=2, value=lot_nom)
            c2.font = font_bold
            c2.alignment = Alignment(horizontal="left", vertical="center")
            c2.border = thin_border

            c3 = ws_plan.cell(row=p_row, column=3, value=f"{duree_phase_jours} Jours")
            c3.alignment = Alignment(horizontal="center", vertical="center")
            c3.border = thin_border

            c4 = ws_plan.cell(row=p_row, column=4, value=f"Semaine {s_start}")
            c4.alignment = Alignment(horizontal="center", vertical="center")
            c4.border = thin_border

            c5 = ws_plan.cell(row=p_row, column=5, value=f"Semaine {s_end}")
            c5.alignment = Alignment(horizontal="center", vertical="center")
            c5.border = thin_border

            for g_idx in range(1, nb_colonnes_gantt + 1):
                col_target = 5 + g_idx
                cg = ws_plan.cell(row=p_row, column=col_target, value="")
                cg.border = thin_border
                if s_start <= g_idx <= s_end:
                    cg.fill = fill_gantt_corps if idx_phase < nb_total_phases else fill_gantt_fin

        p_row += 2
        ws_plan.merge_cells(f"A{p_row}:K{p_row}")
        r_cell = ws_plan.cell(row=p_row, column=1, value="📌 Prescriptions d'Exécution & Cadences de Chantier (Décret 15-247) :")
        r_cell.font = font_bold
        p_row += 1

        prescriptions = [
            "1. L'entreprise s'engage à mobiliser les effectifs et le matériel dès notification de l'Ordre de Service (O.S).",
            "2. Les cadences hebdomadaires feront l'objet de réunions de chantier contradictoires avec attachements contradictoires.",
            "3. L'approvisionnement des matériaux (ciment, agrégats, ronds à béton, revêtements) sera anticipé de 15 jours par rapport au planning.",
            "4. En cas d'intempéries dûment constatées par le Maître d'Œuvre, le délai contractuel pourra faire l'objet d'un avenant conformément au Code des Marchés Publics."
        ]
        for pres in prescriptions:
            ws_plan.merge_cells(f"A{p_row}:K{p_row}")
            pc = ws_plan.cell(row=p_row, column=1, value=pres)
            pc.font = font_sub_ent
            p_row += 1

        p_row += 1
        sig_p_row = p_row
        ws_plan.merge_cells(f"A{sig_p_row}:D{sig_p_row+2}")
        sp1 = ws_plan.cell(row=sig_p_row, column=1, value="Pour l'Entreprise de Réalisation\n(Nom, Signature et Cachet)")
        sp1.font = font_bold
        sp1.alignment = Alignment(horizontal="center", vertical="top", wrap_text=True)
        sp1.border = Border(left=Side(style="medium"), right=Side(style="medium"), top=Side(style="medium"), bottom=Side(style="medium"))

        ws_plan.merge_cells(f"F{sig_p_row}:I{sig_p_row+2}")
        sp2 = ws_plan.cell(row=sig_p_row, column=6, value="Pour le Maître de l'Ouvrage / Maître d'Œuvre\n(Visa, Signature et Mention 'Lu et Approuvé')")
        sp2.font = font_bold
        sp2.alignment = Alignment(horizontal="center", vertical="top", wrap_text=True)
        sp2.border = Border(left=Side(style="medium"), right=Side(style="medium"), top=Side(style="medium"), bottom=Side(style="medium"))
    except Exception as e_plan:
        print(f"[create_excel_multilots] Note: Erreur création onglet planning: {e_plan}")

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

@app.get("/titulaire")
@app.get("/admin")
def serve_titulaire_espace():
    """Route directe pour accéder à l'espace Titulaire / Administration."""
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="index.html non trouvé")

@app.get("/didacticiel")
def serve_didacticiel():
    didacticiel_path = os.path.join(os.path.dirname(__file__), "video_didacticiel.html")
    if os.path.exists(didacticiel_path):
        return FileResponse(didacticiel_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="video_didacticiel.html non trouvé")

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
    """Appelle l'API Gemini de façon synchrone en utilisant en priorité le nouveau SDK google-genai, avec repli automatique sur google.generativeai."""
    key_clean = (api_key or "").strip()
    if HAS_NEW_GENAI:
        try:
            client = genai.Client(api_key=key_clean)
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
            if response and response.text:
                return response.text
        except Exception as e_new:
            print(f"[SDK google-genai] Note: modèle {model_name} non résolu via google-genai ({e_new}), tentative via google.generativeai...")

    # Repli sur le SDK historique google.generativeai
    legacy_genai.configure(api_key=key_clean)
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
    credits_actuels: Optional[int] = Form(None),
    nb_pages_demandees: Optional[int] = Form(1),
    gemini_key: str = Form(None),
    strategie_prix: str = Form("moins_disant"),
    region: str = Form("centre")
):
    global current_key_index

    # 0. Reconnaissance du Titulaire / Propriétaire (M. BENABDALLAH) : Accès gratuit & illimité absolu
    tel_str = str(telephone or "").strip()
    is_titulaire = (
        "0551422166" in tel_str or
        "213551422166" in tel_str or
        "titulaire" in tel_str.lower() or
        "benabdallah" in tel_str.lower() or
        (credits_actuels is not None and int(credits_actuels) >= 9000)
    )

    # 1. Vérification stricte du solde local transmis (barrière d'accès immédiate pour clients normaux)
    if not is_titulaire and credits_actuels is not None and int(credits_actuels) <= 0:
        raise HTTPException(
            status_code=402,
            detail="🚫 Solde de crédits épuisé (0 page restante). Veuillez recharger votre compte via BaridiMob pour continuer à chiffrer vos devis."
        )

    keys_pool = get_api_keys_pool(client_key=gemini_key)
    if not keys_pool:
        raise HTTPException(
            status_code=500,
            detail="Aucune clé Gemini configurée. Veuillez ajouter votre clé Gemini dans l'interface ou dans les paramètres du serveur."
        )

    # 2. Vérification stricte des crédits dans Supabase avant tout calcul (Rupture d'accès si solde épuisé pour clients)
    sb = get_supabase_client()
    client_sb = None
    if sb and telephone and isinstance(telephone, str) and telephone.strip():
        tel_clean = re.sub(r'[^0-9+a-zA-Z_-]', '', telephone.strip())
        if tel_clean:
            try:
                c_res = sb.table("clients").select("id, credits_pages, type_abonnement").eq("telephone", tel_clean).execute()
                if not c_res.data:
                    c_res = sb.table("clients").select("id, credits_pages, type_abonnement").eq("id", tel_clean).execute()

                if c_res.data and len(c_res.data) > 0:
                    client_sb = c_res.data[0]
                    solde_actuel = int(client_sb.get("credits_pages", 0) or 0)
                    if solde_actuel <= 0 and not is_titulaire:
                        raise HTTPException(
                            status_code=402,
                            detail="🚫 Solde de crédits épuisé (0 page restante). Veuillez recharger votre compte via BaridiMob pour continuer à chiffrer vos devis."
                        )
                else:
                    # Enregistrer automatiquement le nouveau client avec ses 5 pages offertes
                    try:
                        new_c = {
                            "telephone": tel_clean,
                            "nom_complet": "Client Invité BTP",
                            "type_abonnement": "gratuit",
                            "credits_pages": 5
                        }
                        ins = sb.table("clients").insert(new_c).execute()
                        if ins.data:
                            client_sb = ins.data[0]
                    except Exception:
                        pass
            except HTTPException as he:
                raise he
            except Exception:
                pass

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
                # Exécution asynchrone non-bloquante avec timeout de sécurité de 65s par modèle (indispensable pour les devis multi-lots complexes)
                raw_text = await asyncio.wait_for(
                    asyncio.to_thread(call_gemini_sync, api_key, model_name, contents_list),
                    timeout=65.0
                )
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

                # Décompte automatique et garanti du crédit page
                nb_a_deduire = max(1, int(nb_pages_demandees or 1))
                if fichiers_a_traiter and len(fichiers_a_traiter) > 1:
                    nb_a_deduire = max(nb_a_deduire, len(fichiers_a_traiter))

                credits_restants = None
                if sb and client_sb:
                    try:
                        solde = int(client_sb.get("credits_pages", 0) or 0)
                        nouveau_solde = max(0, solde - nb_a_deduire)
                        sb.table("clients").update({"credits_pages": nouveau_solde}).eq("id", client_sb["id"]).execute()
                        credits_restants = nouveau_solde
                    except Exception:
                        pass
                elif not sb and telephone:
                    try:
                        tel_clean = re.sub(r'[^0-9+]', '', str(telephone))
                        clients_local = charger_clients_locaux()
                        if tel_clean in clients_local:
                            solde = int(clients_local[tel_clean].get("credits_pages", 0) or 0)
                            nouveau_solde = max(0, solde - nb_a_deduire)
                            clients_local[tel_clean]["credits_pages"] = nouveau_solde
                            clients_local[tel_clean]["pages_consommees"] = int(clients_local[tel_clean].get("pages_consommees", 0) or 0) + nb_a_deduire
                            sauvegarder_clients_locaux(clients_local)
                            credits_restants = nouveau_solde
                    except Exception:
                        pass

                if credits_restants is None:
                    if credits_actuels is not None:
                        credits_restants = max(0, int(credits_actuels) - nb_a_deduire)
                    else:
                        credits_restants = 0

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
                print(f"⚠️ [IA Gemini] Échec du modèle {model_name} (clé {key_idx+1}/{total_keys}): {inner_e}")
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
# ENDPOINTS SUPABASE / LOCAL : CLIENTS, DEVIS & PAIEMENTS BARIDIMOB
# ============================================================

CLIENTS_LOCAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clients_local_db.json")

def charger_clients_locaux() -> dict:
    if os.path.exists(CLIENTS_LOCAL_FILE):
        try:
            with open(CLIENTS_LOCAL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}

def sauvegarder_clients_locaux(data: dict):
    try:
        with open(CLIENTS_LOCAL_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

@app.post("/api/clients/connexion")
async def client_connexion(payload: dict = Body(...)):
    telephone_brut = (payload.get("telephone") or "").strip()
    nom_complet = (payload.get("nom_complet") or "").strip() or "Artisan BTP"
    wilaya = (payload.get("wilaya") or "Alger").strip()
    
    tel_clean = re.sub(r'[^0-9+]', '', telephone_brut)
    if not tel_clean or len(tel_clean) < 8:
        # Identifiant client automatique si pas encore de téléphone
        tel_clean = "05" + str(int(time.time()))[-8:]
        
    is_titulaire = (
        "0551422166" in tel_clean or
        "213551422166" in tel_clean or
        "titulaire" in nom_complet.lower() or
        "benabdallah" in nom_complet.lower()
    )

    sb = get_supabase_client()
    if not sb:
        clients_local = charger_clients_locaux()
        if tel_clean in clients_local:
            client = clients_local[tel_clean]
            if nom_complet and nom_complet != "Artisan BTP":
                client["nom_complet"] = nom_complet
            if is_titulaire:
                client["credits_pages"] = 9999
                client["type_abonnement"] = "titulaire_illimite"
            sauvegarder_clients_locaux(clients_local)
            return {"success": True, "nouveau": False, "client": client}
        else:
            new_c = {
                "id": f"cli_{tel_clean}",
                "telephone": tel_clean,
                "nom_complet": "BENABDALLAH (Titulaire)" if is_titulaire else nom_complet,
                "wilaya": wilaya,
                "credits_pages": 9999 if is_titulaire else 5,
                "pages_consommees": 0,
                "type_abonnement": "titulaire_illimite" if is_titulaire else "gratuit"
            }
            clients_local[tel_clean] = new_c
            sauvegarder_clients_locaux(clients_local)
            return {"success": True, "nouveau": True, "client": new_c}
        
    try:
        res = sb.table("clients").select("*").eq("telephone", tel_clean).execute()
        if res.data and len(res.data) > 0:
            client = res.data[0]
            if is_titulaire:
                client["credits_pages"] = 9999
                client["type_abonnement"] = "titulaire_illimite"
            return {"success": True, "nouveau": False, "client": client}
        else:
            new_client = {
                "nom_complet": "BENABDALLAH (Titulaire)" if is_titulaire else nom_complet,
                "telephone": tel_clean,
                "wilaya": wilaya,
                "type_abonnement": "titulaire_illimite" if is_titulaire else "gratuit",
                "credits_pages": 9999 if is_titulaire else 5,
                "pages_consommees": 0
            }
            ins = sb.table("clients").insert(new_client).execute()
            created = ins.data[0] if ins.data else new_client
            return {"success": True, "nouveau": True, "client": created}
    except Exception as e:
        clients_local = charger_clients_locaux()
        if tel_clean in clients_local:
            return {"success": True, "nouveau": False, "client": clients_local[tel_clean]}
        new_c = {
            "id": f"cli_{tel_clean}",
            "telephone": tel_clean,
            "nom_complet": nom_complet,
            "wilaya": wilaya,
            "credits_pages": 5,
            "pages_consommees": 0,
            "type_abonnement": "gratuit"
        }
        clients_local[tel_clean] = new_c
        sauvegarder_clients_locaux(clients_local)
        return {
            "success": True,
            "mode": "fallback_local",
            "message": f"Supabase en attente d'initialisation SQL ({str(e)}).",
            "client": new_c
        }

@app.get("/api/clients/profil/{telephone}")
async def get_client_profil(telephone: str):
    tel_clean = re.sub(r'[^0-9+]', '', telephone)
    sb = get_supabase_client()
    if not sb:
        clients_local = charger_clients_locaux()
        if tel_clean in clients_local:
            return {"success": True, "client": clients_local[tel_clean]}
        return {"success": True, "client": {"telephone": tel_clean, "credits_pages": 0, "type_abonnement": "gratuit"}}
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

# ============================================================
# SÉCURITÉ TITULAIRE, CODE PIN CHIFFRÉ & COORDONNÉES BARIDIMOB
# ============================================================
ADMIN_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin_config.json")
PIN_SALT = "BTP_DEV_ALG_2026_SECRET_SALT"

def hash_admin_pin(pin: str) -> str:
    """Hachage cryptographique sécurisé du PIN avec sel pour empêcher toute rétro-ingénierie."""
    return hashlib.sha256(f"{PIN_SALT}:{pin.strip()}".encode("utf-8")).hexdigest()

def charger_admin_config() -> dict:
    """Charge la configuration administrative et les coordonnées officielles BaridiMob."""
    cfg = {
        "pin_hash": None,
        "baridimob": {
            "titulaire": "BOUFELDJA BENABDALLAH",
            "rip": "007 99999 0001918047 08",
            "ccp": "0001918047",
            "cle": "08",
            "telephone": "0551 42 21 66",
            "instructions": "Veuillez renseigner votre nom et numéro de téléphone dans la note du virement BaridiMob."
        }
    }
    if os.path.exists(ADMIN_CONFIG_FILE):
        try:
            with open(ADMIN_CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    if "pin_hash" in saved and saved["pin_hash"]:
                        cfg["pin_hash"] = saved["pin_hash"]
                    if "baridimob" in saved and isinstance(saved["baridimob"], dict):
                        cfg["baridimob"].update(saved["baridimob"])
        except Exception:
            pass
    return cfg

def sauvegarder_admin_config(cfg: dict):
    """Sauvegarde la configuration administrative de manière persistante."""
    try:
        with open(ADMIN_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erreur sauvegarde admin_config: {e}")

# Protection anti-brute-force (Max 5 tentatives consécutives / 5 minutes)
FAILED_PIN_ATTEMPTS = []
MAX_FAILED_PIN_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 300

def verifier_tentatives_autorisees():
    now = time.time()
    recent = [t for t in FAILED_PIN_ATTEMPTS if now - t < LOCKOUT_WINDOW_SECONDS]
    FAILED_PIN_ATTEMPTS[:] = recent
    if len(recent) >= MAX_FAILED_PIN_ATTEMPTS:
        attente = int(LOCKOUT_WINDOW_SECONDS - (now - recent[0]))
        raise HTTPException(
            status_code=429,
            detail=f"⛔ Accès temporairement verrouillé pour des raisons de sécurité. Réessayez dans {max(1, attente)} secondes."
        )

def valider_admin_pin(pin_propose: str) -> bool:
    """Vérifie le code PIN de manière sécurisée sans jamais l'exposer."""
    if not pin_propose or not isinstance(pin_propose, str):
        return False
    pin_clean = pin_propose.strip()

    verifier_tentatives_autorisees()
    cfg = charger_admin_config()
    stored_hash = cfg.get("pin_hash")
    default_hash = hash_admin_pin("7788")

    # 1. Si un code PIN personnalisé est configuré (différent de 7788), SEUL ce code est accepté.
    # L'ancien code 7788 est immédiatement et définitivement révoqué et refusé.
    if stored_hash and stored_hash != default_hash:
        if hash_admin_pin(pin_clean) == stored_hash:
            FAILED_PIN_ATTEMPTS.clear()
            return True
        custom_env = os.environ.get("ADMIN_PIN")
        if custom_env and pin_clean == custom_env.strip() and custom_env.strip() != "7788":
            FAILED_PIN_ATTEMPTS.clear()
            return True
        FAILED_PIN_ATTEMPTS.append(time.time())
        return False

    # 2. Code initial par défaut uniquement avant toute personnalisation
    env_pin = (os.environ.get("ADMIN_PIN") or "7788").strip()
    if pin_clean == env_pin:
        FAILED_PIN_ATTEMPTS.clear()
        return True

    FAILED_PIN_ATTEMPTS.append(time.time())
    return False

@app.get("/api/public/baridimob-info")
async def public_baridimob_info():
    """Endpoint public pour diffuser aux clients les coordonnées officielles BaridiMob configurées par le titulaire."""
    cfg = charger_admin_config()
    b = cfg.get("baridimob", {})
    return {
        "success": True,
        "baridimob": {
            "titulaire": b.get("titulaire") or "BOUFELDJA BENABDALLAH",
            "rip": b.get("rip") or "007 99999 0001918047 08",
            "ccp": b.get("ccp") or "0001918047",
            "cle": b.get("cle") or "08",
            "telephone": b.get("telephone") or "0551 42 21 66",
            "instructions": b.get("instructions") or "Veuillez renseigner votre nom et numéro de téléphone dans la note du virement BaridiMob."
        }
    }

@app.post("/api/admin/verifier-pin")
async def api_verifier_pin(payload: dict = Body(...)):
    """Vérification sécurisée du code PIN titulaire au déverrouillage de la session."""
    pin = payload.get("pin")
    if not valider_admin_pin(pin):
        raise HTTPException(status_code=401, detail="Code PIN ou mot de passe incorrect.")
    cfg = charger_admin_config()
    return {
        "success": True,
        "message": "Session titulaire sécurisée déverrouillée avec succès.",
        "baridimob": cfg.get("baridimob", {})
    }

@app.post("/api/admin/changer-pin")
async def api_changer_pin(payload: dict = Body(...)):
    """Modification sécurisée du code PIN par le titulaire."""
    ancien_pin = (payload.get("ancien_pin") or "").strip()
    nouveau_pin = (payload.get("nouveau_pin") or "").strip()
    if not valider_admin_pin(ancien_pin):
        raise HTTPException(status_code=401, detail="Le code PIN actuel est incorrect.")
    if len(nouveau_pin) < 4:
        raise HTTPException(status_code=400, detail="Le nouveau code PIN / mot de passe doit comporter au moins 4 caractères.")
    if nouveau_pin == "7788":
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas choisir '7788' comme nouveau code. Définissez un code PIN secret personnalisé.")
    
    cfg = charger_admin_config()
    cfg["pin_hash"] = hash_admin_pin(nouveau_pin)
    sauvegarder_admin_config(cfg)
    FAILED_PIN_ATTEMPTS.clear()
    return {
        "success": True,
        "message": "Code PIN / Mot de passe mis à jour et chiffré avec succès !"
    }

@app.post("/api/admin/baridimob-config")
async def api_sauvegarder_baridimob_config(payload: dict = Body(...)):
    """Permet au titulaire de configurer ses véritables coordonnées de virement BaridiMob & CCP."""
    pin = payload.get("pin")
    if not valider_admin_pin(pin):
        raise HTTPException(status_code=401, detail="Code PIN Titulaire incorrect.")
    b_info = payload.get("baridimob", {})
    cfg = charger_admin_config()
    cfg["baridimob"] = {
        "titulaire": str(b_info.get("titulaire") or "").strip(),
        "rip": str(b_info.get("rip") or "").strip(),
        "ccp": str(b_info.get("ccp") or "").strip(),
        "cle": str(b_info.get("cle") or "").strip(),
        "telephone": str(b_info.get("telephone") or "").strip(),
        "instructions": str(b_info.get("instructions") or "").strip()
    }
    sauvegarder_admin_config(cfg)
    return {
        "success": True,
        "message": "Vos coordonnées BaridiMob & CCP ont été enregistrées avec succès !",
        "baridimob": cfg["baridimob"]
    }

@app.get("/api/public/jauge-stats")
async def public_jauge_stats():
    sb = get_supabase_client()
    default_stats = {
        "success": True,
        "clients_total": 5,
        "clients_abonnes": 3,
        "clients_gratuits": 2,
        "taux_abonnements_pct": 60.0,
        "devis_total": 12
    }
    if not sb:
        return default_stats
    try:
        c_res = sb.table("clients").select("id, type_abonnement, credits_pages").execute()
        clients_data = c_res.data or []
        tot = len(clients_data)
        if tot == 0:
            return default_stats
        abonnes = [c for c in clients_data if (c.get("type_abonnement") not in (None, "", "gratuit", "free")) or (int(c.get("credits_pages", 0) or 0) > 5)]
        nb_ab = len(abonnes)
        nb_grat = tot - nb_ab
        taux = round((nb_ab / tot * 100), 1) if tot > 0 else 0.0

        d_res = sb.table("devis").select("id", count="exact").execute()
        devis_tot = d_res.count if hasattr(d_res, "count") and d_res.count is not None else len(d_res.data or [])

        return {
            "success": True,
            "clients_total": tot,
            "clients_abonnes": nb_ab,
            "clients_gratuits": nb_grat,
            "taux_abonnements_pct": taux,
            "devis_total": devis_tot
        }
    except Exception:
        return default_stats

@app.get("/api/admin/stats")
async def admin_stats(pin: str = None):
    if not valider_admin_pin(pin):
        raise HTTPException(status_code=401, detail="Code PIN Administrateur incorrect.")
    sb = get_supabase_client()
    keys = get_api_keys_pool()
    stats = {
        "keys_count": len(keys),
        "models_priority": MODELS_PRIORITY,
        "clients_total": 0,
        "clients_abonnes": 0,
        "clients_gratuits": 0,
        "taux_abonnements_pct": 0.0,
        "devis_total": 0,
        "paiements_en_attente": 0,
        "paiements_valides": 0,
        "revenus_total_dzd": 0,
        "clients_recents": []
    }
    if sb:
        try:
            c_res = sb.table("clients").select("*").order("created_at", desc=True).execute()
            clients_data = c_res.data or []
            stats["clients_total"] = len(clients_data)

            abonnes = []
            gratuits = []
            for c in clients_data:
                type_ab = (c.get("type_abonnement") or "").strip().lower()
                credits = int(c.get("credits_pages", 0) or 0)
                if type_ab not in ("", "gratuit", "free") or credits > 5:
                    abonnes.append(c)
                else:
                    gratuits.append(c)

            stats["clients_abonnes"] = len(abonnes)
            stats["clients_gratuits"] = len(gratuits)
            stats["taux_abonnements_pct"] = round((len(abonnes) / len(clients_data) * 100), 1) if clients_data else 0.0
            stats["clients_recents"] = clients_data[:15]

            d_res = sb.table("devis").select("id", count="exact").execute()
            stats["devis_total"] = d_res.count if hasattr(d_res, "count") and d_res.count is not None else len(d_res.data or [])

            p_res = sb.table("paiements_baridimob").select("id, montant_dzd, statut").execute()
            p_data = p_res.data or []
            stats["paiements_en_attente"] = len([p for p in p_data if p.get("statut") == "en_attente"])
            stats["paiements_valides"] = len([p for p in p_data if p.get("statut") == "valide"])
            stats["revenus_total_dzd"] = sum(float(p.get("montant_dzd", 0) or 0) for p in p_data if p.get("statut") == "valide")
        except Exception:
            pass
    return {"success": True, "stats": stats}

@app.get("/api/admin/clients")
async def admin_liste_clients(pin: str = None):
    if not valider_admin_pin(pin):
        raise HTTPException(status_code=401, detail="Code PIN Administrateur incorrect.")
    sb = get_supabase_client()
    if not sb:
        return {"success": True, "clients": list(charger_clients_locaux().values())}
    try:
        res = sb.table("clients").select("*").order("created_at", desc=True).limit(150).execute()
        return {"success": True, "clients": res.data or []}
    except Exception as e:
        return {"success": False, "detail": str(e), "clients": []}

@app.get("/api/admin/paiements")
async def admin_liste_paiements(pin: str = None):
    if not valider_admin_pin(pin):
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
    if not valider_admin_pin(pin):
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
            if "complet" in formule or "pack_complet" in formule: credits_attribues = 80
            elif "100" in formule: credits_attribues = 100
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
    if not valider_admin_pin(pin):
        raise HTTPException(status_code=401, detail="Code PIN Administrateur incorrect.")
    telephone = re.sub(r'[^0-9+]', '', payload.get("telephone", ""))
    credits_a_ajouter = int(payload.get("credits", 50))
    formule = payload.get("formule", "pack_credits")
    
    if not telephone:
        raise HTTPException(status_code=400, detail="Numéro de téléphone requis.")
        
    sb = get_supabase_client()
    if not sb:
        clients_local = charger_clients_locaux()
        if telephone not in clients_local:
            clients_local[telephone] = {
                "id": f"cli_{telephone}",
                "telephone": telephone,
                "nom_complet": "Client BTP",
                "credits_pages": credits_a_ajouter,
                "pages_consommees": 0,
                "type_abonnement": formule
            }
        else:
            actuel = int(clients_local[telephone].get("credits_pages", 0) or 0)
            clients_local[telephone]["credits_pages"] = actuel + credits_a_ajouter
            clients_local[telephone]["type_abonnement"] = formule
        sauvegarder_clients_locaux(clients_local)
        return {"success": True, "message": f"{credits_a_ajouter} crédits ajoutés avec succès ! Nouveau solde : {clients_local[telephone]['credits_pages']} pages."}
        
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

# ============================================================
# ASSISTANCE CHIFFRAGE & QUESTIONS CLIENTS (TABLEAU DE BORD TITULAIRE)
# ============================================================
ASSISTANCE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assistance_demandes.json")

def charger_demandes_assistance() -> list:
    if os.path.exists(ASSISTANCE_FILE):
        try:
            with open(ASSISTANCE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []

def sauvegarder_demandes_assistance(demandes: list):
    try:
        with open(ASSISTANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(demandes, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erreur sauvegarde assistance: {e}")

@app.post("/api/assistance/envoyer")
async def api_envoyer_assistance(payload: dict = Body(...)):
    """Permet aux clients de signaler un problème ou de demander des explications sur leur chiffrage."""
    nom = (payload.get("nom") or "").strip() or "Client BTP"
    telephone = (payload.get("telephone") or "").strip()
    email = (payload.get("email") or "").strip()
    projet = (payload.get("projet") or "").strip()
    type_demande = (payload.get("type_demande") or "Explication chiffrage").strip()
    message = (payload.get("message") or "").strip()
    devis_info = payload.get("devis_info", {})

    if not message:
        raise HTTPException(status_code=400, detail="Veuillez décrire votre question ou problème de chiffrage.")

    nouvelle_demande = {
        "id": f"ast_{int(time.time())}_{hashlib.md5((telephone or 'client').encode()).hexdigest()[:4]}",
        "date": time.strftime("%d/%m/%Y %H:%M"),
        "timestamp": int(time.time()),
        "nom_client": nom,
        "telephone": telephone,
        "email": email,
        "nom_projet": projet,
        "type_demande": type_demande,
        "message": message,
        "devis_info": devis_info,
        "statut": "en_attente",
        "reponse_notes": ""
    }

    demandes = charger_demandes_assistance()
    demandes.insert(0, nouvelle_demande)
    sauvegarder_demandes_assistance(demandes)

    sb = get_supabase_client()
    if sb:
        try:
            sb.table("demandes_assistance").insert({
                "telephone": telephone,
                "nom_client": nom,
                "nom_projet": projet,
                "type_demande": type_demande,
                "message": message,
                "statut": "en_attente"
            }).execute()
        except Exception:
            pass

    return {
        "success": True,
        "message": "Votre demande a été transmise au Titulaire M. BOUFELDJA BENABDALLAH. Vous recevrez une réponse très rapidement.",
        "demande_id": nouvelle_demande["id"]
    }

@app.get("/api/admin/assistance")
async def api_admin_assistance(pin: str = None):
    """Permet au Titulaire de voir toutes les demandes d'assistance et d'explications des clients."""
    if not valider_admin_pin(pin):
        raise HTTPException(status_code=401, detail="Code PIN Administrateur incorrect.")
    demandes = charger_demandes_assistance()
    total = len(demandes)
    en_attente = len([d for d in demandes if d.get("statut") == "en_attente"])
    traitees = len([d for d in demandes if d.get("statut") == "traite"])
    return {
        "success": True,
        "stats": {
            "total": total,
            "en_attente": en_attente,
            "traitees": traitees
        },
        "demandes": demandes
    }

@app.post("/api/admin/assistance/traiter")
async def api_admin_traiter_assistance(payload: dict = Body(...)):
    """Marquer une demande comme traitée ou enregistrer une note."""
    pin = payload.get("pin")
    if not valider_admin_pin(pin):
        raise HTTPException(status_code=401, detail="Code PIN Administrateur incorrect.")
    demande_id = payload.get("demande_id")
    nouveau_statut = payload.get("statut", "traite")
    reponse = payload.get("reponse_notes", "")

    demandes = charger_demandes_assistance()
    modifie = False
    for d in demandes:
        if d.get("id") == demande_id:
            d["statut"] = nouveau_statut
            if reponse:
                d["reponse_notes"] = reponse
            modifie = True
            break

    if modifie:
        sauvegarder_demandes_assistance(demandes)
        return {"success": True, "message": f"Demande marquée comme '{nouveau_statut}' avec succès."}
    raise HTTPException(status_code=404, detail="Demande introuvable.")

# ============================================================
# AVIS & TÉMOIGNAGES CLIENTS SUR LE LOGICIEL BTP
# ============================================================
AVIS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "avis_clients.json")

AVIS_INITIAUX = [
    {
        "id": "av_1",
        "date": "16/10/2026",
        "nom": "Sarl Bâtiment Moderne Algérie",
        "metier": "Entreprise Générale BTP TCE",
        "wilaya": "Alger",
        "note": 5,
        "commentaire": "Le chiffrage direct à partir des photos WhatsApp et plans PDF est d'une rapidité impressionnante. Nos bordereaux DQE sortent aux normes en quelques secondes.",
        "statut": "approuve"
    },
    {
        "id": "av_2",
        "date": "14/10/2026",
        "nom": "M. Karim Belhadj",
        "metier": "Travaux Publics & VRD",
        "wilaya": "Oran",
        "note": 5,
        "commentaire": "Base des prix BPU très fidèle aux réalités du marché algérien en Dinars. Le calcul des délais et le planning des travaux Gantt nous ont fait remporter un marché clé.",
        "statut": "approuve"
    },
    {
        "id": "av_3",
        "date": "12/10/2026",
        "nom": "Ahmed Benali",
        "metier": "Génie Civil & Hydraulique",
        "wilaya": "Sétif",
        "note": 5,
        "commentaire": "Outil indispensable pour tout entrepreneur BTP. L'assistance et les explications de chiffrage de M. Benabdallah sont toujours rapides et précises.",
        "statut": "approuve"
    },
    {
        "id": "av_4",
        "date": "09/10/2026",
        "nom": "Yacine Mansouri",
        "metier": "Artisan Électricité & Climatisation",
        "wilaya": "Constantine",
        "note": 5,
        "commentaire": "Très simple à utiliser, même sur smartphone sur le chantier. L'export Excel avec formules automatiques évite toute erreur de sous-détail.",
        "statut": "approuve"
    },
    {
        "id": "av_5",
        "date": "05/10/2026",
        "nom": "Bureau d'Études & Métré BET",
        "metier": "Ingénierie & Suivi de Chantiers",
        "wilaya": "Tlemcen",
        "note": 4.9,
        "commentaire": "Excellente solution pour les métrés et la décomposition par lots. Le variateur anti-collision protège nos soumissions. Bravo pour cette innovation.",
        "statut": "approuve"
    }
]

def charger_avis_clients() -> list:
    if os.path.exists(AVIS_FILE):
        try:
            with open(AVIS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception:
            pass
    sauvegarder_avis_clients(AVIS_INITIAUX)
    return AVIS_INITIAUX

def sauvegarder_avis_clients(avis: list):
    try:
        with open(AVIS_FILE, "w", encoding="utf-8") as f:
            json.dump(avis, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erreur sauvegarde avis: {e}")

@app.get("/api/public/avis")
async def api_public_avis():
    """Récupère les avis approuvés des clients avec la note moyenne calculée."""
    avis = charger_avis_clients()
    approuves = [a for a in avis if a.get("statut", "approuve") == "approuve"]
    notes = [float(a.get("note", 5)) for a in approuves if a.get("note")]
    moyenne = round(sum(notes) / len(notes), 1) if notes else 4.9
    return {
        "success": True,
        "note_moyenne": moyenne,
        "total_avis": len(approuves),
        "avis": approuves
    }

@app.post("/api/public/avis/ajouter")
async def api_public_ajouter_avis(payload: dict = Body(...)):
    """Permet à un client de déposer un avis et une note sur le logiciel."""
    nom = (payload.get("nom") or "").strip() or "Client BTP"
    metier = (payload.get("metier") or "").strip() or "Entrepreneur BTP"
    wilaya = (payload.get("wilaya") or "").strip() or "Alger"
    commentaire = (payload.get("commentaire") or "").strip()
    try:
        note = float(payload.get("note", 5))
    except Exception:
        note = 5.0
    note = max(1.0, min(5.0, note))

    if not commentaire or len(commentaire) < 5:
        raise HTTPException(status_code=400, detail="Veuillez saisir votre commentaire ou retour d'expérience.")

    nouvel_avis = {
        "id": f"av_{int(time.time())}_{hashlib.md5(nom.encode()).hexdigest()[:4]}",
        "date": time.strftime("%d/%m/%Y"),
        "timestamp": int(time.time()),
        "nom": nom,
        "metier": metier,
        "wilaya": wilaya,
        "note": note,
        "commentaire": commentaire,
        "statut": "approuve"
    }

    avis = charger_avis_clients()
    avis.insert(0, nouvel_avis)
    sauvegarder_avis_clients(avis)

    return {
        "success": True,
        "message": "Merci beaucoup pour votre avis ! Votre témoignage est désormais visible.",
        "avis": nouvel_avis
    }

@app.get("/api/admin/avis")
async def api_admin_avis(pin: str = None):
    """Permet au Titulaire de modérer et consulter tous les avis."""
    if not valider_admin_pin(pin):
        raise HTTPException(status_code=401, detail="Code PIN Administrateur incorrect.")
    avis = charger_avis_clients()
    notes = [float(a.get("note", 5)) for a in avis if a.get("note")]
    moyenne = round(sum(notes) / len(notes), 1) if notes else 4.9
    return {
        "success": True,
        "stats": {
            "total": len(avis),
            "note_moyenne": moyenne
        },
        "avis": avis
    }

@app.post("/api/admin/avis/moderer")
async def api_admin_moderer_avis(payload: dict = Body(...)):
    """Action de modération (approuver, masquer, supprimer)."""
    pin = payload.get("pin")
    if not valider_admin_pin(pin):
        raise HTTPException(status_code=401, detail="Code PIN Administrateur incorrect.")
    avis_id = payload.get("avis_id")
    action = payload.get("action", "approuver")

    avis = charger_avis_clients()
    if action == "supprimer":
        avis = [a for a in avis if a.get("id") != avis_id]
        sauvegarder_avis_clients(avis)
        return {"success": True, "message": "Avis supprimé avec succès."}
    else:
        modifie = False
        for a in avis:
            if a.get("id") == avis_id:
                a["statut"] = "approuve" if action == "approuver" else "masque"
                modifie = True
                break
        if modifie:
            sauvegarder_avis_clients(avis)
            return {"success": True, "message": f"Statut de l'avis mis à jour ({action})."}
        raise HTTPException(status_code=404, detail="Avis introuvable.")