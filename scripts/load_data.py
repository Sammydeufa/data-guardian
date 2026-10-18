import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
import random

load_dotenv()

DB_URL = (
    f"mysql+pymysql://"
    f"{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}"
    f"/{os.getenv('DB_NAME')}"
)
engine = create_engine(DB_URL)

print("Génération de 100 000 clients...")

n = 100000
prenoms = ["Lucas","Emma","Thomas","Léa","Nicolas","Camille","Julien","Sophie","Antoine","Marie"]
noms = ["Martin","Bernard","Dubois","Thomas","Robert","Richard","Petit","Durand","Leroy","Moreau"]
pays = ["France","Belgique","Suisse","Canada","Cameroun"]

df = pd.DataFrame({
    "id":         range(1, n+1),
    "prenom":     [random.choice(prenoms) for _ in range(n)],
    "nom":        [random.choice(noms) for _ in range(n)],
    "email":      [f"user{i}@gmail.com" for i in range(n)],
    "telephone":  [f"06{random.randint(10000000,99999999)}" for _ in range(n)],
    "entreprise": [f"Entreprise_{random.randint(1,200)}" for _ in range(n)],
    "pays":       [random.choice(pays) for _ in range(n)]
})

# Ajout d'anomalies
df.loc[np.random.choice(df.index, 5000, replace=False), "email"] = None
df.loc[np.random.choice(df.index, 2000, replace=False), "prenom"] = None
df = pd.concat([df, df.sample(3000)], ignore_index=True)

print("Chargement dans MySQL...")
df.to_sql("clients", engine, if_exists="replace", index=False)
print(f"✅ Terminé ! {len(df)} lignes chargées.")