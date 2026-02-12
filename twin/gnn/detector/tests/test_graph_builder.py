"""
Test GraphBuilder component.
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph_builder import GraphBuilder


class TestGraphBuilder(unittest.TestCase):
    """Test graph building for GCN inference."""

    def setUp(self):
        """Initialize graph builder."""
        self.feature_keys = [
            'net_throughput_mbps',
            'net_avg_delay_ms',
            'mac_total_tx'
        ]

        self.builder = GraphBuilder(feature_keys=self.feature_keys)

    def test_build_single_graph(self):
        """Test building graph from single segment."""
        segment = {
            'experiment_id': 'exp-001',
            'entity_id': 'sta-0',
            'segment_id': 'seg-001',
            'window_start_idx': 0,
            'window_end_idx': 255,
            'ts_start': '2025-01-01T00:00:00Z',
            'ts_end': '2025-01-01T00:25:36Z',
            'windows': [
                {
                    'net_throughput_mbps': 10.5,
                    'net_avg_delay_ms': 5.2,
                    'mac_total_tx': 100
                },
                {
                    'net_throughput_mbps': 11.0,
                    'net_avg_delay_ms': 5.5,
                    'mac_total_tx': 110
                },
                {
                    'net_throughput_mbps': 10.8,
                    'net_avg_delay_ms': 5.3,
                    'mac_total_tx': 105
                }
            ]
        }

        graph = self.builder.build_graph(segment)

        # Check graph properties
        self.assertEqual(graph.num_nodes, 3)
        self.assertEqual(graph.x.shape, (3, 3))  # 3 nodes, 3 features

        # Check edge structure (temporal chain)
        # Should have edges: 0->1, 1->0, 1->2, 2->1
        self.assertEqual(graph.edge_index.shape[1], 4)

    def test_build_batch(self):
        """Test building batched graph from multiple segments."""
        segments = []
        for i in range(3):
            segment = {
                'experiment_id': f'exp-{i:03d}',
                'entity_id': 'sta-0',
                'segment_id': f'seg-{i:03d}',
                'window_start_idx': 0,
                'window_end_idx': 255,
                'ts_start': '2025-01-01T00:00:00Z',
                'ts_end': '2025-01-01T00:25:36Z',
                'windows': [
                    {
                        'net_throughput_mbps': 10.0 + i,
                        'net_avg_delay_ms': 5.0,
                        'mac_total_tx': 100
                    },
                    {
                        'net_throughput_mbps': 11.0 + i,
                        'net_avg_delay_ms': 5.5,
                        'mac_total_tx': 110
                    }
                ]
            }
            segments.append(segment)

        batch = self.builder.build_batch(segments)

        # Check batch properties
        self.assertEqual(batch.num_graphs, 3)
        self.assertEqual(batch.num_nodes, 6)  # 2 nodes per graph
        self.assertEqual(batch.x.shape, (6, 3))  # 6 nodes, 3 features

        # Check batch assignment
        self.assertEqual(batch.batch.tolist(), [0, 0, 1, 1, 2, 2])

    def test_missing_features(self):
        """Test handling of missing features (should default to 0.0)."""
        segment = {
            'experiment_id': 'exp-001',
            'entity_id': 'sta-0',
            'segment_id': 'seg-001',
            'window_start_idx': 0,
            'window_end_idx': 255,
            'ts_start': '2025-01-01T00:00:00Z',
            'ts_end': '2025-01-01T00:25:36Z',
            'windows': [
                {
                    'net_throughput_mbps': 10.5
                    # Missing other features
                }
            ]
        }

        graph = self.builder.build_graph(segment)

        # Should have filled missing features with 0.0
        self.assertEqual(graph.x[0, 0].item(), 10.5)
        self.assertEqual(graph.x[0, 1].item(), 0.0)
        self.assertEqual(graph.x[0, 2].item(), 0.0)

    def test_empty_segment(self):
        """Test handling of empty segment."""
        segment = {
            'experiment_id': 'exp-001',
            'entity_id': 'sta-0',
            'segment_id': 'seg-001',
            'window_start_idx': 0,
            'window_end_idx': 255,
            'ts_start': '2025-01-01T00:00:00Z',
            'ts_end': '2025-01-01T00:25:36Z',
            'windows': []
        }

        graph = self.builder.build_graph(segment)

        # Should return empty graph
        self.assertEqual(graph.num_nodes, 0)


if __name__ == '__main__':
    unittest.main()
