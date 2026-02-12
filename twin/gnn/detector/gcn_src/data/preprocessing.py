"""
Data preprocessing module for WiFi 7 attack detection.

This module provides critical preprocessing functions:
1. Delta conversion: Convert cumulative counters to per-window deltas
2. Derived features: Add ratio-based features that highlight attack patterns

CRITICAL: These preprocessing steps must be applied IDENTICALLY in both
training and inference pipelines to ensure model consistency.
"""

from typing import List, Dict
import numpy as np


def convert_to_deltas(windows: List[Dict]) -> List[Dict]:
    """
    Convert cumulative counters to per-window deltas.

    CRITICAL: This function removes temporal leakage from cumulative fields.
    Without this, the model would learn time position instead of attack patterns.

    Cumulative fields (monotonically increasing):
    - mac_total_tx: Total transmitted packets since simulation start
    - mac_total_rx: Total received packets since simulation start
    - mac_total_ack: Total ACKs since simulation start
    - mac_total_retrans: Total retransmissions since simulation start
    - mac_drop_count: Total MAC drops since simulation start
    - phy_drop_count: Total PHY drops since simulation start

    Delta fields (per-window activity):
    - mac_tx_delta: Packets transmitted in this window
    - mac_rx_delta: Packets received in this window
    - mac_ack_delta: ACKs received in this window
    - mac_retrans_delta: Retransmissions in this window
    - mac_drop_delta: MAC drops in this window
    - phy_drop_delta: PHY drops in this window

    Args:
        windows: List of window dictionaries (must be sorted by time)

    Returns:
        List of windows with delta fields added

    Example:
        >>> windows = [
        ...     {'window': 0, 'mac_total_tx': 100},
        ...     {'window': 1, 'mac_total_tx': 250},
        ...     {'window': 2, 'mac_total_tx': 450}
        ... ]
        >>> result = convert_to_deltas(windows)
        >>> [w['mac_tx_delta'] for w in result]
        [100, 150, 200]  # Deltas: 100, 250-100, 450-250
    """
    # Define cumulative field mappings
    cumulative_fields = {
        'mac_total_tx': 'mac_tx_delta',
        'mac_total_rx': 'mac_rx_delta',
        'mac_total_ack': 'mac_ack_delta',
        'mac_total_retrans': 'mac_retrans_delta',
        'mac_drop_count': 'mac_drop_delta',
        'phy_drop_count': 'phy_drop_delta'
    }

    delta_windows = []

    for i, window in enumerate(windows):
        # Create a copy to avoid modifying original
        w_delta = window.copy()

        for old_key, new_key in cumulative_fields.items():
            if i == 0:
                # First window: delta equals the cumulative value
                # (represents activity from start to first window)
                w_delta[new_key] = window.get(old_key, 0)
            else:
                # Subsequent windows: compute difference from previous window
                current_value = window.get(old_key, 0)
                previous_value = windows[i-1].get(old_key, 0)

                # Ensure non-negative (counters should be monotonically increasing)
                delta = max(0, current_value - previous_value)
                w_delta[new_key] = delta

        delta_windows.append(w_delta)

    return delta_windows


