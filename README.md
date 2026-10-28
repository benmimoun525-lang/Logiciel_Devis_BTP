# Logiciel Devis BTP - Version Europe 🇪🇺

Application web moderne, réactive et autonome d'estimation, de métrés et d'édition de devis professionnels pour les entreprises et artisans du BTP en **France 🇫🇷, Belgique 🇧🇪, Luxembourg 🇱🇺 et Suisse 🇨🇭**.

---

## 🌟 Points Forts & Spécificités Européennes

### 1. Multi-Pays & Fiscalités Adaptées
- **France (FR)** :
  - Taux de TVA : **20.0%** (Neuf / standard), **10.0%** (Rénovation intermédiaire), **5.5%** (Rénovation énergétique / RGE), **0.0%** (Autoliquidation).
  - Identifiants légaux : SIRET, SIREN, Code NAF/APE, RCS, N° TVA intracommunautaire.
  - Mentions légales : Décennale obligatoire, médiateur de la consommation, indemnité forfaitaire de recouvrement (40 €).
- **Belgique (BE)** :
  - Taux de TVA : **21.0%** (Standard), **6.0%** (Rénovation logement > 10 ans), **12.0%** (Logements sociaux), **0.0%** (Report de perception / Co-contractant art. 20 AR n°1).
  - Identifiants légaux : N° Entreprise BCE, N° TVA, IBAN, BIC.
- **Luxembourg (LU)** :
  - Taux de TVA : **17.0%** (Normal), **3.0%** (Super-réduit pour création/rénovation logement principal), **8.0%** (Intermédiaire), **0.0%** (Autoliquidation).
  - Identifiants légaux : Matricule national / RCSL, Autorisation d'établissement.
- **Suisse (CH)** :
  - Devise : **CHF (Franc suisse)**.
  - Taux de TVA 2024+ : **8.1%** (Normal), **2.6%** (Réduit), **0.0%** (Exonéré).
  - Identifiants légaux : Numéro IDE/UID, Registre du Commerce, QR-IBAN.
  - Conformité avec les normes **SIA 118**.

---

### 2. Fonctionnalités Métier BTP Avancées
- **Bibliothèque d'ouvrages BTP intégrée** :
  - Gros œuvre, maçonnerie, terrassement, démolition, électricité NF C 15-100, plomberie sanitaire, PAC, menuiseries Uw <= 1.3, carrelage UPEC, peinture A+, toiture.
  - Recherche instantanée par mot-clé et filtre par corps d'état.
- **Autoliquidation de la TVA (Sous-traitance BTP)** :
  - Activation en 1 clic : bascule immédiate de la TVA à 0% et ajout de la mention légale obligatoire (*Art. 283-2 nonies du CGI* ou équivalent européen).
- **Retenue de garantie (5% légal)** :
  - Déduction automatique de la garantie de parfait achèvement (loi 71-584).
- **Étude de déboursé & Rentabilité Chantier** :
  - Calcul analytique du Déboursé Sec (DS = Fournitures + Main d'œuvre).
  - Calcul en temps réel de la marge brute de chantier (€) et du taux de marge (%).
  - Calcul du coefficient multiplicateur de vente `K = Prix Vente / Déboursé Sec`.
- **Ventilation de TVA dynamique** :
  - Calcul automatique des sous-totaux HT ventilés par taux de TVA.
- **Impression & Export PDF A4 Professionnel** :
  - Mise en page soignée pour impression papier ou génération PDF direct depuis le navigateur.
  - Cartouche de signature « Bon pour accord » avec mention obligatoire.
  - Mention des attestations d'assurances décennales.
- **Sauvegarde & Sécurité** :
  - Sauvegarde locale automatique (LocalStorage).
  - Export et Import de devis en **JSON** (sauvegarde portable).
  - Export métrique en **CSV / Excel**.

---

## 🚀 Utilisation Immédiate

L'application est **100% autonome et ne requiert aucune installation serveur**.

1. Ouvrez simplement le fichier `index.html` dans n'importe quel navigateur moderne (Chrome, Edge, Safari, Firefox).
2. Choisissez votre pays cible en haut à droite (🇫🇷, 🇧🇪, 🇱🇺, 🇨🇭).
3. Ajoutez vos ouvrages depuis la bibliothèque ou saisissez vos lignes personnalisées.
4. Ajustez les quantités et prix, puis cliquez sur **PDF / Imprimer** pour générer votre devis client officiel.

---

## 📁 Structure du Projet

```text
Logiciel_Devis_BTP/
├── index.html        # Application Web responsive (Desktop, Tablette, Mobile)
├── app.js            # Moteur applicatif, calculs BTP, fiscalités européennes
├── data-btp.js       # Bibliothèque d'ouvrages BTP et spécifications par pays
├── style.css         # Feuille de styles et règles d'impression A4 haute précision
└── README.md         # Documentation et guide technique
```
