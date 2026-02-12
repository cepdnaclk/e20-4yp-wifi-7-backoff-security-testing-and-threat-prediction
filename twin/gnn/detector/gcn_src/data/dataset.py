"""
PyTorch Geometric Dataset for WiFi 7 attack detection.

This module implements the WiFi7AttackDataset class that:
1. Loads JSON files containing window data
2. Applies delta conversion to cumulative counters
3. Segments files into fixed-length graphs
4. Builds temporal chain edges (NOT k-NN!)
5. Extracts features (13 base or 16 with derived - NO bias!)
6. Applies feature scaling
7. Returns PyG Data objects

CRITICAL: This dataset ensures NO data leakage and follows all critical rules
from the implementation plan.
"""

import json
from pathlib import Path
from typing import List, Tuple, Optional, Union
import torch
import numpy as np
from torch_geometric.data import Dataset, Data
from sklearn.preprocessing import StandardScaler

# Import preprocessing functions
from .preprocessing import (
    convert_to_deltas,
    add_derived_features,
    segment_windows,
    BASE_FEATURE_KEYS,
    DERIVED_FEATURE_KEYS,
    get_label_from_windows
)


class WiFi7AttackDataset(Dataset):
    """
    PyTorch Geometric dataset for WiFi 7 backoff attack detection.

    Key features:
    - File-level loading (respects train/val/test splits)
    - Delta conversion for cumulative counters
    - Temporal chain graph topology
    - Fixed-length segmentation
    - Optional feature scaling
    - Optional derived features

    CRITICAL DESIGN DECISIONS:
    1. 'bias' is NEVER included in input features (used only for labels)
    2. Temporal chain edges (t ↔ t+1), NOT k-NN
    3. File-level segmentation to balance dataset
    4. Same preprocessing in train and inference
    """

    def __init__(
        self,
        root: str,
        file_list: List[Path],
        segment_length: int = 256,
        stride: int = None,
        scaler: Optional[StandardScaler] = None,
        use_derived_features: bool = True,
        transform=None,
        pre_transform=None
    ):
        """
        Initialize WiFi7AttackDataset.

        Args:
            root: Root directory (for PyG compatibility)
            file_list: List of JSON file paths to process
            segment_length: Number of windows per segment (L), default 256
            stride: Segmentation stride (None = non-overlapping)
            scaler: Feature scaler (fit on training data only!)
            use_derived_features: Whether to add ratio features (default: True)
            transform: Optional PyG transform
            pre_transform: Optional PyG pre-transform

        Example:
            >>> from pathlib import Path
            >>> train_files = [Path("data/Attack/file1.json"), ...]
            >>> scaler = StandardScaler()
            >>> # Fit scaler on training data first
            >>> dataset = WiFi7AttackDataset(
            ...     root="data",
            ...     file_list=train_files,
            ...     segment_length=256,
            ...     scaler=scaler,
            ...     use_derived_features=True
            ... )
        """
        self.file_list = file_list
        self.segment_length = segment_length
        self.stride = stride if stride else segment_length  # Non-overlapping by default
        self.scaler = scaler
        self.use_derived_features = use_derived_features

        # Feature keys (13 base or 16 with derived)
        self.feature_keys = BASE_FEATURE_KEYS.copy()
        if use_derived_features:
            self.feature_keys.extend(DERIVED_FEATURE_KEYS)

        # CRITICAL: Verify 'bias' is NOT in feature keys
        assert 'bias' not in self.feature_keys, \
            "CRITICAL ERROR: 'bias' must NEVER be in feature keys!"

        self.in_channels = len(self.feature_keys)

        # Pre-process all files into graph samples
        print(f"Loading {len(file_list)} files with segment_length={segment_length}...")
        self.samples = self._preprocess_files()
        print(f"Created {len(self.samples)} graph samples")

        super().__init__(root, transform, pre_transform)

    def _preprocess_files(self) -> List[Tuple[torch.Tensor, torch.Tensor, int, str]]:
        """
        Convert all JSON files into graph samples.

        Returns:
            List of (node_features, edge_index, label, source_file) tuples
        """
        samples = []

        for file_path in self.file_list:
            try:
                # Load JSON file
                with open(file_path, 'r') as f:
                    windows = json.load(f)

                if len(windows) < self.segment_length:
                    print(f"Warning: {file_path.name} has only {len(windows)} windows, "
                          f"skipping (need at least {self.segment_length})")
                    continue

                # Determine label from bias (CRITICAL: bias not used as feature!)
                label = get_label_from_windows(windows)

                # Convert cumulative counters to deltas
                windows = convert_to_deltas(windows)

                # Add derived features if enabled
                if self.use_derived_features:
                    windows = [add_derived_features(w) for w in windows]

                # Segment the file into fixed-length chunks
                segments = segment_windows(
                    windows,
                    segment_length=self.segment_length,
                    stride=self.stride
                )

                # Convert each segment to a graph
                for segment in segments:
                    x = self._extract_features(segment)
                    edge_index = self._build_temporal_chain_edges(len(segment))

                    samples.append((x, edge_index, label, file_path.name))

            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")
                continue

        return samples

    def _extract_features(self, segment: List[dict]) -> torch.Tensor:
        """
        Extract feature matrix from segment.

        Args:
            segment: List of window dictionaries

        Returns:
            Feature tensor of shape [segment_length, in_channels]
        """
        features = []

        for window in segment:
            feature_vector = [
                float(window.get(key, 0.0))
                for key in self.feature_keys
            ]
            features.append(feature_vector)

        x = torch.tensor(features, dtype=torch.float)

        # Apply scaling if scaler is provided
        if self.scaler is not None:
            x_np = x.numpy()
            x_scaled = self.scaler.transform(x_np)
            x = torch.from_numpy(x_scaled).float()

        return x

    def _build_temporal_chain_edges(self, num_nodes: int) -> torch.Tensor:
        """
        Build temporal chain edge index.

        Creates edges connecting consecutive windows: (t ↔ t+1) for all t

        Args:
            num_nodes: Number of windows (nodes) in segment

        Returns:
            Edge index tensor of shape [2, num_edges]

        Example:
            >>> edge_index = self._build_temporal_chain_edges(4)
            >>> edge_index
            tensor([[0, 1, 2, 1, 2, 3],
                    [1, 2, 3, 0, 1, 2]])
            # Edges: 0→1, 1→2, 2→3, 1→0, 2→1, 3→2 (bidirectional)
        """
        # Create forward edges: 0→1, 1→2, ..., (n-2)→(n-1)
        src = torch.arange(0, num_nodes - 1, dtype=torch.long)
        dst = src + 1

        # Make bidirectional (undirected graph)
        # Forward: 0→1, 1→2, ..., (n-2)→(n-1)
        # Backward: 1→0, 2→1, ..., (n-1)→(n-2)
        edge_index = torch.stack([
            torch.cat([src, dst]),  # Source nodes
            torch.cat([dst, src])   # Destination nodes
        ], dim=0)

        return edge_index

    def len(self) -> int:
        """Return number of graph samples."""
        return len(self.samples)

    def get(self, idx: int) -> Data:
        """
        Get a single graph sample.

        Args:
            idx: Sample index

        Returns:
            PyG Data object with:
            - x: Node features [segment_length, in_channels]
            - edge_index: Temporal chain edges [2, num_edges]
            - y: Binary label [1] (0=Normal, 1=Attack)
            - file_name: Source file name (for debugging)
        """
        x, edge_index, y, file_name = self.samples[idx]

        data = Data(
            x=x,
            edge_index=edge_index,
            y=torch.tensor([y], dtype=torch.long),
            file_name=file_name  # Store for debugging
        )

        return data

    def get_feature_statistics(self) -> dict:
        """
        Compute feature statistics across the dataset.

        Useful for debugging and understanding feature distributions.

        Returns:
            Dictionary with mean, std, min, max for each feature
        """
        all_features = []

        for x, _, _, _ in self.samples:
            all_features.append(x.numpy())

        all_features = np.vstack(all_features)  # [total_windows, in_channels]

        stats = {
            'mean': np.mean(all_features, axis=0),
            'std': np.std(all_features, axis=0),
            'min': np.min(all_features, axis=0),
            'max': np.max(all_features, axis=0)
        }

        return stats

    def get_class_distribution(self) -> dict:
        """
        Get distribution of classes in the dataset.

        Returns:
            Dictionary with count and percentage for each class
        """
        labels = [label for _, _, label, _ in self.samples]

        normal_count = sum(1 for l in labels if l == 0)
        attack_count = sum(1 for l in labels if l == 1)
        total = len(labels)

        distribution = {
            'total': total,
            'normal': {
                'count': normal_count,
                'percentage': normal_count / total * 100
            },
            'attack': {
                'count': attack_count,
                'percentage': attack_count / total * 100
            }
        }

        return distribution

    def __repr__(self) -> str:
        """String representation of the dataset."""
        dist = self.get_class_distribution()
        return (
            f"WiFi7AttackDataset(\n"
            f"  samples={len(self)},\n"
            f"  segment_length={self.segment_length},\n"
            f"  in_channels={self.in_channels} "
            f"({'with derived' if self.use_derived_features else 'base only'}),\n"
            f"  normal={dist['normal']['count']} "
            f"({dist['normal']['percentage']:.1f}%),\n"
            f"  attack={dist['attack']['count']} "
            f"({dist['attack']['percentage']:.1f}%),\n"
            f"  scaled={'Yes' if self.scaler else 'No'}\n"
            f")"
        )


