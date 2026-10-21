# ============================================================
# SERVEUR WEB : server.py — version générique multi-bases
# ============================================================

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from groq import Groq
import pandas as pd
import os
import pathlib
from datetime import datetime
import random

env_path = pathlib.Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

app = Flask(__name__, template_folder="templates")
CORS(app)

# ---- ÉTAT ACTIF (base + table sélectionnées) ----
state = {"db": None, "table": None, "engine": None, "pk_col": "id"}

def make_engine(db_name):
    return create_engine(
        f"mysql+pymysql://root:@localhost:3306/{db_name}",
        pool_pre_ping=True, pool_recycle=3600
    )

# ---- PAGE PRINCIPALE ----
@app.route("/")
def index():
    return render_template("index.html")

# ---- LISTER LES BASES DE DONNÉES ----
@app.route("/api/databases")
def get_databases():
    try:
        engine = make_engine("information_schema")
        with engine.connect() as conn:
            rows = conn.execute(text("SHOW DATABASES")).fetchall()
            exclues = {"information_schema", "performance_schema", "mysql", "sys", "phpmyadmin"}
            dbs = [r[0] for r in rows if r[0] not in exclues]
        return jsonify({"databases": dbs})
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

# ---- LISTER LES TABLES D'UNE BASE ----
@app.route("/api/tables")
def get_tables():
    db = request.args.get("db")
    if not db:
        return jsonify({"erreur": "Paramètre db manquant"}), 400
    try:
        engine = make_engine(db)
        with engine.connect() as conn:
            rows = conn.execute(text("SHOW TABLES")).fetchall()
            tables = [r[0] for r in rows]
        return jsonify({"tables": tables})
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

# ---- SÉLECTIONNER UNE BASE + TABLE ----
@app.route("/api/set-table", methods=["POST"])
def set_table():
    body = request.json
    db    = body.get("db")
    table = body.get("table")
    if not db or not table:
        return jsonify({"erreur": "db et table requis"}), 400
    try:
        engine = make_engine(db)
        # Détecter la clé primaire (fallback : première colonne UNIQUE, puis première colonne)
        with engine.connect() as conn:
            pk_rows = conn.execute(
                text(f"SHOW KEYS FROM `{table}` WHERE Key_name = 'PRIMARY'")
            ).fetchall()
            pk_col = pk_rows[0][4] if pk_rows else None
            if not pk_col:
                # Essayer une colonne UNIQUE
                uq_rows = conn.execute(
                    text(f"SHOW KEYS FROM `{table}` WHERE Non_unique = 0")
                ).fetchall()
                pk_col = uq_rows[0][4] if uq_rows else None
            if not pk_col:
                # Fallback : première colonne
                cols = conn.execute(text(f"SHOW COLUMNS FROM `{table}`")).fetchall()
                pk_col = cols[0][0] if cols else None
        state["db"]     = db
        state["table"]  = table
        state["engine"] = engine
        state["pk_col"] = pk_col
        return jsonify({"ok": True, "db": db, "table": table, "pk_col": pk_col})
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

# ---- RAPPORT DE QUALITÉ (généré dynamiquement) ----
@app.route("/api/rapport")
def get_rapport():
    if not state["engine"]:
        return jsonify({"erreur": "Aucune table sélectionnée"}), 400
    try:
        table = state["table"]
        df = pd.read_sql(f"SELECT * FROM `{table}`", state["engine"])
        total = len(df)
        manquants = {
            col: int(df[col].isna().sum())
            for col in df.columns if df[col].isna().sum() > 0
        }
        cols_dup = [c for c in df.columns if c != state["pk_col"]]
        doublons = int(df.duplicated(subset=cols_dup).sum()) if cols_dup else 0
        total_manquants = sum(manquants.values())
        total_cellules  = total * len(df.columns)
        score = round(max(0,
            100
            - (total_manquants / max(total_cellules, 1)) * 80
            - (doublons / max(total, 1)) * 20
        ), 1)
        if score >= 95:   niveau = "Excellent"
        elif score >= 80: niveau = "Bon"
        elif score >= 60: niveau = "Moyen"
        else:             niveau = "Mauvais"
        return jsonify({
            "date":        datetime.now().strftime("%Y-%m-%d %H:%M"),
            "db":          state["db"],
            "table":       table,
            "pk_col":      state["pk_col"],
            "colonnes":    list(df.columns),
            "total_lignes": total,
            "manquants":   manquants,
            "doublons":    doublons,
            "score":       score,
            "niveau":      niveau
        })
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

