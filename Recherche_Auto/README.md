# AutoCote - Application de Recherche & Aide à l'Achat de Véhicules

Une application moderne conçue pour aider les acheteurs à trouver leur véhicule idéal, évaluer le juste prix grâce au **baromètre de la cote réelle du marché**, et contacter directement les vendeurs.

---

## 🎯 Fonctionnalités Clés

### 1. Entonnoir de Recherche Guidé en Cascade
- **Étape 1 : Marque** : Saisie avec suggestions autocomplétées et accès rapide par badges (ex: *Renault*, *Peugeot*, *Volkswagen*, *Toyota*, *Hyundai*, *Dacia*...).
- **Étape 2 : Modèle** : Dès que la marque est sélectionnée, seuls les modèles associés s'affichent avec le nombre de véhicules disponibles.
- **Étape 3 : Année** : Dès que le modèle est choisi, la liste des années disponibles apparaît avec le prix moyen pour chaque millésime.
- **Étape 4 : Budget (Montant du ... au ...)** : Filtre par tranche de prix min et max, avec sélecteur de devise (**Dinar DZD (DA)** et **Euros (€)**).
- **Filtres supplémentaires** : Type de carburant (*Diesel, Essence, Hybride, Électrique*) et Boîte de vitesse (*Manuelle, Automatique*).

### 2. Baromètre & Cours Réel du Marché (La Cote)
- Calcul instantané de la **cote moyenne du marché** pour le modèle et l'année sélectionnés.
- Présentation de la **fourchette basse** et de la **fourchette haute**.
- Qualification visuelle de chaque annonce :
  - 🟢 **Bonne Affaire** (en dessous de la cote du marché)
  - 🔵 **Prix du Marché** (conforme à la cote)
  - 🟡 **Au-dessus du marché**

### 3. Fiches Véhicules & Contact Vendeur Direct
- Galerie photos avec zoom.
- Kilométrage, motorisation, boîte, couleur, wilaya/ville.
- **Références et coordonnées complètes du vendeur** :
  - Nom / Concession
  - Numéro de téléphone direct avec appel en 1 clic (`tel:`)
  - Bouton **WhatsApp** direct avec message pré-rempli contenant la référence de l'annonce et le prix.

### 4. Sauvegarde de la Sélection (Panier Acheteur)
- Sauvegarde instantanée de vos favoris (icône marque-page).
- Tiroir comparatif pour consulter les véhicules retenus côte à côte.
- Possibilité d'**imprimer ou d'exporter la fiche récapitulative en PDF**.

### 5. Ajout et Publication de Nouvelles Annonces
- Formulaire complet pour ajouter un nouveau véhicule au catalogue.
- Base de données SQLite (`auto_marche.db`) pré-chargée et facilement extensible.

---

## 🚀 Comment Lancer l'Application

### Méthode 1 : En 1 Clic (Windows)
Double-cliquez simplement sur le fichier :
```
lancer_app.bat
```
Il démarre le serveur local et ouvre automatiquement l'application dans votre navigateur à l'adresse `http://127.0.0.1:8050`.

### Méthode 2 : En Ligne de Commande
Dans le dossier `Recherche_Auto` :
```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8050 --reload
```
Puis ouvrez votre navigateur web sur :
[http://127.0.0.1:8050](http://127.0.0.1:8050)

---

## 📁 Structure du Dossier

```
Recherche_Auto/
│
├── auto_marche.db          # Base de données SQLite pré-chargée avec annonces réelles
├── database.py             # Script de gestion et initialisation de la base de données
├── main.py                 # Serveur API REST FastAPI
├── lancer_app.bat          # Fichier de lancement rapide en double-clic
├── README.md               # Documentation complète
└── static/
    └── index.html          # Interface web moderne responsive (Tailwind CSS + JS)
```