def create_datasets_with_scaler(
    train_files: List[Path],
    val_files: List[Path],
    test_files: List[Path],
    segment_length: int = 256,
    use_derived_features: bool = True
) -> Tuple[WiFi7AttackDataset, WiFi7AttackDataset, WiFi7AttackDataset, StandardScaler]:
    """
    Create train/val/test datasets with a shared scaler.

    CRITICAL: Scaler is fit ONLY on training data, then applied to val/test.

    Args:
        train_files: Training file paths
        val_files: Validation file paths
        test_files: Test file paths
        segment_length: Windows per segment
        use_derived_features: Whether to use derived features

    Returns:
        Tuple of (train_dataset, val_dataset, test_dataset, scaler)
    """
    print("Creating datasets with scaler...")
    print(f"  Train files: {len(train_files)}")
    print(f"  Val files: {len(val_files)}")
    print(f"  Test files: {len(test_files)}")

    # Create train dataset without scaler first
    train_dataset_unscaled = WiFi7AttackDataset(
        root="data",
        file_list=train_files,
        segment_length=segment_length,
        scaler=None,  # No scaler yet
        use_derived_features=use_derived_features
    )

    # Collect all training features to fit scaler
    print("\nFitting scaler on training data...")
    all_train_features = []
    for x, _, _, _ in train_dataset_unscaled.samples:
        all_train_features.append(x.numpy())

    all_train_features = np.vstack(all_train_features)

    # Fit scaler on training data ONLY
    scaler = StandardScaler()
    scaler.fit(all_train_features)

    print(f"  Feature means: {scaler.mean_[:5]}... (showing first 5)")
    print(f"  Feature stds: {scaler.scale_[:5]}... (showing first 5)")

    # Create datasets with fitted scaler
    print("\nCreating scaled datasets...")
    train_dataset = WiFi7AttackDataset(
        root="data",
        file_list=train_files,
        segment_length=segment_length,
        scaler=scaler,
        use_derived_features=use_derived_features
    )

    val_dataset = WiFi7AttackDataset(
        root="data",
        file_list=val_files,
        segment_length=segment_length,
        scaler=scaler,
        use_derived_features=use_derived_features
    )

    test_dataset = WiFi7AttackDataset(
        root="data",
        file_list=test_files,
        segment_length=segment_length,
        scaler=scaler,
        use_derived_features=use_derived_features
    )

    print("\n" + "="*60)
    print("DATASET SUMMARY")
    print("="*60)
    print(f"Train: {train_dataset}")
    print(f"\nVal: {val_dataset}")
    print(f"\nTest: {test_dataset}")
    print("="*60)

    return train_dataset, val_dataset, test_dataset, scaler


if __name__ == "__main__":
    # Example usage
    from pathlib import Path
    from .splits import split_files_by_scenario

    print("Testing WiFi7AttackDataset...")
    print()

    # Load and split files
    data_root = Path("data")
    attack_folder = data_root / "Attack"
    normal_folder = data_root / "Normal"

    train_files, val_files, test_files = split_files_by_scenario(
        attack_folder,
        normal_folder
    )

    # Create datasets
    train_ds, val_ds, test_ds, scaler = create_datasets_with_scaler(
        train_files, val_files, test_files,
        segment_length=256,
        use_derived_features=True
    )

    # Test loading a sample
    print("\nTesting sample loading...")
    sample = train_ds[0]
    print(f"  x shape: {sample.x.shape}")
    print(f"  edge_index shape: {sample.edge_index.shape}")
    print(f"  y: {sample.y.item()}")
    print(f"  file: {sample.file_name}")

    print("\n✓ Dataset module working correctly!")
