"""
Étape 3 : Agent IA pour analyser le rapport de qualité
On envoie le rapport à LLaMA 3 (via Groq) et on peut lui poser
des questions sur les données en mode conversation.
"""

import json
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Lecture du rapport généré par quality_check.py
with open("rapport.json", "r") as f:
    rapport = json.load(f)

# On formate le rapport en texte pour le donner à l'IA
contexte = f"""
Voici le rapport de qualité des données clients :
- Date d'analyse : {rapport['date']}
- Nombre total de lignes : {rapport['total_lignes']}
- Score de qualité : {rapport['score']}% ({rapport['niveau']})
- Valeurs manquantes : {rapport['manquants']}
- Doublons détectés : {rapport['doublons']}
"""

# Historique de la conversation (pour que l'IA se souvienne du contexte)
messages = [
    {
        "role": "system",
        "content": (
            "Tu es un assistant spécialisé en qualité des données. "
            "Réponds en français, de façon claire et pratique. "
            "Donne des recommandations concrètes quand on te le demande.\n\n"
            + contexte
        )
    }
]

print("🤖 Agent Data Guardian prêt !")
print("   Tape 'quitter' pour arrêter\n")
print(contexte)

# Boucle de conversation
while True:
    question = input("Vous > ").strip()

    if question.lower() in ["quitter", "exit", "q"]:
        print("Au revoir !")
        break

    if not question:
        continue

    messages.append({"role": "user", "content": question})

    # Appel à l'API Groq
    reponse = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=messages,
        temperature=0.5
    )

    texte = reponse.choices[0].message.content
    messages.append({"role": "assistant", "content": texte})

    print(f"\n🤖 {texte}\n")
