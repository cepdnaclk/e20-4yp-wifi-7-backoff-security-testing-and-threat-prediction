"""
GCN v4 Training Pipeline — Dynamic Generalization.

Separate from train.py (v3).  Uses:
- WiFi7AttackDatasetV4  (per-segment dynamic labeling, 30% attack threshold)
- load_v4_files         (pre-partitioned seed-pool folders, no random split)
- Same GCN model class  (wider: hidden=128, deeper: 3 layers)
- Same training loop    (AdamW + ReduceLROnPlateau + early stopping)
"""

import json
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import torch
from tqdm import tqdm
from torch_geometric.loader import DataLoader

from ..models.gcn import WiFi7AttackGCN
from ..data.dataset_v4 import (
    WiFi7AttackDatasetV4,
    create_v4_datasets_with_scaler,
    load_v4_files,
)
from .config import TrainingConfig
from .metrics import (
    compute_class_weights,
    compute_metrics,
    evaluate_model,
    plot_confusion_matrix,
    plot_training_history,
    print_metrics,
)


def train_epoch(model, loader, optimizer, criterion, device):
    model.train()
    total_loss = 0.0
    n = 0
    for data in tqdm(loader, desc="Training", leave=False):
        data = data.to(device)
        optimizer.zero_grad()
        out = model(data.x, data.edge_index, data.batch)
        loss = criterion(out, data.y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * data.num_graphs
        n += data.num_graphs
    return total_loss / n


def train_wifi7_gcn_v4(config: TrainingConfig) -> Tuple[WiFi7AttackGCN, Dict]:
    """
    Full v4 training pipeline.

    Key differences vs v3 (train.py):
    - Reads pre-partitioned v4 folder structure (train/val/test) via seed pools
    - Uses WiFi7AttackDatasetV4 with dynamic majority-vote labeling (threshold=0.3)
    - Supports Dynamic/ files where bias changes per window
    - Architecture: hidden=128, 3 layers (configured via TrainingConfig)
    """
    print("=" * 70)
    print("WiFi 7 GCN v4 — Dynamic Generalization Training")
    print("=" * 70)

    torch.manual_seed(config.random_seed)
    np.random.seed(config.random_seed)

    device = torch.device(config.device if config.device else
                          ("cuda" if torch.cuda.is_available() else "cpu"))
    print(f"\nDevice: {device}")

    config.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    config.log_dir.mkdir(parents=True, exist_ok=True)

    # ── Load pre-partitioned file lists ───────────────────────────────────
    print("\n" + "=" * 70)
    print("LOADING PRE-PARTITIONED V4 DATA")
    print("=" * 70)

    train_files, val_files, test_files = load_v4_files(config.data_root)

    if not train_files:
        raise RuntimeError(
            f"No training files found under {config.data_root}/train/. "
            "Run data collection first: make gcn-collect-v4 SPLIT=train"
        )

    # Attack-bias threshold from config (default 0.3 if not set)
    dyn_threshold = getattr(config, "dynamic_label_threshold", 0.3)

    # ── Create datasets across all segment lengths ─────────────────────────
    print("\n" + "=" * 70)
    print("CREATING V4 DATASETS")
    print("=" * 70)

    seg_lengths = config.segment_lengths if config.segment_lengths else [config.segment_length]
    print(f"Segment lengths: {seg_lengths}")
    print(f"Dynamic label threshold: {dyn_threshold} (attack if >{dyn_threshold*100:.0f}% windows are attack)")

    all_splits: list = []
    for seg_len in seg_lengths:
        stride = config.segment_strides.get(seg_len, seg_len)
        print(f"\n  seg_len={seg_len}, stride={stride}")
        tr, va, te, sc = create_v4_datasets_with_scaler(
            train_files, val_files, test_files,
            segment_length=seg_len,
            stride=stride,
            use_derived_features=config.use_derived_features,
            multi_ap_normalise=config.multi_ap_normalise,
            dynamic_label_threshold=dyn_threshold,
        )
        all_splits.append((tr, va, te, sc))
        print(f"    → train={len(tr)}, val={len(va)}, test={len(te)} segments")

    # Merge all segment lengths into combined datasets
    train_ds, val_ds, test_ds, scaler = all_splits[0]
    for tr_x, va_x, te_x, _ in all_splits[1:]:
        train_ds.samples.extend(tr_x.samples)
        val_ds.samples.extend(va_x.samples)
        test_ds.samples.extend(te_x.samples)

    print(f"\nTotal segments (all lengths):")
    print(f"  Train : {len(train_ds)}")
    print(f"  Val   : {len(val_ds)}")
    print(f"  Test  : {len(test_ds)}")

    d = train_ds.get_class_distribution()
    print(f"\nTrain class distribution:")
    print(f"  Normal : {d['normal']['count']} ({d['normal']['pct']:.1f}%)")
    print(f"  Attack : {d['attack']['count']} ({d['attack']['pct']:.1f}%)")

    train_loader = DataLoader(train_ds, batch_size=config.batch_size, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=config.batch_size, shuffle=False)
    test_loader  = DataLoader(test_ds,  batch_size=config.batch_size, shuffle=False)

    # ── Model ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("INITIALIZING MODEL")
    print("=" * 70)

    model = WiFi7AttackGCN(
        in_channels=config.in_channels,
        hidden_channels=config.hidden_channels,
        num_layers=config.num_layers,
        dropout=config.dropout,
        pooling=config.pooling,
    ).to(device)

    print(model)
    print(f"\nTotal parameters: {model.count_parameters():,}")

    # ── Loss & optimizer ───────────────────────────────────────────────────
    if config.use_class_weights:
        train_labels = [data.y.item() for data in train_ds]
        class_weights = compute_class_weights(train_labels).to(device)
        criterion = torch.nn.CrossEntropyLoss(weight=class_weights)
        print(f"\nClass weights: {class_weights.cpu().numpy()}")
    else:
        criterion = torch.nn.CrossEntropyLoss()

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=10
    )

    # ── Training loop ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("TRAINING")
    print("=" * 70)

    best_val_f1 = 0.0
    patience_counter = 0
    history = {"train_loss": [], "val_metrics": []}

    for epoch in range(1, config.max_epochs + 1):
        train_loss = train_epoch(model, train_loader, optimizer, criterion, device)
        val_metrics = evaluate_model(model, val_loader, device)
        scheduler.step(val_metrics["f1"])

        history["train_loss"].append(train_loss)
        history["val_metrics"].append(val_metrics)

        print(
            f"Epoch {epoch:03d}/{config.max_epochs} | "
            f"Loss: {train_loss:.4f} | "
            f"Val F1: {val_metrics['f1']:.4f} | "
            f"Val Acc: {val_metrics['accuracy']:.4f} | "
            f"Val AUC: {val_metrics['auc']:.4f}"
        )

        if val_metrics["f1"] > best_val_f1:
            best_val_f1 = val_metrics["f1"]
            patience_counter = 0
            checkpoint = {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_f1": best_val_f1,
                "config": config.to_dict(),
            }
            torch.save(checkpoint, config.checkpoint_dir / "best_model.pt")

            scaler_dict = {"mean": scaler.mean_.tolist(), "std": scaler.scale_.tolist()}
            with open(config.checkpoint_dir / "scaler.json", "w") as f:
                json.dump(scaler_dict, f, indent=2)

            print(f"  ✓ Saved best model (Val F1: {best_val_f1:.4f})")
        else:
            patience_counter += 1

        if patience_counter >= config.patience:
            print(f"\n⚠ Early stopping at epoch {epoch} (patience {config.patience})")
            break

    # ── Test ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("TESTING WITH BEST MODEL")
    print("=" * 70)

    ckpt = torch.load(config.checkpoint_dir / "best_model.pt")
    model.load_state_dict(ckpt["model_state_dict"])
    print(f"Loaded best model from epoch {ckpt['epoch']} (Val F1: {ckpt['val_f1']:.4f})")

    test_metrics = evaluate_model(model, test_loader, device)
    print_metrics(test_metrics, prefix="TEST")

    # ── Save results ───────────────────────────────────────────────────────
    test_results = {
        "accuracy": float(test_metrics["accuracy"]),
        "precision": float(test_metrics["precision"]),
        "recall": float(test_metrics["recall"]),
        "f1": float(test_metrics["f1"]),
        "auc": float(test_metrics["auc"]),
        "confusion_matrix": test_metrics["confusion_matrix"].tolist(),
        "best_epoch": int(ckpt["epoch"]),
        "best_val_f1": float(ckpt["val_f1"]),
        "dynamic_label_threshold": dyn_threshold,
    }
    with open(config.checkpoint_dir / "test_results.json", "w") as f:
        json.dump(test_results, f, indent=2)

    plot_confusion_matrix(
        test_metrics["confusion_matrix"],
        save_path=str(config.log_dir / "confusion_matrix.png"),
        title="Test Set Confusion Matrix (v4)",
    )
    plot_training_history(
        history["train_loss"],
        history["val_metrics"],
        save_path=str(config.log_dir / "training_history.png"),
    )
    config.save(config.checkpoint_dir / "config.yaml")

    print("\n" + "=" * 70)
    print("V4 TRAINING COMPLETE")
    print("=" * 70)
    print(f"Best Val F1 : {best_val_f1:.4f}")
    print(f"Test F1     : {test_metrics['f1']:.4f}")
    print(f"Test Recall : {test_metrics['recall']:.4f}  ← Attacks detected")
    print(f"Test AUC    : {test_metrics['auc']:.4f}")
    print("=" * 70)

    return model, test_metrics
