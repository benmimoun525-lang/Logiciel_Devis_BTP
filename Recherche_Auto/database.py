import sqlite3
import os
import json
from typing import List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "auto_marche.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Table des véhicules avec support multi-photos et caractéristiques marché Ouedkniss
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        marque TEXT NOT NULL,
        modele TEXT NOT NULL,
        version TEXT,
        annee INTEGER NOT NULL,
        prix REAL NOT NULL,
        prix_marche_estime REAL NOT NULL,
        kilometrage INTEGER NOT NULL,
        carburant TEXT NOT NULL,
        boite TEXT NOT NULL,
        couleur TEXT,
        wilaya TEXT,
        papiers TEXT DEFAULT 'Carte Grise (Safia)',
        sbigha TEXT DEFAULT '00 Peinture (Tôle d''origine)',
        vendeur_nom TEXT NOT NULL,
        vendeur_type TEXT DEFAULT 'Particulier',
        vendeur_tel TEXT NOT NULL,
        vendeur_whatsapp TEXT,
        vendeur_email TEXT,
        reference_annonce TEXT UNIQUE NOT NULL,
        photo_principale TEXT NOT NULL,
        photos_liste TEXT,
        description TEXT,
        date_ajout TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Si la table existe déjà sans les colonnes, on les ajoute si besoin
    try:
        cursor.execute("ALTER TABLE vehicules ADD COLUMN photos_liste TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE vehicules ADD COLUMN papiers TEXT DEFAULT 'Carte Grise (Safia)'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE vehicules ADD COLUMN sbigha TEXT DEFAULT '00 Peinture (Tôle d''origine)'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE vehicules ADD COLUMN version TEXT")
    except Exception:
        pass

    cursor.execute("SELECT COUNT(*) FROM vehicules")
    count = cursor.fetchone()[0]
    
    # Si vide ou ancienne structure sans multi-photos, on réinitialise avec le catalogue riche
    cursor.execute("SELECT photos_liste FROM vehicules LIMIT 1")
    first_row = cursor.fetchone()
    if count == 0 or (first_row and not first_row[0]):
        cursor.execute("DELETE FROM vehicules")
        seed_data(cursor)
        
    conn.commit()
    conn.close()

