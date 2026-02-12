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
        self.base_feature_keys = [
            'net_throughput_mbps',
            'net_avg_delay_ms',
            'net_avg_jitter_ms',
            'net_packet_loss_ratio',
            'net_active_flows',
            'mac_total_tx',
            'mac_total_rx',
            'mac_total_ack',
            'mac_total_retrans',
            'mac_drop_count',
            'phy_drop_count',
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
            mac_total_tx = window.get('mac_total_tx', 0.0)
            mac_total_retrans = window.get('mac_total_retrans', 0.0)

            if mac_total_tx > 0:
                window_copy['retrans_rate'] = mac_total_retrans / mac_total_tx
            else:
                window_copy['retrans_rate'] = 0.0

            # Drop rate
            mac_drop = window.get('mac_drop_count', 0.0)
            phy_drop = window.get('phy_drop_count', 0.0)
            total_drops = mac_drop + phy_drop

            if mac_total_tx > 0:
                window_copy['drop_rate'] = total_drops / mac_total_tx
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
