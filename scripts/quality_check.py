# ============================================================
# FICHIER 2 : quality_check.py
# Ce script analyse la qualité des données dans la table "clients".
# Il cherche les valeurs manquantes et les doublons,
# calcule un score de qualité, et sauvegarde un rapport.
# ============================================================

import pandas as pd
import json                          # pour sauvegarder le rapport en format JSON
from sqlalchemy import create_engine
from datetime import datetime        # pour savoir la date et l'heure de l'analyse
from dotenv import load_dotenv
import os

load_dotenv()

# Connexion à MySQL (même chose que dans load_data.py)
DB_URL = (
    f"mysql+pymysql://"
    f"{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}"
    f"/{os.getenv('DB_NAME')}"
)
engine = create_engine(DB_URL)

# ---- LECTURE DES DONNÉES ----
print("Étape 1 : Lecture de la table 'clients' depuis MySQL...")
df = pd.read_sql("SELECT * FROM clients", engine)
total = len(df)
print(f"  ✅ {total} lignes trouvées")

# ---- RECHERCHE DES VALEURS MANQUANTES ----
# On vérifie colonne par colonne combien de cases sont vides
print("Étape 2 : Recherche des valeurs manquantes...")

manquants = {}  # dictionnaire : { "email": 5021, "prenom": 2003, ... }

for colonne in df.columns:
    nb_vides = df[colonne].isna().sum()  # .isna() retourne True si la case est vide
    if nb_vides > 0:
        manquants[colonne] = int(nb_vides)
        print(f"  → Colonne '{colonne}' : {nb_vides} valeurs manquantes")

if not manquants:
    print("  ✅ Aucune valeur manquante !")

# ---- RECHERCHE DES DOUBLONS ----
# Un doublon = deux lignes avec le même prénom + nom + email
print("Étape 3 : Recherche des doublons...")
nb_doublons = int(df.duplicated(subset=["prenom", "nom", "email"]).sum())
print(f"  → {nb_doublons} doublons trouvés")

# ---- CALCUL DU SCORE DE QUALITÉ ----
# Plus il y a d'anomalies par rapport au total, plus le score baisse.
# Formule : score = 100 - (nb_anomalies / total * 100)
print("Étape 4 : Calcul du score de qualité...")

total_anomalies = sum(manquants.values()) + nb_doublons
score = max(0, round(100 - (total_anomalies / total * 100), 1))

# On définit un niveau selon le score obtenu
if score >= 95:
    niveau = "🟢 BONNE SANTÉ"
elif score >= 80:
    niveau = "🟡 DÉGRADÉE"
else:
    niveau = "🔴 CRITIQUE"

print(f"\n  ⭐ Score de qualité : {score}% — {niveau}")

# ---- SAUVEGARDE DU RAPPORT ----
# On crée un dictionnaire qui résume tout ce qu'on a trouvé
rapport = {
    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "total_lignes": total,
    "score": score,
    "niveau": niveau,
    "manquants": manquants,
    "doublons": nb_doublons
}

# Sauvegarde en JSON (ce fichier sera lu par l'agent IA et le dashboard)
with open("rapport.json", "w", encoding="utf-8") as f:
    json.dump(rapport, f, ensure_ascii=False, indent=2)

print("  ✅ Rapport sauvegardé dans rapport.json")

# Sauvegarde aussi dans MySQL pour garder un historique des analyses
historique = pd.DataFrame([{
    "date_analyse": rapport["date"],
    "total_lignes": total,
    "score": score,
    "niveau": niveau,
    "nb_manquants": sum(manquants.values()),
    "nb_doublons": nb_doublons
}])
historique.to_sql("rapports_qualite", engine, if_exists="append", index=False)

print("  ✅ Rapport sauvegardé dans la table MySQL 'rapports_qualite'")
print("\nTerminé ! Tu peux maintenant lancer ai_agent.py ou streamlit run dashboard/app.py")
