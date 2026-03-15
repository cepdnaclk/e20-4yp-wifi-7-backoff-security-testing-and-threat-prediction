"""
GCN v4 Training Entrypoint — Dynamic Generalization.

Usage:
    python run_training_v4.py --config /config/training_v4.yaml \
                               --data-root /data \
                               --output-dir /output

Reads pre-partitioned v4 data from:
    <data-root>/train/Static/Normal/*.json
    <data-root>/train/Static/Attack/*.json
    <data-root>/train/Dynamic/*.json
    <data-root>/val/...
    <data-root>/test/...

Does NOT use v3 training code (train.py / dataset.py).
"""

import argparse
import shutil
import sys
from pathlib import Path

from gcn_src.training.config import TrainingConfig
from gcn_src.training.train_v4 import train_wifi7_gcn_v4


_V4_EXTRA_FIELDS = {"dynamic_label_threshold", "split_mode", "version"}


def parse_args():
    p = argparse.ArgumentParser(description="Train WiFi7 GCN v4 (dynamic generalization)")
    p.add_argument("--config",      type=Path, help="Path to training_v4.yaml")
    p.add_argument("--data-root",   type=Path, help="Override data_root")
    p.add_argument("--output-dir",  type=Path, help="Output directory for model artifacts")
    p.add_argument("--device",      type=str,  help="Override device (cuda/cpu)")
    p.add_argument("--threshold",   type=float, help="Override dynamic_label_threshold")
    return p.parse_args()


def main():
    args = parse_args()

    if args.config and args.config.exists():
        print(f"Loading config: {args.config}")
        import yaml
        with open(args.config) as f:
            raw = yaml.safe_load(f)

        # Keep only fields known to TrainingConfig; stash v4-specific extras
        known = set(TrainingConfig.__dataclass_fields__)
        extra = {k: v for k, v in raw.items() if k not in known}
        raw   = {k: v for k, v in raw.items() if k in known}

        config = TrainingConfig(**raw)
        # Attach extra v4 fields as plain attributes
        for k, v in extra.items():
            setattr(config, k, v)
    else:
        print("No config — using default TrainingConfig with v4 defaults")
        config = TrainingConfig(
            hidden_channels=128,
            num_layers=3,
            dropout=0.4,
            batch_size=64,
            learning_rate=0.0005,
            max_epochs=300,
            patience=30,
        )

    # CLI overrides
    if args.data_root:
        config.data_root = args.data_root
    if args.output_dir:
        config.checkpoint_dir = args.output_dir / "checkpoints"
        config.log_dir        = args.output_dir / "logs"
    if args.device:
        config.device = args.device
    if args.threshold is not None:
        config.dynamic_label_threshold = args.threshold

    # Ensure dynamic_label_threshold has a value
    if not hasattr(config, "dynamic_label_threshold"):
        config.dynamic_label_threshold = 0.3

    print(f"\nConfig: {config}\n")
    print(f"Dynamic label threshold: {config.dynamic_label_threshold}")

    model, test_metrics = train_wifi7_gcn_v4(config)

    # Copy artifacts to output root
    if args.output_dir:
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        for fname in ["best_model.pt", "scaler.json", "test_results.json", "config.yaml"]:
            src = config.checkpoint_dir / fname
            if src.exists():
                shutil.copy(src, out / fname)
                print(f"Copied {fname} → {out / fname}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
