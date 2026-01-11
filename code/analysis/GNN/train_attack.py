# import glob, json
# import numpy as np
# import torch
# import torch.nn as nn
# from pathlib import Path

# from GNN.attack_model import AttackGCN
from backoff_dataset import load_json, make_samples, F_DIM
from attack_model import AttackGCN


# def build_scaler(samples):
#     # fit on all node-features across training samples
#     Xall = np.concatenate([s.X for s in samples], axis=0)  # [(sum N), F]
#     mean = Xall.mean(axis=0)
#     std = Xall.std(axis=0) + 1e-6
#     return mean, std


# def apply_scaler(samples, mean, std):
#     for s in samples:
#         s.X = ((s.X - mean) / std).astype(np.float32)


# def load_folder(folder_glob: str, label: int,
#                 graph_len: int | None = 32, stride: int = 8):
#     """
#     Reads each JSON file -> creates one or many GraphSample(s)

#     graph_len:
#       - None => ONE graph per file using ALL windows (can be huge / variable)
#       - int  => sliding graphs of fixed length (recommended)
#     """
#     paths = sorted(glob.glob(folder_glob))
#     all_samples = []

#     for p in paths:
#         windows = load_json(p)  # ✅ list of window metric dicts

#         # ✅ Create graphs from windows
#         # window_s is unused now; kept for signature compatibility
#         all_samples.extend(
#             make_samples(
#                 windows,
#                 label=label,
#                 window_s=0.0,
#                 graph_len=graph_len,
#                 stride=stride
#             )
#         )

#     return all_samples


# def main():
#     # -------------------------
#     # 1) Load datasets
#     # -------------------------
#     # ✅ recommended: fixed-length temporal graphs
#     GRAPH_LEN = 32   # number of windows per graph (tune: 16/32/64)
#     STRIDE = 8       # overlap control

#     normal = load_folder("data/normal/*.json", label=0, graph_len=GRAPH_LEN, stride=STRIDE)
#     attack = load_folder("data/attack/*.json", label=1, graph_len=GRAPH_LEN, stride=STRIDE)
#     samples = normal + attack

#     if len(samples) == 0:
#         raise RuntimeError("No samples found. Check your data paths: data/normal/*.json and data/attack/*.json")

#     # -------------------------
#     # 2) Shuffle + split
#     # -------------------------
#     rng = np.random.default_rng(42)
#     idx = rng.permutation(len(samples))
#     samples = [samples[i] for i in idx]

#     n_train = int(0.8 * len(samples))
#     train_s, test_s = samples[:n_train], samples[n_train:]

#     # -------------------------
#     # 3) Scale features (fit on train only)
#     # -------------------------
#     mean, std = build_scaler(train_s)
#     apply_scaler(train_s, mean, std)
#     apply_scaler(test_s, mean, std)

#     # -------------------------
#     # 4) Torch setup
#     # -------------------------
#     device = "cpu"
#     model = AttackGCN(in_dim=F_DIM, hidden=32).to(device)   # ✅ 14-dim now
#     opt = torch.optim.Adam(model.parameters(), lr=1e-5)
#     loss_fn = nn.BCEWithLogitsLoss()

#     # -------------------------
#     # 5) Train
#     # -------------------------
#     for epoch in range(1, 25):
#         model.train()
#         total = 0.0

#         for s in train_s:
#             A = torch.tensor(s.A, dtype=torch.float32, device=device)
#             X = torch.tensor(s.X, dtype=torch.float32, device=device)
#             y = torch.tensor(float(s.y), dtype=torch.float32, device=device)

#             logit = model(A, X)
#             loss = loss_fn(logit, y)

#             opt.zero_grad()
#             loss.backward()
#             opt.step()
#             total += float(loss.item())

#         # -------------------------
#         # 6) Quick eval
#         # -------------------------
#         model.eval()
#         correct, n = 0, 0
#         with torch.no_grad():
#             for s in test_s:
#                 A = torch.tensor(s.A, dtype=torch.float32, device=device)
#                 X = torch.tensor(s.X, dtype=torch.float32, device=device)
#                 prob = torch.sigmoid(model(A, X)).item()
#                 pred = 1 if prob >= 0.5 else 0
#                 correct += int(pred == s.y)
#                 n += 1

#         acc = correct / max(n, 1)
#         print(f"epoch {epoch:02d}  train_loss={total/len(train_s):.4f}  test_acc={acc:.3f}")

#     # -------------------------
#     # 7) Save artifacts
#     # -------------------------
#     out_dir = Path("GNN/artifacts")
#     out_dir.mkdir(parents=True, exist_ok=True)

#     torch.save(model.state_dict(), out_dir / "attack_gnn_v1.pt")
#     with open(out_dir / "attack_gnn_v1_scaler.json", "w", encoding="utf-8") as f:
#         json.dump({"mean": mean.tolist(), "std": std.tolist()}, f, indent=2)

