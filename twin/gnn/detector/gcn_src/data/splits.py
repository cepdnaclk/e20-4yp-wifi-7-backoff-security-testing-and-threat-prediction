"""
Data splitting module for WiFi 7 attack detection.

CRITICAL: This module ensures file-level splitting to prevent data leakage.
Never split by rows/windows/segments - always split by complete files!
"""

from pathlib import Path
from typing import List, Tuple
from sklearn.model_selection import train_test_split
import numpy as np


def split_files_by_scenario(
    attack_folder: Path,
    normal_folder: Path,
    test_size: float = 0.15,
    val_size: float = 0.15,
    random_state: int = 42
) -> Tuple[List[Path], List[Path], List[Path]]:
    """
    Split files into train/val/test sets.

    CRITICAL: Split by FILE, not by window/segment!
    This prevents data leakage where segments from the same file
    appear in both training and test sets.

    Why file-level splitting is essential:
    - Windows within a file are highly correlated (same attack, same conditions)
    - Segment-level split would give artificially high test performance
    - File-level split tests generalization to new attack instances

    Args:
        attack_folder: Path to folder containing attack JSON files
        normal_folder: Path to folder containing normal JSON files
        test_size: Fraction of files for test set (default: 0.15 = 15%)
        val_size: Fraction of files for validation set (default: 0.15 = 15%)
        random_state: Random seed for reproducibility

    Returns:
        Tuple of (train_files, val_files, test_files)
        - train_files: ~70% of files
        - val_files: ~15% of files
        - test_files: ~15% of files

    Example:
        >>> attack_folder = Path("data/Attack")
        >>> normal_folder = Path("data/Normal")
        >>> train, val, test = split_files_by_scenario(attack_folder, normal_folder)
        >>> # 192 attack + 12 normal = 204 total files
        >>> # Train: ~142 files (70%), Val: ~31 files (15%), Test: ~31 files (15%)
    """
    # Collect all attack files
    attack_files = sorted(attack_folder.glob("*.json"))
    print(f"Found {len(attack_files)} attack files in {attack_folder}")

    # Collect all normal files
    normal_files = sorted(normal_folder.glob("*.json"))
    print(f"Found {len(normal_files)} normal files in {normal_folder}")

    # Combine all files with labels
    all_files = attack_files + normal_files
    labels = [1] * len(attack_files) + [0] * len(normal_files)

    print(f"Total files: {len(all_files)}")
    print(f"Attack files: {len(attack_files)} ({len(attack_files)/len(all_files)*100:.1f}%)")
    print(f"Normal files: {len(normal_files)} ({len(normal_files)/len(all_files)*100:.1f}%)")

    # First split: (train+val) vs test
    # Use stratify to maintain class balance
    train_val_files, test_files, train_val_labels, test_labels = train_test_split(
        all_files,
        labels,
        test_size=test_size,
        stratify=labels,  # Maintain attack/normal ratio
        random_state=random_state
    )

    # Second split: train vs val
    # Adjust val_size relative to remaining data
    val_ratio = val_size / (1 - test_size)

    train_files, val_files, train_labels, val_labels = train_test_split(
        train_val_files,
        train_val_labels,
        test_size=val_ratio,
        stratify=train_val_labels,  # Maintain attack/normal ratio
        random_state=random_state
    )

    # Verify no overlap (critical check)
    train_set = set(train_files)
    val_set = set(val_files)
    test_set = set(test_files)

    assert len(train_set & val_set) == 0, "ERROR: Train/Val overlap detected!"
    assert len(train_set & test_set) == 0, "ERROR: Train/Test overlap detected!"
    assert len(val_set & test_set) == 0, "ERROR: Val/Test overlap detected!"

    # Print split statistics
    print("\n" + "="*60)
    print("FILE-LEVEL SPLIT RESULTS")
    print("="*60)
    print(f"Train files: {len(train_files):3d} ({len(train_files)/len(all_files)*100:.1f}%)")
    print(f"  - Attack: {sum(train_labels):3d}")
    print(f"  - Normal: {len(train_labels) - sum(train_labels):3d}")

    print(f"\nVal files:   {len(val_files):3d} ({len(val_files)/len(all_files)*100:.1f}%)")
    print(f"  - Attack: {sum(val_labels):3d}")
    print(f"  - Normal: {len(val_labels) - sum(val_labels):3d}")

    print(f"\nTest files:  {len(test_files):3d} ({len(test_files)/len(all_files)*100:.1f}%)")
    print(f"  - Attack: {sum(test_labels):3d}")
    print(f"  - Normal: {len(test_labels) - sum(test_labels):3d}")

    print("\n✓ No file overlap between splits (data leakage prevented)")
    print("="*60)

    return train_files, val_files, test_files