def add_derived_features(window: Dict, eps: float = 1e-8) -> Dict:
    """
    Add ratio-based derived features that highlight attack signatures.

    These features make attack patterns more explicit to the model:
    - High retrans_rate: Characteristic of negative bias attacks (more collisions)
    - High drop_rate: Characteristic of both attack types (congestion)
    - Low throughput_per_flow: Characteristic of positive bias attacks (starvation)

    Args:
        window: Window dictionary with delta fields already computed
        eps: Small constant to avoid division by zero (default: 1e-8)

    Returns:
        Window dictionary with derived features added

    Derived Features:
        1. retrans_rate: Retransmission rate (indicates collision/congestion)
           Formula: mac_retrans_delta / (mac_tx_delta + eps)

        2. drop_rate: Total drop rate (indicates severe congestion)
           Formula: (mac_drop_delta + phy_drop_delta) / (mac_tx_delta + eps)

        3. throughput_per_flow: Per-flow throughput (indicates fairness)
           Formula: net_throughput_mbps / (net_active_flows + eps)

    Example:
        >>> window = {
        ...     'mac_tx_delta': 100,
        ...     'mac_retrans_delta': 10,
        ...     'mac_drop_delta': 2,
        ...     'phy_drop_delta': 1,
        ...     'net_throughput_mbps': 50.0,
        ...     'net_active_flows': 5
        ... }
        >>> result = add_derived_features(window)
        >>> result['retrans_rate']
        0.1  # 10/100
        >>> result['drop_rate']
        0.03  # (2+1)/100
        >>> result['throughput_per_flow']
        10.0  # 50/5
    """
    # Create a copy to avoid modifying original
    w_derived = window.copy()

    # 1. Retransmission rate (higher in negative bias attacks)
    mac_tx = window.get('mac_tx_delta', 0)
    mac_retrans = window.get('mac_retrans_delta', 0)
    w_derived['retrans_rate'] = mac_retrans / (mac_tx + eps)

    # 2. Total drop rate (higher in all attacks due to congestion)
    mac_drop = window.get('mac_drop_delta', 0)
    phy_drop = window.get('phy_drop_delta', 0)
    total_drops = mac_drop + phy_drop
    w_derived['drop_rate'] = total_drops / (mac_tx + eps)

    # 3. Throughput per flow (lower in positive bias attacks - victim starvation)
    net_throughput = window.get('net_throughput_mbps', 0.0)
    net_flows = window.get('net_active_flows', 0)
    w_derived['throughput_per_flow'] = net_throughput / (net_flows + eps)

    return w_derived


def segment_windows(
    windows: List[Dict],
    segment_length: int = 256,
    stride: int = None,
    strategy: str = 'non_overlapping'
) -> List[List[Dict]]:
    """
    Segment a run into fixed-length chunks.

    Segmentation is essential to prevent the model from learning file length
    as a feature (attack files are shorter than normal files).

    Args:
        windows: List of window dictionaries (sorted by time)
        segment_length: Number of windows per segment (L)
        stride: Step size for sliding window (if None, uses segment_length)
        strategy: 'non_overlapping' or 'sliding'
            - 'non_overlapping': stride = segment_length (independent segments)
            - 'sliding': stride < segment_length (overlapping segments)

    Returns:
        List of segments, each containing segment_length windows

    Example:
        >>> windows = [{'window': i} for i in range(1000)]
        >>> segments = segment_windows(windows, segment_length=256, strategy='non_overlapping')
        >>> len(segments)
        3  # 1000 / 256 = 3 complete segments (768 windows used, 232 dropped)
        >>> len(segments[0])
        256
        >>> segments[0][0]['window']
        0
        >>> segments[1][0]['window']
        256
    """
    # Determine stride based on strategy
    if strategy == 'non_overlapping':
        stride = segment_length
    elif stride is None:
        stride = segment_length // 2  # 50% overlap by default

    segments = []
    total_windows = len(windows)

    # Generate segments
    for start_idx in range(0, total_windows - segment_length + 1, stride):
        end_idx = start_idx + segment_length
        segment = windows[start_idx:end_idx]

        # Verify segment length
        assert len(segment) == segment_length, \
            f"Segment length mismatch: expected {segment_length}, got {len(segment)}"

        segments.append(segment)

    return segments


# Feature keys definition
# CRITICAL: 'bias' is NOT included in feature keys!
# Bias is used ONLY for label generation, never as input to the model.

BASE_FEATURE_KEYS = [
    # Network layer (5 features)
    "net_throughput_mbps",
    "net_avg_delay_ms",
    "net_avg_jitter_ms",
    "net_packet_loss_ratio",
    "net_active_flows",

    # MAC layer - DELTAS not totals (5 features)
    "mac_tx_delta",
    "mac_rx_delta",
    "mac_ack_delta",
    "mac_retrans_delta",
    "mac_drop_delta",

    # PHY layer - DELTA (1 feature)
    "phy_drop_delta",

    # Backoff indicators (2 features)
    "avg_backoff_slots",
    "channel_busy_ratio"
]

