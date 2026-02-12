# GCN Detector Service

The GCN detector service performs real-time attack detection on windowed telemetry segments using a Graph Convolutional Network.

## Purpose

Consume windowed feature segments from Kafka, run GCN inference, and emit attack predictions to Kafka and TimescaleDB.

## Data Flow

```
Kafka: wifi7.ml.windowed_features.v1
        (256-window segments)
              ↓
        GCN Detector
    - Load model from registry
    - Build temporal chain graph
    - Run inference (forward pass)
    - Compute predictions + confidence
              ↓
   Kafka: wifi7.security.gcn_predictions.v1
              ↓
   TimescaleDB: public.gcn_predictions
```

## Architecture

**Model**: WiFi7AttackGCN (2-layer GCN)
- Input: 256 windows × 16 features
- Graph: Temporal chain (t ↔ t+1)
- Output: Binary classification (0=Normal, 1=Attack) + confidence

**Hot Reloading**: Watches `twin/registry/gcn/current` symlink for model updates.

## Configuration

See `config.yaml` for full configuration options.

Key settings:
- `model.registry_path`: /app/registry
- `model.active_version`: current (symlink)
- `model.device`: cpu (or cuda for GPU)
- `inference.batch_size`: 32
- `inference.threshold`: 0.5

## Building

```bash
make gcn-detector-build
```

## Running

```bash
# Start as background service
make gcn-detector-run

# View logs
make gcn-detector-logs

# Check health
make gcn-detector-health

# Stop service
make gcn-detector-stop
```

## Health Endpoint

```bash
curl http://localhost:8080/health

{
  "status": "healthy",
  "model_loaded": true,
  "model_version": "v1.0.0",
  "kafka_connected": true,
  "db_connected": true,
  "uptime_seconds": 12345
}
```

## Implementation Status

**Phase 1 (Foundation)**: ✅ Configuration created, model artifacts copied
**Phase 3 (Implementation)**: 🔲 Not started

## Files

- `config.yaml`: Service configuration
- `Dockerfile`: Container definition (to be created in Phase 3)
- `requirements.txt`: Python dependencies (to be created in Phase 3)
- `detector.py`: Main service (to be created in Phase 3)
- `model_loader.py`: Model management (to be created in Phase 3)
- `inference_engine.py`: Inference logic (to be created in Phase 3)
- `graph_builder.py`: PyG graph creation (to be created in Phase 3)
- `feature_processor.py`: Feature engineering (to be created in Phase 3)
- `kafka_client.py`: Kafka I/O (to be created in Phase 3)
- `db_writer.py`: DB persistence (to be created in Phase 3)
- `health_api.py`: Health endpoint (to be created in Phase 3)
- `gcn_src/`: GCN model source (to be copied from wifi7_gcn_attack_detection)
- `tests/`: Unit tests (to be created in Phase 3)
