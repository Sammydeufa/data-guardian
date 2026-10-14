# ============================================================
# FICHIER 1 : load_data.py
# Ce script sert à télécharger des données clients depuis
# internet et à les stocker dans notre base de données MySQL.
# On ajoute aussi des erreurs artificielles pour simuler
# une vraie base de données imparfaite.
# ============================================================

# On importe les outils dont on a besoin
import pandas as pd          # pour lire et manipuler les données sous forme de tableau
import numpy as np           # pour faire des calculs mathématiques (ex: choisir des lignes au hasard)
from sqlalchemy import create_engine  # pour se connecter à MySQL depuis Python
from dotenv import load_dotenv        # pour lire le fichier .env (mots de passe, etc.)
import os                    # pour accéder aux variables d'environnement

# On charge les informations de connexion depuis le fichier .env
load_dotenv()

# ---- CONNEXION À MYSQL ----
# On construit l'adresse de connexion à partir des infos du fichier .env
# C'est comme une URL : mysql://utilisateur:motdepasse@adresse:port/nomdelabase
DB_URL = (
    f"mysql+pymysql://"
    f"{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}"
    f"/{os.getenv('DB_NAME')}"
)

# On crée la connexion
engine = create_engine(DB_URL)

# ---- TÉLÉCHARGEMENT DES DONNÉES ----
print("Étape 1 : Téléchargement des données clients...")

# Ce fichier CSV contient 100 000 clients fictifs (noms, emails, téléphones...)
# Il est hébergé gratuitement sur GitHub
url = "https://raw.githubusercontent.com/datablist/sample-csv-files/main/files/customers/customers-100000.csv"
df = pd.read_csv(url)

# On garde seulement les colonnes qui nous intéressent
# et on les renomme en français pour plus de clarté
df = df[["Index", "First Name", "Last Name", "Email", "Phone", "Company", "Country"]].copy()
df.columns = ["id", "prenom", "nom", "email", "telephone", "entreprise", "pays"]

print(f"  ✅ {len(df)} clients téléchargés")

# ---- INJECTION D'ANOMALIES ----
# Dans une vraie base de données, il y a toujours des erreurs.
# On en simule quelques-unes pour rendre notre projet réaliste.

print("Étape 2 : Ajout d'anomalies pour simuler des données réelles imparfaites...")

# Anomalie 1 : 5% des emails sont vides (oubli lors de la saisie)
nb_emails_manquants = int(len(df) * 0.05)  # 5% de 100 000 = 5 000 lignes
lignes_sans_email = np.random.choice(df.index, nb_emails_manquants, replace=False)
df.loc[lignes_sans_email, "email"] = None  # on efface l'email de ces lignes

# Anomalie 2 : 2% des prénoms sont vides
nb_prenoms_manquants = int(len(df) * 0.02)  # 2% = 2 000 lignes
lignes_sans_prenom = np.random.choice(df.index, nb_prenoms_manquants, replace=False)
df.loc[lignes_sans_prenom, "prenom"] = None

# Anomalie 3 : 3% de doublons (même personne enregistrée deux fois)
nb_doublons = int(len(df) * 0.03)  # 3% = 3 000 lignes copiées
lignes_copiees = df.sample(nb_doublons)  # on choisit 3 000 lignes au hasard
df = pd.concat([df, lignes_copiees], ignore_index=True)  # on les ajoute à la fin

print(f"  → {nb_emails_manquants} emails manquants")
print(f"  → {nb_prenoms_manquants} prénoms manquants")
print(f"  → {nb_doublons} doublons ajoutés")

# ---- CHARGEMENT DANS MYSQL ----
print("Étape 3 : Chargement dans la base de données MySQL...")

# On envoie tout le tableau dans MySQL dans une table appelée "clients"
# if_exists="replace" : si la table existe déjà, on la supprime et on la recrée
df.to_sql("clients", engine, if_exists="replace", index=False)

print(f"  ✅ Table 'clients' créée avec {len(df)} lignes au total")
print("\nTerminé ! Tu peux maintenant lancer quality_check.py")
