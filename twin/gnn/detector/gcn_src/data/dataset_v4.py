"""
GCN v4 Dataset — Dynamic Generalization.

This module provides WiFi7AttackDatasetV4, a new dataset class separate from
the v3 WiFi7AttackDataset.  It adds:

1. Dynamic file support — per-segment majority-vote labeling for files in
   Dynamic/ folders (bias changes per window mid-simulation).
2. Attack-biased labeling threshold — default 0.3 means a segment is labeled
   Attack if >30% of its windows have |bias| > 0.  This gives higher recall
   on transition segments and weak attacks.
3. Folder-based split loading — reads pre-partitioned train/val/test directories
   (no random splitting needed; leakage is controlled at data-generation time
   via seed pools).

v3 code (dataset.py, splits.py, train.py) is NOT modified.
"""

import json
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import torch
from sklearn.preprocessing import StandardScaler
from torch_geometric.data import Dataset, Data

from .preprocessing import (
    BASE_FEATURE_KEYS,
    DERIVED_FEATURE_KEYS,
    add_derived_features,
    convert_to_deltas,
    extract_features,
    get_label_from_segment_dynamic,
    segment_windows,
)


class WiFi7AttackDatasetV4(Dataset):
    """
    GCN v4 dataset.  Handles both static and dynamic training files.

    Static files (Static/Normal/, Static/Attack/):
        All windows have the same bias — label determined by parent folder name.
        Normal/ → 0, Attack/ → 1.

    Dynamic files (Dynamic/):
        Bias changes per window.  Each segment is labeled independently via
        majority-vote: Attack if fraction of windows with |bias|>0 > threshold.

    Args:
        root            : Root directory (PyG compatibility).
        file_list       : List of Path objects to process.
        segment_length  : Windows per segment.
        stride          : Segmentation stride (None = non-overlapping).
        scaler          : StandardScaler fitted on train data only.
        use_derived_features : Include ratio-based derived features.
        multi_ap_normalise   : Per-AP/per-STA normalisation.
        dynamic_label_threshold : Fraction of attack windows to call a
                                   dynamic segment an Attack.  Default 0.3
                                   gives more bias toward attack detection.
    """

    def __init__(
        self,
        root: str,
        file_list: List[Path],
        segment_length: int = 256,
        stride: Optional[int] = None,
        scaler: Optional[StandardScaler] = None,
        use_derived_features: bool = True,
        multi_ap_normalise: bool = True,
        dynamic_label_threshold: float = 0.3,
        transform=None,
        pre_transform=None,
    ):
        self.file_list = file_list
        self.segment_length = segment_length
        self.stride = stride if stride is not None else segment_length
        self.scaler = scaler
        self.use_derived_features = use_derived_features
        self.multi_ap_normalise = multi_ap_normalise
        self.dynamic_label_threshold = dynamic_label_threshold

        self.feature_keys = BASE_FEATURE_KEYS.copy()
        if use_derived_features:
            self.feature_keys.extend(DERIVED_FEATURE_KEYS)
        assert "bias" not in self.feature_keys, "bias must NEVER be a feature"

        # +1 for the segment-length conditioning feature
        self.in_channels = len(self.feature_keys) + 1

        print(f"Loading {len(file_list)} files (seg_len={segment_length}, "
              f"dyn_threshold={dynamic_label_threshold})...")
        self.samples = self._preprocess_files()
        print(f"Created {len(self.samples)} graph samples")

        super().__init__(root, transform, pre_transform)

    # ──────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _is_dynamic(file_path: Path) -> bool:
        """Return True if this file lives inside a Dynamic/ directory."""
        return any(part == "Dynamic" for part in file_path.parts)

    @staticmethod
    def _static_label_from_folder(file_path: Path) -> int:
        """
        Determine label for a static file from its parent folder name.
        Normal/ → 0, Attack/ → 1.
        Falls back to bias-based labeling if folder name is unexpected.
        """
        for part in reversed(file_path.parts):
            if part == "Normal":
                return 0
            if part == "Attack":
                return 1
        # Unexpected layout — return unknown sentinel; caller will skip
        return -1

    def _preprocess_files(self) -> list:
        samples = []

        for file_path in self.file_list:
            try:
                with open(file_path, "r") as f:
                    windows = json.load(f)

                if len(windows) < self.segment_length:
                    print(f"  Skip {file_path.name}: only {len(windows)} windows "
                          f"(need {self.segment_length})")
                    continue

                is_dynamic = self._is_dynamic(file_path)

                # Static files: one label for the whole file
                if not is_dynamic:
                    static_label = self._static_label_from_folder(file_path)
                    if static_label == -1:
                        print(f"  Skip {file_path.name}: cannot determine label from folder")
                        continue

                # Delta conversion (removes temporal leakage from cumulative counters)
                windows = convert_to_deltas(windows)

                # Derived features
                if self.use_derived_features:
                    windows = [add_derived_features(w) for w in windows]

                # Segment into fixed-length chunks
                segments = segment_windows(
                    windows,
                    segment_length=self.segment_length,
                    stride=self.stride,
                )

                for segment in segments:
                    if is_dynamic:
                        # Per-segment majority-vote with attack-biased threshold
                        label = get_label_from_segment_dynamic(
                            segment, threshold=self.dynamic_label_threshold
                        )
                    else:
                        label = static_label

                    x = self._extract_features(segment)
                    edge_index = self._build_temporal_chain_edges(len(segment))
                    samples.append((x, edge_index, label, file_path.name))

            except Exception as exc:
                print(f"  Error processing {file_path.name}: {exc}")

        return samples

    def _extract_features(self, segment: list) -> torch.Tensor:
        x_np = extract_features(
            segment,
            use_derived=self.use_derived_features,
            segment_length=self.segment_length,
            multi_ap_normalise=self.multi_ap_normalise,
        )
        x = torch.from_numpy(x_np)
        if self.scaler is not None:
            x = torch.from_numpy(self.scaler.transform(x.numpy())).float()
        return x

    @staticmethod
    def _build_temporal_chain_edges(num_nodes: int) -> torch.Tensor:
        src = torch.arange(0, num_nodes - 1, dtype=torch.long)
        dst = src + 1
        return torch.stack([
            torch.cat([src, dst]),
            torch.cat([dst, src]),
        ], dim=0)

    # ──────────────────────────────────────────────────────────────────────
    # PyG interface
    # ──────────────────────────────────────────────────────────────────────

    def len(self) -> int:
        return len(self.samples)

    def get(self, idx: int) -> Data:
        x, edge_index, y, file_name = self.samples[idx]
        return Data(
            x=x,
            edge_index=edge_index,
            y=torch.tensor([y], dtype=torch.long),
            file_name=file_name,
        )

    def get_class_distribution(self) -> dict:
        labels = [lbl for _, _, lbl, _ in self.samples]
        n_normal = sum(1 for l in labels if l == 0)
        n_attack = sum(1 for l in labels if l == 1)
        total = len(labels)
        return {
            "total": total,
            "normal": {"count": n_normal, "pct": n_normal / total * 100},
            "attack": {"count": n_attack, "pct": n_attack / total * 100},
        }

    def __repr__(self) -> str:
        d = self.get_class_distribution()
        return (
            f"WiFi7AttackDatasetV4(\n"
            f"  samples={len(self)},\n"
            f"  seg_len={self.segment_length},\n"
            f"  dyn_threshold={self.dynamic_label_threshold},\n"
            f"  normal={d['normal']['count']} ({d['normal']['pct']:.1f}%),\n"
            f"  attack={d['attack']['count']} ({d['attack']['pct']:.1f}%),\n"
            f"  scaled={'Yes' if self.scaler else 'No'}\n"
            f")"
        )


