#!/usr/bin/env python3
"""
Compare feature distributions between training data and validation experiments.
"""
import json
import numpy as np
from pathlib import Path

def analyze_file(filepath, label):
    """Analyze feature distribution in a file."""
    with open(filepath, 'r') as f:
        windows = json.load(f)

    # Extract features from all windows
    features = {
        'net_throughput_mbps': [],
        'net_avg_delay_ms': [],
        'net_avg_jitter_ms': [],
        'net_packet_loss_ratio': [],
        'net_active_flows': [],
        'avg_backoff_slots': [],
        'channel_busy_ratio': [],
        'bias': []
    }

    for w in windows:
        for key in features.keys():
            if key in w:
                features[key].append(w[key])

    # Compute statistics
    stats = {}
    for key, values in features.items():
        if values:
            arr = np.array(values)
            stats[key] = {
                'mean': float(np.mean(arr)),
                'std': float(np.std(arr)),
                'min': float(np.min(arr)),
                'max': float(np.max(arr)),
                'median': float(np.median(arr))
            }

    return stats, features

# Analyze training normal file
print("="*80)
print("TRAINING DATA (Normal)")
print("="*80)
training_file = Path('/home/cobrakali/github/wifi7_gcn_attack_detection/data/Normal/session_2_scenario_3_normal_run_1.json')
train_stats, train_features = analyze_file(training_file, 'Training Normal')

for feature, stat in train_stats.items():
    print(f"\n{feature}:")
    print(f"  Mean: {stat['mean']:.4f}, Std: {stat['std']:.4f}")
    print(f"  Range: [{stat['min']:.4f}, {stat['max']:.4f}]")
    print(f"  Median: {stat['median']:.4f}")

# Analyze validation normal file
print("\n" + "="*80)
print("VALIDATION EXPERIMENT (Normal)")
print("="*80)
validation_file = Path('/home/cobrakali/github/ndt-wifi7-mlo-security/sim/ns3/artifacts/20260215-validation-normal-01/mlo_output.json')
val_stats, val_features = analyze_file(validation_file, 'Validation Normal')

for feature, stat in val_stats.items():
    print(f"\n{feature}:")
    print(f"  Mean: {stat['mean']:.4f}, Std: {stat['std']:.4f}")
    print(f"  Range: [{stat['min']:.4f}, {stat['max']:.4f}]")
    print(f"  Median: {stat['median']:.4f}")

# Compare differences
print("\n" + "="*80)
print("DIFFERENCES (Validation - Training)")
print("="*80)

for feature in train_stats.keys():
    if feature in val_stats:
        train_mean = train_stats[feature]['mean']
        val_mean = val_stats[feature]['mean']
        diff = val_mean - train_mean
        pct_diff = (diff / train_mean * 100) if train_mean != 0 else 0

        print(f"\n{feature}:")
        print(f"  Training Mean: {train_mean:.4f}")
        print(f"  Validation Mean: {val_mean:.4f}")
        print(f"  Difference: {diff:+.4f} ({pct_diff:+.2f}%)")

        # Check if difference is significant (>20% or std difference)
        if abs(pct_diff) > 20:
            print(f"  ⚠️  SIGNIFICANT DIFFERENCE!")

# Check bias values
print("\n" + "="*80)
print("BIAS VALUES")
print("="*80)
print(f"Training bias: {train_features['bias'][0] if train_features['bias'] else 'N/A'}")
print(f"Validation bias: {val_features['bias'][0] if val_features['bias'] else 'N/A'}")
print(f"All training bias values unique: {len(set(train_features['bias']))}")
print(f"All validation bias values unique: {len(set(val_features['bias']))}")
