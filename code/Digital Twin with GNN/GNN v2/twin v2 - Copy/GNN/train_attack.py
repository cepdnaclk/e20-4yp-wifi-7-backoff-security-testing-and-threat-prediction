import glob, json
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path

from GNN.backoff_dataset import load_json, make_samples
from GNN.attack_model import AttackGCN

def build_scaler(samples):
    # fit on all node-features across training samples
    Xall = np.concatenate([s.X for s in samples], axis=0)  # [(sum N), F]
    mean = Xall.mean(axis=0)
    std = Xall.std(axis=0) + 1e-6
    return mean, std

def apply_scaler(samples, mean, std):
    for s in samples:
        s.X = ((s.X - mean) / std).astype(np.float32)

def load_folder(folder: str, label: int, window_s: float):
    paths = sorted(glob.glob(folder))
    all_samples = []
    for p in paths:
        ev = load_json(p)
        all_samples.extend(make_samples(ev, label=label, window_s=window_s))
    return all_samples

def main():
    # 1) Load
    normal = load_folder("data/normal/*.json", label=0, window_s=0.01)
    attack = load_folder("data/attack/*.json", label=1, window_s=0.01)
    samples = normal + attack

    # 2) Shuffle + split
    rng = np.random.default_rng(42)
    idx = rng.permutation(len(samples))
    samples = [samples[i] for i in idx]

    n_train = int(0.8 * len(samples))
    train_s, test_s = samples[:n_train], samples[n_train:]

    # 3) Scale features (fit on train only)
    mean, std = build_scaler(train_s)
    apply_scaler(train_s, mean, std)
    apply_scaler(test_s, mean, std)

    # 4) Torch setup
    device = "cpu"
    model = AttackGCN(in_dim=8, hidden=32).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.BCEWithLogitsLoss()

    # 5) Train
    for epoch in range(1, 21):
        model.train()
        total = 0.0

        for s in train_s:
            A = torch.tensor(s.A, dtype=torch.float32, device=device)
            X = torch.tensor(s.X, dtype=torch.float32, device=device)
            y = torch.tensor(float(s.y), dtype=torch.float32, device=device)

            logit = model(A, X)
            loss = loss_fn(logit, y)

            opt.zero_grad()
            loss.backward()
            opt.step()
            total += float(loss.item())

        # 6) Quick eval
        model.eval()
        correct, n = 0, 0
        with torch.no_grad():
            for s in test_s:
                A = torch.tensor(s.A, dtype=torch.float32, device=device)
                X = torch.tensor(s.X, dtype=torch.float32, device=device)
                prob = torch.sigmoid(model(A, X)).item()
                pred = 1 if prob >= 0.5 else 0
                correct += int(pred == s.y)
                n += 1
        acc = correct / max(n, 1)

        print(f"epoch {epoch:02d}  train_loss={total/len(train_s):.4f}  test_acc={acc:.3f}")

    # 7) Save artifacts
    out_dir = Path("GNN/artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)

    torch.save(model.state_dict(), out_dir / "attack_gnn_v0.pt")
    with open(out_dir / "attack_gnn_v0_scaler.json", "w") as f:
        json.dump({"mean": mean.tolist(), "std": std.tolist()}, f, indent=2)

    print("Saved:", out_dir / "attack_gnn_v0.pt")

if __name__ == "__main__":
    main()
