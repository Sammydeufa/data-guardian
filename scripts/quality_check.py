# ================================================
# DATA GUARDIAN - SCRIPT 2 : ANALYSE QUALITÉ
# ================================================

import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
import json
from datetime import datetime

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

DB_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DB_URL)

print("=" * 55)
print("  DATA GUARDIAN - Analyse Qualité des Données")
print("=" * 55)

# Lecture des données
df = pd.read_sql("SELECT * FROM clients", engine)
print(f"\n📁 Table analysée : clients | {len(df)} lignes | {len(df.columns)} colonnes")

rapport = {
    "date_analyse": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "total_lignes": len(df),
    "total_colonnes": len(df.columns),
    "anomalies": []
}

# ── 1. VALEURS MANQUANTES ──
print("\n📊 ANALYSE 1 : Valeurs manquantes")
print("-" * 40)
missing = df.isnull().sum()
missing_pct = (missing / len(df) * 100).round(2)
has_missing = False
for col in df.columns:
    if missing[col] > 0:
        has_missing = True
        niveau = "🔴 CRITIQUE" if missing_pct[col] > 10 else "🟡 ATTENTION"
        print(f"  {niveau} | {col} : {missing[col]} manquantes ({missing_pct[col]}%)")
        rapport["anomalies"].append({
            "type": "Valeurs manquantes",
            "colonne": col,
            "valeur": f"{missing[col]} ({missing_pct[col]}%)",
            "niveau": "CRITIQUE" if missing_pct[col] > 10 else "ATTENTION"
        })
if not has_missing:
    print("  ✅ Aucune valeur manquante détectée")

# ── 2. DOUBLONS ──
print("\n📊 ANALYSE 2 : Doublons")
print("-" * 40)
doublons = df.duplicated().sum()
doublons_pct = round(doublons / len(df) * 100, 2)
if doublons > 0:
    niveau = "🔴 CRITIQUE" if doublons_pct > 5 else "🟡 ATTENTION"
    print(f"  {niveau} | {doublons} lignes dupliquées ({doublons_pct}%)")
    rapport["anomalies"].append({
        "type": "Doublons",
        "colonne": "Toutes",
        "valeur": f"{doublons} ({doublons_pct}%)",
        "niveau": "CRITIQUE" if doublons_pct > 5 else "ATTENTION"
    })
else:
    print("  ✅ Aucun doublon détecté")

# ── 3. SCORE GLOBAL ──
print("\n📊 SCORE GLOBAL DE QUALITÉ")
print("-" * 40)
total_cells = len(df) * len(df.columns)
missing_cells = df.isnull().sum().sum()
doublon_cells = doublons * len(df.columns)
score = round((1 - (missing_cells + doublon_cells) / total_cells) * 100, 2)
score = max(0, min(100, score))

rapport["score_qualite"] = score
rapport["nb_anomalies"] = len(rapport["anomalies"])

if score >= 95:
    emoji = "🟢"
    statut = "BONNE SANTÉ"
elif score >= 80:
    emoji = "🟡"
    statut = "DÉGRADÉE"
else:
    emoji = "🔴"
    statut = "CRITIQUE"

print(f"  {emoji} Score : {score}% — {statut}")
print(f"  📌 {len(rapport['anomalies'])} anomalie(s) détectée(s)")

# ── 4. SAUVEGARDE DU RAPPORT ──
rapport_df = pd.DataFrame(rapport["anomalies"]) if rapport["anomalies"] else pd.DataFrame(
    columns=["type", "colonne", "valeur", "niveau"])
rapport_df["date_analyse"] = rapport["date_analyse"]
rapport_df["score_qualite"] = score
rapport_df.to_sql("rapports_qualite", engine, if_exists="replace", index=False)

# Sauvegarde JSON
rapport_path = os.path.join(os.path.dirname(__file__), '..', 'rapport.json')
with open(rapport_path, 'w', encoding='utf-8') as f:
    json.dump(rapport, f, ensure_ascii=False, indent=2)

print(f"\n✅ Rapport sauvegardé dans MySQL (table 'rapports_qualite') et rapport.json")
print("\n🎉 Étape 2 terminée ! Lance maintenant : python scripts/ai_agent.py")
