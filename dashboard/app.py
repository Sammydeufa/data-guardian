# ================================================
# DATA GUARDIAN - DASHBOARD STREAMLIT
# ================================================

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
import json
from groq import Groq
import time

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

DB_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DB_URL)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── CONFIG PAGE ──
st.set_page_config(
    page_title="Data Guardian",
    page_icon="🛡️",
    layout="wide"
)

# ── STYLE ──
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border-radius: 12px;
        padding: 20px;
        color: white;
        text-align: center;
        border: 1px solid #c9a84c;
    }
    .score-high { color: #00ff88; font-size: 3rem; font-weight: bold; }
    .score-mid  { color: #ffcc00; font-size: 3rem; font-weight: bold; }
    .score-low  { color: #ff4444; font-size: 3rem; font-weight: bold; }
    h1 { color: #c9a84c !important; }
</style>
""", unsafe_allow_html=True)

# ── HEADER ──
st.title("🛡️ Data Guardian")
st.markdown("**Plateforme intelligente de surveillance de la qualité des données**")
st.markdown("---")

# ── CHARGEMENT DONNÉES ──
@st.cache_data(ttl=30)
def charger_donnees():
    df = pd.read_sql("SELECT * FROM clients", engine)
    return df

@st.cache_data(ttl=30)
def charger_rapport():
    try:
        rapport_path = os.path.join(os.path.dirname(__file__), '..', 'rapport.json')
        with open(rapport_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

df = charger_donnees()
rapport = charger_rapport()

# ── CALCUL MÉTRIQUES ──
total = len(df)
doublons = df.duplicated().sum()
missing_total = df.isnull().sum().sum()
missing_pct = round(missing_total / (total * len(df.columns)) * 100, 2)
score = rapport["score_qualite"] if rapport else 0

# ── KPIs ──
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📁 Total lignes", f"{total:,}")

with col2:
    couleur = "normal" if missing_pct < 5 else "inverse"
    st.metric("⚠️ Valeurs manquantes", f"{missing_total:,}", f"{missing_pct}%", delta_color=couleur)

with col3:
    couleur = "normal" if doublons < 100 else "inverse"
    st.metric("🔄 Doublons", f"{doublons:,}", delta_color=couleur)

with col4:
    couleur_score = "score-high" if score >= 95 else ("score-mid" if score >= 80 else "score-low")
    st.markdown(f"""
    <div class="metric-card">
        <p style="margin:0; color:#aaa">Score Qualité</p>
        <p class="{couleur_score}">{score}%</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ── ANOMALIES ──
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("📊 Analyse des colonnes")
    missing_par_col = df.isnull().sum()
    missing_par_col = missing_par_col[missing_par_col > 0].reset_index()
    missing_par_col.columns = ["Colonne", "Valeurs manquantes"]
    missing_par_col["Pourcentage"] = (missing_par_col["Valeurs manquantes"] / total * 100).round(2)
    
    if not missing_par_col.empty:
        st.dataframe(missing_par_col, use_container_width=True)
        st.bar_chart(missing_par_col.set_index("Colonne")["Valeurs manquantes"])
    else:
        st.success("✅ Aucune valeur manquante !")

with col_right:
    st.subheader("🔍 Aperçu des données")
    st.dataframe(df.head(20), use_container_width=True)

st.markdown("---")

# ── AGENT IA ──
st.subheader("🤖 Agent Data Guardian — Posez vos questions")

if "messages" not in st.session_state:
    st.session_state.messages = []
    if rapport:
        with st.spinner("Analyse IA en cours..."):
            prompt_initial = f"""
Tu es Data Guardian. Voici le rapport :
- Score qualité : {rapport['score_qualite']}%
- Anomalies : {json.dumps(rapport['anomalies'], ensure_ascii=False)}
- Lignes : {rapport['total_lignes']}
Fais un résumé en 4-5 phrases en français, avec les actions prioritaires.
"""
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt_initial}],
                max_tokens=400
            )
            analyse_initiale = response.choices[0].message.content
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"🔍 **Analyse automatique :**\n\n{analyse_initiale}"
            })

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if question := st.chat_input("Ex: Pourquoi le score est-il bas ? Quelles actions prioriser ?"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Analyse en cours..."):
            contexte = f"Rapport data: score={rapport['score_qualite']}%, anomalies={rapport['anomalies']}"
            historique = [{"role": "system", "content": f"Tu es Data Guardian, expert data. {contexte}"}]
            historique += [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
            
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=historique,
                max_tokens=400
            )
            reponse = response.choices[0].message.content
            st.markdown(reponse)
            st.session_state.messages.append({"role": "assistant", "content": reponse})
