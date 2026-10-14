# ============================================================
# FICHIER 4 : dashboard/app.py
# Ce fichier crée un tableau de bord visuel avec Streamlit.
# Lance-le avec : streamlit run dashboard/app.py
# Une page web s'ouvre automatiquement sur http://localhost:8501
# ============================================================

import streamlit as st       # le framework pour créer des pages web en Python
import pandas as pd
import json
from groq import Groq
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

# ---- CONFIGURATION DE LA PAGE ----
st.set_page_config(
    page_title="Data Guardian",
    page_icon="🛡️",
    layout="wide"   # la page prend toute la largeur de l'écran
)

st.title("🛡️ Data Guardian — Tableau de bord qualité des données")
st.caption("Analyse automatique de la qualité d'une base de données clients")

# ---- CONNEXION À MYSQL ----
DB_URL = (
    f"mysql+pymysql://"
    f"{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}"
    f"/{os.getenv('DB_NAME')}"
)
engine = create_engine(DB_URL)

# ---- LECTURE DU RAPPORT ----
# Si le fichier rapport.json n'existe pas encore, on affiche un message d'erreur
try:
    with open("rapport.json", "r", encoding="utf-8") as f:
        rapport = json.load(f)
except FileNotFoundError:
    st.error("⚠️ Aucun rapport trouvé. Lance d'abord les scripts dans l'ordre :")
    st.code("python scripts/load_data.py\npython scripts/quality_check.py")
    st.stop()  # on arrête l'affichage ici si pas de rapport

# ---- SECTION 1 : INDICATEURS CLÉS (KPIs) ----
# Ces 4 chiffres donnent un aperçu rapide de la santé des données
st.subheader("📊 Résumé de l'analyse")
st.write(f"Dernière analyse : {rapport['date']}")

col1, col2, col3, col4 = st.columns(4)  # on divise la page en 4 colonnes

col1.metric(
    label="Total de lignes",
    value=f"{rapport['total_lignes']:,}"   # le :, ajoute des espaces (ex: 103 000)
)
col2.metric(
    label="Valeurs manquantes",
    value=sum(rapport["manquants"].values()),
    delta="anomalies détectées",
    delta_color="inverse"  # rouge si > 0
)
col3.metric(
    label="Doublons",
    value=rapport["doublons"],
    delta="lignes en double",
    delta_color="inverse"
)
col4.metric(
    label="Score de qualité",
    value=f"{rapport['score']}%",
    delta=rapport["niveau"]
)

st.divider()

# ---- SECTION 2 : GRAPHIQUE DES VALEURS MANQUANTES ----
st.subheader("📉 Valeurs manquantes par colonne")

if rapport["manquants"]:
    # On transforme le dictionnaire en tableau pour pouvoir faire un graphique
    df_manquants = pd.DataFrame(
        list(rapport["manquants"].items()),   # [ ["email", 5021], ["prenom", 2003] ]
        columns=["Colonne", "Nb valeurs manquantes"]
    )
    st.bar_chart(df_manquants.set_index("Colonne"))
else:
    st.success("✅ Aucune valeur manquante dans la base !")

st.divider()

# ---- SECTION 3 : APERÇU DES DONNÉES ----
st.subheader("🔍 Aperçu des données (50 premières lignes)")

# On lit les 50 premières lignes de la table clients pour les afficher
df_apercu = pd.read_sql("SELECT * FROM clients LIMIT 50", engine)
st.dataframe(df_apercu, use_container_width=True)

st.divider()

# ---- SECTION 4 : CHAT AVEC L'IA ----
st.subheader("💬 Poser une question à l'agent IA")
st.caption("Exemple : Quelles colonnes corriger en priorité ? Que penses-tu du score ?")

# On prépare le contexte que l'IA va recevoir
contexte_ia = f"""
Voici le rapport de qualité des données :
- Total de lignes : {rapport['total_lignes']}
- Score de qualité : {rapport['score']}% ({rapport['niveau']})
- Valeurs manquantes : {rapport['manquants']}
- Doublons : {rapport['doublons']}
"""

# Streamlit garde en mémoire les messages pendant toute la session
if "historique_chat" not in st.session_state:
    st.session_state.historique_chat = []

# On affiche les messages précédents
for message in st.session_state.historique_chat:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Champ où l'utilisateur tape sa question
question = st.chat_input("Ta question ici...")

if question:
    # On affiche la question de l'utilisateur
    with st.chat_message("user"):
        st.write(question)

    # On l'ajoute à l'historique
    st.session_state.historique_chat.append({"role": "user", "content": question})

    # On appelle l'IA via Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    reponse = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {
                "role": "system",
                "content": "Tu es un assistant qualité des données. Réponds en français, simplement.\n" + contexte_ia
            },
            *st.session_state.historique_chat  # on envoie tout l'historique pour que l'IA se souvienne
        ],
        temperature=0.4
    )

    texte = reponse.choices[0].message.content

    # On affiche et sauvegarde la réponse
    with st.chat_message("assistant"):
        st.write(texte)

    st.session_state.historique_chat.append({"role": "assistant", "content": texte})
