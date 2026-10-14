# ============================================================
# FICHIER 3 : ai_agent.py
# Ce script lance un agent IA (LLaMA 3) qui lit le rapport
# de qualité et répond à tes questions en mode conversation.
# Tu lui poses une question, il te répond en français.
# ============================================================

import json
from groq import Groq          # le client pour parler à l'IA via l'API Groq
from dotenv import load_dotenv
import os

load_dotenv()

# ---- LECTURE DU RAPPORT ----
# On récupère le rapport créé par quality_check.py
print("Lecture du rapport de qualité...")

try:
    with open("rapport.json", "r", encoding="utf-8") as f:
        rapport = json.load(f)
except FileNotFoundError:
    print("❌ Erreur : rapport.json introuvable.")
    print("   Lance d'abord : python scripts/quality_check.py")
    exit()

# ---- PRÉPARATION DU CONTEXTE POUR L'IA ----
# On transforme le rapport en texte pour que l'IA puisse le comprendre
contexte = f"""
Voici le rapport de qualité des données que tu dois analyser :
- Date de l'analyse : {rapport['date']}
- Nombre total de lignes dans la base : {rapport['total_lignes']}
- Score de qualité : {rapport['score']}% ({rapport['niveau']})
- Colonnes avec des valeurs manquantes : {rapport['manquants']}
- Nombre de doublons détectés : {rapport['doublons']}
"""

print(contexte)
print("=" * 50)
print("Agent IA prêt ! Pose ta question (tape 'quitter' pour arrêter)")
print("=" * 50)

# ---- CONNEXION À L'IA ----
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# On garde en mémoire toute la conversation (nécessaire pour que l'IA se souvienne des échanges précédents)
conversation = [
    {
        "role": "system",  # "system" = les instructions qu'on donne à l'IA au départ
        "content": (
            "Tu es un assistant spécialisé en qualité des données. "
            "Tu réponds toujours en français, de façon claire et simple. "
            "Quand tu donnes des recommandations, sois concret et pratique.\n\n"
            + contexte
        )
    }
]

# ---- BOUCLE DE CONVERSATION ----
# On répète indéfiniment : l'utilisateur pose une question, l'IA répond
while True:
    question = input("\nVous > ").strip()

    # Condition pour sortir de la boucle
    if question.lower() in ["quitter", "exit", "q", "stop"]:
        print("Conversation terminée. À bientôt !")
        break

    # Si l'utilisateur n'a rien tapé, on recommence
    if not question:
        continue

    # On ajoute la question de l'utilisateur à l'historique
    conversation.append({
        "role": "user",
        "content": question
    })

    # On envoie toute la conversation à l'IA et on attend sa réponse
    reponse = client.chat.completions.create(
        model="llama3-70b-8192",   # le modèle IA qu'on utilise
        messages=conversation,
        temperature=0.4            # 0 = réponses très précises, 1 = plus créatif
    )

    # On récupère le texte de la réponse
    texte_reponse = reponse.choices[0].message.content

    # On ajoute la réponse à l'historique (pour que l'IA s'en souvienne)
    conversation.append({
        "role": "assistant",
        "content": texte_reponse
    })

    print(f"\n🤖 {texte_reponse}")
