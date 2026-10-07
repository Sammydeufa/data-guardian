"""
Étape 1 : Chargement des données clients dans MySQL
On télécharge un dataset public de 100 000 clients et on injecte
quelques anomalies pour simuler des données réelles imparfaites.
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

# Connexion à la base de données
DB_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DB_URL)

# Téléchargement du dataset (100 000 lignes de clients fictifs)
print("Téléchargement du dataset...")
url = "https://raw.githubusercontent.com/datablist/sample-csv-files/main/files/customers/customers-100000.csv"
df = pd.read_csv(url)

# On garde seulement les colonnes utiles
df = df[["Index", "First Name", "Last Name", "Email", "Phone", "Company", "Country"]].copy()
df.columns = ["id", "prenom", "nom", "email", "telephone", "entreprise", "pays"]

print(f"Dataset chargé : {len(df)} lignes")

# --- Injection d'anomalies réalistes ---

# 5% d'emails manquants (erreur de saisie fréquente)
nb_emails = int(len(df) * 0.05)
idx_emails = np.random.choice(df.index, nb_emails, replace=False)
df.loc[idx_emails, "email"] = None

# 2% de prénoms manquants
nb_prenoms = int(len(df) * 0.02)
idx_prenoms = np.random.choice(df.index, nb_prenoms, replace=False)
df.loc[idx_prenoms, "prenom"] = None

# 3% de doublons (on copie des lignes existantes)
nb_doublons = int(len(df) * 0.03)
doublons = df.sample(nb_doublons)
df = pd.concat([df, doublons], ignore_index=True)

print(f"Anomalies injectées : {nb_emails} emails manquants, {nb_prenoms} prénoms manquants, {nb_doublons} doublons")

# Chargement dans MySQL
print("Chargement dans MySQL...")
df.to_sql("clients", engine, if_exists="replace", index=False)

print("✅ Table 'clients' créée avec succès !")
print(f"   Total lignes : {len(df)}")
