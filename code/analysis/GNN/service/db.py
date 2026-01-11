# GNN/service/db.py
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# Create DB next to this file (stable path even with uvicorn reload)
DB_PATH = Path(__file__).resolve().parent / "udr.sqlite"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        experiment_id TEXT NOT NULL,
        node_id TEXT,
        kpi_name TEXT NOT NULL,
        predicted_value REAL NOT NULL,
        model_version TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

def insert_predictions(experiment_id: str, preds, model_version: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    for node_id, kpi_name, val in preds:
        cur.execute("""
          INSERT INTO predictions(experiment_id,node_id,kpi_name,predicted_value,model_version,created_at)
          VALUES(?,?,?,?,?,?)
        """, (experiment_id, str(node_id) if node_id is not None else None, kpi_name, float(val), model_version, now))

    conn.commit()
    conn.close()
