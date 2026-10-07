"""
Dashboard Streamlit — Data Guardian
Visualisation du rapport de qualité + chat IA intégré
"""

import streamlit as st
import pandas as pd
import json
from groq import Groq
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(page_title="Data Guardian", page_icon="🛡️", layout="wide")
st.title("🛡️ Data Guardian — Tableau de bord qualité")

# Connexion MySQL
DB_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DB_URL)

# Lecture du rapport JSON
try:
    with open("rapport.json", "r") as f:
        rapport = json.load(f)
except FileNotFoundError:
    st.error("Rapport introuvable. Lance d'abord quality_check.py")
    st.stop()

# --- KPIs ---
st.subheader("Indicateurs clés")
col1, col2, col3, col4 = st.columns(4)

col1.metric("Total lignes", f"{rapport['total_lignes']:,}")
col2.metric("Valeurs manquantes", sum(rapport["manquants"].values()))
col3.metric("Doublons", rapport["doublons"])
col4.metric("Score qualité", f"{rapport['score']}%", rapport["niveau"])

st.divider()

# --- Graphique des anomalies par colonne ---
st.subheader("Anomalies par colonne")

if rapport["manquants"]:
    manquants_df = pd.DataFrame(
        rapport["manquants"].items(),
        columns=["Colonne", "Valeurs manquantes"]
    )
    st.bar_chart(manquants_df.set_index("Colonne"))
else:
    st.success("Aucune valeur manquante détectée !")

st.divider()

# --- Aperçu des données ---
st.subheader("Aperçu des données (50 premières lignes)")
df = pd.read_sql("SELECT * FROM clients LIMIT 50", engine)
st.dataframe(df, use_container_width=True)

st.divider()

# --- Chat IA ---
st.subheader("💬 Poser une question à l'IA")

contexte = f"""
Rapport de qualité :
- Total lignes : {rapport['total_lignes']}
- Score : {rapport['score']}% ({rapport['niveau']})
- Valeurs manquantes : {rapport['manquants']}
- Doublons : {rapport['doublons']}
"""

# Initialisation de l'historique de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage des messages précédents
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Champ de saisie
question = st.chat_input("Ex : Quelles colonnes corriger en priorité ?")

if question:
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.write(question)

    # Appel Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    reponse = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {"role": "system", "content": "Tu es un assistant qualité des données. Réponds en français.\n" + contexte},
            *st.session_state.messages
        ],
        temperature=0.5
    )

    texte = reponse.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": texte})

    with st.chat_message("assistant"):
        st.write(texte)
