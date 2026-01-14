import json
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict

@dataclass
class GraphSample:
    A: np.ndarray        # [N, N] normalized adjacency
    X: np.ndarray        # [N, F] node features
    y: int               # 0 normal, 1 attack
    meta: dict           # optional debug info

def _normalize_adj(A: np.ndarray) -> np.ndarray:
    # A: adjacency with self loops
    D = A.sum(axis=1)
    D_inv = np.diag(1.0 / np.sqrt(D + 1e-8))
    return D_inv @ A @ D_inv

def _make_star_topology(node_ids: List[int]) -> np.ndarray:
    # node 0 is AP, connect to all others
    N = len(node_ids)
    idx = {nid: i for i, nid in enumerate(node_ids)}
    A = np.zeros((N, N), dtype=np.float32)

    if 0 in idx:
        ap = idx[0]
        for nid in node_ids:
            if nid == 0:
                continue
            j = idx[nid]
            A[ap, j] = 1.0
            A[j, ap] = 1.0

    # self-loops
    A = A + np.eye(N, dtype=np.float32)
    return _normalize_adj(A)

def _agg_features(rows: List[dict]) -> np.ndarray:
    """
    rows: events for ONE node in ONE time-window.
    Output: feature vector [F]
    """
    if len(rows) == 0:
        # no events in this window -> zeros
        return np.zeros((8,), dtype=np.float32)

    b = np.array([r["backoff_value"] for r in rows], dtype=np.float32)
    cw_max = float(rows[0]["cw_max"]) if "cw_max" in rows else 1023.0
    cw_max = max(cw_max, 1.0)

    b_norm = b / cw_max  # normalize

    neg_ratio = float((b < 0).mean())
    mcs_mean = float(np.mean([r["mcs"] for r in rows]))
    width_mean = float(np.mean([r["channel_width"] for r in rows])) / 160.0
    freq_mean = float(np.mean([r["frequency"] for r in rows])) / 6.0  # (0/5/6) scaled

    feats = np.array([
        float(b_norm.mean()),
        float(b_norm.std()),
        float(b_norm.min()),
        float(b_norm.max()),
        neg_ratio,
        mcs_mean / 13.0,     # scale to ~0..1
        width_mean,
        freq_mean,
    ], dtype=np.float32)

    return feats

def load_json(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def make_samples(events: List[dict], label: int, window_s: float = 0.01) -> List[GraphSample]:
    """
    Convert event stream -> list of graph samples
    """
    # sort by time (important)
    events = sorted(events, key=lambda r: float(r["timestamp"]))

    node_ids = sorted({int(r["node_id"]) for r in events})
    A = _make_star_topology(node_ids)
    idx = {nid: i for i, nid in enumerate(node_ids)}

    # windowing
    t0 = float(events[0]["timestamp"])
    t1 = float(events[-1]["timestamp"])
    nwin = int(np.ceil((t1 - t0) / window_s)) + 1

    samples: List[GraphSample] = []
    ptr = 0

    for w in range(nwin):
        ws = t0 + w * window_s
        we = ws + window_s

        bucket = []
        while ptr < len(events) and float(events[ptr]["timestamp"]) < we:
            if float(events[ptr]["timestamp"]) >= ws:
                bucket.append(events[ptr])
            ptr += 1

        # group by node_id
        per_node: Dict[int, List[dict]] = {nid: [] for nid in node_ids}
        for r in bucket:
            per_node[int(r["node_id"])].append(r)

        # build X
        X = np.zeros((len(node_ids), 8), dtype=np.float32)
        for nid in node_ids:
            X[idx[nid]] = _agg_features(per_node[nid])

        samples.append(GraphSample(
            A=A,
            X=X,
            y=label,
            meta={"win_start": ws, "win_end": we, "n_events": len(bucket)}
        ))

    return samples
