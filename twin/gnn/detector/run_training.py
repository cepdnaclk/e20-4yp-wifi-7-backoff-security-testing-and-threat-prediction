"""
GCN v3 Training Entrypoint.

Usage:
    python run_training.py --config /config/training_v3.yaml \
                           --data-root /data \
                           --output-dir /output
"""
import argparse
import sys
from pathlib import Path

from gcn_src.training.config import TrainingConfig
from gcn_src.training.train import train_wifi7_gcn


def parse_args():
    p = argparse.ArgumentParser(description="Train WiFi7 GCN attack detector")
    p.add_argument("--config", type=Path, help="Path to training YAML config")
    p.add_argument("--data-root", type=Path, help="Override data_root path")
    p.add_argument("--output-dir", type=Path, help="Override checkpoint/log output dir")
    p.add_argument("--device", type=str, help="Override device (cuda/cpu)")
    return p.parse_args()


def main():
    args = parse_args()

    if args.config and args.config.exists():
        print(f"Loading config from: {args.config}")
        import yaml
        with open(args.config) as f:
            raw = yaml.safe_load(f)
        # Strip fields not in TrainingConfig (e.g. 'version', 'pooling' comment fields)
        known = {f.name for f in TrainingConfig.__dataclass_fields__.values()}
        raw = {k: v for k, v in raw.items() if k in known}
        config = TrainingConfig(**raw)
    else:
        print("No config file provided — using default TrainingConfig (v3 defaults)")
        config = TrainingConfig()

    if args.data_root:
        config.data_root = args.data_root
    if args.output_dir:
        config.checkpoint_dir = args.output_dir / "checkpoints"
        config.log_dir = args.output_dir / "logs"
    if args.device:
        config.device = args.device

    print(f"\nConfig:\n{config}\n")

    model, test_metrics = train_wifi7_gcn(config)

    # Copy best_model.pt and scaler.json to output root for easy deployment
    if args.output_dir:
        import shutil, json
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        src_ckpt = config.checkpoint_dir / "best_model.pt"
        src_scaler = config.checkpoint_dir / "scaler.json"
        src_results = config.checkpoint_dir / "test_results.json"
        src_cfg = config.checkpoint_dir / "config.yaml"
        for src in [src_ckpt, src_scaler, src_results, src_cfg]:
            if src.exists():
                shutil.copy(src, out / src.name)
                print(f"Copied {src.name} → {out / src.name}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
