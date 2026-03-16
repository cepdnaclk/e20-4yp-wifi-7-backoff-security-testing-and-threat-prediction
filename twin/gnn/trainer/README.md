# GCN Trainer

On-demand training pipeline for GCN models.

## Purpose

Train new GCN models on labeled telemetry data and deploy to the model registry.

## Usage

```bash
# Train new model on existing datasets
make gcn-train \
  DATA_DIR=/path/to/Wifi7_Datasets \
  OUTPUT_DIR=twin/registry/gcn/v1.1.0

# Export data from DB and train
make gcn-export-data \
  EXP_IDS="exp1,exp2,exp3" \
  LABELS="0,1,0" \
  OUTPUT=data/new_training

make gcn-train \
  DATA_DIR=data/new_training \
  OUTPUT_DIR=twin/registry/gcn/v1.1.0

# Evaluate model
make gcn-evaluate MODEL=v1.1.0

# Deploy model
make gcn-deploy VERSION=v1.1.0
```

## Configuration

See `training.yaml` for full configuration options.

Key settings:
- `model.in_channels`: 16 (13 base + 3 derived)
- `model.hidden_channels`: 64
- `model.num_layers`: 2
- `training.batch_size`: 32
- `training.max_epochs`: 150
- `training.patience`: 20 (early stopping)

## Implementation Status

**Phase 1 (Foundation)**: ✅ Configuration created
**Phase 6 (Implementation)**: 🔲 Not started

## Files

- `training.yaml`: Training configuration
- `Dockerfile`: Container definition (to be created in Phase 6)
- `requirements.txt`: Python dependencies (to be created in Phase 6)
- `train.py`: Training script (to be created in Phase 6)
- `data_exporter.py`: Export from DB (to be created in Phase 6)
- `evaluator.py`: Model evaluation (to be created in Phase 6)
- `deployer.py`: Model deployment (to be created in Phase 6)
- `tests/`: Unit tests (to be created in Phase 6)