#     print("Saved:", out_dir / "attack_gnn_v1.pt")
#     print("Scaler:", out_dir / "attack_gnn_v1_scaler.json")


# if __name__ == "__main__":
#     main()


# import glob
# import json
# import numpy as np
# import torch
# import torch.nn as nn
# from pathlib import Path
# from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
# import matplotlib.pyplot as plt
# import re
# import copy
# from attack_model import AttackGCN


# def build_scaler(samples):
#     if not samples:
#         return np.zeros(F_DIM), np.ones(F_DIM)
#     Xall = np.concatenate([s.X for s in samples], axis=0)
#     mean = Xall.mean(axis=0)
#     std = Xall.std(axis=0) + 1e-6
#     return mean, std


# def apply_scaler(samples, mean, std):
#     for s in samples:
#         s.X = ((s.X - mean) / std).astype(np.float32)


# def get_label_from_filename(path):
#     """
#     Determines the class label from the file path.
#     - 0: Normal
#     - 1: Positive Bias Attack
#     - 2: Negative Bias Attack
#     """
#     if "normal" in str(path).lower():
#         return 0

#     filename = Path(path).name
#     # Use regex to find bias value
#     match = re.search(r'bias_([a-zA-Z]*)?(\d+)', filename)
#     if match:
#         sign = match.group(1)
#         if sign == "neg":
#             return 2  # Negative Bias Attack
#         else:
#             return 1  # Positive Bias Attack

#     # Fallback if pattern doesn't match
#     return 1 # Default to positive attack if unsure


# def process_and_split_file(path, label, graph_len, stride, topology='knn', k=5, split_ratio=0.8):
#     """
#     Loads ONE file, converts it to samples, and splits those samples 80/20.
#     """
#     try:
#         with open(path, 'r') as f:
#             windows = json.load(f)

#         file_samples = make_samples(
#             windows,
#             label=label,
#             window_s=0.0,
#             graph_len=graph_len,
#             stride=stride,
#             topology=topology,
#             k=k
#         )
#         cut_idx = int(len(file_samples) * split_ratio)
#         train_part = file_samples[:cut_idx]
#         test_part = file_samples[cut_idx:]
#         return train_part, test_part
#     except (json.JSONDecodeError, OSError) as e:
#         print(f"⚠️  WARNING: Skipping corrupted file: {path}")
#         return [], []


# def evaluate_model(model, samples, device, dataset_name="Test"):
#     model.eval()
#     y_true = []
#     y_pred = []

#     if len(samples) == 0:
#         print(f"⚠️  No samples in {dataset_name} set.")
#         return 0.0

#     with torch.no_grad():
#         for s in samples:
#             A = torch.tensor(s.A, dtype=torch.float32, device=device)
#             X = torch.tensor(s.X, dtype=torch.float32, device=device)

#             logits = model(A, X)
#             pred = torch.argmax(logits, dim=0).item()

#             y_true.append(s.y)
#             y_pred.append(pred)

#     print(f"\n{'='*20} {dataset_name} Set Results {'='*20}")

#     labels = [0, 1, 2]
#     target_names = ['Normal', 'Positive Attack', 'Negative Attack']

#     cm = confusion_matrix(y_true, y_pred, labels=labels)

#     print("\n--- Confusion Matrix ---")
#     print(cm)

#     print("\n--- Detailed Classification Report ---")
#     print(classification_report(y_true, y_pred, target_names=target_names, labels=labels, digits=4, zero_division=0))

#     return accuracy_score(y_true, y_pred)


# def main():
#     GRAPH_LEN = 32
#     STRIDE = 8
#     TOPOLOGY = 'knn' # 'knn' or 'chain'
#     K_NEIGHBORS = 5  # for knn

#     normal_files = sorted(glob.glob("data/normal/*.json"))
#     attack_files = sorted(glob.glob("data/attack/*.json"))

#     all_files = [(f, get_label_from_filename(f)) for f in normal_files] + \
#                 [(f, get_label_from_filename(f)) for f in attack_files]

#     print(f"Processing {len(normal_files)} Normal files and {len(attack_files)} Attack files...")
#     print(f"Using graph topology: {TOPOLOGY}" + (f" with k={K_NEIGHBORS}" if TOPOLOGY == 'knn' else ""))

#     train_s = []
#     test_s = []

#     for fpath, label in all_files:
#         tr, te = process_and_split_file(fpath, label, GRAPH_LEN, STRIDE, topology=TOPOLOGY, k=K_NEIGHBORS)
#         train_s.extend(tr)
#         test_s.extend(te)

#     rng = np.random.default_rng(42)
#     rng.shuffle(train_s)

