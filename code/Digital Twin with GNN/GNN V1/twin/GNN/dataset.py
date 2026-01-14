import json, sqlite3
import numpy as np
import torch

FEATURES = ["f_throughput_hint", "f_delay_hint", "f_retry_hint"]
TARGETS  = ["throughput_mbps", "delay_p95_ms", "retry_rate"]  # per-STA targets
GLOBAL_TARGETS = ["jain_fairness_index"]

def load_experiments(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT experiment_id, topology_json, topology_hash, load_level FROM snapshots")
    rows = cur.fetchall()

    experiments = []
    for exp_id, topo_json, topo_hash, load_level in rows:
        topo = json.loads(topo_json)

        # node order
        nodes = topo["nodes"]
        node_ids = [n["id"] for n in nodes]
        node_types = {n["id"]: n["type"] for n in nodes}
        node_index = {nid:i for i,nid in enumerate(node_ids)}

        # adjacency
        N = len(node_ids)
        A = np.zeros((N,N), dtype=np.float32)
        for e in topo["edges"]:
            i = node_index[e["src"]]
            j = node_index[e["dst"]]
            A[i,j] = 1.0
            A[j,i] = 1.0

        # add self loops
        A = A + np.eye(N, dtype=np.float32)

        # normalize A (GCN)
        D = np.sum(A, axis=1)
        D_inv_sqrt = np.diag(1.0 / np.sqrt(D + 1e-8))
        A_norm = D_inv_sqrt @ A @ D_inv_sqrt

        # features X
        X = np.zeros((N, len(FEATURES)), dtype=np.float32)
        cur.execute("SELECT node_id, " + ",".join(FEATURES) + " FROM features WHERE experiment_id=?", (exp_id,))
        for node_id, *fs in cur.fetchall():
            X[node_index[node_id]] = np.array(fs, dtype=np.float32)

        # targets Y per-node (STA nodes only)
        # We'll predict 3 KPI values for each STA; AP node target = zeros (masked)
        Y = np.zeros((N, len(TARGETS)), dtype=np.float32)
        mask = np.zeros((N,), dtype=np.float32)

        for ti, kpi in enumerate(TARGETS):
            cur.execute("SELECT node_id, kpi_value FROM kpis WHERE experiment_id=? AND kpi_name=? AND node_id IS NOT NULL",
                        (exp_id, kpi))
            for node_id, val in cur.fetchall():
                if node_types[node_id] == "STA":
                    Y[node_index[node_id], ti] = float(val)

        for nid in node_ids:
            if node_types[nid] == "STA":
                mask[node_index[nid]] = 1.0

        # global target
        cur.execute("SELECT kpi_value FROM kpis WHERE experiment_id=? AND kpi_name=? AND node_id IS NULL",
                    (exp_id, "jain_fairness_index"))
        gval = cur.fetchone()[0]

        experiments.append({
            "experiment_id": exp_id,
            "topology_hash": topo_hash,
            "load_level": load_level,
            "A": torch.tensor(A_norm),
            "X": torch.tensor(X),
            "Y": torch.tensor(Y),
            "mask": torch.tensor(mask),
            "gY": torch.tensor([gval], dtype=torch.float32)
        })

    return experiments
