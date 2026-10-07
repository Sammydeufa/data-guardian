# ================================================
# DATA GUARDIAN - SCRIPT 3 : AGENT IA (GROQ)
# ================================================

import json
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Charger le rapport généré par quality_check.py
rapport_path = os.path.join(os.path.dirname(__file__), '..', 'rapport.json')
with open(rapport_path, 'r', encoding='utf-8') as f:
    rapport = json.load(f)

print("=" * 55)
print("  DATA GUARDIAN - Agent IA")
print("=" * 55)
print(f"\n📋 Rapport chargé du : {rapport['date_analyse']}")
print(f"📊 Score qualité : {rapport['score_qualite']}%")
print(f"⚠️  Anomalies : {rapport['nb_anomalies']}")

def analyser_avec_ia(rapport):
    """Envoie le rapport à l'IA et retourne une analyse en français."""
    
    prompt = f"""
Tu es Data Guardian, un expert en qualité des données d'entreprise.
Voici le rapport d'analyse des données clients :

- Date : {rapport['date_analyse']}
- Nombre de lignes analysées : {rapport['total_lignes']}
- Score de qualité global : {rapport['score_qualite']}%
- Nombre d'anomalies détectées : {rapport['nb_anomalies']}
- Détail des anomalies : {json.dumps(rapport['anomalies'], ensure_ascii=False, indent=2)}

Réponds en français avec :
1. Un résumé clair de l'état des données (2-3 phrases)
2. Les causes probables des anomalies détectées
3. L'impact métier potentiel (marketing, commercial, etc.)
4. Les 3 actions correctives prioritaires à mener
5. Un niveau d'urgence global : FAIBLE / MOYEN / ÉLEVÉ / CRITIQUE

Sois concis, professionnel et orienté business.
"""
    
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=800
    )
    
    return response.choices[0].message.content

def chat_interactif():
    """Mode conversation interactive avec l'agent."""
    historique = []
    
    contexte_systeme = f"""
Tu es Data Guardian, un assistant expert en Data Management et qualité des données.
Tu as accès au rapport d'analyse suivant :
- Score qualité : {rapport['score_qualite']}%
- Anomalies : {json.dumps(rapport['anomalies'], ensure_ascii=False)}
- Lignes analysées : {rapport['total_lignes']}

Réponds toujours en français, de manière professionnelle et concise.
Si on te pose une question hors sujet data/qualité, ramène la conversation sur le rapport.
"""
    
    print("\n" + "=" * 55)
    print("  ANALYSE IA EN COURS...")
    print("=" * 55)
    
    analyse = analyser_avec_ia(rapport)
    print(f"\n🤖 Data Guardian :\n\n{analyse}")
    
    print("\n" + "=" * 55)
    print("  MODE CONVERSATION ACTIVÉ")
    print("  (tape 'quitter' pour arrêter)")
    print("=" * 55)
    
    historique.append({
        "role": "system",
        "content": contexte_systeme
    })
    historique.append({
        "role": "assistant", 
        "content": analyse
    })
    
    while True:
        print()
        question = input("👤 Toi : ").strip()
        
        if question.lower() in ['quitter', 'exit', 'q']:
            print("\n👋 Data Guardian : À bientôt !")
            break
            
        if not question:
            continue
        
        historique.append({"role": "user", "content": question})
        
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=historique,
            temperature=0.3,
            max_tokens=500
        )
        
        reponse = response.choices[0].message.content
        historique.append({"role": "assistant", "content": reponse})
        
        print(f"\n🤖 Data Guardian : {reponse}")

if __name__ == "__main__":
    chat_interactif()
