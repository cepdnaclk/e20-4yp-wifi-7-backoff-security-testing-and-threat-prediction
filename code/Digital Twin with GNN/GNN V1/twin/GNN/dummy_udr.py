import json, sqlite3, random, hashlib
from datetime import datetime
import numpy as np

DB_PATH = "udr_dummy.sqlite"

def init_db(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS snapshots(
      experiment_id TEXT PRIMARY KEY,
      topology_json TEXT NOT NULL,
      config_json TEXT NOT NULL,
      topology_hash TEXT NOT NULL,
      load_level TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS features(
      experiment_id TEXT NOT NULL,
      node_id TEXT NOT NULL,
      node_type TEXT NOT NULL,      -- "AP" or "STA"
      f_throughput_hint REAL NOT NULL,
      f_delay_hint REAL NOT NULL,
      f_retry_hint REAL NOT NULL,
      PRIMARY KEY (experiment_id, node_id)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS kpis(
      experiment_id TEXT NOT NULL,
      node_id TEXT,                 -- NULL for global KPI
      kpi_name TEXT NOT NULL,        -- e.g. throughput_mbps, delay_p95_ms
      kpi_value REAL NOT NULL,
      PRIMARY KEY (experiment_id, node_id, kpi_name)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS predictions(
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

def topo_hash(topo: dict) -> str:
    s = json.dumps(topo, sort_keys=True).encode("utf-8")
    return hashlib.sha256(s).hexdigest()[:12]

def make_topology(n_sta: int):
    # 1 AP + N STAs, fully connected AP<->STA edges
    nodes = [{"id":"ap1","type":"AP"}] + [{"id":f"sta{i+1}","type":"STA"} for i in range(n_sta)]
    edges = [{"src":"ap1","dst":f"sta{i+1}"} for i in range(n_sta)]
    return {"nodes": nodes, "edges": edges}

def generate_one_experiment(conn, experiment_id: str, n_sta: int, load_level: str, seed: int):
    rng = np.random.default_rng(seed)

    topo = make_topology(n_sta)
    cfg = {"load_level": load_level, "seed": seed}

    th = topo_hash(topo)

    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO snapshots(experiment_id, topology_json, config_json, topology_hash, load_level) VALUES(?,?,?,?,?)",
        (experiment_id, json.dumps(topo), json.dumps(cfg), th, load_level)
    )

    # Map load_level to numeric pressure
    load_factor = {"low":0.6, "med":1.0, "high":1.5}[load_level]

    # Features per STA: create learnable correlation with KPIs
    # "hints" are inputs; KPIs are targets (ground truth).
    throughputs = []
    delays = []
    for i in range(n_sta):
        link_quality = rng.uniform(0.6, 1.0)  # better link => higher throughput, lower delay
        retry = float(np.clip(rng.normal(0.05*load_factor*(1.1-link_quality), 0.01), 0.0, 0.30))
        delay = float(np.clip(rng.normal(20*load_factor*(1.1-link_quality), 3.0), 5.0, 120.0))
        thr = float(np.clip(rng.normal(150*link_quality/load_factor, 10.0), 5.0, 250.0))

        node_id = f"sta{i+1}"

        # store features (inputs)
        cur.execute(
            "INSERT OR REPLACE INTO features(experiment_id,node_id,node_type,f_throughput_hint,f_delay_hint,f_retry_hint) VALUES(?,?,?,?,?,?)",
            (experiment_id, node_id, "STA", thr*0.9, delay*1.1, retry)  # slightly “noisy hints”
        )

        # store KPIs (targets)
        cur.execute(
            "INSERT OR REPLACE INTO kpis(experiment_id,node_id,kpi_name,kpi_value) VALUES(?,?,?,?)",
            (experiment_id, node_id, "throughput_mbps", thr)
        )
        cur.execute(
            "INSERT OR REPLACE INTO kpis(experiment_id,node_id,kpi_name,kpi_value) VALUES(?,?,?,?)",
            (experiment_id, node_id, "delay_p95_ms", delay)
        )
        cur.execute(
            "INSERT OR REPLACE INTO kpis(experiment_id,node_id,kpi_name,kpi_value) VALUES(?,?,?,?)",
            (experiment_id, node_id, "retry_rate", retry)
        )

        throughputs.append(thr)
        delays.append(delay)

    # AP node features (simple aggregates)
    cur.execute(
        "INSERT OR REPLACE INTO features(experiment_id,node_id,node_type,f_throughput_hint,f_delay_hint,f_retry_hint) VALUES(?,?,?,?,?,?)",
        (experiment_id, "ap1", "AP",
         float(np.mean(throughputs)), float(np.mean(delays)), float(np.mean([0.0] + [0.0])))
    )

    # Global KPI example: fairness (Jain) across STAs
    t = np.array(throughputs, dtype=np.float32)
    fairness = float((t.sum()**2) / (len(t) * (t**2).sum() + 1e-8))
    cur.execute(
        "INSERT OR REPLACE INTO kpis(experiment_id,node_id,kpi_name,kpi_value) VALUES(?,?,?,?)",
        (experiment_id, None, "jain_fairness_index", fairness)
    )

    conn.commit()

def main():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    random.seed(7)
    exp_count = 200
    for idx in range(exp_count):
        n_sta = random.choice([2,3,4,5])
        load = random.choice(["low","med","high"])
        exp_id = f"exp_{idx:04d}"
        generate_one_experiment(conn, exp_id, n_sta, load, seed=1000+idx)

    print(f"✅ Created {exp_count} dummy experiments in {DB_PATH}")

if __name__ == "__main__":
    main()
