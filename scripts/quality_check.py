"""
Étape 2 : Analyse de la qualité des données
On lit la table clients et on cherche les problèmes :
- valeurs manquantes par colonne
- lignes dupliquées
On calcule un score global et on sauvegarde le rapport.
"""

import pandas as pd
import json
from sqlalchemy import create_engine
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

DB_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DB_URL)

# Lecture des données
print("Lecture de la table clients...")
df = pd.read_sql("SELECT * FROM clients", engine)
total = len(df)
print(f"{total} lignes trouvées")

# --- Analyse des valeurs manquantes ---
manquants = {}
for col in df.columns:
    nb = df[col].isna().sum()
    if nb > 0:
        manquants[col] = int(nb)

# --- Détection des doublons ---
# On considère deux lignes comme doublons si même prénom + nom + email
nb_doublons = int(df.duplicated(subset=["prenom", "nom", "email"]).sum())

# --- Calcul du score de qualité ---
# Formule simple : on pénalise chaque anomalie trouvée
total_anomalies = sum(manquants.values()) + nb_doublons
score = max(0, round(100 - (total_anomalies / total * 100), 1))

# Niveau de santé
if score >= 95:
    niveau = "🟢 BONNE SANTÉ"
elif score >= 80:
    niveau = "🟡 DÉGRADÉE"
else:
    niveau = "🔴 CRITIQUE"

# Affichage dans le terminal
print("\n--- Rapport de qualité ---")
print(f"Score global : {niveau} ({score}%)")
print(f"Valeurs manquantes : {manquants}")
print(f"Doublons détectés : {nb_doublons}")

# --- Sauvegarde du rapport ---
rapport = {
    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "total_lignes": total,
    "score": score,
    "niveau": niveau,
    "manquants": manquants,
    "doublons": nb_doublons
}

# En JSON (pour l'agent IA)
with open("rapport.json", "w") as f:
    json.dump(rapport, f, ensure_ascii=False, indent=2)

# En base MySQL (pour l'historique)
rapport_df = pd.DataFrame([{
    "date_analyse": rapport["date"],
    "total_lignes": total,
    "score": score,
    "niveau": niveau,
    "nb_manquants": sum(manquants.values()),
    "nb_doublons": nb_doublons
}])
rapport_df.to_sql("rapports_qualite", engine, if_exists="append", index=False)

print("\n✅ Rapport sauvegardé dans rapport.json et dans MySQL")
