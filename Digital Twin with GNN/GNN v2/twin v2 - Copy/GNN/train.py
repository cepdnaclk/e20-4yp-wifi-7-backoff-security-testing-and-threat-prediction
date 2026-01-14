# GNN/train.py
import os, random
import torch
import torch.nn as nn
from torch.optim import Adam

from dataset import load_samples, FEATURE_COLS
from model import GraphAttackDetector

def split(samples, seed=1):
    random.seed(seed)
    random.shuffle(samples)
    n = len(samples)
    n_train = int(0.7 * n)
    n_val = int(0.15 * n)
    return samples[:n_train], samples[n_train:n_train+n_val], samples[n_train+n_val:]

def eval_loop(model, samples, loss_fn):
    model.eval()
    total_loss = 0.0
    correct = 0
    with torch.no_grad():
        for s in samples:
            logit = model(s["A_norm"], s["X"])
            loss = loss_fn(logit.view(1), s["y_graph"])
            total_loss += float(loss.item())
            prob = torch.sigmoid(logit).item()
            pred = 1 if prob >= 0.5 else 0
            correct += int(pred == int(s["y_graph"].item()))
    return total_loss / max(len(samples), 1), correct / max(len(samples), 1)

def main():
    samples = load_samples("backoff_udr_dummy.sqlite")
    train_s, val_s, test_s = split(samples)

    model = GraphAttackDetector(in_dim=len(FEATURE_COLS))
    opt = Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.BCEWithLogitsLoss()

    best_val = 1e9
    os.makedirs("GNN/artifacts", exist_ok=True)
    for epoch in range(1, 21):
        model.train()
        for s in train_s:
            opt.zero_grad()
            logit = model(s["A_norm"], s["X"])
            loss = loss_fn(logit.view(1), s["y_graph"])
            loss.backward()
            opt.step()

        val_loss, val_acc = eval_loop(model, val_s, loss_fn)
        print(f"epoch={epoch:02d} val_loss={val_loss:.4f} val_acc={val_acc:.3f}")
        if val_loss < best_val:
            best_val = val_loss
            torch.save({"state_dict": model.state_dict()}, "GNN/artifacts/attack_gnn_v0.pt")

    # final test
    ckpt = torch.load("GNN/artifacts/attack_gnn_v0.pt", map_location="cpu")
    model.load_state_dict(ckpt["state_dict"])
    test_loss, test_acc = eval_loop(model, test_s, loss_fn)
    print(f"TEST loss={test_loss:.4f} acc={test_acc:.3f}")

if __name__ == "__main__":
    main()
