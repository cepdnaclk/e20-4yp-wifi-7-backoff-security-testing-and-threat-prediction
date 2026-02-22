#!/usr/bin/env python3
"""
Compare aligned pipeline data with original GCN training data
to validate configuration alignment success.

Usage:
    python3 compare_alignment.py [aligned_exp_id]

Example:
    python3 compare_alignment.py aligned-normal-test-42
"""

import json
import sys
import numpy as np
from pathlib import Path

# Paths
ORIG_DATA_PATH = Path.home() / 'github/wifi7_gcn_attack_detection/Wifi7_Datasets/Normal/session_1_scenario_1_normal_run_1.json'
PIPELINE_BASE = Path.home() / 'github/ndt-wifi7-mlo-security/sim/ns3/artifacts'

def load_json_data(path):
    """Load JSON data from file."""
    with open(path, 'r') as f:
        return json.load(f)

def calculate_statistics(data, skip_warmup=100):
    """Calculate statistics from window data."""
    # Skip warmup period
    if len(data) > skip_warmup:
        data = data[skip_warmup:]

    if len(data) == 0:
        return None

    return {
        'total_windows': len(data),
        'throughput_mean': np.mean([w['net_throughput_mbps'] for w in data]),
        'throughput_std': np.std([w['net_throughput_mbps'] for w in data]),
        'throughput_min': np.min([w['net_throughput_mbps'] for w in data]),
        'throughput_max': np.max([w['net_throughput_mbps'] for w in data]),
        'active_flows': np.mean([w['net_active_flows'] for w in data]),
        'delay_mean': np.mean([w['net_avg_delay_ms'] for w in data]),
        'delay_std': np.std([w['net_avg_delay_ms'] for w in data]),
        'backoff_mean': np.mean([w['avg_backoff_slots'] for w in data]),
        'backoff_std': np.std([w['avg_backoff_slots'] for w in data]),
        'channel_busy': np.mean([w['channel_busy_ratio'] for w in data]),
    }

def print_comparison(orig_stats, algn_stats):
    """Print comparison table."""
    print("\n" + "=" * 75)
    print("CONFIGURATION ALIGNMENT RESULTS")
    print("=" * 75)
    print(f"\n{'Metric':<25} {'Original':<15} {'Aligned':<15} {'Diff':>15}")
    print("-" * 75)

    metrics = [
        ('total_windows', 'Total Windows'),
        ('throughput_mean', 'Throughput Mean (Mbps)'),
        ('throughput_std', 'Throughput Std'),
        ('active_flows', 'Active Flows'),
        ('delay_mean', 'Delay Mean (ms)'),
        ('backoff_mean', 'Backoff Mean (slots)'),
        ('channel_busy', 'Channel Busy Ratio'),
    ]

    for key, label in metrics:
        orig_val = orig_stats[key]
        algn_val = algn_stats[key]
        diff = algn_val - orig_val

        if orig_val != 0:
            diff_pct = (diff / orig_val * 100)
            diff_str = f"{diff_pct:+.1f}%"
        else:
            diff_str = f"{diff:+.2f}"

        print(f"{label:<25} {orig_val:>14.2f} {algn_val:>14.2f} {diff_str:>15}")

    print("-" * 75)

