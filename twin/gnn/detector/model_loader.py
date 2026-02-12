"""
Model Loader
Loads GCN model, scaler, and configuration from model registry.
Supports hot-reloading when model changes.
"""

import torch
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Optional
import time
import os

# Import GCN model
from gcn_src.models.gcn import WiFi7AttackGCN

logger = logging.getLogger(__name__)


class ModelLoader:
    """
    Loads and manages GCN model artifacts.

    Supports hot-reloading by watching the 'current' symlink.
    """

    def __init__(self, registry_path: str, active_version: str = 'current', device: str = 'cpu'):
        """
        Initialize model loader.

        Args:
            registry_path: Path to model registry (e.g., /app/registry)
            active_version: Version to load (e.g., 'current' or 'v1.0.0')
            device: Device to load model on ('cpu' or 'cuda')
        """
        self.registry_path = Path(registry_path)
        self.active_version = active_version
        self.device = torch.device(device)

        self.model = None
        self.scaler = None
        self.config = None
        self.loaded_version = None
        self.loaded_path = None

        # For hot-reloading
        self.last_check_time = 0
        self.symlink_mtime = 0

    def load_model(self) -> bool:
        """
        Load model from registry.

        Returns:
            True if model loaded successfully
        """
        try:
            # Resolve version path
            version_path = self.registry_path / self.active_version

            if not version_path.exists():
                logger.error(f"Model path does not exist: {version_path}")
                return False

            # If active_version is a symlink, resolve it
            if version_path.is_symlink():
                resolved_path = version_path.resolve()
                version_name = resolved_path.name
            else:
                resolved_path = version_path
                version_name = self.active_version

            logger.info(f"Loading model from: {resolved_path} (version: {version_name})")

            # Load configuration
            config_path = resolved_path / 'config.yaml'
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)

            logger.info(f"Loaded config: {self.config}")

            # Load scaler
            scaler_path = resolved_path / 'scaler.json'
            with open(scaler_path, 'r') as f:
                self.scaler = json.load(f)

            logger.info(f"Loaded scaler with {len(self.scaler['mean'])} features")

            # Create model
            self.model = WiFi7AttackGCN(
                in_channels=self.config['in_channels'],
                hidden_channels=self.config['hidden_channels'],
                num_layers=self.config['num_layers'],
                dropout=self.config['dropout'],
                pooling=self.config['pooling']
            )

            # Load weights
            model_path = resolved_path / 'best_model.pt'
            checkpoint = torch.load(model_path, map_location=self.device)

            # Handle both checkpoint format and direct state_dict format
            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                state_dict = checkpoint['model_state_dict']
            else:
                state_dict = checkpoint

            self.model.load_state_dict(state_dict)

            # Move to device and set to eval mode
            self.model.to(self.device)
            self.model.eval()

            # Update loaded info
            self.loaded_version = version_name
            self.loaded_path = str(resolved_path)

            logger.info(f"Model loaded successfully: {version_name}")
            logger.info(f"  Device: {self.device}")
            logger.info(f"  Parameters: {self.model.count_parameters():,}")

            return True

        except Exception as e:
            logger.error(f"Error loading model: {e}", exc_info=True)
            return False

    def check_for_updates(self) -> bool:
        """
        Check if model has been updated (symlink changed).

        Returns:
            True if model should be reloaded
        """
        try:
            # Only check every 60 seconds
            current_time = time.time()
            if current_time - self.last_check_time < 60:
                return False

            self.last_check_time = current_time

            # Check if symlink has changed
            symlink_path = self.registry_path / self.active_version

            if not symlink_path.is_symlink():
                return False

            # Get symlink modification time
            stat = os.lstat(symlink_path)
            mtime = stat.st_mtime

            if self.symlink_mtime == 0:
                # First check
                self.symlink_mtime = mtime
                return False

            if mtime > self.symlink_mtime:
                logger.info("Model symlink has changed, reloading...")
                self.symlink_mtime = mtime
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking for model updates: {e}")
            return False

    def reload_if_needed(self) -> bool:
        """
        Reload model if symlink has changed.

        Returns:
            True if model was reloaded
        """
        if self.check_for_updates():
            logger.info("Hot-reloading model...")
            success = self.load_model()
            if success:
                logger.info(f"Model hot-reloaded successfully: {self.loaded_version}")
            else:
                logger.error("Model hot-reload failed")
            return success
        return False

    def get_model_info(self) -> Dict:
        """
        Get information about loaded model.

        Returns:
            Dict with model metadata
        """
        if self.model is None:
            return {'loaded': False}

        return {
            'loaded': True,
            'version': self.loaded_version,
            'path': self.loaded_path,
            'device': str(self.device),
            'parameters': self.model.count_parameters(),
            'config': self.config
        }
