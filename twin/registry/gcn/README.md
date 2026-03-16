# GCN Model Registry

This directory contains versioned GCN model artifacts for WiFi 7 attack detection.

## Directory Structure

```
twin/registry/gcn/
├── v1.0.0/                      # Model version 1.0.0
│   ├── best_model.pt            # PyTorch model weights
│   ├── scaler.json              # StandardScaler parameters
│   ├── config.yaml              # Model hyperparameters
│   ├── test_results.json        # Evaluation metrics
│   └── metadata.json            # Training metadata (optional)
├── v1.1.0/                      # Future versions...
├── current -> v1.0.0            # Symlink to active version
└── README.md                    # This file
```

## Model Versioning

Model versions follow semantic versioning: `vMAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (e.g., different input features)
- **MINOR**: Model improvements (e.g., better architecture)
- **PATCH**: Bug fixes or retraining on same architecture

## Active Model

The `current` symlink points to the currently deployed model version. The GCN detector service loads the model from this symlink.

To deploy a new model version:
```bash
make gcn-deploy VERSION=v1.1.0
```

This updates the symlink and triggers hot-reloading in the detector service.

## Model Artifacts

Each model version directory must contain:

1. **best_model.pt**: PyTorch model state dict
2. **scaler.json**: StandardScaler parameters (mean, std for each feature)
3. **config.yaml**: Model hyperparameters (in_channels, hidden_channels, etc.)
4. **test_results.json**: Performance metrics on test set

Optional:
- **metadata.json**: Training dataset info, git commit, author, notes

## Model Deployment Workflow

```bash
# 1. Train new model
make gcn-train OUTPUT_DIR=twin/registry/gcn/v1.1.0

# 2. Evaluate on test set
make gcn-evaluate MODEL=v1.1.0

# 3. Compare with current model
python scripts/compare_models.py --baseline current --candidate v1.1.0

# 4. Deploy if better
make gcn-deploy VERSION=v1.1.0

# 5. Rollback if issues
make gcn-deploy VERSION=v1.0.0
```

## Current Model: v1.0.0

**Performance**:
- Test Accuracy: 95.23%
- Test F1: 94.81%
- Test Precision: 96.12%
- Test Recall: 93.54%
- ROC-AUC: 98.91%

**Training Dataset**: Wifi7_Datasets (3 scenarios: Normal, Positive, Negative)

**Architecture**:
- Input: 16 features (13 base + 3 derived)
- Hidden: 64 dimensions
- Layers: 2 GCN layers
- Pooling: Mean pooling
- Segment length: 256 windows

**Trained by**: cobrakali
**Git commit**: 9f0139f
**Deployed**: 2026-02-10