#     # Address class imbalance using oversampling
#     class_counts = {i: sum(1 for s in train_s if s.y == i) for i in [0, 1, 2]}
#     print(f"Initial training set class counts: {class_counts}")

#     max_count = max(class_counts.values()) if class_counts else 0
#     if max_count > 0:
#         balanced_train_s = []
#         for i in range(3):
#             class_samples = [s for s in train_s if s.y == i]
#             if class_samples:
#                 oversampled = rng.choice(class_samples, size=max_count, replace=True)
#                 balanced_train_s.extend(oversampled)

#         train_s = balanced_train_s
#         rng.shuffle(train_s)
#         print(f"After oversampling, training set has {len(train_s)} samples.")

#     # Split train_s into training and validation
#     n_train = int(0.8 * len(train_s))
#     val_s = train_s[n_train:]
#     train_s = train_s[:n_train]

#     print(f"Final Dataset: {len(train_s)} Training samples, {len(val_s)} Validation samples, {len(test_s)} Test samples")

#     mean, std = build_scaler(train_s)
#     apply_scaler(train_s, mean, std)
#     apply_scaler(val_s, mean, std)
#     apply_scaler(test_s, mean, std)

#     device = "cpu"
#     model = AttackGCN(in_dim=F_DIM, hidden=32, n_classes=3).to(device)
#     opt = torch.optim.Adam(model.parameters(), lr=1e-2)
#     loss_fn = nn.CrossEntropyLoss()

#     # Early stopping parameters
#     patience = 10
#     min_delta = 0.001
#     best_val_loss = float('inf')
#     epochs_no_improve = 0
#     best_model_state = None

#     # For plotting
#     train_losses = []
#     val_losses = []
#     val_accuracies = []

#     print("\nStarting Training...")
#     for epoch in range(1, 151):
#         model.train()
#         total_loss = 0.0

#         for s in train_s:
#             A = torch.tensor(s.A, dtype=torch.float32, device=device)
#             X = torch.tensor(s.X, dtype=torch.float32, device=device)
#             y = torch.tensor(s.y, dtype=torch.long, device=device)

#             logits = model(A, X)
#             loss = loss_fn(logits.unsqueeze(0), y.unsqueeze(0))

#             opt.zero_grad()
#             loss.backward()
#             opt.step()
#             total_loss += float(loss.item())

#         avg_train_loss = total_loss / len(train_s)
#         train_losses.append(avg_train_loss)

#         # Validation loop
#         model.eval()
#         val_loss = 0.0
#         correct = 0
#         with torch.no_grad():
#             for s in val_s:
#                 A = torch.tensor(s.A, dtype=torch.float32, device=device)
#                 X = torch.tensor(s.X, dtype=torch.float32, device=device)
#                 y = torch.tensor(s.y, dtype=torch.long, device=device)

#                 logits = model(A, X)
#                 loss = loss_fn(logits.unsqueeze(0), y.unsqueeze(0))
#                 val_loss += float(loss.item())

#                 pred = torch.argmax(logits, dim=0).item()
#                 if pred == y.item():
#                     correct += 1

#         avg_val_loss = val_loss / len(val_s)
#         val_accuracy = correct / len(val_s)
#         val_losses.append(avg_val_loss)
#         val_accuracies.append(val_accuracy)

#         print(f"Epoch {epoch:02d} | Avg Train Loss: {avg_train_loss:.4f} | Avg Val Loss: {avg_val_loss:.4f} | Val Acc: {val_accuracy:.4f}")

#         # Early stopping check
#         if best_val_loss - avg_val_loss > min_delta:
#             best_val_loss = avg_val_loss
#             epochs_no_improve = 0
#             best_model_state = copy.deepcopy(model.state_dict())
#         else:
#             epochs_no_improve += 1

#         if epochs_no_improve >= patience:
#             print(f"\nEarly stopping triggered at epoch {epoch}. Best validation loss: {best_val_loss:.4f}")
#             break

#     # Load best model
#     if best_model_state:
#         model.load_state_dict(best_model_state)

#     evaluate_model(model, test_s, device, dataset_name="Final Test")

#     # Plotting
#     fig, ax1 = plt.subplots(figsize=(12, 6))

#     ax1.set_xlabel('Epochs')
#     ax1.set_ylabel('Loss', color='tab:blue')
#     ax1.plot(train_losses, label='Training Loss', color='tab:blue', linestyle='--')
#     ax1.plot(val_losses, label='Validation Loss', color='tab:blue')
#     ax1.tick_params(axis='y', labelcolor='tab:blue')

#     ax2 = ax1.twinx()
#     ax2.set_ylabel('Accuracy', color='tab:red')
#     ax2.plot(val_accuracies, label='Validation Accuracy', color='tab:red')
#     ax2.tick_params(axis='y', labelcolor='tab:red')

