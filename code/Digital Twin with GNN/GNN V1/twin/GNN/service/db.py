import sqlite3
from datetime import datetime

DB_PATH = "udr_dummy.sqlite"

def insert_predictions(experiment_id: str, preds, model_version: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    for node_id, kpi_name, val in preds:
        cur.execute("""
          INSERT INTO predictions(experiment_id,node_id,kpi_name,predicted_value,model_version,created_at)
          VALUES(?,?,?,?,?,?)
        """, (experiment_id, node_id, kpi_name, float(val), model_version, now))

    conn.commit()
    conn.close()