# ---- TYPES DES COLONNES ----
@app.route("/api/columns")
def get_columns():
    if not state["engine"]:
        return jsonify([])
    try:
        with state["engine"].connect() as conn:
            rows = conn.execute(text(f"SHOW COLUMNS FROM `{state['table']}`")).fetchall()
            cols = []
            for r in rows:
                raw_type = str(r[1]).lower()
                if any(t in raw_type for t in ["date", "time", "year"]):
                    kind = "date" if "datetime" not in raw_type else "datetime"
                elif any(t in raw_type for t in ["int", "float", "double", "decimal", "numeric"]):
                    kind = "number"
                else:
                    kind = "text"
                cols.append({"name": r[0], "type": raw_type, "kind": kind})
        return jsonify(cols)
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

# ---- APERÇU DES DONNÉES (50 lignes) ----
@app.route("/api/data")
def get_data():
    if not state["engine"]:
        return jsonify([])
    try:
        df = pd.read_sql(f"SELECT * FROM `{state['table']}` LIMIT 50", state["engine"])
        return app.response_class(
            df.to_json(orient="records", force_ascii=False),
            content_type='application/json'
        )
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

# ---- SUPPRESSION DES DOUBLONS ----
@app.route("/api/supprimer-doublons", methods=["POST"])
def supprimer_doublons():
    if not state["engine"]:
        return jsonify({"erreur": "Aucune table sélectionnée"}), 400
    try:
        table  = state["table"]
        pk_col = state["pk_col"]
        engine = state["engine"]
        with engine.connect() as conn:
            avant = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).fetchone()[0]
            cols  = [r[0] for r in conn.execute(text(f"SHOW COLUMNS FROM `{table}`")).fetchall()]
        cols_dup = [c for c in cols if c != pk_col]
        if not pk_col or not cols_dup:
            return jsonify({"erreur": "Impossible de détecter la clé primaire"}), 400
        group_by = ", ".join([f"`{c}`" for c in cols_dup])
        with engine.begin() as conn:
            conn.execute(text(f"""
                DELETE FROM `{table}`
                WHERE `{pk_col}` NOT IN (
                    SELECT min_pk FROM (
                        SELECT MIN(`{pk_col}`) AS min_pk
                        FROM `{table}`
                        GROUP BY {group_by}
                    ) AS t
                )
            """))
        with engine.connect() as conn:
            apres = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).fetchone()[0]
        return jsonify({"supprimes": avant - apres, "total": apres})
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

# ---- MODIFICATION D'UNE CELLULE ----
@app.route("/api/modifier-cellule", methods=["POST"])
def modifier_cellule():
    if not state["engine"]:
        return jsonify({"erreur": "Aucune table sélectionnée"}), 400
    try:
        body   = request.json
        pk_val = body["pk_val"]
        col    = body["colonne"]
        valeur = body["valeur"]
        table  = state["table"]
        pk_col = state["pk_col"]
        # Vérifier que la colonne existe dans la table
        with state["engine"].connect() as conn:
            cols = [r[0] for r in conn.execute(text(f"SHOW COLUMNS FROM `{table}`")).fetchall()]
        if col not in cols:
            return jsonify({"erreur": "Colonne non autorisée"}), 400
        if not pk_col:
            return jsonify({"erreur": "Aucune clé d'identification trouvée pour cette table"}), 400
        if pk_val is None:
            return jsonify({"erreur": f"Valeur de clé nulle pour la colonne '{pk_col}'"}), 400
        with state["engine"].begin() as conn:
            result = conn.execute(
                text(f"UPDATE `{table}` SET `{col}` = :val WHERE `{pk_col}` = :pk LIMIT 1"),
                {"val": valeur, "pk": pk_val}
            )
            if result.rowcount == 0:
                return jsonify({"erreur": f"Aucune ligne trouvée avec {pk_col}='{pk_val}'"}), 400
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

