"""
Training configuration for WiFi 7 attack detection.

This module defines the TrainingConfig dataclass that contains all
hyperparameters and settings for training the GCN model.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TrainingConfig:
    """
    Training hyperparameters and paths.

    This dataclass encapsulates all configuration needed for training,
    including model architecture, data processing, training hyperparameters,
    and file paths.
    """

    # ========== Model Architecture ==========
    in_channels: int = 13  # 13 base features (NO bias!) or 16 with derived
    hidden_channels: int = 64  # Hidden dimension
    num_layers: int = 2  # Number of GCN layers
    dropout: float = 0.3  # Dropout rate
    pooling: str = 'mean'  # 'mean', 'max', or 'concat'

    # ========== Data Processing ==========
    segment_length: int = 256  # Windows per segment (L)
    stride: int = 256  # Segmentation stride (None = non-overlapping)
    use_derived_features: bool = True  # Add ratio features
    test_size: float = 0.15  # Test set fraction
    val_size: float = 0.15  # Validation set fraction

    # ========== Training Hyperparameters ==========
    batch_size: int = 32  # Batch size
    learning_rate: float = 1e-3  # Learning rate
    weight_decay: float = 1e-4  # L2 regularization
    max_epochs: int = 150  # Maximum epochs
    patience: int = 20  # Early stopping patience

    # ========== Class Imbalance ==========
    use_class_weights: bool = True  # Use class weights in loss

    # ========== Paths ==========
    data_root: Path = field(default_factory=lambda: Path("./data"))
    checkpoint_dir: Path = field(default_factory=lambda: Path("./checkpoints"))
    log_dir: Path = field(default_factory=lambda: Path("./logs"))

    # ========== Reproducibility ==========
    random_seed: int = 42  # Random seed for reproducibility

    # ========== Device ==========
    device: Optional[str] = None  # 'cuda' or 'cpu' (None = auto-detect)

    def __post_init__(self):
        """Post-initialization: Ensure paths are Path objects."""
        if not isinstance(self.data_root, Path):
            self.data_root = Path(self.data_root)

        if not isinstance(self.checkpoint_dir, Path):
            self.checkpoint_dir = Path(self.checkpoint_dir)

        if not isinstance(self.log_dir, Path):
            self.log_dir = Path(self.log_dir)

        # Update in_channels based on use_derived_features
        if self.use_derived_features:
            self.in_channels = 16  # 13 base + 3 derived
        else:
            self.in_channels = 13  # 13 base only

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            # Model
            'in_channels': self.in_channels,
            'hidden_channels': self.hidden_channels,
            'num_layers': self.num_layers,
            'dropout': self.dropout,
            'pooling': self.pooling,

            # Data
            'segment_length': self.segment_length,
            'stride': self.stride,
            'use_derived_features': self.use_derived_features,
            'test_size': self.test_size,
            'val_size': self.val_size,

            # Training
            'batch_size': self.batch_size,
            'learning_rate': self.learning_rate,
            'weight_decay': self.weight_decay,
            'max_epochs': self.max_epochs,
            'patience': self.patience,

            # Other
            'use_class_weights': self.use_class_weights,
            'random_seed': self.random_seed,
            'data_root': str(self.data_root),
            'checkpoint_dir': str(self.checkpoint_dir),
            'log_dir': str(self.log_dir),
            'device': self.device
        }

    def save(self, path: Path):
        """Save configuration to YAML file."""
        import yaml
        with open(path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)

    @classmethod
    def from_dict(cls, config_dict: dict) -> 'TrainingConfig':
        """Create config from dictionary."""
        return cls(**config_dict)

    @classmethod
    def load(cls, path: Path) -> 'TrainingConfig':
        """Load configuration from YAML file."""
        import yaml
        with open(path, 'r') as f:
            config_dict = yaml.safe_load(f)
        return cls.from_dict(config_dict)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"TrainingConfig(\n"
            f"  Model: in={self.in_channels}, hidden={self.hidden_channels}, "
            f"layers={self.num_layers}, dropout={self.dropout}\n"
            f"  Data: L={self.segment_length}, stride={self.stride}, "
            f"derived={self.use_derived_features}\n"
            f"  Training: batch={self.batch_size}, lr={self.learning_rate}, "
            f"epochs={self.max_epochs}, patience={self.patience}\n"
            f"  Paths: data={self.data_root}, ckpt={self.checkpoint_dir}\n"
            f")"
        )


# Predefined configurations for different scenarios

DEFAULT_CONFIG = TrainingConfig()

FAST_CONFIG = TrainingConfig(
    # Smaller model for quick experimentation
    hidden_channels=32,
    num_layers=2,
    batch_size=64,
    max_epochs=50,
    patience=10,
    segment_length=128  # Shorter segments
)

LARGE_CONFIG = TrainingConfig(
    # Larger model for better performance
    hidden_channels=128,
    num_layers=3,
    batch_size=16,
    max_epochs=200,
    patience=25,
    segment_length=256
)

CPU_CONFIG = TrainingConfig(
    # Optimized for CPU training
    hidden_channels=64,
    num_layers=2,
    batch_size=8,  # Smaller batch for CPU
    max_epochs=100,
    device='cpu'
)


if __name__ == "__main__":
    # Test configuration
    print("Default Configuration:")
    print(DEFAULT_CONFIG)
    print()

    print("Configuration Dictionary:")
    config_dict = DEFAULT_CONFIG.to_dict()
    for key, value in config_dict.items():
        print(f"  {key:25s}: {value}")
    print()

    # Test save/load
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        temp_path = Path(f.name)

    DEFAULT_CONFIG.save(temp_path)
    loaded_config = TrainingConfig.load(temp_path)

    print("Loaded Configuration:")
    print(loaded_config)

    temp_path.unlink()  # Clean up

    print("\n✓ Config module working correctly!")