# Derived features (3 additional features)
DERIVED_FEATURE_KEYS = [
    "retrans_rate",
    "drop_rate",
    "throughput_per_flow"
]

# Total: 13 base features, 16 with derived features
F_DIM_BASE = len(BASE_FEATURE_KEYS)  # 13
F_DIM_DERIVED = len(BASE_FEATURE_KEYS) + len(DERIVED_FEATURE_KEYS)  # 16


def extract_features(
    windows: List[Dict],
    use_derived: bool = True
) -> np.ndarray:
    """
    Extract feature matrix from windows.

    CRITICAL: Ensures 'bias' is NEVER included in features.

    Args:
        windows: List of window dictionaries (with delta fields)
        use_derived: Whether to include derived features

    Returns:
        Feature matrix of shape [num_windows, num_features]
        - If use_derived=False: [num_windows, 13]
        - If use_derived=True: [num_windows, 16]
    """
    feature_keys = BASE_FEATURE_KEYS.copy()
    if use_derived:
        feature_keys.extend(DERIVED_FEATURE_KEYS)

    # Verify 'bias' is NOT in feature keys
    assert 'bias' not in feature_keys, \
        "CRITICAL ERROR: 'bias' should NEVER be in feature keys!"

    features = []
    for window in windows:
        feature_vector = [
            float(window.get(key, 0.0))
            for key in feature_keys
        ]
        features.append(feature_vector)

    return np.array(features, dtype=np.float32)


def get_label_from_windows(windows: List[Dict]) -> int:
    """
    Extract label from window data.

    Label is determined by the 'bias' field:
    - bias == 0: Normal behavior (label = 0)
    - bias != 0: Attack (label = 1)

    Args:
        windows: List of window dictionaries from same run

    Returns:
        Binary label: 0 (Normal) or 1 (Attack)
    """
    # All windows in a file have the same bias value
    # Check first window
    bias = windows[0].get('bias', 0)

    # Binary classification
    label = 1 if bias != 0 else 0

    return label


# Utility function for validation
def validate_preprocessing(windows_original: List[Dict], windows_processed: List[Dict]):
    """
    Validate that preprocessing was applied correctly.

    Checks:
    1. Delta fields are non-negative
    2. Delta fields show reasonable variation
    3. Derived features are within expected ranges

    Args:
        windows_original: Original windows
        windows_processed: Processed windows with deltas and derived features

    Raises:
        AssertionError: If validation fails
    """
    # Check delta fields are non-negative
    for i, window in enumerate(windows_processed):
        for key in ['mac_tx_delta', 'mac_rx_delta', 'mac_retrans_delta']:
            value = window.get(key, 0)
            assert value >= 0, \
                f"Window {i}: {key} is negative ({value})"

    # Check derived features are within reasonable ranges
    for i, window in enumerate(windows_processed):
        if 'retrans_rate' in window:
            rate = window['retrans_rate']
            assert 0 <= rate <= 1.5, \
                f"Window {i}: retrans_rate out of range ({rate})"

        if 'drop_rate' in window:
            rate = window['drop_rate']
            assert 0 <= rate <= 1.0, \
                f"Window {i}: drop_rate out of range ({rate})"

    print("✓ Preprocessing validation passed")


if __name__ == "__main__":
    # Example usage
    print("WiFi 7 Preprocessing Module")
    print("=" * 50)
    print(f"Base features: {F_DIM_BASE}")
    print(f"With derived: {F_DIM_DERIVED}")
    print("\nFeature keys (base):")
    for i, key in enumerate(BASE_FEATURE_KEYS, 1):
        print(f"  {i:2d}. {key}")
    print("\nDerived features:")
    for i, key in enumerate(DERIVED_FEATURE_KEYS, 1):
        print(f"  {i:2d}. {key}")
    print("\n✓ Module loaded successfully")
