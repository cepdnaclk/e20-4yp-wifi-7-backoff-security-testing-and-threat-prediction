"""
Delta Converter
Converts cumulative counters to deltas in temporal order.
"""

from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class DeltaConverter:
    """
    Converts cumulative counters to deltas.

    Maintains state per (experiment_id, entity_id) to track previous values.
    """

    def __init__(self, cumulative_counters: List[str]):
        """
        Initialize converter.

        Args:
            cumulative_counters: List of metric names that are cumulative
        """
        self.cumulative_counters = set(cumulative_counters)
        # State: {(experiment_id, entity_id): {metric: last_value}}
        self.state = {}

    def convert_windows(
        self,
        windows: List[Dict],
        experiment_id: str,
        entity_id: str
    ) -> List[Dict]:
        """
        Convert cumulative counters to deltas for a sequence of windows.

        Args:
            windows: List of window dicts in temporal order
            experiment_id: Experiment ID
            entity_id: Entity ID

        Returns:
            List of windows with deltas applied
        """
        if not windows:
            return []

        state_key = (experiment_id, entity_id)

        # Initialize state if needed
        if state_key not in self.state:
            self.state[state_key] = {}

        previous_values = self.state[state_key]
        converted_windows = []

        # Field name mappings for consistency with training data
        field_name_map = {
            'mac_total_tx': 'mac_tx_delta',
            'mac_total_rx': 'mac_rx_delta',
            'mac_total_ack': 'mac_ack_delta',
            'mac_total_retrans': 'mac_retrans_delta',
            'mac_drop_count': 'mac_drop_delta',
            'phy_drop_count': 'phy_drop_delta'
        }

        for window in windows:
            converted_window = window.copy()

            for metric in self.cumulative_counters:
                if metric in window:
                    current_value = window[metric]

                    if metric in previous_values:
                        # Compute delta
                        delta = current_value - previous_values[metric]

                        # Handle counter reset (negative delta)
                        if delta < 0:
                            logger.warning(
                                f"Negative delta for {metric} "
                                f"(experiment={experiment_id}, entity={entity_id}): "
                                f"{previous_values[metric]} -> {current_value}. "
                                f"Assuming counter reset."
                            )
                            # Treat as new counter starting from 0
                            delta = current_value

                        # Use delta field name to match training data
                        delta_field_name = field_name_map.get(metric, metric)
                        converted_window[delta_field_name] = delta
                        # Remove original cumulative field
                        if metric in converted_window and delta_field_name != metric:
                            del converted_window[metric]
                    else:
                        # First window: no previous value
                        # Set delta to 0 (can't compute delta without baseline)
                        delta_field_name = field_name_map.get(metric, metric)
                        converted_window[delta_field_name] = 0.0
                        # Remove original cumulative field
                        if metric in converted_window and delta_field_name != metric:
                            del converted_window[metric]

                    # Update state with current value for next iteration
                    previous_values[metric] = current_value

            converted_windows.append(converted_window)

        return converted_windows

    def reset_state(self, experiment_id: str = None, entity_id: str = None):
        """
        Reset state for given experiment/entity or all.

        Args:
            experiment_id: Experiment ID (None = all)
            entity_id: Entity ID (None = all for experiment)
        """
        if experiment_id is None:
            # Reset all state
            self.state.clear()
            logger.info("Reset all delta converter state")
        elif entity_id is None:
            # Reset all entities for experiment
            keys_to_delete = [k for k in self.state.keys() if k[0] == experiment_id]
            for key in keys_to_delete:
                del self.state[key]
            logger.info(f"Reset state for experiment {experiment_id}")
        else:
            # Reset specific entity
            state_key = (experiment_id, entity_id)
            if state_key in self.state:
                del self.state[state_key]
                logger.info(f"Reset state for {experiment_id}/{entity_id}")