#     fig.tight_layout()
#     plt.title('Training and Validation Metrics')
#     fig.legend(loc='upper right', bbox_to_anchor=(0.9, 0.9))

#     out_dir = Path("GNN/artifacts")
#     out_dir.mkdir(parents=True, exist_ok=True)
#     plot_path = out_dir / "training_metrics.png"
#     plt.savefig(plot_path)
#     print(f"\nSaved training metrics plot to: {plot_path}")

#     torch.save(model.state_dict(), out_dir / "attack_gnn_v2_large_datasetV1.pt")
#     with open(out_dir / "attack_gnn_v2_large_datasetV1.json", "w") as f:
#         json.dump({"mean": mean.tolist(), "std": std.tolist()}, f)
#     print(f"\nSaved model to: {out_dir / 'attack_gnn_v2_large_datasetV1.pt'}")


# if __name__ == "__main__":
#     main()


# import glob
# import json
# import numpy as np
# import torch
# import torch.nn as nn
# from pathlib import Path
# from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
# import matplotlib.pyplot as plt
# import re
# import copy
# import sys

# # Ensure you import make_samples if it is in attack_model.py,
# # otherwise define it in this file.
# from attack_model import AttackGCN
# # from attack_model import make_samples  <-- UNCOMMENT THIS if make_samples is in that file

# # ---------------- CONFIGURATION ---------------- #
# # You must define F_DIM (Feature Dimension) based on your dataset
# F_DIM = 14  # Replace with the actual number of features in your JSON data

# def build_scaler(samples):
#     if not samples:
#         # Returns a dummy scaler if no samples exist to prevent crash
#         return np.zeros(F_DIM), np.ones(F_DIM)
#     Xall = np.concatenate([s.X for s in samples], axis=0)
#     mean = Xall.mean(axis=0)
#     std = Xall.std(axis=0) + 1e-6
#     return mean, std


# def apply_scaler(samples, mean, std):
#     for s in samples:
#         s.X = ((s.X - mean) / std).astype(np.float32)


# def get_label_from_filename(path):
#     """
#     Determines the class label from the file path using string matching.
#     - 0: Normal
#     - 1: Positive Bias Attack
#     - 2: Negative Bias Attack
#     """
#     # Convert filename to lowercase for easier matching
#     filename = Path(path).name.lower()

#     if "normal" in filename:
#         return 0
#     elif "negative" in filename:
#         return 2
#     elif "positive" in filename:
#         return 1

#     # Fallback if pattern doesn't match
#     print(f"⚠️  Warning: Could not identify label for {filename}, defaulting to Positive (1)")
#     return 1


# def process_and_split_file(path, label, graph_len, stride, topology='knn', k=5, split_ratio=0.8):
#     """
#     Loads ONE file, converts it to samples, and splits those samples 80/20.
#     """
#     try:
#         with open(path, 'r') as f:
#             windows = json.load(f)

#         # NOTE: Ensure make_samples is defined or imported!
#         if 'make_samples' not in globals():
#             raise NameError("The function 'make_samples' is missing. Please import or define it.")

#         file_samples = make_samples(
#             windows,
#             label=label,
#             window_s=0.0,
#             graph_len=graph_len,
#             stride=stride,
#             topology=topology,
#             k=k
#         )

#         if not file_samples:
#             return [], []

#         cut_idx = int(len(file_samples) * split_ratio)
#         train_part = file_samples[:cut_idx]
#         test_part = file_samples[cut_idx:]
#         return train_part, test_part

#     except (json.JSONDecodeError, OSError) as e:
#         print(f"⚠️  WARNING: Skipping corrupted file: {path}")
#         return [], []


# def evaluate_model(model, samples, device, dataset_name="Test"):
#     model.eval()
#     y_true = []
#     y_pred = []

#     if len(samples) == 0:
#         print(f"⚠️  No samples in {dataset_name} set.")
#         return 0.0

#     with torch.no_grad():
#         for s in samples:
#             A = torch.tensor(s.A, dtype=torch.float32, device=device)
#             X = torch.tensor(s.X, dtype=torch.float32, device=device)

#             logits = model(A, X)
#             pred = torch.argmax(logits, dim=0).item()

#             y_true.append(s.y)
#             y_pred.append(pred)

#     print(f"\n{'='*20} {dataset_name} Set Results {'='*20}")

#     labels = [0, 1, 2]
#     target_names = ['Normal', 'Positive Attack', 'Negative Attack']

#     # Handle cases where not all labels are present in the batch
#     present_labels = sorted(list(set(y_true) | set(y_pred)))

#     cm = confusion_matrix(y_true, y_pred, labels=labels)

#     print("\n--- Confusion Matrix ---")
#     print(cm)

