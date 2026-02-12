"""
Test InferenceEngine component.
"""

import unittest
import tempfile
import shutil
import json
import yaml
import torch
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from model_loader import ModelLoader
from inference_engine import InferenceEngine


class TestInferenceEngine(unittest.TestCase):
    """Test inference engine."""

    def setUp(self):
        """Create temporary model and initialize engine."""
        self.temp_dir = tempfile.mkdtemp()
        self.registry_path = Path(self.temp_dir) / "registry"
        self.registry_path.mkdir()

        # Create mock v1.0.0 model
        self.version_path = self.registry_path / "v1.0.0"
        self.version_path.mkdir()

        # Create mock config
        config = {
            'model': {
                'hidden_dim': 64,
                'num_layers': 2,
                'dropout': 0.3,
                'num_classes': 2
            },
            'features': {
                'base': [
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
                ],
                'derived': [
                    'retrans_rate',
                    'drop_rate',
                    'throughput_per_flow'
                ]
            }
        }

        with open(self.version_path / 'config.yaml', 'w') as f:
            yaml.dump(config, f)

        # Create mock scaler
        scaler = {
            'mean': [0.0] * 16,
            'scale': [1.0] * 16
        }

        with open(self.version_path / 'scaler.json', 'w') as f:
            json.dump(scaler, f)

        # Create mock model
        from gcn_src.models.gcn import WiFi7AttackGCN
        model = WiFi7AttackGCN(
            num_features=16,
            hidden_dim=64,
            num_layers=2,
            dropout=0.3,
            num_classes=2
        )
        torch.save(model.state_dict(), self.version_path / 'best_model.pt')

        # Create symlink
        current_link = self.registry_path / 'current'
        current_link.symlink_to('v1.0.0')

        # Initialize model loader and engine
        self.model_loader = ModelLoader(
            registry_path=str(self.registry_path),
            active_version='current',
            device='cpu'
        )
        self.model_loader.load_model()

        self.engine = InferenceEngine(
            model_loader=self.model_loader,
            use_derived_features=True,
            threshold=0.5,
            batch_size=2
        )
        self.engine.initialize()

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_predict_single_segment(self):
        """Test prediction on single segment."""
        segment = self._create_mock_segment('exp-001', 'sta-0', 'seg-001')

        predictions = self.engine.predict([segment])

        self.assertEqual(len(predictions), 1)
        pred = predictions[0]

        # Check prediction structure
        self.assertIn('experiment_id', pred)
        self.assertIn('entity_id', pred)
        self.assertIn('segment_id', pred)
        self.assertIn('prediction', pred)
        self.assertIn('confidence', pred)
        self.assertIn('probabilities', pred)
        self.assertIn('model_version', pred)

        # Check prediction values
        self.assertIn(pred['prediction'], [0, 1])
        self.assertTrue(0.0 <= pred['confidence'] <= 1.0)
        self.assertEqual(len(pred['probabilities']), 2)

    def test_predict_batch(self):
        """Test prediction on multiple segments."""
        segments = [
            self._create_mock_segment('exp-001', 'sta-0', 'seg-001'),
            self._create_mock_segment('exp-001', 'sta-1', 'seg-002'),
            self._create_mock_segment('exp-002', 'sta-0', 'seg-003')
        ]

        predictions = self.engine.predict(segments)

        self.assertEqual(len(predictions), 3)

        # Check each prediction
        for i, pred in enumerate(predictions):
            self.assertEqual(pred['experiment_id'], segments[i]['experiment_id'])
            self.assertEqual(pred['entity_id'], segments[i]['entity_id'])
            self.assertEqual(pred['segment_id'], segments[i]['segment_id'])

    def test_derived_features(self):
        """Test that derived features are added."""
        segment = self._create_mock_segment('exp-001', 'sta-0', 'seg-001')

        # Should add retrans_rate, drop_rate, throughput_per_flow
        predictions = self.engine.predict([segment])

        # If successful, derived features were computed
        self.assertEqual(len(predictions), 1)

    def test_empty_input(self):
        """Test handling of empty input."""
        predictions = self.engine.predict([])

        self.assertEqual(len(predictions), 0)

    def _create_mock_segment(self, exp_id, entity_id, seg_id):
        """Create mock segment for testing."""
        windows = []
        for i in range(10):
            window = {
                'net_throughput_mbps': 10.0 + i * 0.1,
                'net_avg_delay_ms': 5.0,
                'net_avg_jitter_ms': 1.0,
                'net_packet_loss_ratio': 0.01,
                'net_active_flows': 5,
                'mac_total_tx': 100 + i * 10,
                'mac_total_rx': 95 + i * 10,
                'mac_total_ack': 90 + i * 10,
                'mac_total_retrans': 5 + i,
                'mac_drop_count': 2,
                'phy_drop_count': 1,
                'avg_backoff_slots': 3.5,
                'channel_busy_ratio': 0.3
            }
            windows.append(window)

        return {
            'experiment_id': exp_id,
            'entity_id': entity_id,
            'segment_id': seg_id,
            'window_start_idx': 0,
            'window_end_idx': 255,
            'ts_start': '2025-01-01T00:00:00Z',
            'ts_end': '2025-01-01T00:25:36Z',
            'windows': windows
        }


if __name__ == '__main__':
    unittest.main()