def seed_data(cursor):
    sample_vehicles = [
        # 1. RENAULT CLIO 4 GT-LINE
        {
            "marque": "Renault",
            "modele": "Clio 4",
            "version": "GT-Line 1.5 dCi 85ch",
            "annee": 2019,
            "prix": 2450000,
            "prix_marche_estime": 2500000,
            "kilometrage": 85000,
            "carburant": "Diesel (1.5 dCi)",
            "boite": "Manuelle",
            "couleur": "Gris Titanium",
            "wilaya": "Alger (Bab Ezzouar)",
            "papiers": "Carte Grise (Safia)",
            "sbigha": "00 Peinture, 00 Retouche (Tôle d'origine)",
            "vendeur_nom": "Karim Bouzid",
            "vendeur_type": "Particulier",
            "vendeur_tel": "0550 12 34 56",
            "vendeur_whatsapp": "213550123456",
            "vendeur_email": "karim.bouzid@email.com",
            "reference_annonce": "OK-REN-CL4-2019",
            "photo_principale": "https://images.unsplash.com/photo-1541348263662-e0c8666579f1?auto=format&fit=crop&w=1000&q=80",
            "photos_liste": json.dumps([
                "https://images.unsplash.com/photo-1541348263662-e0c8666579f1?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1590362891988-f77804702088?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1542282088-72c9c27ed0cd?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1000&q=80"
            ]),
            "description": "Renault Clio 4 GT-Line dCi 85ch d'origine, première main. Entretien à jour chaque 10 000 km avec filtre et huile d'origine. Pneus Michelin récents, plaquettes neuves. Intérieur semi-cuir très propre, non-fumeur, carnet d'entretien disponible."
        },

        # 2. RENAULT CLIO 4 LIMITED
        {
            "marque": "Renault",
            "modele": "Clio 4",
            "version": "Limited 0.9 TCe 90ch",
            "annee": 2018,
            "prix": 2200000,
            "prix_marche_estime": 2300000,
            "kilometrage": 115000,
            "carburant": "Essence (0.9 TCe)",
            "boite": "Manuelle",
            "couleur": "Blanc Glacier",
            "wilaya": "Blida (Centre)",
            "papiers": "Carte Grise (Safia)",
            "sbigha": "Raccord à froid 10cm aile arrière, le reste d'origine",
            "vendeur_nom": "Garage Auto Plus Blida",
            "vendeur_type": "Professionnel",
            "vendeur_tel": "0661 88 99 00",
            "vendeur_whatsapp": "213661889900",
            "vendeur_email": "contact@autoplus-blida.com",
            "reference_annonce": "OK-REN-CL4-2018",
            "photo_principale": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1000&q=80",
            "photos_liste": json.dumps([
                "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1542282088-72c9c27ed0cd?auto=format&fit=crop&w=1000&q=80"
            ]),
            "description": "Clio 4 Limited propre, écran tactile Media Nav avec GPS, climatisation automatique, régulateur/limiteur de vitesse. Moteur essence très silencieux et faible consommation. Vidange et révision faites il y a 2 semaines."
        },

        # 3. RENAULT CLIO 5 INTENS
        {
            "marque": "Renault",
            "modele": "Clio 5",
            "version": "Intens Full LED 1.0 TCe 100ch",
            "annee": 2021,
            "prix": 3150000,
            "prix_marche_estime": 3220000,
            "kilometrage": 48000,
            "carburant": "Essence (1.0 TCe)",
            "boite": "Manuelle",
            "couleur": "Bleu Celadon",
            "wilaya": "Oran (Akid Lotfi)",
            "papiers": "Carte Grise (Safia)",
            "sbigha": "00 Peinture, 00 Masrofa (État Neuf)",
            "vendeur_nom": "Sofiane Mansouri",
            "vendeur_type": "Particulier",
            "vendeur_tel": "0770 45 67 89",
            "vendeur_whatsapp": "213770456789",
            "vendeur_email": "s.mansouri@gmail.com",
            "reference_annonce": "OK-REN-CL5-2021",
            "photo_principale": "https://images.unsplash.com/photo-1617814076367-b759c7d7e738?auto=format&fit=crop&w=1000&q=80",
            "photos_liste": json.dumps([
                "https://images.unsplash.com/photo-1617814076367-b759c7d7e738?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1542282088-72c9c27ed0cd?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=1000&q=80"
            ]),
            "description": "Renault Clio 5 Intens comme neuve, feux Pure Vision LED avant/arrière, tableau de bord numérique cockpit, radar et caméra de recul 360°, allumage automatique des feux, jantes alliage diamantées 16 pouces."
        },

        # 4. RENAULT CLIO 5 R.S. LINE
        {
            "marque": "Renault",
            "modele": "Clio 5",
            "version": "R.S. Line X-Tronic BVA",
            "annee": 2022,
            "prix": 3480000,
            "prix_marche_estime": 3550000,
            "kilometrage": 26000,
            "carburant": "Essence (1.0 TCe 100)",
            "boite": "Automatique",
            "couleur": "Rouge Flamme",
            "wilaya": "Alger (Hydra)",
            "papiers": "Carte Grise (Safia)",
            "sbigha": "00 Peinture (Voiture de maison)",
            "vendeur_nom": "Elite Cars Alger",
            "vendeur_type": "Professionnel",
            "vendeur_tel": "0555 77 11 22",
            "vendeur_whatsapp": "213555771122",
            "vendeur_email": "elite.cars.alger@gmail.com",
            "reference_annonce": "OK-REN-CL5-2022",
            "photo_principale": "https://images.unsplash.com/photo-1502877338535-766e1452684a?auto=format&fit=crop&w=1000&q=80",
            "photos_liste": json.dumps([
                "https://images.unsplash.com/photo-1502877338535-766e1452684a?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1617814076367-b759c7d7e738?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1541348263662-e0c8666579f1?auto=format&fit=crop&w=1000&q=80"
            ]),
            "description": "Clio 5 finition sportive R.S. Line avec boîte automatique séquentielle. Sièges baquets spécifiques RS, volant cuir perforé, pack Multi-Sense avec modes de conduite (Sport, Eco, MySense), jantes Magny-Cours 17 pouces."
        },

        # 5. RENAULT MÉGANE 4 GT-LINE
        {
            "marque": "Renault",
            "modele": "Megane 4",
            "version": "GT-Line 1.5 dCi 115ch",
            "annee": 2020,
            "prix": 3600000,
            "prix_marche_estime": 3750000,
            "kilometrage": 68000,
            "carburant": "Diesel (1.5 dCi)",
            "boite": "Manuelle",
            "couleur": "Noir Etoilé",
            "wilaya": "Setif (El Eulma)",
            "papiers": "Carte Grise (Safia)",
            "sbigha": "00 Peinture, 00 Rayures",
            "vendeur_nom": "Yacine Rahmani",
            "vendeur_type": "Particulier",
            "vendeur_tel": "0660 33 44 55",
            "vendeur_whatsapp": "213660334455",
            "vendeur_email": "yacine.setif@yahoo.fr",
            "reference_annonce": "OK-REN-MEG-2020",
            "photo_principale": "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=1000&q=80",
            "photos_liste": json.dumps([
                "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1541348263662-e0c8666579f1?auto=format&fit=crop&w=1000&q=80"
            ]),
            "description": "Mégane 4 GT Line phase 2, très belle configuration : affichage tête haute HUD, sellerie alcantara surpiquée bleue, grand écran vertical R-Link 2 avec Apple CarPlay/Android Auto, régulateur adaptatif."
        },

        # 6. RENAULT DUSTER PRESTIGE 4x4
        {
            "marque": "Renault",
            "modele": "Duster",
            "version": "Prestige 4x4 1.5 dCi 110",
            "annee": 2021,
            "prix": 3720000,
            "prix_marche_estime": 3800000,
            "kilometrage": 54000,
            "carburant": "Diesel (1.5 dCi 4x4)",
            "boite": "Manuelle",
            "couleur": "Orange Atacama",
            "wilaya": "Batna",
            "papiers": "Carte Grise (Safia)",
            "sbigha": "00 Peinture (Tôle saine)",
            "vendeur_nom": "Mourad Chaoui",
            "vendeur_type": "Particulier",
            "vendeur_tel": "0670 11 22 33",
            "vendeur_whatsapp": "213670112233",
            "vendeur_email": "mourad.chaoui@hotmail.com",
            "reference_annonce": "OK-REN-DUS-2021",
            "photo_principale": "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&w=1000&q=80",
            "photos_liste": json.dumps([
                "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1511919884226-fd3cad34687c?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1000&q=80"
            ]),
            "description": "Duster Prestige véritable 4 roues motrices avec blocage de différentiel, caméras multivues 360°, avertisseur d'angle mort, barres de toit et sabot de protection alu. Idéal routes et pistes."
        },

        # 7. VOLKSWAGEN GOLF 7.5 R-LINE
        {
            "marque": "Volkswagen",
            "modele": "Golf 7",
            "version": "R-Line 2.0 TDI 150ch DSG7",
            "annee": 2019,
            "prix": 3950000,
            "prix_marche_estime": 4100000,
            "kilometrage": 95000,
            "carburant": "Diesel (2.0 TDI)",
            "boite": "Automatique (DSG7)",
            "couleur": "Gris Indium Métallisé",
            "wilaya": "Alger (Chéraga)",
            "papiers": "Carte Grise (Safia)",
            "sbigha": "00 Peinture (Contrôle technique vierge)",
            "vendeur_nom": "Tarek Benali",
            "vendeur_type": "Particulier",
            "vendeur_tel": "0560 90 80 70",
            "vendeur_whatsapp": "213560908070",
            "vendeur_email": "tarek.benali@gmail.com",
            "reference_annonce": "OK-VW-G7-2019",
            "photo_principale": "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?auto=format&fit=crop&w=1000&q=80",
            "photos_liste": json.dumps([
                "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1502877338535-766e1452684a?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1542282088-72c9c27ed0cd?auto=format&fit=crop&w=1000&q=80"
            ]),
            "description": "Golf 7.5 R-Line intérieure et extérieure d'origine. Toit ouvrant panoramique, Active Info Display (Virtual Cockpit), boîte DSG 7 rapports avec palettes au volant, feux LED Matrix directionnels."
        },

        # 8. VOLKSWAGEN GOLF 8 LIFE
        {
            "marque": "Volkswagen",
            "modele": "Golf 8",
            "version": "Life 1.5 eTSI 150ch DSG7",
            "annee": 2022,
            "prix": 5600000,
            "prix_marche_estime": 5800000,
            "kilometrage": 32000,
            "carburant": "Essence (Mild Hybrid)",
            "boite": "Automatique (DSG7)",
            "couleur": "Blanc Pur",
            "wilaya": "Oran (Bir El Djir)",
            "papiers": "Carte Grise (Safia)",
            "sbigha": "00 Peinture (État sortie de showroom)",
            "vendeur_nom": "Prestige Motors Oran",
            "vendeur_type": "Professionnel",
            "vendeur_tel": "0550 99 88 77",
            "vendeur_whatsapp": "213550998877",
            "vendeur_email": "contact@prestigemotors-oran.com",
            "reference_annonce": "OK-VW-G8-2022",
            "photo_principale": "https://images.unsplash.com/photo-1502877338535-766e1452684a?auto=format&fit=crop&w=1000&q=80",
            "photos_liste": json.dumps([
                "https://images.unsplash.com/photo-1502877338535-766e1452684a?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=1000&q=80"
            ]),
            "description": "Golf 8 importée avec carte grise finale safia. Double écran Innovision Cockpit numérique, chargeur sans fil smartphone, climatisation tactile tri-zone, système de maintien dans la voie Lane Assist."
        },

        # 9. VOLKSWAGEN POLO 6 HIGHLINE
        {
            "marque": "Volkswagen",
            "modele": "Polo",
            "version": "Highline 1.0 TSI 95ch",
            "annee": 2020,
            "prix": 3100000,
            "prix_marche_estime": 3200000,
            "kilometrage": 72000,
            "carburant": "Essence (1.0 TSI)",
            "boite": "Manuelle",
            "couleur": "Rouge Flash",
            "wilaya": "Tizi Ouzou",
            "papiers": "Carte Grise (Safia)",
            "sbigha": "00 Peinture",
            "vendeur_nom": "Nabil Hamdi",
            "vendeur_type": "Particulier",
            "vendeur_tel": "0771 22 33 44",
            "vendeur_whatsapp": "213771223344",
            "vendeur_email": "nabil.hamdi@yahoo.com",
            "reference_annonce": "OK-VW-POL-2020",
            "photo_principale": "https://images.unsplash.com/photo-1541348263662-e0c8666579f1?auto=format&fit=crop&w=1000&q=80",
            "photos_liste": json.dumps([
                "https://images.unsplash.com/photo-1541348263662-e0c8666579f1?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1502877338535-766e1452684a?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1590362891988-f77804702088?auto=format&fit=crop&w=1000&q=80"
            ]),
            "description": "Polo 6 Highline très soignée, jantes alliage 16 pouces, radar avant et arrière avec affichage graphique, feux antibrouillard avec éclairage d'intersection, volant multifonction cuir."
        },

        # 10. PEUGEOT 208 ALLURE
        {
            "marque": "Peugeot",
            "modele": "208",
            "version": "Allure 1.2 PureTech 100ch",
            "annee": 2021,
            "prix": 3200000,
            "prix_marche_estime": 3300000,
            "kilometrage": 41000,
            "carburant": "Essence (1.2 PureTech)",
            "boite": "Manuelle",
            "couleur": "Jaune Faro Métallisé",
            "wilaya": "Annaba",
            "papiers": "Carte Grise (Safia)",
            "sbigha": "00 Peinture, 00 Choc",
            "vendeur_nom": "Hichem Saidi",
            "vendeur_type": "Particulier",
            "vendeur_tel": "0665 44 33 22",
            "vendeur_whatsapp": "213665443322",
            "vendeur_email": "hichem.annaba@gmail.com",
            "reference_annonce": "OK-PEU-208-2021",
            "photo_principale": "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=1000&q=80",
            "photos_liste": json.dumps([
                "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1617814076367-b759c7d7e738?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1541348263662-e0c8666579f1?auto=format&fit=crop&w=1000&q=80"
            ]),
            "description": "Nouvelle 208 Allure couleur Jaune Faro avec intérieur i-Cockpit 3D holographique, grand écran tactile 10 pouces, frein de stationnement électrique, jantes Soho 16 diamantées."
        },

        # 11. DACIA SANDERO STEPWAY
        {
            "marque": "Dacia",
            "modele": "Sandero Stepway",
            "version": "Stepway Confort 1.5 dCi",
            "annee": 2019,
            "prix": 2100000,
            "prix_marche_estime": 2150000,
            "kilometrage": 89000,
            "carburant": "Diesel (1.5 dCi)",
            "boite": "Manuelle",
            "couleur": "Gris Comète",
            "wilaya": "Bejaia",
            "papiers": "Carte Grise (Safia)",
            "sbigha": "00 Peinture (Tôle d'origine intacte)",
            "vendeur_nom": "Samir Meziani",
            "vendeur_type": "Particulier",
            "vendeur_tel": "0662 55 44 33",
            "vendeur_whatsapp": "213662554433",
            "vendeur_email": "samir.bejaia@gmail.com",
            "reference_annonce": "OK-DAC-SAN-2019",
            "photo_principale": "https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?auto=format&fit=crop&w=1000&q=80",
            "photos_liste": json.dumps([
                "https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1541348263662-e0c8666579f1?auto=format&fit=crop&w=1000&q=80"
            ]),
            "description": "Sandero Stepway réputée pour sa robustesse et faible consommation (4.2L/100). Barres de toit modulables, garde au sol surélevée, climatisation puissante, radar de stationnement."
        },

        # 12. TOYOTA HILUX DOUBLE CABINE 4x4
        {
            "marque": "Toyota",
            "modele": "Hilux",
            "version": "Invincible 2.4 D-4D 4x4",
            "annee": 2020,
            "prix": 5900000,
            "prix_marche_estime": 6100000,
            "kilometrage": 82000,
            "carburant": "Diesel (2.4 D-4D)",
            "boite": "Manuelle",
            "couleur": "Blanc Pur",
            "wilaya": "Biskra",
            "papiers": "Carte Grise (Safia)",
            "sbigha": "00 Peinture (Jamais fait de travaux lourds)",
            "vendeur_nom": "Agence Auto Sahara",
            "vendeur_type": "Professionnel",
            "vendeur_tel": "0661 55 66 77",
            "vendeur_whatsapp": "213661556677",
            "vendeur_email": "contact@autosahara.dz",
            "reference_annonce": "OK-TOY-HIL-2020",
            "photo_principale": "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&w=1000&q=80",
            "photos_liste": json.dumps([
                "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1511919884226-fd3cad34687c?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1000&q=80"
            ]),
            "description": "Toyota Hilux double cabine 4x4 légendaire pour sa fiabilité indestructible. Benne protégée avec revêtement plastique d'origine, arceau inox chromé, climatisation automatique, suspension renforcée."
        },

        # 13. HYUNDAI TUCSON N-LINE
        {
            "marque": "Hyundai",
            "modele": "Tucson",
            "version": "N-Line 2.0 CRDi 185ch 4WD BVA",
            "annee": 2020,
            "prix": 4800000,
            "prix_marche_estime": 4950000,
            "kilometrage": 65000,
            "carburant": "Diesel (2.0 CRDi)",
            "boite": "Automatique",
            "couleur": "Noir Fantôme",
            "wilaya": "Setif",
            "papiers": "Carte Grise (Safia)",
            "sbigha": "00 Peinture",
            "vendeur_nom": "Farid Belhadj",
            "vendeur_type": "Particulier",
            "vendeur_tel": "0552 66 77 88",
            "vendeur_whatsapp": "213552667788",
            "vendeur_email": "farid.belhadj@gmail.com",
            "reference_annonce": "OK-HYU-TUC-2020",
            "photo_principale": "https://images.unsplash.com/photo-1511919884226-fd3cad34687c?auto=format&fit=crop&w=1000&q=80",
            "photos_liste": json.dumps([
                "https://images.unsplash.com/photo-1511919884226-fd3cad34687c?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1502877338535-766e1452684a?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?auto=format&fit=crop&w=1000&q=80"
            ]),
            "description": "Hyundai Tucson N-Line 4 roues motrices. Sièges sport en cuir et alcantara surpiqués rouge, toit ouvrant panoramique, hayon de coffre électrique mains libres, sono KRELL premium."
        }
    ]

    for item in sample_vehicles:
        cursor.execute("""
        INSERT INTO vehicules (
            marque, modele, version, annee, prix, prix_marche_estime, kilometrage,
            carburant, boite, couleur, wilaya, papiers, sbigha, vendeur_nom, vendeur_type,
            vendeur_tel, vendeur_whatsapp, vendeur_email, reference_annonce,
            photo_principale, photos_liste, description
        ) VALUES (
            :marque, :modele, :version, :annee, :prix, :prix_marche_estime, :kilometrage,
            :carburant, :boite, :couleur, :wilaya, :papiers, :sbigha, :vendeur_nom, :vendeur_type,
            :vendeur_tel, :vendeur_whatsapp, :vendeur_email, :reference_annonce,
            :photo_principale, :photos_liste, :description
        )
        """, item)

if __name__ == "__main__":
    init_db()
    print("Base de données actualisée avec succès avec annonces réelles multi-photos !")
