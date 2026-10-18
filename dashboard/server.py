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
