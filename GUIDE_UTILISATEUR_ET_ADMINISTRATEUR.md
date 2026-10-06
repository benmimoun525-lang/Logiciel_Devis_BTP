# 📘 MANUEL OFFICIEL & DIDACTICIEL COMPLET : LOGICIEL DEVIS BTP ALGÉRIE
*Chiffrage Intelligent par IA • BTP, Hydraulique & VRD • Normes Algériennes (DZD)*

---

## 🎯 1. CLARIFICATION DES RÔLES : PARTIE CLIENT vs PARTIE TITULAIRE

Le logiciel fonctionne selon une architecture **SaaS (Logiciel en tant que Service)** hermétique. Les rôles et les écrans sont strictement séparés :

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ESPACE CLIENT (PUBLIC)                          │
│  (Artisans, Métreurs, Bureaux d'études, Entrepreneurs de travaux)           │
│                                                                             │
│  • Saisie du numéro de téléphone (5 pages offertes)                         │
│  • Importation des bordereaux (WhatsApp, Photos chantier, PDF)              │
│  • Choix de la stratégie (Moins-disant pour soumission / Prix Moyen / Marge)│
│  • Consultation et insertion depuis le BPU Algérie (74 ouvrages BTP/VRD)    │
│  • Exports directs : WhatsApp en fichier Excel (.xlsx), Email, PDF officiel │
│  • Déclaration de paiement BaridiMob / CCP                                 │
│                                                                             │
│  ❌ AUCUN ACCÈS : Clés Gemini, marge du titulaire, devis des concurrents.   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Envoi de la preuve BaridiMob
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   ESPACE TITULAIRE / PROPRIÉTAIRE (PRIVÉ)                   │
│                    (Toi, le gérant et éditeur du logiciel)                  │
│                                                                             │
│  • Accès protégé par Code PIN secret (Bouton 👑 Titulaire Admin)            │
│  • Réception directe de l'argent sur ton compte BaridiMob / CCP             │
│  • Validation en 1 Clic des recharges clients (Ajout immédiat des crédits)  │
│  • Rechargement manuel express pour les paiements en espèces                │
│  • Supervision des quotas et pool de clés Gemini (hébergées sur Render)     │
│  • Contrôle et actualisation du BPU des prix unitaires (bpu_algerie.json)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📱 2. DIDACTICIEL DÉTAILLÉ : LA PARTIE CLIENT

### Étape 1 : Accès & Installation Mobile (PWA)
1. **Sur Smartphone (Android / iPhone)** :
   - Le client ouvre le lien dans Chrome ou Safari : `https://logiciel-devis-btp.onrender.com`.
   - Une bannière bleue apparaît : **"📲 Installer l'application sur votre smartphone"**.
   - Le client clique sur **"Installer l'App"** (ou *Ajouter à l'écran d'accueil*).
   - L'application s'installe comme une application native sans avoir besoin du Play Store.

### Étape 2 : Identification & Crédits Offerts
1. Le client clique sur **"👤 Mon Compte"** en haut de l'écran.
2. Il entre son **numéro de téléphone mobile algérien** (ex: `0550123456`).
3. **5 crédits pages lui sont offerts immédiatement** pour tester le chiffrage gratuitement.
4. Son solde s'affiche en temps réel sur le bouton d'en-tête (ex: `👤 Mon Compte (5 p.)`).

### Étape 3 : Chargement du Document Client
Trois méthodes simples s'offrent au client :
- **📸 Appareil Photo** : Pour photographier directement un bordereau papier sur le capot de la voiture ou sur le chantier.
- **🖼️ Photo WhatsApp / Galerie** : Pour sélectionner une capture d'écran reçue par WhatsApp.
- **📄 Fichier PDF** : Pour importer un appel d'offres complet reçu par email ou WhatsApp.

### Étape 4 : Découpage Automatique & File de Pages (Multi-Pages)
- Si le fichier PDF contient plusieurs pages (ex: 5 pages), le logiciel le découpe instantanément en 5 vignettes ordonnées.
- Le client peut cliquer sur la vignette de son choix pour visualiser la page avant chiffrage.

### Étape 5 : Le Chiffrage Intelligent par IA
Le client a deux boutons puissants :
1. **`⚡ Analyser la page active`** : Numérise et chiffre uniquement la page sélectionnée.
2. **`⚡ Analyser TOUT le PDF en un clic`** : Traite automatiquement toutes les pages de façon séquentielle sans intervention, en décomptant les crédits correspondants.
- **Règle 1:1 Respectée** : Si un article se répète plusieurs fois dans le document client, l'IA retranscrit scrupuleusement chaque ligne sans jamais les regrouper.

### Étape 6 : Choix de la Stratégie Commerciale
Dans la barre d'outils, le client sélectionne la stratégie adaptée à son objectif :
- **🎯 Moins-Disant (Recommandé pour Appel d'Offres)** : Calcule le prix plancher réaliste du marché pour remporter la soumission tout en restant viable.
- **⚖️ Prix Moyen** : Applique les prix médians constatés en Algérie.
- **🛡️ Marge Sécurisée** : Majore les prix de +10% à +15% pour les chantiers privés complexes.
- **🎲 Variateur Anti-Collision (±1.5%)** : Si deux entreprises utilisent le logiciel sur le même marché public, ce curseur applique une micro-variation invisible qui garantit que leurs montants totaux sont distincts, évitant tout soupçon d'entente illicite devant la commission des marchés publics.
- **📍 Région Géographique** : Option *Sud & Hauts-Plateaux* pour intégrer la majoration de transport des matériaux.

### Étape 7 : Utilisation de la Base des Prix (BPU Algérie)
- En cliquant sur **"💰 Base des Prix (BPU)"**, le client accède à **74 ouvrages de référence** classés par secteur :
  - 🏢 BTP / Gros-Œuvre / Second-Œuvre (44 articles).
  - 💧 Hydraulique & AEP (16 articles : conduites PEHD, fonte, regards, vannes).
  - 🛣️ Travaux Publics & VRD (14 articles : décapage, tuf, GNT, enrobés, bordures).
- En cliquant sur **"➕ Insérer"**, l'article s'ajoute directement dans le lot approprié du devis.

### Étape 8 : Retouche & Édition Manuelle
- Le tableau généré est 100% interactif. Le client peut :
  - Modifier le texte d'un article.
  - Ajuster les quantités et prix unitaires.
  - Ajouter une remise globale (%) ou modifier le taux de TVA (19% ou 9%).
  - Ajouter de nouveaux lots ou supprimer des lignes inutiles.

### Étape 9 : Canaux d'Exportation & Transmission
Le client dispose de 4 canaux de sortie professionnels :
1. **`📤 Partager sur WhatsApp`** :
   - Sur smartphone : ouvre directement le partage natif WhatsApp avec le **vrai fichier Excel `.xlsx` joint**.
   - Sur PC : télécharge le fichier `.xlsx` et ouvre WhatsApp Web avec le message récapitulatif.
2. **`📧 Envoyer par Email`** :
   - Ouvre le client de messagerie avec l'objet, le corps récapitulatif en Dinars (chiffres et lettres) et la proposition d'envoi.
3. **`📥 Télécharger Excel (.xlsx)`** :
   - Génère un fichier Excel professionnel complet avec formules automatiques de somme et en-tête d'entreprise.
4. **`🖨️ Imprimer / PDF Officiel`** :
   - Mise en page conforme aux normes algériennes : en-tête d'entreprise, NIF/RC, montant en toutes lettres, et zones de signature/cachet pour l'entreprise et le maître d'ouvrage.

### Étape 10 : Recharge de Crédits par BaridiMob
Quand le solde du client s'épuise :
1. Il clique sur **"💳 Tarifs & BaridiMob"**.
2. Il consulte les tarifs :
   - **Pack 50 Pages** : 4 000 DZD
   - **Pack 100 Pages** : 7 500 DZD
   - **Abonnement Mensuel (150 pages)** : 4 500 DZD
   - **Au devis (10 pages)** : 1 000 DZD
3. Il effectue le virement depuis son application BaridiMob vers ton RIP.
4. Il entre son numéro de transaction BaridiMob et clique sur **"📤 Confirmer mon virement BaridiMob"**.

---

## 👑 3. DIDACTICIEL DÉTAILLÉ : LA PARTIE TITULAIRE (ADMINISTRATEUR)

En tant que créateur et propriétaire du logiciel, voici comment tu gères ton activité :

### 1. Accès au Cockpit Administrateur
1. Dans l'en-tête du logiciel, clique sur le bouton violet : **"👑 Titulaire (Admin)"**.
2. Saisis ton **code PIN secret** : `7788` *(ce code reste mémorisé sur ton smartphone)*.
3. Le tableau de bord s'ouvre avec les indicateurs clés en direct :
   - 🤖 **Clés Gemini en service** : nombre de clés IA actives.
   - 👥 **Clients inscrits** : nombre d'artisans utilisant la plateforme.
   - 📑 **Devis générés** : total des devis créés.
   - ⏳ **En attente virement** : nombre de clients ayant payé par BaridiMob.

### 2. Encaissement de l'Argent Réel & Validation des Crédits
- **Flux financier** : L'argent des clients arrive directement sur ton compte BaridiMob / CCP via ton RIP :
  `007 99999 0023456789 25`.
- **Validation** :
  1. Dès que tu reçois la notification de virement sur ton application BaridiMob (ex: 4 000 DZD reçus de 0550123456), ouvre l'Espace Titulaire du logiciel.
  2. Dans la liste **"Virements BaridiMob & CCP à Valider"**, tu vois la ligne du client avec son téléphone et son numéro de transaction.
  3. Clique sur le bouton vert **`✅ Valider (+Crédits)`**.
  4. Le compte du client est **instantanément crédité** (50, 100 ou 150 pages selon la formule).
  5. S'il s'agit d'une tentative frauduleuse ou sans virement, clique sur **`❌ Rejeter`**.

### 3. Recharge Express Manuelle (Paiement Cash / Chantier)
Si un entrepreneur ou artisan te paie de main à main en espèces (dinars en liquide) sur le chantier :
1. Dans l'espace Titulaire, va dans la section **"⚡ Recharge Express Manuelle"**.
2. Tape son numéro de téléphone (ex: `0661234567`).
3. Choisis le nombre de pages (ex: `+50 pages`).
4. Clique sur **`➕ Créditer`**. Le client a ses crédits dans la seconde.

### 4. Gestion des Clés IA Gemini (Hébergées sur Render)
- **Protection absolue** : Les clients ne voient jamais tes clés API Gemini. Elles sont hébergées sur ton serveur Cloud (Render).
- **Zéro coupure** : Le logiciel intègre une rotation automatique multi-clés et multi-modèles (`gemini-3.5-flash`, `gemini-3.5-flash-lite`, etc.).
- **Pour ajouter des clés gratuites supplémentaires** :
  1. Va sur [Render.com](https://dashboard.render.com).
  2. Ouvre ton service web `logiciel-devis-btp` > **Environment**.
  3. Ajoute une variable `GEMINI_KEY_2`, `GEMINI_KEY_3`, etc.
  4. Sauvegarde : le serveur les prend en compte automatiquement sans aucune coupure.

### 5. Modification du Barème des Prix Unitaires (BPU)
Pour ajuster les prix du marché algérien en cas d'inflation (ex: augmentation du prix de la tonne de rond à béton ou du tuf) :
- Les prix sont répertoriés dans le fichier [`bpu_algerie.json`](file:///c:/Users/hp/Logiciel_Devis_BTP/bpu_algerie.json).
- Il suffit de modifier le champ `"prix_unitaire_moyen"` de l'article concerné.

### 6. Garantie Déontologique & Secret des Affaires
- Chaque devis client est hermétique et isolé. Aucun concurrent ne peut voir les bordereaux chiffrés par un autre entrepreneur.
- Conforme aux exigences du Code des marchés publics algériens (Décret présidentiel 15-247).

---

## 📋 RÉCAPITULATIF DES COMMANDES DU LOGICIEL

| Bouton / Commande | Visible Par | Fonction Précise |
| :--- | :--- | :--- |
| **👑 Titulaire (Admin)** | Titulaire (PIN) | Accès au panneau d'administration, validation BaridiMob, KPIs et recharge manuelle |
| **🔒 Confidentialité** | Tous | Affiche la charte de secret commercial et déontologie BTP |
| **💰 Base des Prix (BPU)**| Tous | Ouvre le catalogue de 74 prix référentiels avec insertion directe |
| **👤 Mon Compte** | Client | Affiche le solde de pages restantes et historique de l'artisan |
| **🏢 Profil Entreprise** | Client | Personnalise l'en-tête (Nom entreprise, NIF, RC, Téléphone, Email) |
| **📚 Historique** | Client | Sauvegarde et rechargement de devis antérieurs |
| **💳 Tarifs & BaridiMob** | Client | Consultation des formules et déclaration de virement |
| **🔄 Nouveau Devis** | Client | Réinitialise l'espace de travail pour un nouveau projet |
| **⚡ Analyser la page** | Client | Déclenche l'extraction et le chiffrage IA de la page sélectionnée |
| **⚡ Analyser TOUT le PDF** | Client | Chiffre automatiquement toutes les pages du PDF à la suite |
| **📤 Partager WhatsApp** | Client | Envoie directement le fichier Excel `.xlsx` sur WhatsApp |
| **📧 Envoyer par Email** | Client | Prépare l'email avec le récapitulatif financier et fichier Excel joint |
| **📥 Télécharger Excel** | Client | Télécharge le classeur Excel professionnel avec formules |
| **🖨️ Imprimer / PDF** | Client | Ouvre l'aperçu d'impression aux normes algériennes (chiffres et lettres) |
