import os, json, random
import torch
import torch.nn as nn
import torch.optim as optim
from dataset import load_experiments
from model import GNNRegressor

DB_PATH = "udr_dummy.sqlite"
ART_DIR = "twin/gnn/artifacts"
os.makedirs(ART_DIR, exist_ok=True)

def group_key(exp):
    return f"{exp['topology_hash']}|{exp['load_level']}"

def split_group(exps, test_ratio=0.2, val_ratio=0.1, seed=42):
    random.seed(seed)
    groups = {}
    for e in exps:
        groups.setdefault(group_key(e), []).append(e)

    keys = list(groups.keys())
    random.shuffle(keys)

    n = len(keys)
    n_test = max(1, int(n*test_ratio))
    n_val  = max(1, int(n*val_ratio))

    test_keys = set(keys[:n_test])
    val_keys  = set(keys[n_test:n_test+n_val])
    train_keys= set(keys[n_test+n_val:])

    train = [e for k in train_keys for e in groups[k]]
    val   = [e for k in val_keys   for e in groups[k]]
    test  = [e for k in test_keys  for e in groups[k]]
    return train, val, test

def masked_mse(pred, y, mask):
    # pred,y: [N,C], mask:[N]
    m = mask.unsqueeze(1)  # [N,1]
    return ((pred - y)**2 * m).sum() / (m.sum() * y.size(1) + 1e-8)

def main():
    exps = load_experiments(DB_PATH)
    train_set, val_set, test_set = split_group(exps)

    model = GNNRegressor(in_dim=3, hidden=32, node_out=3)
    opt = optim.Adam(model.parameters(), lr=1e-3)
    mse = nn.MSELoss()

    best_val = 1e9
    for epoch in range(1, 51):
        model.train()
        total = 0.0
        for e in train_set:
            opt.zero_grad()
            node_pred, g_pred = model(e["A"], e["X"])
            loss_node = masked_mse(node_pred, e["Y"], e["mask"])
            loss_g    = mse(g_pred, e["gY"])
            loss = loss_node + 0.2*loss_g
            loss.backward()
            opt.step()
            total += float(loss.item())

        model.eval()
        with torch.no_grad():
            v = 0.0
            for e in val_set:
                node_pred, g_pred = model(e["A"], e["X"])
                v += float(masked_mse(node_pred, e["Y"], e["mask"]).item())
            v /= max(1, len(val_set))

        if v < best_val:
            best_val = v
            ckpt_path = os.path.join(ART_DIR, "gnn_v0.pt")
            torch.save(model.state_dict(), ckpt_path)
            with open(os.path.join(ART_DIR, "meta.json"), "w") as f:
                json.dump({"model_version":"gnn_v0_dummy", "best_val":best_val}, f)

        if epoch % 10 == 0:
            print(f"epoch {epoch:02d} train_loss={total/len(train_set):.4f} val_node_mse={v:.4f}")

    # quick test eval
    model.load_state_dict(torch.load(os.path.join(ART_DIR, "gnn_v0.pt")))
    model.eval()
    with torch.no_grad():
        t = 0.0
        for e in test_set:
            node_pred, _ = model(e["A"], e["X"])
            t += float(masked_mse(node_pred, e["Y"], e["mask"]).item())
        t /= max(1, len(test_set))
    print(f"✅ Test node MSE on unseen topology/load groups: {t:.4f}")

if __name__ == "__main__":
    main()
