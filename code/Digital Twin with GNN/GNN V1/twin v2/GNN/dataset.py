# GNN/dataset.py
import json, sqlite3
import numpy as np
import torch

FEATURE_COLS = [
    "event_count",
    "mean_backoff",
    "std_backoff",
    "p95_backoff",
    "max_backoff",
    "mean_norm",
    "p95_norm",
    "cw_min",
    "cw_max",
    "mcs",
    "channel_width",
    "guard_interval",
    "frequency",
]

def build_adjacency(nodes, edges):
    node_ids = [n["id"] for n in nodes]
    idx = {nid: i for i, nid in enumerate(node_ids)}
    n = len(node_ids)
    A = np.zeros((n, n), dtype=np.float32)
    for e in edges:
        i, j = idx[e["src"]], idx[e["dst"]]
        A[i, j] = 1.0
        A[j, i] = 1.0
    # self loops
    A += np.eye(n, dtype=np.float32)
    # normalize D^-1/2 A D^-1/2
    deg = A.sum(axis=1)
    D_inv_sqrt = np.diag(1.0 / np.sqrt(np.maximum(deg, 1e-6)))
    A_norm = D_inv_sqrt @ A @ D_inv_sqrt
    return node_ids, A_norm

def load_samples(db_path="backoff_udr_dummy.sqlite"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT experiment_id, topology_json FROM snapshots")
    snaps = cur.fetchall()

    samples = []
    for experiment_id, topo_json in snaps:
        topo = json.loads(topo_json)
        node_ids, A_norm = build_adjacency(topo["nodes"], topo["edges"])
        n = len(node_ids)

        # find windows
        cur.execute("SELECT DISTINCT window_idx FROM window_features WHERE experiment_id=?", (experiment_id,))
        windows = [r[0] for r in cur.fetchall()]

        for w in windows:
            # graph label (attack vs normal)
            cur.execute("SELECT label FROM window_labels WHERE experiment_id=? AND window_idx=?", (experiment_id, w))
            y = cur.fetchone()
            if y is None:
                continue
            y_graph = float(y[0])

            # build X [N,F]
            X = np.zeros((n, len(FEATURE_COLS)), dtype=np.float32)

            cur.execute("""
              SELECT node_id, node_type,
                     event_count, mean_backoff, std_backoff, p95_backoff, max_backoff,
                     mean_norm, p95_norm, cw_min, cw_max, mcs, channel_width, guard_interval, frequency
              FROM window_features
              WHERE experiment_id=? AND window_idx=?
            """, (experiment_id, w))
            rows = cur.fetchall()
            row_map = {r[0]: r for r in rows}

            for i, nid in enumerate(node_ids):
                r = row_map.get(nid)
                if r is None:
                    continue
                feats = np.array(r[2:], dtype=np.float32)
                X[i] = feats

            samples.append({
                "experiment_id": experiment_id,
                "window_idx": w,
                "A_norm": torch.tensor(A_norm),
                "X": torch.tensor(X),
                "y_graph": torch.tensor([y_graph], dtype=torch.float32),
            })

    conn.close()
    return samples
