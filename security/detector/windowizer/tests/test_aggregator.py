"""
Tests for window_aggregator.py
"""

import pytest
from datetime import datetime, timezone
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from window_aggregator import WindowAggregator


def test_compute_window_key():
    """Test window key computation."""
    aggregator = WindowAggregator(
        window_interval_ms=100,
        base_feature_keys=['metric1', 'metric2']
    )

    # Test with specific timestamp
    ts = "2026-01-01T00:00:00.050Z"  # 50ms into second
    key = aggregator.compute_window_key(ts, "exp1", "sta_0")

    # Should be bucketed to 0ms
    assert key[0] == "exp1"
    assert key[2] == "sta_0"
    assert "2026-01-01T00:00:00" in key[1]


def test_aggregate_events():
    """Test event aggregation."""
    aggregator = WindowAggregator(
        window_interval_ms=100,
        base_feature_keys=['throughput', 'delay']
    )

    events = [
        {
            'experiment_id': 'exp1',
            'ts': '2026-01-01T00:00:00.050Z',
            'entity_id': 'sta_0',
            'metric': 'throughput',
            'value': 120.5
        },
        {
            'experiment_id': 'exp1',
            'ts': '2026-01-01T00:00:00.080Z',  # Same window
            'entity_id': 'sta_0',
            'metric': 'delay',
            'value': 2.1
        },
        {
            'experiment_id': 'exp1',
            'ts': '2026-01-01T00:00:00.150Z',  # Different window
            'entity_id': 'sta_0',
            'metric': 'throughput',
            'value': 125.0
        }
    ]

    windows = aggregator.aggregate_events(events)

    # Should have 2 windows
    assert len(windows) == 2

    # Check first window has both metrics
    first_window = list(windows.values())[0]
    assert 'throughput' in first_window
    assert 'delay' in first_window


def test_is_window_complete():
    """Test window completeness check."""
    aggregator = WindowAggregator(
        window_interval_ms=100,
        base_feature_keys=['metric1', 'metric2', 'metric3']
    )

    # Complete window
    complete_window = {'metric1': 1.0, 'metric2': 2.0, 'metric3': 3.0}
    assert aggregator.is_window_complete(complete_window)

    # Incomplete window
    incomplete_window = {'metric1': 1.0, 'metric2': 2.0}
    assert not aggregator.is_window_complete(incomplete_window)


def test_fill_missing_metrics():
    """Test missing metric filling."""
    aggregator = WindowAggregator(
        window_interval_ms=100,
        base_feature_keys=['metric1', 'metric2', 'metric3']
    )

    incomplete_window = {'metric1': 1.0, 'metric2': 2.0}
    filled = aggregator.fill_missing_metrics(incomplete_window, strategy='zero')

    assert 'metric3' in filled
    assert filled['metric3'] == 0.0
    assert filled['metric1'] == 1.0  # Existing values preserved
