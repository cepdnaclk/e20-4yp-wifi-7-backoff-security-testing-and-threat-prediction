# # GNN/service/main.py
# import json
# import numpy as np
# import torch
# from pathlib import Path
# from fastapi import FastAPI, HTTPException

# from .schemas import PredictRequest, PredictResponse
# from .db import insert_predictions
# from GNN.attack_model import AttackGCN

# MODEL_VERSION = "attack_gnn_v1"

# BASE_DIR = Path(__file__).resolve().parents[1]  # .../GNN
# MODEL_PATH = BASE_DIR / "artifacts" / "attack_gnn_v1.pt"
# SCALER_PATH = BASE_DIR / "artifacts" / "attack_gnn_v1_scaler.json"

# app = FastAPI()

# # ---------------------------
# # Load scaler (mean/std)  -> must be length 14
# # ---------------------------
# with open(SCALER_PATH, "r", encoding="utf-8") as f:
#     scaler = json.load(f)

# SCALER_MEAN = np.array(scaler["mean"], dtype=np.float32)  # [14]
# SCALER_STD  = np.array(scaler["std"], dtype=np.float32)   # [14]

# if SCALER_MEAN.shape[0] != 14 or SCALER_STD.shape[0] != 14:
#     raise RuntimeError(f"Scaler must be 14-dim. Got mean={SCALER_MEAN.shape}, std={SCALER_STD.shape}")

# # ---------------------------
# # Load model -> must match checkpoint: in_dim=14
# # ---------------------------
# model = AttackGCN(in_dim=14, hidden=32)
# ckpt = torch.load(MODEL_PATH, map_location="cpu")
# model.load_state_dict(ckpt)
# model.eval()

# def normalize_adj(A: np.ndarray) -> np.ndarray:
#     D = A.sum(axis=1)
#     D_inv = np.diag(1.0 / np.sqrt(D + 1e-8))
#     return D_inv @ A @ D_inv

# def make_chain_adj(n: int) -> np.ndarray:
#     # temporal chain: i <-> i+1 + self loops
#     A = np.zeros((n, n), dtype=np.float32)
#     for i in range(n - 1):
#         A[i, i + 1] = 1.0
#         A[i + 1, i] = 1.0
#     A = A + np.eye(n, dtype=np.float32)
#     return normalize_adj(A)

# @app.get("/")
# def root():
#     return {"status": "ok", "hint": "Open /docs and POST /predict"}

# @app.post("/predict", response_model=PredictResponse)
# def predict(req: PredictRequest):
#     try:
#         if not req.windows:
#             raise HTTPException(status_code=400, detail="windows is empty")

#         # Build X: [N,14] from your schema (exclude 'window' index)
#         X = []
#         for w in req.windows:
#             X.append([
#                 w.bias,
#                 w.net_throughput_mbps,
#                 w.net_avg_delay_ms,
#                 w.net_avg_jitter_ms,
#                 w.net_packet_loss_ratio,
#                 w.net_active_flows,
#                 w.mac_total_tx,
#                 w.mac_total_rx,
#                 w.mac_total_ack,
#                 w.mac_total_retrans,
#                 w.mac_drop_count,
#                 w.phy_drop_count,
#                 w.avg_backoff_slots,
#                 w.channel_busy_ratio,
#             ])

#         X = np.array(X, dtype=np.float32)  # [N,14]
#         if X.shape[1] != 14:
#             raise HTTPException(status_code=400, detail=f"Expected 14 features, got {X.shape[1]}")

#         # Scale (same as training)
#         Xn = (X - SCALER_MEAN) / (SCALER_STD + 1e-8)

#         # Adjacency over windows (chain)
#         A = make_chain_adj(len(req.windows))

#         with torch.no_grad():
#             At = torch.tensor(A, dtype=torch.float32)
#             Xt = torch.tensor(Xn, dtype=torch.float32)
#             logit = model(At, Xt)
#             attack_prob = float(torch.sigmoid(logit).item())

#         # Store in DB
#         insert_predictions(req.experiment_id, [(None, "attack_probability", attack_prob)], MODEL_VERSION)

#         return PredictResponse(model_version=MODEL_VERSION, attack_probability=attack_prob)

#     except HTTPException:
#         raise
#     except Exception as e:
#         # This makes the real error visible in Swagger (instead of just "Internal Server Error")
#         raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

import json
import numpy as np
import torch
from pathlib import Path
from fastapi import FastAPI, HTTPException

from .schemas import PredictRequest, PredictResponse
from .db import insert_predictions
from attack_model import AttackGCN

