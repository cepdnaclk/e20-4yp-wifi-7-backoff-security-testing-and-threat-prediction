"""
Tests for delta_converter.py
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from delta_converter import DeltaConverter


def test_convert_windows():
    """Test delta conversion."""
    converter = DeltaConverter(
        cumulative_counters=['tx_count', 'rx_count']
    )

    windows = [
        {'tx_count': 1000, 'rx_count': 500, 'throughput': 120.0},
        {'tx_count': 1050, 'rx_count': 550, 'throughput': 125.0},
        {'tx_count': 1120, 'rx_count': 610, 'throughput': 130.0},
    ]

    converted = converter.convert_windows(windows, 'exp1', 'sta_0')

    # First window: delta = 0 (no previous)
    assert converted[0]['tx_count'] == 0.0
    assert converted[0]['rx_count'] == 0.0

    # Second window: delta = 50, 50
    assert converted[1]['tx_count'] == 50
    assert converted[1]['rx_count'] == 50

    # Third window: delta = 70, 60
    assert converted[2]['tx_count'] == 70
    assert converted[2]['rx_count'] == 60

    # Non-cumulative metrics unchanged
    assert converted[1]['throughput'] == 125.0


def test_counter_reset():
    """Test handling of counter reset (negative delta)."""
    converter = DeltaConverter(
        cumulative_counters=['tx_count']
    )

    windows = [
        {'tx_count': 1000},
        {'tx_count': 100},  # Counter reset
        {'tx_count': 150},
    ]

    converted = converter.convert_windows(windows, 'exp1', 'sta_0')

    # First: delta = 0
    assert converted[0]['tx_count'] == 0.0

    # Second: counter reset, treat as new counter
    assert converted[1]['tx_count'] == 100

    # Third: delta from reset value
    assert converted[2]['tx_count'] == 50


def test_reset_state():
    """Test state reset."""
    converter = DeltaConverter(cumulative_counters=['tx_count'])

    # Convert some windows to build state
    windows = [{'tx_count': 1000}, {'tx_count': 1050}]
    converter.convert_windows(windows, 'exp1', 'sta_0')

    # Verify state exists
    assert ('exp1', 'sta_0') in converter.state

    # Reset state
    converter.reset_state('exp1', 'sta_0')

    # Verify state cleared
    assert ('exp1', 'sta_0') not in converter.state


def test_multiple_entities():
    """Test delta conversion for multiple entities."""
    converter = DeltaConverter(cumulative_counters=['tx_count'])

    # Entity 1
    windows1 = [{'tx_count': 1000}, {'tx_count': 1050}]
    converted1 = converter.convert_windows(windows1, 'exp1', 'sta_0')

    # Entity 2 (different state)
    windows2 = [{'tx_count': 2000}, {'tx_count': 2100}]
    converted2 = converter.convert_windows(windows2, 'exp1', 'sta_1')

    # Verify independent state
    assert converted1[1]['tx_count'] == 50
    assert converted2[1]['tx_count'] == 100