#     print("\n--- Detailed Classification Report ---")
#     print(classification_report(y_true, y_pred, target_names=target_names, labels=labels, digits=4, zero_division=0))

#     return accuracy_score(y_true, y_pred)


# def main():
#     GRAPH_LEN = 32
#     STRIDE = 8
#     TOPOLOGY = 'knn'
#     K_NEIGHBORS = 5

#     # Updated paths to match your folder structure if running from 'my-gnn-code' folder
#     # Assuming script is run from: ~/FYP Project/my-gnn-code/
#     normal_path = "data/normal/*.json"
#     attack_path = "data/attack/*.json"

#     normal_files = sorted(glob.glob(normal_path))
#     attack_files = sorted(glob.glob(attack_path))

#     # --- ERROR CHECKING FOR PATHS ---
#     if not normal_files and not attack_files:
#         print(f"❌ ERROR: No files found!")
#         print(f"   Looking in: {Path(normal_path).absolute()}")
#         print("   Please check your current working directory using 'pwd'.")
#         return
#     # --------------------------------

#     all_files = [(f, get_label_from_filename(f)) for f in normal_files] + \
#                 [(f, get_label_from_filename(f)) for f in attack_files]

#     print(f"Processing {len(normal_files)} Normal files and {len(attack_files)} Attack files...")

#     train_s = []
#     test_s = []

#     for fpath, label in all_files:
#         tr, te = process_and_split_file(fpath, label, GRAPH_LEN, STRIDE, topology=TOPOLOGY, k=K_NEIGHBORS)
#         train_s.extend(tr)
#         test_s.extend(te)

#     if not train_s:
#         print("❌ Error: No training samples were generated. Check 'make_samples' or file contents.")
#         return

#     rng = np.random.default_rng(42)
#     rng.shuffle(train_s)

#     # Address class imbalance using oversampling
#     class_counts = {i: sum(1 for s in train_s if s.y == i) for i in [0, 1, 2]}
#     print(f"Initial training set class counts: {class_counts}")

#     max_count = max(class_counts.values()) if class_counts else 0
#     if max_count > 0:
#         balanced_train_s = []
#         for i in range(3):
#             class_samples = [s for s in train_s if s.y == i]
#             if class_samples:
#                 oversampled = rng.choice(class_samples, size=max_count, replace=True)
#                 balanced_train_s.extend(oversampled)

#         train_s = balanced_train_s
#         rng.shuffle(train_s)
#         print(f"After oversampling, training set has {len(train_s)} samples.")

#     # Split train_s into training and validation
#     n_train = int(0.8 * len(train_s))
#     val_s = train_s[n_train:]
#     train_s = train_s[:n_train]

#     print(f"Final Dataset: {len(train_s)} Training samples, {len(val_s)} Validation samples, {len(test_s)} Test samples")

#     mean, std = build_scaler(train_s)
#     apply_scaler(train_s, mean, std)
#     apply_scaler(val_s, mean, std)
#     apply_scaler(test_s, mean, std)

#     device = "cpu"
#     # Ensure F_DIM is passed correctly here
#     model = AttackGCN(in_dim=F_DIM, hidden=32, n_classes=3).to(device)
#     opt = torch.optim.Adam(model.parameters(), lr=1e-2)
#     loss_fn = nn.CrossEntropyLoss()

#     # Early stopping parameters
#     patience = 10
#     min_delta = 0.001
#     best_val_loss = float('inf')
#     epochs_no_improve = 0
#     best_model_state = None

#     # For plotting
#     train_losses = []
#     val_losses = []
#     val_accuracies = []

#     print("\nStarting Training...")
#     for epoch in range(1, 151):
#         model.train()
#         total_loss = 0.0

#         for s in train_s:
#             A = torch.tensor(s.A, dtype=torch.float32, device=device)
#             X = torch.tensor(s.X, dtype=torch.float32, device=device)
#             y = torch.tensor(s.y, dtype=torch.long, device=device)

#             logits = model(A, X)
#             loss = loss_fn(logits.unsqueeze(0), y.unsqueeze(0))

#             opt.zero_grad()
#             loss.backward()
#             opt.step()
#             total_loss += float(loss.item())

#         avg_train_loss = total_loss / len(train_s)
#         train_losses.append(avg_train_loss)

#         # Validation loop
#         model.eval()
#         val_loss = 0.0
#         correct = 0
#         with torch.no_grad():
#             for s in val_s:
#                 A = torch.tensor(s.A, dtype=torch.float32, device=device)
#                 X = torch.tensor(s.X, dtype=torch.float32, device=device)
#                 y = torch.tensor(s.y, dtype=torch.long, device=device)

#                 logits = model(A, X)
#                 loss = loss_fn(logits.unsqueeze(0), y.unsqueeze(0))
#                 val_loss += float(loss.item())