# ---------------------------
# Global Constants & Paths
# ---------------------------
MODEL_VERSION = "attack_gnn_v2_large_datasetV3"
GRAPH_LEN = 32
F_DIM = 14

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "GNN" / "artifacts" / "attack_gnn_v2_large_datasetV3.pt"
SCALER_PATH = BASE_DIR / "GNN" / "artifacts" / "attack_gnn_v2_large_datasetV3.json"

app = FastAPI()

# ---------------------------
# 1. Load Resources on Startup
# ---------------------------
if not SCALER_PATH.exists():
    raise RuntimeError(f"Scaler file not found at: {SCALER_PATH}")

with open(SCALER_PATH, "r", encoding="utf-8") as f:
    scaler = json.load(f)

SCALER_MEAN = np.array(scaler["mean"], dtype=np.float32)
SCALER_STD = np.array(scaler["std"], dtype=np.float32)

if SCALER_MEAN.shape[0] != F_DIM or SCALER_STD.shape[0] != F_DIM:
    raise RuntimeError(f"Scaler dimension mismatch. Expected {F_DIM}, got mean={SCALER_MEAN.shape}, std={SCALER_STD.shape}")

if not MODEL_PATH.exists():
    raise RuntimeError(f"Model file not found at: {MODEL_PATH}")

# Load 3-class model
model = AttackGCN(in_dim=F_DIM, hidden=32, n_classes=3)
try:
    ckpt = torch.load(MODEL_PATH, map_location="cpu")
    model.load_state_dict(ckpt)
    model.eval()
except Exception as e:
    raise RuntimeError(f"Failed to load model checkpoint: {e}")

# ---------------------------
# 2. Helper Functions
# ---------------------------
def normalize_adj(A: np.ndarray) -> np.ndarray:
    D = A.sum(axis=1)
    D_inv = np.diag(1.0 / np.sqrt(D + 1e-8))
    return D_inv @ A @ D_inv

def make_chain_adj(n: int) -> np.ndarray:
    A = np.zeros((n, n), dtype=np.float32)
    for i in range(n - 1):
        A[i, i + 1] = 1.0
        A[i + 1, i] = 1.0
    A = A + np.eye(n, dtype=np.float32)
    return normalize_adj(A)

# ---------------------------
# 3. API Endpoints
# ---------------------------
@app.get("/")
def root():
    return {
        "status": "online", 
        "model": MODEL_VERSION,
        "input_requirement": f"Last {GRAPH_LEN} windows"
    }

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    try:
        if not req.windows:
            raise HTTPException(status_code=400, detail="Input 'windows' list is empty.")

        X_full = []
        for w in req.windows:
            X_full.append([
                w.bias, w.net_throughput_mbps, w.net_avg_delay_ms, w.net_avg_jitter_ms,
                w.net_packet_loss_ratio, w.net_active_flows, w.mac_total_tx, w.mac_total_rx,
                w.mac_total_ack, w.mac_total_retrans, w.mac_drop_count, w.phy_drop_count,
                w.avg_backoff_slots, w.channel_busy_ratio,
            ])
        X_full = np.array(X_full, dtype=np.float32)

        if X_full.shape[1] != F_DIM:
            raise HTTPException(status_code=400, detail=f"Feature count mismatch. Expected {F_DIM}, got {X_full.shape[1]}")

        num_windows = X_full.shape[0]
        if num_windows < GRAPH_LEN:
            raise HTTPException(status_code=400, detail=f"Insufficient data. Need at least {GRAPH_LEN} windows (got {num_windows}).")
        
        X = X_full[-GRAPH_LEN:]

        Xn = (X - SCALER_MEAN) / (SCALER_STD + 1e-8)
        A = make_chain_adj(GRAPH_LEN)

        with torch.no_grad():
            At = torch.tensor(A, dtype=torch.float32)
            Xt = torch.tensor(Xn, dtype=torch.float32)
            
            logits = model(At, Xt)
            probs = torch.softmax(logits, dim=0)
            predicted_class = torch.argmax(probs).item()
            
            probs_list = probs.tolist()

        db_payload = [
            (None, "prob_normal", probs_list[0]),
            (None, "prob_pos_attack", probs_list[1]),
            (None, "prob_neg_attack", probs_list[2]),
        ]
        insert_predictions(req.experiment_id, db_payload, MODEL_VERSION)

        return PredictResponse(
            model_version=MODEL_VERSION, 
            predicted_class=predicted_class,
            probabilities=probs_list
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {type(e).__name__} - {e}")