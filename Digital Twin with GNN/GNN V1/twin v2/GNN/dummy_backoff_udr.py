# GNN/dummy_backoff_udr.py
import json, math, os, random, sqlite3
from dataclasses import dataclass
from typing import List, Dict, Any
import numpy as np

DB_PATH = "backoff_udr_dummy.sqlite"

WINDOW_SEC = 0.05        # 50ms windows
SIM_TIME_SEC = 0.5       # similar to your ns-3
LINK_ID = 0

@dataclass
class Node:
    id: str
    type: str  # "AP" or "STA"

def jain_fairness(xs: List[float]) -> float:
    xs = np.array(xs, dtype=float)
    if np.all(xs == 0):
        return 0.0
    return float((xs.sum() ** 2) / (len(xs) * (xs ** 2).sum()))

def ensure_schema(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS snapshots(
      experiment_id TEXT PRIMARY KEY,
      topology_json TEXT NOT NULL,
      ctx_json TEXT NOT NULL
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS window_features(
      experiment_id TEXT NOT NULL,
      window_idx INTEGER NOT NULL,
      node_id TEXT NOT NULL,
      node_type TEXT NOT NULL,
      link_id INTEGER NOT NULL,
      frequency REAL NOT NULL,
      channel_width INTEGER NOT NULL,
      mcs INTEGER NOT NULL,
      guard_interval INTEGER NOT NULL,
      cw_min INTEGER NOT NULL,
      cw_max INTEGER NOT NULL,

      event_count INTEGER NOT NULL,
      mean_backoff REAL NOT NULL,
      std_backoff REAL NOT NULL,
      p95_backoff REAL NOT NULL,
      max_backoff REAL NOT NULL,
      mean_norm REAL NOT NULL,
      p95_norm REAL NOT NULL,

      PRIMARY KEY (experiment_id, window_idx, node_id, link_id)
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS window_labels(
      experiment_id TEXT NOT NULL,
      window_idx INTEGER NOT NULL,
      label INTEGER NOT NULL,
      PRIMARY KEY (experiment_id, window_idx)
    )""")
    conn.commit()

def simulate_backoff_events(
    nodes: List[Node],
    cw_min: int,
    cw_max: int,
    attack: bool,
    attacker_node_id: str | None,
) -> List[Dict[str, Any]]:
    """
    Produce ns-3-like backoff events:
    {timestamp,node_id,link_id,frequency,width,mcs,gi,cw_min,cw_max,backoff_value}
    In attack mode: attacker has larger/burstier backoff distribution.
    """
    events = []
    t = 0.0
    # event rate baseline: how often backoff events happen per node
    base_rate = 200  # events/sec (dummy)
    for node in nodes:
        # make STAs generate most backoff events
        rate = base_rate * (1.3 if node.type == "STA" else 0.6)

        # Attack effect: one STA gets inflated backoff + bursts
        is_attacker = attack and (node.id == attacker_node_id)

        # Build per-node event timestamps
        n_events = int(rate * SIM_TIME_SEC)
        ts = np.sort(np.random.uniform(0, SIM_TIME_SEC, size=n_events))

        for timestamp in ts:
            if is_attacker:
                # abnormal: much larger typical backoff and occasional extreme spikes
                # sample from a mixture distribution
                if random.random() < 0.10:
                    backoff = random.randint(cw_max * 2, cw_max * 10)  # "spike"
                else:
                    backoff = int(np.random.normal(loc=cw_max * 0.9, scale=cw_max * 0.25))
            else:
                # normal: bounded-ish backoff around mid-CW
                backoff = int(np.random.normal(loc=(cw_min + cw_max) * 0.25, scale=(cw_max - cw_min) * 0.10))

            backoff = max(0, backoff)

            events.append({
                "timestamp": float(timestamp),
                "node_id": node.id,
                "link_id": LINK_ID,
                "frequency": 5.0,
                "channel_width": 80,
                "mcs": 7,
                "guard_interval": 1600,
                "cw_min": cw_min,
                "cw_max": cw_max,
                "backoff_value": int(backoff),
            })
    return events

def window_aggregate(events: List[Dict[str, Any]], nodes: List[Node]) -> Dict[int, Dict[str, Dict[str, float]]]:
    """
    returns: window_idx -> node_id -> feature dict
    """
    # group events by window and node
    windows: Dict[int, Dict[str, List[int]]] = {}
    for e in events:
        w = int(e["timestamp"] / WINDOW_SEC)
        windows.setdefault(w, {}).setdefault(e["node_id"], []).append(int(e["backoff_value"]))

    # compute features per node per window
    out: Dict[int, Dict[str, Dict[str, float]]] = {}
    for w in range(int(SIM_TIME_SEC / WINDOW_SEC)):
        out[w] = {}
        for node in nodes:
            values = np.array(windows.get(w, {}).get(node.id, []), dtype=float)
            if values.size == 0:
                values = np.array([0.0])
            p95 = float(np.percentile(values, 95))
            mean = float(values.mean())
            std = float(values.std())
            mx = float(values.max())
            out[w][node.id] = {
                "event_count": float(len(values)),
                "mean_backoff": mean,
                "std_backoff": std,
                "p95_backoff": p95,
                "max_backoff": mx,
            }
    return out

def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    ensure_schema(conn)
    cur = conn.cursor()

    random.seed(1)
    np.random.seed(1)

    n_experiments = 80
    n_stas = 3

    for i in range(n_experiments):
        experiment_id = f"exp_{i:04d}"

        nodes = [Node("ap1", "AP")] + [Node(f"sta{k+1}", "STA") for k in range(n_stas)]
        edges = [{"src": "ap1", "dst": f"sta{k+1}"} for k in range(n_stas)]
        topology = {"nodes": [n.__dict__ for n in nodes], "edges": edges}

        # Context (you can randomize later)
        cw_min = 15
        cw_max = 1023

        # label
        attack = (i % 2 == 1)
        attacker = "sta1" if attack else None

        ctx = {
            "attack": int(attack),
            "attacker": attacker,
            "cw_min": cw_min,
            "cw_max": cw_max,
            "window_sec": WINDOW_SEC,
        }

        # Insert snapshot
        cur.execute(
            "INSERT INTO snapshots(experiment_id, topology_json, ctx_json) VALUES (?,?,?)",
            (experiment_id, json.dumps(topology), json.dumps(ctx)),
        )

        events = simulate_backoff_events(nodes, cw_min, cw_max, attack, attacker)
        agg = window_aggregate(events, nodes)

        # save window labels
        for w in agg.keys():
            cur.execute("INSERT INTO window_labels(experiment_id, window_idx, label) VALUES (?,?,?)",
                        (experiment_id, w, int(attack)))

        # save features
        for w, per_node in agg.items():
            for node in nodes:
                f = per_node[node.id]
                # normalize by cw_max+1
                mean_norm = float(f["mean_backoff"] / (cw_max + 1))
                p95_norm = float(f["p95_backoff"] / (cw_max + 1))

                cur.execute("""
                INSERT INTO window_features(
                  experiment_id, window_idx, node_id, node_type, link_id,
                  frequency, channel_width, mcs, guard_interval, cw_min, cw_max,
                  event_count, mean_backoff, std_backoff, p95_backoff, max_backoff, mean_norm, p95_norm
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    experiment_id, w, node.id, node.type, LINK_ID,
                    5.0, 80, 7, 1600, cw_min, cw_max,
                    int(f["event_count"]), f["mean_backoff"], f["std_backoff"], f["p95_backoff"], f["max_backoff"], mean_norm, p95_norm
                ))

    conn.commit()
    conn.close()
    print(f"Created {DB_PATH} with {n_experiments} experiments.")

if __name__ == "__main__":
    main()