# ---- DONNÉES DÉMO RESTAURANTS ----
def generate_restaurant_data():
    """Génère 6 mois de données réalistes pour 3 restaurants Burger King."""
    random.seed(42)
    restaurants = [
        {"id": "R1", "nom": "BK Montreuil",  "ouverture": 2019, "places": 80},
        {"id": "R2", "nom": "BK Villejuif",   "ouverture": 2021, "places": 60},
        {"id": "R3", "nom": "BK Paris Nation","ouverture": 2017, "places": 95},
    ]
    mois = ["Mai", "Juin", "Juil.", "Août", "Sept.", "Oct."]
    # CA mensuel de base (€) par restaurant
    ca_base = {"R1": 195000, "R2": 148000, "R3": 232000}
    # Coefficients saisonniers
    saison   = [1.0, 1.08, 1.15, 1.12, 0.95, 0.97]

    data = {}
    for r in restaurants:
        rid = r["id"]
        mensuel = []
        for i, m in enumerate(mois):
            ca = round(ca_base[rid] * saison[i] * random.uniform(0.97, 1.03))
            food_cost_pct  = round(random.uniform(28.5, 32.5), 1)   # norme QSR : 28-33%
            labor_cost_pct = round(random.uniform(26.0, 30.0), 1)   # norme QSR : 26-30%
            energie_pct    = round(random.uniform(3.5,  5.0),  1)
            achats         = round(ca * food_cost_pct / 100)
            masse_sal      = round(ca * labor_cost_pct / 100)
            energie        = round(ca * energie_pct / 100)
            autres_charges = round(ca * random.uniform(8, 10) / 100)
            marge_nette    = ca - achats - masse_sal - energie - autres_charges
            marge_pct      = round(marge_nette / ca * 100, 1)
            mensuel.append({
                "mois": m,
                "ca": ca,
                "achats": achats,
                "masse_salariale": masse_sal,
                "energie": energie,
                "autres_charges": autres_charges,
                "marge_nette": marge_nette,
                "marge_pct": marge_pct,
                "food_cost_pct": food_cost_pct,
                "labor_cost_pct": labor_cost_pct,
                "tickets": round(ca / random.uniform(11.5, 13.5)),
            })
        data[rid] = {**r, "mensuel": mensuel}
    return data

_resto_data = generate_restaurant_data()

@app.route("/api/restaurant/overview")
def restaurant_overview():
    result = []
    for rid, r in _resto_data.items():
        tot_ca   = sum(m["ca"]               for m in r["mensuel"])
        tot_ach  = sum(m["achats"]            for m in r["mensuel"])
        tot_sal  = sum(m["masse_salariale"]   for m in r["mensuel"])
        tot_en   = sum(m["energie"]           for m in r["mensuel"])
        tot_marge= sum(m["marge_nette"]       for m in r["mensuel"])
        mois_n   = r["mensuel"][-1]  # dernier mois
        result.append({
            "id":              rid,
            "nom":             r["nom"],
            "ca_total":        tot_ca,
            "ca_mois":         mois_n["ca"],
            "marge_pct":       round(tot_marge / tot_ca * 100, 1),
            "food_cost_pct":   round(tot_ach  / tot_ca * 100, 1),
            "labor_cost_pct":  round(tot_sal  / tot_ca * 100, 1),
            "tickets_mois":    mois_n["tickets"],
            "panier_moyen":    round(mois_n["ca"] / mois_n["tickets"], 2),
        })
    return jsonify(result)