def verify_no_overlap(
    train_files: List[Path],
    val_files: List[Path],
    test_files: List[Path]
) -> bool:
    """
    Verify that there is no file overlap between splits.

    Args:
        train_files: Training file paths
        val_files: Validation file paths
        test_files: Test file paths

    Returns:
        True if no overlap, raises AssertionError otherwise
    """
    train_names = set(f.name for f in train_files)
    val_names = set(f.name for f in val_files)
    test_names = set(f.name for f in test_files)

    # Check for overlaps
    train_val_overlap = train_names & val_names
    train_test_overlap = train_names & test_names
    val_test_overlap = val_names & test_names

    if train_val_overlap:
        raise AssertionError(
            f"Train/Val overlap detected: {train_val_overlap}"
        )

    if train_test_overlap:
        raise AssertionError(
            f"Train/Test overlap detected: {train_test_overlap}"
        )

    if val_test_overlap:
        raise AssertionError(
            f"Val/Test overlap detected: {val_test_overlap}"
        )

    print("✓ No overlap between train/val/test splits")
    return True


def get_split_statistics(
    train_files: List[Path],
    val_files: List[Path],
    test_files: List[Path]
) -> dict:
    """
    Get detailed statistics about the split.

    Args:
        train_files: Training file paths
        val_files: Validation file paths
        test_files: Test file paths

    Returns:
        Dictionary with split statistics
    """
    def count_attack_normal(files):
        """Count attack vs normal files based on filename pattern."""
        attack_count = sum(1 for f in files if 'bias' in f.name and 'negative' not in f.stem or 'positive' in f.stem)
        # Actually, let's just check if filename contains attack indicators
        attack_count = sum(1 for f in files if 'bias' in f.name)
        normal_count = len(files) - attack_count
        return attack_count, normal_count

    train_attack, train_normal = count_attack_normal(train_files)
    val_attack, val_normal = count_attack_normal(val_files)
    test_attack, test_normal = count_attack_normal(test_files)

    total_files = len(train_files) + len(val_files) + len(test_files)

    stats = {
        'total_files': total_files,
        'train': {
            'total': len(train_files),
            'attack': train_attack,
            'normal': train_normal,
            'percentage': len(train_files) / total_files * 100
        },
        'val': {
            'total': len(val_files),
            'attack': val_attack,
            'normal': val_normal,
            'percentage': len(val_files) / total_files * 100
        },
        'test': {
            'total': len(test_files),
            'attack': test_attack,
            'normal': test_normal,
            'percentage': len(test_files) / total_files * 100
        }
    }

    return stats


def print_split_summary(
    train_files: List[Path],
    val_files: List[Path],
    test_files: List[Path]
):
    """
    Print a detailed summary of the split.

    Args:
        train_files: Training file paths
        val_files: Validation file paths
        test_files: Test file paths
    """
    stats = get_split_statistics(train_files, val_files, test_files)

    print("\n" + "="*70)
    print("DATA SPLIT SUMMARY")
    print("="*70)
    print(f"Total files: {stats['total_files']}")
    print()
    print(f"{'Split':<10} {'Total':<10} {'Attack':<10} {'Normal':<10} {'Percentage':<10}")
    print("-" * 70)
    print(f"{'Train':<10} {stats['train']['total']:<10} {stats['train']['attack']:<10} "
          f"{stats['train']['normal']:<10} {stats['train']['percentage']:>6.1f}%")
    print(f"{'Val':<10} {stats['val']['total']:<10} {stats['val']['attack']:<10} "
          f"{stats['val']['normal']:<10} {stats['val']['percentage']:>6.1f}%")
    print(f"{'Test':<10} {stats['test']['total']:<10} {stats['test']['attack']:<10} "
          f"{stats['test']['normal']:<10} {stats['test']['percentage']:>6.1f}%")
    print("="*70)


# Example usage
if __name__ == "__main__":
    import sys

    # Test the splitting function
    data_root = Path("data")
    attack_folder = data_root / "Attack"
    normal_folder = data_root / "Normal"

    if not attack_folder.exists() or not normal_folder.exists():
        print("Error: data/Attack and data/Normal folders not found")
        sys.exit(1)

    print("Testing file-level split function...")
    print()

    train_files, val_files, test_files = split_files_by_scenario(
        attack_folder,
        normal_folder,
        test_size=0.15,
        val_size=0.15,
        random_state=42
    )

    verify_no_overlap(train_files, val_files, test_files)
    print_split_summary(train_files, val_files, test_files)

    print("\n✓ Split module working correctly!")
