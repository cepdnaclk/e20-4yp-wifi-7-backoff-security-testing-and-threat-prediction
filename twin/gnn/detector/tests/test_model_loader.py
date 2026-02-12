"""
Test ModelLoader component.
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


class TestModelLoader(unittest.TestCase):
    """Test model loading and hot-reloading."""

    def setUp(self):
        """Create temporary registry directory."""
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

        # Create mock model (random weights)
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

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_load_model(self):
        """Test loading model from registry."""
        loader = ModelLoader(
            registry_path=str(self.registry_path),
            active_version='current',
            device='cpu'
        )

        success = loader.load_model()
        self.assertTrue(success)
        self.assertIsNotNone(loader.model)
        self.assertEqual(loader.loaded_version, 'v1.0.0')

    def test_model_inference(self):
        """Test that loaded model can run inference."""
        loader = ModelLoader(
            registry_path=str(self.registry_path),
            active_version='current',
            device='cpu'
        )

        loader.load_model()

        # Create dummy input
        x = torch.randn(10, 16)  # 10 nodes, 16 features
        edge_index = torch.tensor([[0, 1, 2], [1, 2, 3]], dtype=torch.long)
        batch = torch.zeros(10, dtype=torch.long)

        # Run inference
        with torch.no_grad():
            output = loader.model(x, edge_index, batch)

        self.assertEqual(output.shape, (1, 2))  # 1 graph, 2 classes

    def test_invalid_version(self):
        """Test loading invalid version fails gracefully."""
        loader = ModelLoader(
            registry_path=str(self.registry_path),
            active_version='v99.0.0',
            device='cpu'
        )

        success = loader.load_model()
        self.assertFalse(success)

    def test_scaler_loaded(self):
        """Test scaler is loaded correctly."""
        loader = ModelLoader(
            registry_path=str(self.registry_path),
            active_version='current',
            device='cpu'
        )

        loader.load_model()

        self.assertIsNotNone(loader.scaler)
        self.assertIn('mean', loader.scaler)
        self.assertIn('scale', loader.scaler)
        self.assertEqual(len(loader.scaler['mean']), 16)


if __name__ == '__main__':
    unittest.main()
