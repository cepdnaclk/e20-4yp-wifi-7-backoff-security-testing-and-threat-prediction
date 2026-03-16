"""
Tests for segment_builder.py
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from segment_builder import SegmentBuilder


def test_add_window():
    """Test adding windows to segment builder."""
    builder = SegmentBuilder(segment_length=4)  # Small segment for testing

    # Add windows one by one
    for i in range(3):
        segment = builder.add_window(
            window={'metric1': float(i)},
            experiment_id='exp1',
            entity_id='sta_0',
            window_ts=f'2026-01-01T00:00:0{i}.000Z',
            window_idx=i
        )
        # Should not emit segment yet
        assert segment is None

    # Add 4th window - should emit segment
    segment = builder.add_window(
        window={'metric1': 3.0},
        experiment_id='exp1',
        entity_id='sta_0',
        window_ts='2026-01-01T00:00:03.000Z',
        window_idx=3
    )

    # Should emit complete segment
    assert segment is not None
    assert len(segment['windows']) == 4
    assert segment['window_start_idx'] == 0
    assert segment['window_end_idx'] == 3


def test_multiple_segments():
    """Test emitting multiple segments."""
    builder = SegmentBuilder(segment_length=2)

    # First segment
    builder.add_window({'m': 0}, 'exp1', 'sta_0', 'ts0', 0)
    seg1 = builder.add_window({'m': 1}, 'exp1', 'sta_0', 'ts1', 1)

    assert seg1 is not None
    assert seg1['segment_id'] == 'seg_0'

    # Second segment
    builder.add_window({'m': 2}, 'exp1', 'sta_0', 'ts2', 2)
    seg2 = builder.add_window({'m': 3}, 'exp1', 'sta_0', 'ts3', 3)

    assert seg2 is not None
    assert seg2['segment_id'] == 'seg_1'
    assert seg2['window_start_idx'] == 2


def test_multiple_entities():
    """Test independent buffers for multiple entities."""
    builder = SegmentBuilder(segment_length=2)

    # Entity 1: add 2 windows
    builder.add_window({'m': 0}, 'exp1', 'sta_0', 'ts0', 0)
    seg1 = builder.add_window({'m': 1}, 'exp1', 'sta_0', 'ts1', 1)

    assert seg1 is not None
    assert seg1['entity_id'] == 'sta_0'

    # Entity 2: add 1 window (should not emit yet)
    seg2 = builder.add_window({'m': 0}, 'exp1', 'sta_1', 'ts0', 0)

    assert seg2 is None  # Not enough windows yet


def test_flush_incomplete_segments():
    """Test flushing partial segments."""
    builder = SegmentBuilder(segment_length=4)

    # Add only 2 windows (incomplete segment)
    builder.add_window({'m': 0}, 'exp1', 'sta_0', 'ts0', 0)
    builder.add_window({'m': 1}, 'exp1', 'sta_0', 'ts1', 1)

    # Flush
    partial_segments = builder.flush_incomplete_segments()

    assert len(partial_segments) == 1
    assert len(partial_segments[0]['windows']) == 2
    assert partial_segments[0]['partial'] == True


def test_buffer_status():
    """Test buffer status reporting."""
    builder = SegmentBuilder(segment_length=4)

    # Add windows
    builder.add_window({'m': 0}, 'exp1', 'sta_0', 'ts0', 0)
    builder.add_window({'m': 1}, 'exp1', 'sta_0', 'ts1', 1)

    status = builder.get_buffer_status()

    assert 'exp1/sta_0' in status
    assert status['exp1/sta_0']['buffered_windows'] == 2
    assert status['exp1/sta_0']['progress'] == '2/4'