@app.route("/api/restaurant/evolution")
def restaurant_evolution():
    mois = [m["mois"] for m in list(_resto_data.values())[0]["mensuel"]]
    series = []
    for rid, r in _resto_data.items():
        series.append({
            "id":    rid,
            "nom":   r["nom"],
            "ca":    [m["ca"]         for m in r["mensuel"]],
            "marge": [m["marge_pct"]  for m in r["mensuel"]],
            "food":  [m["food_cost_pct"]  for m in r["mensuel"]],
            "labor": [m["labor_cost_pct"] for m in r["mensuel"]],
        })
    return jsonify({"mois": mois, "series": series})

@app.route("/api/restaurant/detail/<rid>")
def restaurant_detail(rid):
    if rid not in _resto_data:
        return jsonify({"erreur": "Restaurant introuvable"}), 404
    return jsonify(_resto_data[rid])

@app.route("/api/restaurant/chat", methods=["POST"])
def restaurant_chat():
    body = request.json
    question   = body.get("question", "")
    historique = body.get("historique", [])
    # Construire un résumé des données pour le contexte IA
    lignes = []
    for rid, r in _resto_data.items():
        m = r["mensuel"]
        ca_tot = sum(x["ca"] for x in m)
        marge_moy = round(sum(x["marge_pct"] for x in m) / len(m), 1)
        food_moy  = round(sum(x["food_cost_pct"] for x in m) / len(m), 1)
        labor_moy = round(sum(x["labor_cost_pct"] for x in m) / len(m), 1)
        lignes.append(
            f"- {r['nom']} : CA 6 mois = {ca_tot:,}€ | marge moy. = {marge_moy}% "
            f"| food cost = {food_moy}% | labor cost = {labor_moy}%"
        )
    contexte = f"""Tu es un analyste de données spécialisé en restauration rapide (QSR).
Tu assistes le franchisé de 3 restaurants Burger King (Montreuil, Villejuif, Paris Nation).
Réponds en français, de façon concise et opérationnelle.
Données des 6 derniers mois :
{chr(10).join(lignes)}
Normes secteur QSR France : food cost 28-33%, labor cost 26-30%, marge nette 8-14%.
"""
    client   = Groq(api_key=os.getenv("GROQ_API_KEY"))
    messages = [{"role": "system", "content": contexte}] + historique + [{"role": "user", "content": question}]
    reponse  = client.chat.completions.create(model="qwen/qwen3.8-27b", messages=messages, temperature=0.4)
    return jsonify({"reponse": reponse.choices[0].message.content})

# ---- CHAT IA ----
@app.route("/api/chat", methods=["POST"])
def chat():
    body       = request.json
    question   = body.get("question", "")
    historique = body.get("historique", [])
    r          = body.get("rapport", {})
    manquants  = r.get("manquants", {})
    total_m    = sum(manquants.values()) if isinstance(manquants, dict) else manquants
    contexte = f"""Tu es un assistant qualité des données. Réponds en français, simplement.
Rapport actuel :
- Base : {r.get('db','?')} / Table : {r.get('table','?')}
- Total lignes : {r.get('total_lignes')}
- Score : {r.get('score')}% ({r.get('niveau')})
- Valeurs manquantes : {total_m}
- Doublons : {r.get('doublons')}
"""
    client   = Groq(api_key=os.getenv("GROQ_API_KEY"))
    messages = [{"role": "system", "content": contexte}] + historique + [{"role": "user", "content": question}]
    reponse  = client.chat.completions.create(model="qwen/qwen3.8-27b", messages=messages, temperature=0.4)
    return jsonify({"reponse": reponse.choices[0].message.content})

# ---- LANCEMENT ----
if __name__ == "__main__":
    print("✅ Dashboard disponible sur http://localhost:5000")
    app.run(debug=False, port=5000)
