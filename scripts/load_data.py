# ================================================
# DATA GUARDIAN - SCRIPT 1 : CHARGEMENT DES DONNÉES
# ================================================

import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

# Charger les variables du fichier .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

DB_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

print("=" * 50)
print("  DATA GUARDIAN - Chargement des données")
print("=" * 50)

# Connexion MySQL
try:
    engine = create_engine(DB_URL)
    conn = engine.connect()
    print("✅ Connexion MySQL réussie !")
    conn.close()
except Exception as e:
    print(f"❌ Erreur de connexion : {e}")
    exit()

# Téléchargement du dataset
print("\n⏳ Téléchargement du dataset clients...")
url = "https://raw.githubusercontent.com/datablist/sample-csv-files/main/files/customers/customers-100000.csv"

try:
    df = pd.read_csv(url)
    print(f"✅ Dataset chargé : {len(df)} lignes | {len(df.columns)} colonnes")
    print(f"\n📋 Colonnes disponibles : {list(df.columns)}")
    print(f"\n🔍 Aperçu des données :")
    print(df.head(3).to_string())
except Exception as e:
    print(f"❌ Erreur chargement dataset : {e}")
    exit()

# Injection de quelques anomalies pour rendre le projet réaliste
print("\n⚙️  Injection d'anomalies simulées pour le projet...")
import numpy as np
np.random.seed(42)

# 5% de valeurs manquantes sur Email
mask_email = np.random.choice(df.index, size=int(len(df) * 0.05), replace=False)
df.loc[mask_email, 'Email'] = np.nan

# 3% de doublons
doublons = df.sample(int(len(df) * 0.03))
df = pd.concat([df, doublons], ignore_index=True)

# 2% de valeurs aberrantes sur le prénom (valeurs vides)
mask_name = np.random.choice(df.index, size=int(len(df) * 0.02), replace=False)
df.loc[mask_name, 'First Name'] = np.nan

print(f"✅ Anomalies injectées | Nouveau total : {len(df)} lignes")

# Envoi dans MySQL
print("\n⏳ Envoi dans MySQL...")
try:
    df.to_sql("clients", engine, if_exists="replace", index=False)
    print(f"✅ Table 'clients' créée dans MySQL avec {len(df)} lignes !")
    print("\n🎉 Étape 1 terminée avec succès !")
except Exception as e:
    print(f"❌ Erreur envoi MySQL : {e}")
