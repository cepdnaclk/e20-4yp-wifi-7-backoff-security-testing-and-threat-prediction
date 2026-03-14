"""
Feature Processor
Processes features for GCN inference: scaling and derived features.
"""

import torch
import numpy as np
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class FeatureProcessor:
    """
    Processes features for GCN inference.

    - Applies StandardScaler
    - Adds derived features (optional)
    """

    def __init__(self, scaler: Dict, use_derived_features: bool = True):
        """
        Initialize feature processor.

        Args:
            scaler: Scaler dict with 'mean' and 'scale'/'std' lists
            use_derived_features: Whether to add derived features
        """
        self.scaler_mean = np.array(scaler['mean'])
        # Handle both 'scale' and 'std' keys (std is standard deviation)
        self.scaler_scale = np.array(scaler.get('scale', scaler.get('std')))
        self.use_derived_features = use_derived_features

        # Base feature keys (order matters!)
        # Updated to match delta field names from windowizer
        self.base_feature_keys = [
            'net_throughput_mbps',
            'net_avg_delay_ms',
            'net_avg_jitter_ms',
            'net_packet_loss_ratio',
            'net_active_flows',
            'mac_tx_delta',
            'mac_rx_delta',
            'mac_ack_delta',
            'mac_retrans_delta',
            'mac_drop_delta',
            'phy_drop_delta',
            'avg_backoff_slots',
            'channel_busy_ratio'
        ]

        # Derived feature keys
        self.derived_feature_keys = [
            'retrans_rate',
            'drop_rate',
            'throughput_per_flow'
        ]

        # All feature keys
        if use_derived_features:
            self.feature_keys = self.base_feature_keys + self.derived_feature_keys
        else:
            self.feature_keys = self.base_feature_keys

    def add_derived_features(self, windows: List[Dict]) -> List[Dict]:
        """
        Add derived features to windows.

        Args:
            windows: List of window dicts

        Returns:
            List of windows with derived features
        """
        if not self.use_derived_features:
            return windows

        processed_windows = []

        for window in windows:
            window_copy = window.copy()

            # Retransmission rate
            mac_tx_delta = window.get('mac_tx_delta', 0.0)
            mac_retrans_delta = window.get('mac_retrans_delta', 0.0)

            if mac_tx_delta > 0:
                window_copy['retrans_rate'] = mac_retrans_delta / mac_tx_delta
            else:
                window_copy['retrans_rate'] = 0.0

            # Drop rate
            mac_drop = window.get('mac_drop_delta', 0.0)
            phy_drop = window.get('phy_drop_delta', 0.0)
            total_drops = mac_drop + phy_drop

            if mac_tx_delta > 0:
                window_copy['drop_rate'] = total_drops / mac_tx_delta
            else:
                window_copy['drop_rate'] = 0.0

            # Throughput per flow
            throughput = window.get('net_throughput_mbps', 0.0)
            active_flows = window.get('net_active_flows', 1.0)

            if active_flows > 0:
                window_copy['throughput_per_flow'] = throughput / active_flows
            else:
                window_copy['throughput_per_flow'] = 0.0

            processed_windows.append(window_copy)

        return processed_windows

    def build_feature_matrix(self, windows: List[Dict]) -> np.ndarray:
        """
        Build a scaled numpy feature matrix from a list of window dicts.

        Applies derived features, multi-AP normalisation, StandardScaler,
        and (when the scaler has 17 dimensions) appends a segment-length
        conditioning feature so that inference is compatible with v3 models.

        Args:
            windows: List of window dicts (already windowed)

        Returns:
            Scaled feature array of shape [len(windows), num_features]
        """
        # Add derived features
        windows = self.add_derived_features(windows)

        # Build raw feature matrix
        features = np.array(
            [[float(w.get(k, 0.0)) for k in self.feature_keys] for w in windows],
            dtype=np.float32,
        )

        # Multi-AP normalisation — divide absolute metrics by topology count
        # Falls back gracefully when num_ap/num_sta absent (v2 data)
        num_ap  = float(windows[0].get('num_ap',  1) or 1) if windows else 1.0
        num_sta = float(windows[0].get('num_sta', 2) or 2) if windows else 2.0

        if num_ap != 1.0 or num_sta != 2.0:
            # Throughput scales with nAp
            try:
                tp_idx = self.feature_keys.index('net_throughput_mbps')
                features[:, tp_idx] /= num_ap
            except (ValueError, AttributeError):
                pass
            # MAC/PHY delta counters scale with nSta
            per_sta = ['mac_tx_delta', 'mac_rx_delta', 'mac_ack_delta',
                       'mac_retrans_delta', 'mac_drop_delta', 'phy_drop_delta']
            for key in per_sta:
                try:
                    idx = self.feature_keys.index(key)
                    features[:, idx] /= num_sta
                except (ValueError, AttributeError):
                    pass

        # Apply StandardScaler: (x - mean) / scale
        features = (features - self.scaler_mean) / self.scaler_scale

        # Append segment-length conditioning feature: log2(L) / 8.0
        # This must match what training preprocessing.py adds
        seg_len = float(len(windows))
        seg_len_val = np.log2(max(seg_len, 1.0)) / 8.0

        # Only add seg-len feature if model expects 17 channels (v3)
        # Scaler mean has length 17 for v3, 16 for v2
        if hasattr(self, 'scaler_mean') and len(self.scaler_mean) == 17:
            seg_len_col = np.full((features.shape[0], 1), seg_len_val, dtype=np.float32)
            features = np.hstack([features, seg_len_col])

        return features

    def process_segment(self, segment: Dict) -> Dict:
        """
        Process segment: add derived features and prepare for scaling.

        Args:
            segment: Segment dict with 'windows' list

        Returns:
            Processed segment
        """
        segment_copy = segment.copy()
        segment_copy['windows'] = self.add_derived_features(segment['windows'])
        return segment_copy

    def scale_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        Apply StandardScaler to features.

        Args:
            x: Feature tensor [num_nodes, num_features]

        Returns:
            Scaled feature tensor
        """
        # Convert to numpy
        x_np = x.numpy()

        # Apply scaling: (x - mean) / scale
        x_scaled = (x_np - self.scaler_mean) / self.scaler_scale

        # Convert back to tensor
        x_scaled_tensor = torch.from_numpy(x_scaled).float()

        return x_scaled_tensor
