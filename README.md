# 🛡️ Data Guardian

**Plateforme intelligente de surveillance de la qualité des données**

> Projet académique — MSc2 Data Management | Aivancity

---

## 📌 Présentation

Data Guardian est une plateforme Python qui surveille automatiquement la qualité d'une base de données clients. Elle détecte les anomalies, calcule un score de santé des données et génère des recommandations correctives grâce à un agent IA (LLaMA 3).

### Problème traité
Dans les entreprises, les problèmes de qualité des données (valeurs manquantes, doublons, incohérences) sont souvent détectés **trop tard**, après qu'ils ont impacté les processus métiers.

### Solution
Data Guardian surveille en continu la qualité d'un référentiel de données et **alerte proactivement** avec un diagnostic et des actions correctives.

---

## 🔄 Architecture

```
Base de données clients (MySQL)
        ↓
  [Script 1] load_data.py
  Chargement + injection d'anomalies simulées
        ↓
  [Script 2] quality_check.py
  Analyse qualité : valeurs manquantes, doublons, score global
        ↓
  [Script 3] ai_agent.py
  Agent IA (LLaMA 3 / Groq) : diagnostic + recommandations
        ↓
  [Dashboard] app.py (Streamlit)
  Visualisation : KPIs, graphiques, chat IA intégré
```

---

## 🛠️ Stack technique

| Composant | Technologie |
|-----------|-------------|
| Base de données | MySQL + phpMyAdmin |
| Traitement données | Python — Pandas, SQLAlchemy |
| Agent IA | Groq API — LLaMA 3 70B |
| Dashboard | Streamlit |
| Variables d'env | python-dotenv |

---

## 🚀 Installation

### Prérequis
- Python 3.10+
- MySQL installé avec une base `data_guardian` créée
- Une clé API Groq gratuite : [console.groq.com](https://console.groq.com)

### Étapes

```bash
# 1. Cloner le projet
git clone https://github.com/sammy-deufa/data-guardian.git
cd data-guardian

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Configurer les variables d'environnement
cp .env.example .env
# → Ouvrir .env et renseigner MySQL password + clé Groq

# 4. Lancer dans l'ordre
python scripts/load_data.py       # Charge 100 000 clients dans MySQL
python scripts/quality_check.py   # Analyse la qualité et génère le rapport
python scripts/ai_agent.py        # Agent IA interactif (optionnel)
streamlit run dashboard/app.py    # Lance le dashboard
```

Dashboard disponible sur **http://localhost:8501**

---

## 📊 Fonctionnalités

### 1. Chargement des données (`load_data.py`)
- Télécharge un dataset de 100 000 clients
- Injecte des anomalies réalistes : 5% d'emails manquants, 3% de doublons, 2% de prénoms vides
- Charge le tout dans MySQL

### 2. Analyse qualité (`quality_check.py`)
- Détecte les **valeurs manquantes** par colonne
- Identifie les **doublons**
- Calcule un **score de santé global** (0-100%)
- Niveaux : 🟢 BONNE SANTÉ (≥95%) · 🟡 DÉGRADÉE (≥80%) · 🔴 CRITIQUE (<80%)
- Sauvegarde le rapport en JSON + table MySQL `rapports_qualite`

### 3. Agent IA (`ai_agent.py`)
- Analyse automatique du rapport de qualité
- Mode conversation interactive
- Recommandations correctives en français

### 4. Dashboard Streamlit (`dashboard/app.py`)
- KPIs : total lignes, valeurs manquantes, doublons, score qualité
- Graphique des anomalies par colonne
- Aperçu des données
- Chat IA intégré

---

## 📁 Structure du projet

```
data-guardian/
├── scripts/
│   ├── load_data.py        # Chargement + injection d'anomalies
│   ├── quality_check.py    # Analyse qualité + score + rapport
│   └── ai_agent.py         # Agent IA conversationnel (Groq)
├── dashboard/
│   └── app.py              # Dashboard Streamlit
├── .env.example            # Template des variables d'environnement
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 👤 Auteur

**Sammy Ullruch Deufa Kamguem**  
MSc2 Data Management — Aivancity, Paris  
[linkedin.com/in/sammy-deufa](https://linkedin.com/in/sammy-deufa)