#                 pred = torch.argmax(logits, dim=0).item()
#                 if pred == y.item():
#                     correct += 1

#         avg_val_loss = val_loss / len(val_s) if len(val_s) > 0 else 0
#         val_accuracy = correct / len(val_s) if len(val_s) > 0 else 0
#         val_losses.append(avg_val_loss)
#         val_accuracies.append(val_accuracy)

#         print(f"Epoch {epoch:02d} | Avg Train Loss: {avg_train_loss:.4f} | Avg Val Loss: {avg_val_loss:.4f} | Val Acc: {val_accuracy:.4f}")

#         # Early stopping check
#         if best_val_loss - avg_val_loss > min_delta:
#             best_val_loss = avg_val_loss
#             epochs_no_improve = 0
#             best_model_state = copy.deepcopy(model.state_dict())
#         else:
#             epochs_no_improve += 1

#         if epochs_no_improve >= patience:
#             print(f"\nEarly stopping triggered at epoch {epoch}. Best validation loss: {best_val_loss:.4f}")
#             break

#     # Load best model
#     if best_model_state:
#         model.load_state_dict(best_model_state)

#     evaluate_model(model, test_s, device, dataset_name="Final Test")

#     # Plotting
#     fig, ax1 = plt.subplots(figsize=(12, 6))

#     ax1.set_xlabel('Epochs')
#     ax1.set_ylabel('Loss', color='tab:blue')
#     ax1.plot(train_losses, label='Training Loss', color='tab:blue', linestyle='--')
#     ax1.plot(val_losses, label='Validation Loss', color='tab:blue')
#     ax1.tick_params(axis='y', labelcolor='tab:blue')

#     ax2 = ax1.twinx()
#     ax2.set_ylabel('Accuracy', color='tab:red')
#     ax2.plot(val_accuracies, label='Validation Accuracy', color='tab:red')
#     ax2.tick_params(axis='y', labelcolor='tab:red')

#     fig.tight_layout()
#     plt.title('Training and Validation Metrics')
#     # Combine legends
#     lines_1, labels_1 = ax1.get_legend_handles_labels()
#     lines_2, labels_2 = ax2.get_legend_handles_labels()
#     ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right')

#     out_dir = Path("GNN/artifacts")
#     out_dir.mkdir(parents=True, exist_ok=True)
#     plot_path = out_dir / "training_metrics.png"
#     plt.savefig(plot_path)
#     print(f"\nSaved training metrics plot to: {plot_path}")

#     torch.save(model.state_dict(), out_dir / "attack_gnn_v2_large_datasetV1.pt")
#     with open(out_dir / "attack_gnn_v2_large_datasetV1.json", "w") as f:
#         json.dump({"mean": mean.tolist(), "std": std.tolist()}, f)
#     print(f"\nSaved model to: {out_dir / 'attack_gnn_v2_large_datasetV1.pt'}")


# if __name__ == "__main__":
#     main()


import glob
import json
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
import matplotlib.pyplot as plt
import re
import copy
import sys


# ---------------- IMPORTS ---------------- #
# Import the model from attack_model.py
from attack_model import AttackGCN

print(torch.cuda.is_available())  # Should print True
print(torch.cuda.get_device_name(0))  # Should print your GPU name
# Import the data processing function from backoff_dataset.py
# This fixes the "ImportError: cannot import name make_samples"
try:
    from backoff_dataset import make_samples
except ImportError:
    print("❌ ERROR: Could not import 'make_samples' from 'backoff_dataset.py'.")
    print("   Make sure backoff_dataset.py is in the same folder as this script.")
    sys.exit(1)

# ---------------- CONFIGURATION ---------------- #
F_DIM = 14  # Matches the 14 features in your dataset
# ----------------------------------------------- #


def build_scaler(samples):
    if not samples:
        return np.zeros(F_DIM), np.ones(F_DIM)
    Xall = np.concatenate([s.X for s in samples], axis=0)
    mean = Xall.mean(axis=0)
    std = Xall.std(axis=0) + 1e-6
    return mean, std


def apply_scaler(samples, mean, std):
    for s in samples:
        s.X = ((s.X - mean) / std).astype(np.float32)


def get_label_from_filename(path):
    """
    Determines the class label from the file path.
    0: Normal, 1: Positive, 2: Negative
    """
    filename = Path(path).name.lower()

    if "normal" in filename:
        return 0
    elif "negative" in filename:
        return 2
    elif "positive" in filename:
        return 1

    print(
        f"⚠️  Warning: Could not identify label for {filename}, defaulting to Positive (1)")
    return 1