def evaluate_alignment(orig_stats, algn_stats):
    """Evaluate alignment success."""
    tp_diff = abs(algn_stats['throughput_mean'] - orig_stats['throughput_mean'])
    tp_std_ratio = algn_stats['throughput_std'] / orig_stats['throughput_std']
    flows_match = algn_stats['active_flows'] == orig_stats['active_flows']

    print("\n" + "=" * 75)
    print("EVALUATION")
    print("=" * 75)

    print(f"\n1. Throughput Mean Difference: {tp_diff:.2f} Mbps")
    if tp_diff < 20:
        print("   ✅ EXCELLENT (<20 Mbps)")
    elif tp_diff < 50:
        print("   ✅ GOOD (<50 Mbps)")
    elif tp_diff < 100:
        print("   ⚠️  FAIR (<100 Mbps)")
    else:
        print("   ❌ POOR (>100 Mbps)")

    print(f"\n2. Throughput Variability Ratio: {tp_std_ratio:.2f}x")
    if tp_std_ratio < 1.5:
        print("   ✅ EXCELLENT (< 1.5x)")
    elif tp_std_ratio < 2.5:
        print("   ✅ GOOD (< 2.5x)")
    else:
        print("   ⚠️  HIGH (> 2.5x) - Consider lowering MCS")

    print(f"\n3. Active Flows: {algn_stats['active_flows']:.0f} (Original: {orig_stats['active_flows']:.0f})")
    if flows_match:
        print("   ✅ MATCH")
    else:
        print("   ❌ MISMATCH - Check topology configuration")

    print("\n" + "=" * 75)
    print("RECOMMENDATION")
    print("=" * 75)

    if tp_diff < 50 and tp_std_ratio < 2.5 and flows_match:
        print("\n✅ ALIGNMENT SUCCESSFUL!")
        print("\nNext steps:")
        print("  1. Test with GCN model v1.0.0")
        print("  2. Expected false positive rate: < 20%")
        print("  3. If successful, deploy to production")
    elif tp_diff < 100:
        print("\n⚠️  PARTIAL ALIGNMENT")
        print("\nNext steps:")
        print("  1. Try additional tuning:")
        print("     - Lower MCS (HeMcs11 → HeMcs7)")
        print("     - Adjust data rate (40-60 Mbps)")
        print("  2. Test with model v1.0.0")
        print("  3. If FP rate > 20%, consider retraining")
    else:
        print("\n❌ ALIGNMENT FAILED")
        print("\nNext steps:")
        print("  1. Review configuration changes")
        print("  2. Check simulation logs for errors")
        print("  3. Consider retraining approach (WP8-MODEL-ANALYSIS-AND-RETRAINING-GUIDE.md)")

    print("\n" + "=" * 75)

def main():
    # Get experiment ID from args or use default
    if len(sys.argv) > 1:
        exp_id = sys.argv[1]
    else:
        # Find most recent aligned experiment
        aligned_dirs = sorted(PIPELINE_BASE.glob('aligned-*'))
        if not aligned_dirs:
            print("ERROR: No aligned experiment found in sim/ns3/artifacts/")
            print("\nUsage: python3 compare_alignment.py [experiment_id]")
            print("\nExample: python3 compare_alignment.py aligned-normal-test-42")
            sys.exit(1)
        exp_id = aligned_dirs[-1].name
        print(f"Using most recent: {exp_id}")

    aligned_data_path = PIPELINE_BASE / exp_id / 'mlo_output.json'

    # Check files exist
    if not ORIG_DATA_PATH.exists():
        print(f"ERROR: Original data not found: {ORIG_DATA_PATH}")
        sys.exit(1)

    if not aligned_data_path.exists():
        print(f"ERROR: Aligned data not found: {aligned_data_path}")
        print(f"\nRun the aligned simulation first:")
        print(f"  make ns3-run-scenario EXP_ID={exp_id} SCENARIO=normal SEED=42")
        sys.exit(1)

    # Load data
    print(f"Loading original training data...")
    orig_data = load_json_data(ORIG_DATA_PATH)

    print(f"Loading aligned pipeline data: {exp_id}")
    algn_data = load_json_data(aligned_data_path)

    # Calculate statistics
    print("Calculating statistics...")
    orig_stats = calculate_statistics(orig_data, skip_warmup=100)
    algn_stats = calculate_statistics(algn_data, skip_warmup=100)

    if not orig_stats or not algn_stats:
        print("ERROR: Insufficient data for comparison")
        sys.exit(1)

    # Print comparison
    print_comparison(orig_stats, algn_stats)

    # Evaluate
    evaluate_alignment(orig_stats, algn_stats)

if __name__ == '__main__':
    main()
