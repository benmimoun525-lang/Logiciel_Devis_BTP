import os
import json
import pandas as pd
from PIL import Image
from google import genai

# 1. Clé d'API Google AI Studio
API_KEY = "AQ.Ab8RN6KgbTMrnn3fP8ZlFh-kP8d3614fogX9e8QDcwztPtMe_A"  # <-- Insérez votre clé exacte ici

def analyser_devis(image_path, output_excel="Devis_Propose.xlsx"):
    print(f"--- Analyse du document : {image_path} ---")
    
    # Client officiel Google GenAI
    client = genai.Client(api_key=API_KEY)
    
    # Chargement de la photo
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"Erreur lors de l'ouverture de l'image : {e}")
        return

    # Prompt d'extraction
    prompt = """
    Tu es un expert en métré BTP et chiffrage de fournitures.
    Analyse cette image de bordereau/devis et extrais les données sous forme de tableau.

    Pour chaque article ou ligne de prix, extrais :
    - "num_article": le numéro de l'article (ex: 1.1, 01, etc.)
    - "designation": la description précise de la fourniture ou prestation
    - "unite": l'unité (m2, m3, U, kg, ens, ml, etc.)
    - "quantite": la quantité demandée (nombre)
    - "prix_eco": estimation du prix unitaire en DA pour de l'entrée de gamme
    - "prix_std": estimation du prix unitaire en DA pour de la qualité standard / pro
    - "prix_premium": estimation du prix unitaire en DA pour de la haute qualité / marque

    Réponds UNIQUEMENT sous forme d'un tableau JSON valide (sans balises de code markdown ni texte autour). Format :
    [
      {
        "num_article": "1",
        "designation": "...",
        "unite": "U",
        "quantite": 10,
        "prix_eco": 400,
        "prix_std": 700,
        "prix_premium": 1000
      }
    ]
    """

    print("Envoi de la photo à l'IA...")
    
    # Utilisation du modèle recommandé par l'API
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=[img, prompt]
    )
    
    # Nettoyage de la réponse JSON
    texte_propre = response.text.replace("```json", "").replace("```", "").strip()
    
    try:
        data = json.loads(texte_propre)
        df = pd.DataFrame(data)
        
        # Calcul du total par défaut sur la gamme Standard
        df["prix_retenu_da"] = df["prix_std"]
        df["total_da"] = df["quantite"] * df["prix_retenu_da"]
        
        # Génération du fichier Excel
        df.to_excel(output_excel, index=False)
        print(f"\n[SUCCÈS] Le fichier Excel a été généré : {output_excel}")
        print("\nAperçu des données extraites :")
        print(df[["num_article", "designation", "unite", "quantite", "prix_std", "total_da"]])
        
    except Exception as e:
        print(f"Erreur de lecture JSON : {e}")
        print("Réponse brute de l'IA :", response.text)

if __name__ == "__main__":
    analyser_devis("devis_test.jpg")