# ──────────────────────────────────────────────────────────────────────────
# Folder-based split loading
# ──────────────────────────────────────────────────────────────────────────

def load_v4_files(
    data_root: Path,
) -> Tuple[List[Path], List[Path], List[Path]]:
    """
    Load pre-partitioned v4 file lists from the canonical folder structure:

        <data_root>/train/Static/Normal/*.json
        <data_root>/train/Static/Attack/*.json
        <data_root>/train/Dynamic/*.json
        <data_root>/val/Static/Normal/*.json
        ...
        <data_root>/test/Static/Normal/*.json
        ...

    No random splitting: leakage is controlled at data-generation time by
    using strictly disjoint seed pools for train/val/test.

    Returns:
        (train_files, val_files, test_files) — lists of Path objects.
    """
    def _collect(split: str) -> List[Path]:
        base = data_root / split
        files: List[Path] = []
        for sub in [
            "Static/Normal",
            "Static/Attack",
            "Dynamic",
        ]:
            folder = base / sub
            if folder.exists():
                files.extend(sorted(folder.glob("*.json")))
        return files

    train_files = _collect("train")
    val_files   = _collect("val")
    test_files  = _collect("test")

    print(f"v4 file counts — train: {len(train_files)}, "
          f"val: {len(val_files)}, test: {len(test_files)}")
    return train_files, val_files, test_files


def create_v4_datasets_with_scaler(
    train_files: List[Path],
    val_files: List[Path],
    test_files: List[Path],
    segment_length: int = 256,
    stride: Optional[int] = None,
    use_derived_features: bool = True,
    multi_ap_normalise: bool = True,
    dynamic_label_threshold: float = 0.3,
) -> Tuple[
    "WiFi7AttackDatasetV4",
    "WiFi7AttackDatasetV4",
    "WiFi7AttackDatasetV4",
    StandardScaler,
]:
    """
    Create train/val/test v4 datasets with a shared scaler.

    CRITICAL: Scaler is fit ONLY on training data, then applied to val/test.
    """
    # Unscaled train to fit scaler
    train_unscaled = WiFi7AttackDatasetV4(
        root="data",
        file_list=train_files,
        segment_length=segment_length,
        stride=stride,
        scaler=None,
        use_derived_features=use_derived_features,
        multi_ap_normalise=multi_ap_normalise,
        dynamic_label_threshold=dynamic_label_threshold,
    )

    all_feats = np.vstack([x.numpy() for x, _, _, _ in train_unscaled.samples])
    scaler = StandardScaler()
    scaler.fit(all_feats)
    print(f"Scaler fitted on {len(all_feats)} windows (train set).")

    kwargs = dict(
        segment_length=segment_length,
        stride=stride,
        scaler=scaler,
        use_derived_features=use_derived_features,
        multi_ap_normalise=multi_ap_normalise,
        dynamic_label_threshold=dynamic_label_threshold,
    )

    train_ds = WiFi7AttackDatasetV4(root="data", file_list=train_files, **kwargs)
    val_ds   = WiFi7AttackDatasetV4(root="data", file_list=val_files,   **kwargs)
    test_ds  = WiFi7AttackDatasetV4(root="data", file_list=test_files,  **kwargs)

    print("=" * 60)
    print("V4 DATASET SUMMARY")
    print("=" * 60)
    print(f"Train: {train_ds}")
    print(f"Val:   {val_ds}")
    print(f"Test:  {test_ds}")
    print("=" * 60)

    return train_ds, val_ds, test_ds, scaler
