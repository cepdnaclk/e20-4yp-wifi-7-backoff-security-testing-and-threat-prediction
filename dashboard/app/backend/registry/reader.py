import os
import yaml
import json
import pathlib
from datetime import datetime
from typing import Optional


def get_registry_path() -> pathlib.Path:
    env_path = os.getenv("GCN_REGISTRY_PATH", "/app/registry")
    return pathlib.Path(env_path)


def get_active_version(registry_path: pathlib.Path) -> Optional[str]:
    current_link = registry_path / "current"
    if current_link.is_symlink():
        target = current_link.resolve()
        return target.name
    if current_link.is_file():
        return current_link.read_text().strip()
    # Fallback: find latest version directory
    versions = list_versions(registry_path)
    return versions[-1] if versions else None


def list_versions(registry_path: pathlib.Path):
    versions = []
    if not registry_path.exists():
        return versions
    for item in sorted(registry_path.iterdir()):
        if item.is_dir() and item.name.startswith("v"):
            versions.append(item.name)
    return sorted(versions)


def read_version(registry_path: pathlib.Path, version: str) -> dict:
    version_path = registry_path / version
    if not version_path.exists():
        return {}

    result: dict = {"version": version, "has_test_results": False}

    # Read config.yaml
    config_path = version_path / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
            model_cfg = config.get("model", config)
            train_cfg = config.get("training", {})
            data_cfg = config.get("data", {})

            result["architecture"] = {
                "in_channels": model_cfg.get("in_channels", 16),
                "hidden_channels": model_cfg.get("hidden_channels", 64),
                "num_layers": model_cfg.get("num_layers", 2),
                "dropout": model_cfg.get("dropout", 0.3),
                "pooling": model_cfg.get("pooling", "mean"),
                "segment_length": model_cfg.get(
                    "segment_length", train_cfg.get("segment_length", 256)
                ),
                "batch_size": train_cfg.get("batch_size", 32),
            }
            result["dataset"] = data_cfg.get("root", config.get("dataset", "unknown"))
            result["scenarios"] = config.get("num_scenarios", config.get("scenarios", None))
            result["distribution"] = config.get("distribution", "balanced")
        except Exception:
            pass

    # Read test_results.json
    results_path = version_path / "test_results.json"
    if results_path.exists():
        try:
            with open(results_path) as f:
                test_results = json.load(f)
            result["test_results"] = test_results
            result["has_test_results"] = True
        except Exception:
            pass

    # Try to get creation time from file
    try:
        stat = config_path.stat() if config_path.exists() else version_path.stat()
        result["created"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
    except Exception:
        result["created"] = None

    return result