def process_and_split_file(path, label, graph_len, stride, topology='knn', k=5, split_ratio=0.8):
    try:
        with open(path, 'r') as f:
            windows = json.load(f)

        if not windows:
            return [], []

        # Calls make_samples from backoff_dataset.py
        file_samples = make_samples(
            windows,
            label=label,
            window_s=0.0,
            graph_len=graph_len,
            stride=stride,
            topology=topology,
            k=k
        )

        if not file_samples:
            return [], []

        cut_idx = int(len(file_samples) * split_ratio)
        train_part = file_samples[:cut_idx]
        test_part = file_samples[cut_idx:]
        return train_part, test_part

    except (json.JSONDecodeError, OSError):
        print(f"⚠️  WARNING: Skipping corrupted file: {path}")
        return [], []


def evaluate_model(model, samples, device, dataset_name="Test"):
    model.eval()
    y_true = []
    y_pred = []

    if len(samples) == 0:
        print(f"⚠️  No samples in {dataset_name} set.")
        return 0.0

    with torch.no_grad():
        for s in samples:
            A = torch.tensor(s.A, dtype=torch.float32, device=device)
            X = torch.tensor(s.X, dtype=torch.float32, device=device)

            logits = model(A, X)
            pred = torch.argmax(logits, dim=0).item()

            y_true.append(s.y)
            y_pred.append(pred)

    print(f"\n{'='*20} {dataset_name} Set Results {'='*20}")

    labels = [0, 1, 2]
    target_names = ['Normal', 'Positive Attack', 'Negative Attack']

    # Handle cases where not all labels are present
    present_labels = sorted(list(set(y_true) | set(y_pred)))

    cm = confusion_matrix(y_true, y_pred, labels=labels)

    print("\n--- Confusion Matrix ---")
    print(cm)

    print("\n--- Detailed Classification Report ---")
    print(classification_report(y_true, y_pred, target_names=target_names,
          labels=labels, digits=4, zero_division=0))

    return accuracy_score(y_true, y_pred)


