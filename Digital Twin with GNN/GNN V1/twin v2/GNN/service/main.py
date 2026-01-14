# GNN/service/main.py
import numpy as np
import torch
from fastapi import FastAPI

from .schemas import PredictRequest, PredictResponse
from .db import insert_predictions

# ✅ Change model import to your attack detector model
# If you named it differently, update this import.
from ..model import GraphAttackDetector

# ✅ Path to your trained attack model checkpoint
MODEL_PATH = "GNN/artifacts/attack_gnn_v0.pt"
MODEL_VERSION = "attack_gnn_v0_dummy"

# ✅ Must match the exact feature order used in training
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

app = FastAPI()

# Build model
model = GraphAttackDetector(in_dim=len(FEATURE_COLS), hidden=64)

# Robust checkpoint loading
ckpt = torch.load(MODEL_PATH, map_location="cpu")
if isinstance(ckpt, dict) and "state_dict" in ckpt:
    model.load_state_dict(ckpt["state_dict"])
else:
    model.load_state_dict(ckpt)

model.eval()


def _to_dict(obj):
    """Support pydantic v2 (model_dump), v1 (dict), or raw dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj


def build_graph(topology_obj, features_list):
    topo = _to_dict(topology_obj)
    nodes = topo["nodes"]
    edges = topo["edges"]

    node_ids = [n["id"] for n in nodes]
    idx = {nid: i for i, nid in enumerate(node_ids)}

    # Adjacency
    N = len(node_ids)
    A = np.zeros((N, N), dtype=np.float32)
    for e in edges:
        i, j = idx[e["src"]], idx[e["dst"]]
        A[i, j] = 1.0
        A[j, i] = 1.0

    # add self loops + normalize
    A = A + np.eye(N, dtype=np.float32)
    D = A.sum(axis=1)
    D_inv = np.diag(1.0 / np.sqrt(D + 1e-8))
    A_norm = D_inv @ A @ D_inv

    # Features matrix X [N, F]
    X = np.zeros((N, len(FEATURE_COLS)), dtype=np.float32)

    # features_list is list of pydantic objects -> use attributes
    fmap = {f.node_id: f for f in features_list}

    for nid in node_ids:
        if nid not in fmap:
            continue
        f = fmap[nid]

        X[idx[nid]] = np.array([
            f.event_count,
            f.mean_backoff,
            f.std_backoff,
            f.p95_backoff,
            f.max_backoff,
            f.mean_norm,
            f.p95_norm,
            f.cw_min,
            f.cw_max,
            f.mcs,
            f.channel_width,
            f.guard_interval,
            f.frequency,
        ], dtype=np.float32)

    return torch.tensor(A_norm), torch.tensor(X)


@app.get("/")
def root():
    return {"status": "ok", "hint": "Open /docs and POST /predict"}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    A, X = build_graph(req.topology, req.features)

    with torch.no_grad():
        logit = model(A, X)  # shape [1] or scalar tensor

    prob = float(torch.sigmoid(logit).item())

    # Store in DB like a KPI
    store_rows = [(None, "attack_probability", prob)]
    insert_predictions(req.experiment_id, store_rows, MODEL_VERSION)

    return PredictResponse(model_version=MODEL_VERSION, attack_probability=prob)
