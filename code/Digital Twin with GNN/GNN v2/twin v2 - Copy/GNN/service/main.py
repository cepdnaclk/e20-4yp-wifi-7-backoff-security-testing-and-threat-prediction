# GNN/service/main.py
import json
import numpy as np
import torch
from fastapi import FastAPI, HTTPException

from .schemas import PredictRequest, PredictResponse
from .db import insert_predictions

# ✅ must match the model you trained in train_attack.py
from GNN.attack_model import AttackGCN
from GNN.backoff_dataset import make_samples

MODEL_PATH = "GNN/artifacts/attack_gnn_v0.pt"
SCALER_PATH = "GNN/artifacts/attack_gnn_v0_scaler.json"
MODEL_VERSION = "attack_gnn_v0"

app = FastAPI()

# ---------------------------
# Load scaler (mean/std)
# ---------------------------
with open(SCALER_PATH, "r", encoding="utf-8") as f:
    scaler = json.load(f)

SCALER_MEAN = np.array(scaler["mean"], dtype=np.float32)  # shape [8]
SCALER_STD = np.array(scaler["std"], dtype=np.float32)    # shape [8]

# ---------------------------
# Load model
# ---------------------------
model = AttackGCN(in_dim=8, hidden=32)

ckpt = torch.load(MODEL_PATH, map_location="cpu")
# train_attack saved plain state_dict, so this is enough:
model.load_state_dict(ckpt)
model.eval()


@app.get("/")
def root():
    return {"status": "ok", "hint": "Open /docs and POST /predict"}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    print("BACKOFFS:", [e.backoff_value for e in req.window_events][:10])
    # Convert pydantic events -> list[dict]
    events = [
        (e.model_dump() if hasattr(e, "model_dump") else e.dict())
        for e in req.window_events
    ]

    if not events:
        raise HTTPException(status_code=400, detail="window_events is empty")

    # Build graph sample(s) using the SAME logic as training
    samples = make_samples(events, label=0, window_s=req.window_s)

    if not samples:
        raise HTTPException(status_code=400, detail="No samples created from window_events")

    # For API response, we score all windows and return the MAX probability
    probs = []
    with torch.no_grad():
        for s in samples:
            A = torch.tensor(s.A, dtype=torch.float32)      # [N,N]
            X = s.X.astype(np.float32)                      # [N,8]

            # Apply scaler from training
            Xn = (X - SCALER_MEAN) / (SCALER_STD + 1e-8)
            Xt = torch.tensor(Xn, dtype=torch.float32)      # [N,8]

            logit = model(A, Xt)                            # scalar
            prob = float(torch.sigmoid(logit).item())
            probs.append(prob)

    attack_prob = float(max(probs))

    # Store in DB
    insert_predictions(req.experiment_id, [(None, "attack_probability", attack_prob)], MODEL_VERSION)

    return PredictResponse(model_version=MODEL_VERSION, attack_probability=attack_prob)