def main():
    GRAPH_LEN = 32
    STRIDE = 8
    TOPOLOGY = 'knn'
    K_NEIGHBORS = 5

    normal_path = "../data/normal/*.json"
    attack_path = "../data/attack/*.json"

    normal_files = sorted(glob.glob(normal_path))
    attack_files = sorted(glob.glob(attack_path))

    if not normal_files and not attack_files:
        print(f"❌ ERROR: No files found in data/normal/ or data/attack/")
        return

    all_files = [(f, get_label_from_filename(f)) for f in normal_files] + \
                [(f, get_label_from_filename(f)) for f in attack_files]

    print(
        f"Processing {len(normal_files)} Normal files and {len(attack_files)} Attack files...")

    train_s = []
    test_s = []

    for fpath, label in all_files:
        tr, te = process_and_split_file(
            fpath, label, GRAPH_LEN, STRIDE, topology=TOPOLOGY, k=K_NEIGHBORS)
        train_s.extend(tr)
        test_s.extend(te)

    if not train_s:
        print("❌ Error: No training samples generated.")
        return

    rng = np.random.default_rng(42)
    rng.shuffle(train_s)

    # Oversampling to balance classes
    class_counts = {i: sum(1 for s in train_s if s.y == i) for i in [0, 1, 2]}
    print(f"Initial training set class counts: {class_counts}")

    max_count = max(class_counts.values()) if class_counts else 0
    if max_count > 0:
        balanced_train_s = []
        for i in range(3):
            class_samples = [s for s in train_s if s.y == i]
            if class_samples:
                oversampled = rng.choice(
                    class_samples, size=max_count, replace=True)
                balanced_train_s.extend(oversampled)

        train_s = balanced_train_s
        rng.shuffle(train_s)
        print(f"After oversampling, training set has {len(train_s)} samples.")

    # Split train/val
    n_train = int(0.8 * len(train_s))
    val_s = train_s[n_train:]
    train_s = train_s[:n_train]

    print(
        f"Final Dataset: {len(train_s)} Training, {len(val_s)} Validation, {len(test_s)} Test")

    mean, std = build_scaler(train_s)
    apply_scaler(train_s, mean, std)
    apply_scaler(val_s, mean, std)
    apply_scaler(test_s, mean, std)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    # Initialize model with F_DIM=14
    model = AttackGCN(in_dim=F_DIM, hidden=32, n_classes=3).to(device)

    # Optimizer (Adjusted LR to 0.001 for stability)
    opt = torch.optim.Adam(model.parameters(), lr=0.001)
    loss_fn = nn.CrossEntropyLoss()

    # Training Loop
    patience = 10
    min_delta = 0.001
    best_val_loss = float('inf')
    epochs_no_improve = 0
    best_model_state = None

    train_losses = []
    val_losses = []
    val_accuracies = []

    print("\nStarting Training...")
    for epoch in range(1, 151):
        model.train()
        total_loss = 0.0

        for s in train_s:
            A = torch.tensor(s.A, dtype=torch.float32, device=device)
            X = torch.tensor(s.X, dtype=torch.float32, device=device)
            y = torch.tensor(s.y, dtype=torch.long, device=device)

            logits = model(A, X)
            loss = loss_fn(logits.unsqueeze(0), y.unsqueeze(0))

            opt.zero_grad()
            loss.backward()
            opt.step()
            total_loss += float(loss.item())

        avg_train_loss = total_loss / len(train_s)
        train_losses.append(avg_train_loss)

        # Validation
        model.eval()
        val_loss = 0.0
        correct = 0
        with torch.no_grad():
            for s in val_s:
                A = torch.tensor(s.A, dtype=torch.float32, device=device)
                X = torch.tensor(s.X, dtype=torch.float32, device=device)
                y = torch.tensor(s.y, dtype=torch.long, device=device)

                logits = model(A, X)
                loss = loss_fn(logits.unsqueeze(0), y.unsqueeze(0))
                val_loss += float(loss.item())

                pred = torch.argmax(logits, dim=0).item()
                if pred == y.item():
                    correct += 1

        avg_val_loss = val_loss / len(val_s) if len(val_s) > 0 else 0
        val_accuracy = correct / len(val_s) if len(val_s) > 0 else 0
        val_losses.append(avg_val_loss)
        val_accuracies.append(val_accuracy)

        print(f"Epoch {epoch:02d} | Avg Train Loss: {avg_train_loss:.4f} | Avg Val Loss: {avg_val_loss:.4f} | Val Acc: {val_accuracy:.4f}")

        if best_val_loss - avg_val_loss > min_delta:
            best_val_loss = avg_val_loss
            epochs_no_improve = 0
            best_model_state = copy.deepcopy(model.state_dict())
        else:
            epochs_no_improve += 1

        if epochs_no_improve >= patience:
            print(
                f"\nEarly stopping triggered at epoch {epoch}. Best validation loss: {best_val_loss:.4f}")
            break

    if best_model_state:
        model.load_state_dict(best_model_state)

    evaluate_model(model, test_s, device, dataset_name="Final Test")

    # ------------------- SMOOTH PLOTTING ------------------- #
    def smooth_curve(points, factor=0.8):
        """Exponential Moving Average for smoothing"""
        smoothed_points = []
        for point in points:
            if smoothed_points:
                previous = smoothed_points[-1]
                smoothed_points.append(
                    previous * factor + point * (1 - factor))
            else:
                smoothed_points.append(point)
        return smoothed_points

    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.grid(True, linestyle='--', alpha=0.6)

    ax1.set_xlabel('Epochs', fontsize=12)
    ax1.set_ylabel('Loss', color='tab:blue', fontsize=12)

    # Plot Raw Data (Light)
    ax1.plot(train_losses, color='tab:blue', alpha=0.3,
             linewidth=1, label='Train Loss (Raw)')
    ax1.plot(val_losses, color='tab:cyan', alpha=0.3,
             linewidth=1, label='Val Loss (Raw)')

    # Plot Smoothed Data (Solid/Dark)
    ax1.plot(smooth_curve(train_losses), color='tab:blue',
             linewidth=2, label='Train Loss (Smooth)')
    ax1.plot(smooth_curve(val_losses), color='tab:cyan',
             linewidth=2, linestyle='--', label='Val Loss (Smooth)')

    ax1.tick_params(axis='y', labelcolor='tab:blue')
    ax1.legend(loc='upper left', bbox_to_anchor=(0, 1))

    # Second Y-axis for Accuracy
    ax2 = ax1.twinx()
    ax2.set_ylabel('Accuracy', color='tab:red', fontsize=12)

    ax2.plot(val_accuracies, color='tab:red', alpha=0.3,
             linewidth=1, label='Val Acc (Raw)')
    ax2.plot(smooth_curve(val_accuracies), color='tab:red',
             linewidth=2, label='Val Acc (Smooth)')

    ax2.tick_params(axis='y', labelcolor='tab:red')
    ax2.legend(loc='upper right', bbox_to_anchor=(1, 1))

    plt.title('Training Metrics (Smoothed)', fontsize=14)
    fig.tight_layout()
    # ---------------------------------------------------------------- #

    out_dir = Path("GNN/artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_path = out_dir / "training_metrics.png"
    plt.savefig(plot_path, dpi=300)
    print(f"\nSaved clean training metrics plot to: {plot_path}")

    torch.save(model.state_dict(), out_dir /
               "attack_gnn_v2_large_datasetV3.pt")
    with open(out_dir / "attack_gnn_v2_large_datasetV3.json", "w") as f:
        json.dump({"mean": mean.tolist(), "std": std.tolist()}, f)
    print(f"\nSaved model to: {out_dir / 'attack_gnn_v2_large_datasetV3.pt'}")


if __name__ == "__main__":
    main()
