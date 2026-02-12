"""
Window Aggregator
Aggregates raw telemetry events into time windows.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class WindowAggregator:
    """
    Aggregates telemetry events into time windows.

    Groups events by (experiment_id, timestamp_bucket, entity_id) and
    aggregates all metrics for that window.
    """

    def __init__(self, window_interval_ms: int, base_feature_keys: List[str]):
        """
        Initialize aggregator.

        Args:
            window_interval_ms: Window size in milliseconds (e.g., 100 for 0.1s)
            base_feature_keys: List of expected metric names
        """
        self.window_interval_ms = window_interval_ms
        self.base_feature_keys = set(base_feature_keys)

    def compute_window_key(self, ts_str: str, experiment_id: str, entity_id: str) -> tuple:
        """
        Compute window key from timestamp.

        Args:
            ts_str: ISO 8601 timestamp string
            experiment_id: Experiment ID
            entity_id: Entity ID (e.g., "sta_0")

        Returns:
            Tuple of (experiment_id, window_bucket, entity_id)
        """
        # Parse timestamp
        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))

        # Convert to milliseconds since epoch
        ts_ms = int(ts.timestamp() * 1000)

        # Compute window bucket (floor division)
        window_bucket = (ts_ms // self.window_interval_ms) * self.window_interval_ms

        # Convert back to datetime for readability
        window_ts = datetime.fromtimestamp(window_bucket / 1000, tz=timezone.utc)

        return (experiment_id, window_ts.isoformat(), entity_id)

    def aggregate_events(self, events: List[Dict]) -> Dict[tuple, Dict]:
        """
        Aggregate events into windows.

        Args:
            events: List of telemetry event dicts

        Returns:
            Dict mapping window_key -> {metric_name: value, ...}
        """
        windows = {}

        for event in events:
            try:
                # Extract fields
                experiment_id = event.get('experiment_id')
                ts = event.get('ts')
                entity_id = event.get('entity_id')
                metric = event.get('metric')
                value = event.get('value')

                if not all([experiment_id, ts, entity_id, metric, value is not None]):
                    logger.warning(f"Incomplete event: {event}")
                    continue

                # Compute window key
                window_key = self.compute_window_key(ts, experiment_id, entity_id)

                # Initialize window if needed
                if window_key not in windows:
                    windows[window_key] = {}

                # Add metric to window
                windows[window_key][metric] = float(value)

            except Exception as e:
                logger.error(f"Error aggregating event: {e}", exc_info=True)
                continue

        return windows

    def is_window_complete(self, window: Dict) -> bool:
        """
        Check if window has all required base features.

        Args:
            window: Window dict with metric_name: value

        Returns:
            True if all base features present
        """
        window_metrics = set(window.keys())
        return self.base_feature_keys.issubset(window_metrics)

    def fill_missing_metrics(self, window: Dict, strategy: str = 'zero') -> Dict:
        """
        Fill missing metrics in window.

        Args:
            window: Window dict
            strategy: 'zero' or 'last_known' (not implemented yet)

        Returns:
            Window with all base features
        """
        filled_window = window.copy()

        for metric in self.base_feature_keys:
            if metric not in filled_window:
                if strategy == 'zero':
                    filled_window[metric] = 0.0
                    logger.debug(f"Filled missing metric '{metric}' with 0.0")
                # TODO: Implement 'last_known' strategy

        return filled_window
