import json
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional
from sklearn.neighbors import kneighbors_graph
from sklearn.preprocessing import StandardScaler

# -------------------------
# Feature order (IMPORTANT)
# -------------------------
FEATURE_KEYS = [
    "bias",
    "net_throughput_mbps",
    "net_avg_delay_ms",
    "net_avg_jitter_ms",
    "net_packet_loss_ratio",
    "net_active_flows",
    "mac_total_tx",
    "mac_total_rx",
    "mac_total_ack",
    "mac_total_retrans",
    "mac_drop_count",
    "phy_drop_count",
    "avg_backoff_slots",
    "channel_busy_ratio",
]

F_DIM = len(FEATURE_KEYS)  # 14


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


def _make_chain_topology(N: int) -> np.ndarray:
    """
    Windows are nodes: connect i <-> i+1 (temporal chain),
    add self loops, then normalize.

    NOTE: This is a very simple topology that only captures dependencies between adjacent windows.
    For more complex scenarios, a more sophisticated topology might be needed (e.g., a complete graph,
    a k-NN graph, or a learnable topology).
    """
    A = np.zeros((N, N), dtype=np.float32)

    # connect consecutive windows
    for i in range(N - 1):
        A[i, i + 1] = 1.0
        A[i + 1, i] = 1.0

    # self-loops
    A = A + np.eye(N, dtype=np.float32)

    return _normalize_adj(A)


def _make_knn_topology(X: np.ndarray, k: int) -> np.ndarray:
    """
    Creates a k-NN graph topology based on node features.
    Nodes are connected to their k-nearest neighbors based on feature similarity.
    """
    N = X.shape[0]
    if N <= k:
        # Fallback to a fully connected graph if N is too small
        A = np.ones((N, N), dtype=np.float32)
    else:
        # Scale features before computing distances
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Compute k-NN graph, weights are distances
        A = kneighbors_graph(X_scaled, n_neighbors=k, mode='distance', include_self=False)
        A = A.toarray()

        # Invert distances to get similarities (closer = higher weight)
        # Add a small epsilon to avoid division by zero
        A = 1.0 / (A + 1e-6)
        A[A > 1e5] = 0 # zero out the ones that were 0 distance

    # Make symmetric (undirected)
    A = np.maximum(A, A.T)

    # Add self-loops
    A = A + np.eye(N, dtype=np.float32)

    return _normalize_adj(A)


def _row_to_features(row: Dict) -> np.ndarray:
    """
    Extracts features from a dictionary row based on FEATURE_KEYS.
    Note: This function replaces NaN, positive infinity, and negative infinity with 0.0.
    This is a simple imputation strategy and might need to be revisited based on the dataset's characteristics.
    For example, using mean/median imputation or a model-based approach might be more appropriate.
    """
    feats = np.array([float(row.get(k, 0.0)) for k in FEATURE_KEYS], dtype=np.float32)
    feats = np.nan_to_num(feats, nan=0.0, posinf=0.0, neginf=0.0)
    return feats



def load_json(path):
    with open(path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️  WARNING: Skipping corrupted file: {path}")
            return []  # Return empty list so the loop continues safely


def make_samples(
    windows: List[dict],
    label: int,
    window_s: float = 0.01,                 # kept for compatibility; not used now
    graph_len: Optional[int] = None,        # optional sliding window length (number of windows per graph)
    stride: int = 1,
    topology: str = 'knn',                  # 'knn' or 'chain'
    k: int = 5                              # for k-NN
) -> List[GraphSample]:
    """
    Convert window-metrics stream -> list of graph samples

    - If graph_len is None: returns ONE GraphSample using ALL windows.
    - If graph_len is set: returns multiple GraphSamples using sliding chunks.
    """

    if not windows:
        return []

    # sort by "window" index if present (recommended)
    if "window" in windows[0]:
        windows = sorted(windows, key=lambda r: int(r.get("window", 0)))

    X_all = np.stack([_row_to_features(r) for r in windows], axis=0)  # [N,14]
    N = X_all.shape[0]

    samples: List[GraphSample] = []
    
    # Choose topology builder
    if topology == 'knn':
        def topology_builder(X_slice):
            return _make_knn_topology(X_slice, k=k)
    else: # 'chain'
        def topology_builder(X_slice):
            return _make_chain_topology(X_slice.shape[0])


    # Case 1: single graph from all windows
    if graph_len is None or graph_len >= N:
        A = topology_builder(X_all)
        samples.append(GraphSample(
            A=A,
            X=X_all,
            y=label,
            meta={"mode": "full", "n_windows": N}
        ))
        return samples

    # Case 2: sliding graphs
    graph_len = max(2, int(graph_len))
    stride = max(1, int(stride))

    for start in range(0, N - graph_len + 1, stride):
        end = start + graph_len
        X_slice = X_all[start:end]               # [graph_len,14]
        A = topology_builder(X_slice)

        w_start = windows[start].get("window", start)
        w_end = windows[end - 1].get("window", end - 1)

        samples.append(GraphSample(
            A=A,
            X=X_slice,
            y=label,
            meta={"mode": "sliding", "start": start, "end": end, "win_range": [w_start, w_end]}
        ))

    return samples
