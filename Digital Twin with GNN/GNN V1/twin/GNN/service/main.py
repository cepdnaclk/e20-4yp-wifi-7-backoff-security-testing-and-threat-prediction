import json
import numpy as np
import torch
from fastapi import FastAPI
from .schemas import PredictRequest, PredictResponse, Prediction
from .db import insert_predictions
from ..model import GNNRegressor  # adjust import if needed

MODEL_PATH = "twin/gnn/artifacts/gnn_v0.pt"
MODEL_VERSION = "gnn_v0_dummy"

app = FastAPI()
model = GNNRegressor(in_dim=3, hidden=32, node_out=3)
model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
model.eval()

def build_graph(topology: dict, features_list):
    nodes = topology["nodes"]
    edges = topology["edges"]
    node_ids = [n["id"] for n in nodes]
    node_types = {n["id"]: n["type"] for n in nodes}
    idx = {nid:i for i,nid in enumerate(node_ids)}

    N = len(node_ids)
    A = np.zeros((N,N), dtype=np.float32)
    for e in edges:
        i, j = idx[e["src"]], idx[e["dst"]]
        A[i,j] = 1.0
        A[j,i] = 1.0
    A = A + np.eye(N, dtype=np.float32)
    D = A.sum(axis=1)
    D_inv = np.diag(1.0/np.sqrt(D + 1e-8))
    A_norm = D_inv @ A @ D_inv

    X = np.zeros((N,3), dtype=np.float32)
    for f in features_list:
        X[idx[f.node_id]] = np.array([f.f_throughput_hint, f.f_delay_hint, f.f_retry_hint], dtype=np.float32)

    return node_ids, node_types, torch.tensor(A_norm), torch.tensor(X)

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    node_ids, node_types, A, X = build_graph(req.topology, req.features)

    with torch.no_grad():
        node_pred, global_pred = model(A, X)  # node_pred[N,3], global_pred[1]

    out = []
    store_rows = []

    # per-STA KPIs
    kpi_names = ["throughput_mbps", "delay_p95_ms", "retry_rate"]
    for i, nid in enumerate(node_ids):
        if node_types[nid] == "STA":
            for k, kname in enumerate(kpi_names):
                val = float(node_pred[i, k].item())
                out.append(Prediction(node_id=nid, kpi_name=kname, value=val))
                store_rows.append((nid, kname, val))

    # global KPI
    gval = float(global_pred[0].item())
    out.append(Prediction(node_id=None, kpi_name="jain_fairness_index", value=gval))
    store_rows.append((None, "jain_fairness_index", gval))

    insert_predictions(req.experiment_id, store_rows, MODEL_VERSION)
    return PredictResponse(model_version=MODEL_VERSION, predictions=out)
