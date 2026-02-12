# WP8: GCN Attack Detection Integration - Comprehensive Implementation Plan

## Executive Summary

Integrate the WiFi7 GCN attack detection model (`wifi7_gcn_attack_detection`) into the existing digital twin pipeline as a **long-running, real-time inference service**. The system will consume live telemetry from ns-3 simulations (and future live sensors), perform real-time attack detection using a Graph Convolutional Network, and persist predictions to the database and Kafka for downstream consumption.

**Key Design Principles:**
- Inference runs continuously as a long-running service
- Training runs on-demand via dedicated container
- Kafka is the real-time source of truth
- Database is the system of record for historical analysis
- Model artifacts are versioned and hot-swappable
- No data leakage (bias never used as input feature)

---

## Table of Contents

1. [Current State](#current-state)
2. [Target Architecture](#target-architecture)
3. [Component Specifications](#component-specifications)
4. [Data Flow & Schemas](#data-flow--schemas)
5. [Implementation Phases](#implementation-phases)
6. [File Structure](#file-structure)
7. [Configuration Management](#configuration-management)
8. [Deployment & Orchestration](#deployment--orchestration)
9. [Testing Strategy](#testing-strategy)
10. [Monitoring & Observability](#monitoring--observability)
11. [Error Handling & Resilience](#error-handling--resilience)
12. [Performance Optimization](#performance-optimization)
13. [Model Registry & Versioning](#model-registry--versioning)
14. [Training Pipeline](#training-pipeline)
15. [Live Sensor Integration](#live-sensor-integration)
16. [Security & Compliance](#security--compliance)
17. [Rollout Plan](#rollout-plan)
18. [Success Criteria](#success-criteria)

---

## Current State

### Existing Pipeline
```
ns-3 simulation → telemetry.jsonl → ns3-exporter → Kafka (wifi7.telemetry.v0_1)
                                                           ↓
                                                      harmonizer
                                                           ↓
                                                    TimescaleDB (public.metrics)
                                                           ↓
                                                       Grafana
```

### Telemetry Contract
- **Kafka Topic**: `wifi7.telemetry.v0_1`
- **Format**: JSONL with fields:
  - `experiment_id`, `ts`, `entity_id`, `metric`, `value`, `unit`, `source`
- **Window Interval**: 0.1s (100ms) as defined in `convert_mlo_json_to_jsonl.sh`
- **Metrics**: 13 base features required by GCN model

### GCN Model
- **Location**: `/home/cobrakali/github/wifi7_gcn_attack_detection`
- **Architecture**: 2-layer GCN with temporal chain graph
- **Input**: Sequences of 256 windows (L=256), 13 or 16 features per window
- **Output**: Binary classification (0=Normal, 1=Attack) with confidence scores
- **Model Artifacts**:
  - `checkpoints/best_model.pt` (110KB PyTorch model)
  - `checkpoints/scaler.json` (StandardScaler parameters)
  - `checkpoints/config.yaml` (model hyperparameters)

### GCN Feature Requirements
**Base Features (13):**
- `net_throughput_mbps`, `net_avg_delay_ms`, `net_avg_jitter_ms`, `net_packet_loss_ratio`, `net_active_flows`
- `mac_total_tx`, `mac_total_rx`, `mac_total_ack`, `mac_total_retrans`, `mac_drop_count`, `phy_drop_count`
- `avg_backoff_slots`, `channel_busy_ratio`

**Derived Features (optional, +3):**
- `retrans_rate`, `drop_rate`, `throughput_per_flow`

**Critical**: `bias` field is NEVER used as input (only for ground truth labels in training)

---

## Target Architecture

### Complete Data Flow
```
┌──────────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                      │
├──────────────────────────────────────────────────────────────────────────┤
│  ns-3 Simulation                    Future: Live Sensors (WiFi Routers)  │
│       ↓                                                  ↓                │
│  telemetry.jsonl                              Live JSONL Stream          │
└──────────────────────────────────────────────────────────────────────────┘
                                     ↓
                              ns3-exporter (existing)
                                     ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                    KAFKA: wifi7.telemetry.v0_1                           │
│              (Per-metric events, experiment_id, ts, value)               │
└──────────────────────────────────────────────────────────────────────────┘
                     ↓                              ↓
         ┌───────────────────┐          ┌──────────────────────┐
         │   HARMONIZER      │          │   WINDOWIZER (NEW)   │
         │   (existing)      │          │                      │
         │                   │          │ - Group by window    │
         │ Raw metrics →     │          │ - Aggregate features │
         │ TimescaleDB       │          │ - Convert to deltas  │
         └───────────────────┘          │ - Build segments     │
                                        │   (L=256 windows)    │
                                        └──────────────────────┘
                                                   ↓
                              Kafka: wifi7.ml.windowed_features.v1
                                                   ↓
                                    ┌──────────────────────────┐
                                    │  GCN DETECTOR (NEW)      │
                                    │                          │
                                    │ - Load model artifacts   │
                                    │ - Build temporal graph   │
                                    │ - Run inference          │
                                    │ - Emit predictions       │
                                    └──────────────────────────┘
                                         ↓              ↓
                    ┌────────────────────┴──────────────┴────────────┐
                    ↓                                                 ↓
     Kafka: wifi7.security.gcn_predictions.v1            TimescaleDB
                    ↓                                      public.gcn_predictions
         ┌──────────────────────┐                                   ↓
         │  ACTUATION (FUTURE)  │                          ┌─────────────────┐
         │  - Policy engine     │                          │   GRAFANA       │
         │  - Mitigation        │                          │   - Dashboards  │
         └──────────────────────┘                          │   - Alerts      │
                                                            └─────────────────┘
```

### Service Topology

| Service | Type | Purpose | Connects To |
|---------|------|---------|-------------|
| **harmonizer** | Long-running | Raw metric ingestion | Kafka → TimescaleDB |
| **windowizer** | Long-running | Window aggregation & feature engineering | Kafka → Kafka |
| **gcn-detector** | Long-running | Real-time attack detection | Kafka → Kafka + DB |
| **gcn-trainer** | On-demand | Model training & updates | DB → Model Registry |

---

## Component Specifications

### 1. Windowizer Service

**Purpose**: Consume raw telemetry events, group them into time windows, compute features, and emit window batches for inference.

**Location**: `security/detector/windowizer/`

**Key Responsibilities**:
1. Subscribe to `wifi7.telemetry.v0_1` Kafka topic
2. Group events by `(experiment_id, timestamp_bucket, entity_id)`
3. Aggregate 13 base metrics per window
4. Compute deltas for cumulative counters (in temporal order)
5. Buffer windows into segments of length L=256
6. Emit complete segments to `wifi7.ml.windowed_features.v1`

**Input**:
```json
{
  "experiment_id": "20260210-1400-wifi-example-42",
  "ts": "2026-02-10T14:00:05.100Z",
  "entity_id": "sta_0",
  "metric": "net_throughput_mbps",
  "value": 125.4,
  "unit": "Mbps",
  "source": "ns3"
}
```

**Output**:
```json
{
  "experiment_id": "20260210-1400-wifi-example-42",
  "segment_id": "seg_0",
  "window_start_idx": 0,
  "window_end_idx": 255,
  "entity_id": "sta_0",
  "windows": [
    {
      "window_idx": 0,
      "ts": "2026-02-10T14:00:00.000Z",
      "net_throughput_mbps": 120.5,
      "net_avg_delay_ms": 2.1,
      ... // all 13 base features (deltas applied)
    },
    ... // 256 windows total
  ]
}
```

**Configuration** (`windowizer.yaml`):
```yaml
kafka:
  input_topic: wifi7.telemetry.v0_1
  output_topic: wifi7.ml.windowed_features.v1
  brokers: bus-redpanda:9092
  consumer_group: windowizer-gcn-v1
  auto_offset_reset: latest

windowing:
  segment_length: 256          # L: number of windows per segment
  window_interval_ms: 100      # 0.1s window size
  timeout_ms: 5000             # Wait 5s for incomplete windows
  overlap: 0                   # Non-overlapping segments (stride = segment_length)

features:
  base_feature_keys:
    - net_throughput_mbps
    - net_avg_delay_ms
    - net_avg_jitter_ms
    - net_packet_loss_ratio
    - net_active_flows
    - mac_total_tx
    - mac_total_rx
    - mac_total_ack
    - mac_total_retrans
    - mac_drop_count
    - phy_drop_count
    - avg_backoff_slots
    - channel_busy_ratio

  cumulative_counters:        # Apply delta conversion
    - mac_total_tx
    - mac_total_rx
    - mac_total_ack
    - mac_total_retrans
    - mac_drop_count
    - phy_drop_count

logging:
  level: INFO
  format: json
```

**State Management**:
- In-memory buffer per `(experiment_id, entity_id)`
- Tracks last seen timestamp and cumulative values
- Flushes on segment completion or timeout
- Optional Redis for multi-instance deployment (future)

**Error Handling**:
- Missing metrics: Fill with 0.0 or last known value (configurable)
- Late arrivals: Configurable grace period (5s default)
- Malformed events: Log and skip
- Kafka failures: Exponential backoff + DLQ

---

### 2. GCN Detector Service

**Purpose**: Consume windowed feature segments, run GCN inference, and emit attack predictions.

**Location**: `twin/gnn/detector/`

**Key Responsibilities**:
1. Subscribe to `wifi7.ml.windowed_features.v1`
2. Load model artifacts from `twin/registry/gcn/<version>/`
3. Convert windows to PyTorch Geometric graph format
4. Run inference (forward pass)
5. Emit predictions to Kafka and DB

**Input**: Windowed features (from windowizer)

**Output (Kafka)**:
```json
{
  "experiment_id": "20260210-1400-wifi-example-42",
  "segment_id": "seg_0",
  "entity_id": "sta_0",
  "ts_start": "2026-02-10T14:00:00.000Z",
  "ts_end": "2026-02-10T14:00:25.500Z",
  "window_start_idx": 0,
  "window_end_idx": 255,
  "prediction": 1,                    // 0=Normal, 1=Attack
  "confidence": 0.94,                 // max(probabilities)
  "probabilities": [0.06, 0.94],      // [p_normal, p_attack]
  "model_version": "v1.0.0",
  "model_path": "twin/registry/gcn/v1.0.0",
  "inference_time_ms": 12.3,
  "timestamp": "2026-02-10T14:00:26.123Z"
}
```

**Output (Database)**: See [Database Schema](#database-schema) section

**Configuration** (`detector.yaml`):
```yaml
kafka:
  input_topic: wifi7.ml.windowed_features.v1
  output_topic: wifi7.security.gcn_predictions.v1
  brokers: bus-redpanda:9092
  consumer_group: gcn-detector-v1
  auto_offset_reset: latest

model:
  registry_path: /app/registry         # Mounted from twin/registry/gcn/
  active_version: current              # Symlink to active model
  device: cuda                         # cuda or cpu
  batch_size: 32                       # Inference batch size
  use_derived_features: true           # Add retrans_rate, drop_rate, throughput_per_flow

inference:
  threshold: 0.5                       # Attack if p_attack > threshold
  timeout_ms: 10000                    # Max inference time per segment

database:
  host: udr-db
  port: 5432
  dbname: udr
  user: udr
  password: ${PG_PASS}
  table: gcn_predictions
  batch_insert_size: 100

logging:
  level: INFO
  format: json

health:
  port: 8080
  endpoint: /health
```

**Model Loading**:
```python
# Detector loads model on startup and watches for changes
model_path = Path(config.registry_path) / config.active_version
model = WiFi7AttackDetector.load_from_checkpoint(
    model_path / "best_model.pt",
    scaler_path=model_path / "scaler.json",
    config_path=model_path / "config.yaml"
)
model.to(device)
model.eval()
```

**Hot Reloading**:
- Watch `current` symlink for changes
- On change: load new model in background, swap atomically
- Zero-downtime model updates

---

### 3. Model Registry

**Purpose**: Version control for trained models, scalers, and configs.

**Location**: `twin/registry/gcn/`

**Structure**:
```
twin/registry/gcn/
├── v1.0.0/
│   ├── best_model.pt           # PyTorch model weights
│   ├── scaler.json             # StandardScaler params
│   ├── config.yaml             # Model hyperparameters
│   ├── metadata.json           # Training metadata
│   └── test_results.json       # Evaluation metrics
├── v1.1.0/
│   ├── ...
├── current -> v1.0.0           # Symlink to active version
└── README.md                   # Registry documentation
```

**Metadata Format** (`metadata.json`):
```json
{
  "version": "v1.0.0",
  "created_at": "2026-02-10T14:00:00Z",
  "training_dataset": {
    "source": "Wifi7_Datasets/",
    "train_files": 120,
    "val_files": 20,
    "test_files": 20,
    "total_windows": 450000
  },
  "model_config": {
    "in_channels": 16,
    "hidden_channels": 64,
    "num_layers": 2,
    "dropout": 0.3,
    "pooling": "mean",
    "segment_length": 256
  },
  "training_config": {
    "batch_size": 32,
    "learning_rate": 0.001,
    "max_epochs": 150,
    "early_stopping_patience": 20
  },
  "performance": {
    "test_accuracy": 0.9523,
    "test_f1": 0.9481,
    "test_precision": 0.9612,
    "test_recall": 0.9354,
    "test_roc_auc": 0.9891
  },
  "git_commit": "9f0139f",
  "trained_by": "cobrakali",
  "notes": "Baseline model trained on 3 attack scenarios"
}
```

---

### 4. Training Pipeline (On-Demand)

**Purpose**: Train new GCN models on labeled data from experiments or curated datasets.

**Location**: `twin/gnn/trainer/`

**Trigger Options**:
1. Manual: `make gcn-train EXP_ID=<exp_id>`
2. Scheduled: Cron job (weekly retraining)
3. On-demand: After collecting N new labeled experiments

**Input Sources**:
1. **Existing Datasets**: `Wifi7_Datasets/` from GCN repo
2. **DB Export**: Export labeled experiments from `public.metrics` + manual labels
3. **Synthetic**: Generate attack scenarios in ns-3

**Workflow**:
```bash
# 1. Export data from DB (if using live data)
make gcn-export-data EXP_IDS="exp1,exp2,exp3" OUTPUT=data/new_training/

# 2. Train model
make gcn-train \
  DATA_DIR=data/new_training \
  OUTPUT_DIR=twin/registry/gcn/v1.1.0 \
  CONFIG=config/gcn_training.yaml

# 3. Evaluate on test set
make gcn-evaluate MODEL=twin/registry/gcn/v1.1.0

# 4. Deploy new model (update symlink)
make gcn-deploy VERSION=v1.1.0
```

**Training Container**:
```dockerfile
FROM pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime

WORKDIR /app

# Copy GCN repo source
COPY --from=gcn-repo /wifi7_gcn_attack_detection/src ./src
COPY --from=gcn-repo /wifi7_gcn_attack_detection/requirements.txt .

RUN pip install -r requirements.txt

# Training script
COPY trainer/train.py .

CMD ["python", "train.py", "--config", "/config/training.yaml"]
```

**Configuration** (`training.yaml`):
```yaml
data:
  root: /data
  train_ratio: 0.70
  val_ratio: 0.15
  test_ratio: 0.15

model:
  in_channels: 16
  hidden_channels: 64
  num_layers: 2
  dropout: 0.3
  pooling: mean

training:
  batch_size: 32
  learning_rate: 0.001
  weight_decay: 0.0001
  max_epochs: 150
  patience: 20
  use_class_weights: true

output:
  checkpoint_dir: /output
  log_dir: /logs
```

---

## Data Flow & Schemas

### Database Schema

#### `public.gcn_predictions` (New Table)

```sql
CREATE TABLE IF NOT EXISTS public.gcn_predictions (
    id BIGSERIAL PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    segment_id TEXT NOT NULL,

    -- Time range
    ts_start TIMESTAMPTZ NOT NULL,
    ts_end TIMESTAMPTZ NOT NULL,

    -- Window indices
    window_start_idx INTEGER NOT NULL,
    window_end_idx INTEGER NOT NULL,

    -- Prediction
    prediction INTEGER NOT NULL,              -- 0=Normal, 1=Attack
    confidence DOUBLE PRECISION NOT NULL,     -- max(probabilities)
    probabilities JSONB NOT NULL,             -- [p_normal, p_attack]

    -- Model metadata
    model_version TEXT NOT NULL,
    model_path TEXT NOT NULL,

    -- Performance
    inference_time_ms DOUBLE PRECISION,

    -- Provenance
    source TEXT NOT NULL DEFAULT 'gcn-detector',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT prediction_valid CHECK (prediction IN (0, 1)),
    CONSTRAINT confidence_valid CHECK (confidence >= 0 AND confidence <= 1)
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS gcn_pred_exp_ts_idx
  ON public.gcn_predictions (experiment_id, ts_start DESC);

CREATE INDEX IF NOT EXISTS gcn_pred_entity_ts_idx
  ON public.gcn_predictions (entity_id, ts_start DESC);

CREATE INDEX IF NOT EXISTS gcn_pred_attack_idx
  ON public.gcn_predictions (prediction, ts_start DESC)
  WHERE prediction = 1;

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('gcn_predictions', 'ts_start', if_not_exists => TRUE);
```

#### `public.model_registry` (New Table)

```sql
CREATE TABLE IF NOT EXISTS public.model_registry (
    id BIGSERIAL PRIMARY KEY,
    version TEXT UNIQUE NOT NULL,
    model_path TEXT NOT NULL,
    metadata JSONB NOT NULL,
    performance_metrics JSONB NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    deployed_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ,
    notes TEXT
);

-- Only one active model at a time
CREATE UNIQUE INDEX IF NOT EXISTS one_active_model
  ON public.model_registry (is_active)
  WHERE is_active = TRUE;
```

### Kafka Topics

| Topic | Purpose | Schema | Partitions | Retention |
|-------|---------|--------|------------|-----------|
| `wifi7.telemetry.v0_1` | Raw telemetry (existing) | Per-metric events | 3 | 7 days |
| `wifi7.ml.windowed_features.v1` | Aggregated windows | Segment batches | 3 | 1 day |
| `wifi7.security.gcn_predictions.v1` | Attack predictions | Predictions | 3 | 30 days |
| `wifi7.security.gcn_predictions.dlq` | Failed predictions | Errors | 1 | 7 days |

**Topic Creation** (via Makefile):
```bash
make kafka-topics-create
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal**: Set up directory structure, schemas, and basic configs

**Tasks**:
1. ✅ Create directory structure
   ```
   security/detector/windowizer/
   twin/gnn/detector/
   twin/gnn/trainer/
   twin/registry/gcn/
   ```

2. ✅ Add DB migrations
   ```bash
   clab/configs/udr-db/initdb/003_gcn_schema.sql
   ```

3. ✅ Create Kafka topics
   ```bash
   make kafka-topics-create
   ```

4. ✅ Copy model artifacts from GCN repo
   ```bash
   cp -r /path/to/wifi7_gcn_attack_detection/checkpoints twin/registry/gcn/v1.0.0/
   ln -s v1.0.0 twin/registry/gcn/current
   ```

5. ✅ Write configuration files
   - `security/detector/windowizer/config.yaml`
   - `twin/gnn/detector/config.yaml`
   - `twin/gnn/trainer/training.yaml`

**Deliverables**:
- [ ] Directory structure created
- [ ] DB tables created
- [ ] Kafka topics created
- [ ] Model registry initialized
- [ ] Configuration files written

**Acceptance Criteria**:
- DB schema validates
- Kafka topics exist
- Model artifacts loadable

---

### Phase 2: Windowizer Implementation (Week 2-3)

**Goal**: Build and test the windowizer service

**Tasks**:
1. ✅ Implement windowizer core logic
   - `security/detector/windowizer/windowizer.py`
   - Window aggregation
   - Delta conversion
   - Segment buffering

2. ✅ Add Kafka integration
   - Consumer for `wifi7.telemetry.v0_1`
   - Producer for `wifi7.ml.windowed_features.v1`

3. ✅ Implement state management
   - In-memory buffers per entity
   - Timeout handling
   - Graceful shutdown

4. ✅ Add logging and metrics
   - Structured JSON logging
   - Prometheus metrics (optional)

5. ✅ Write unit tests
   - Test window aggregation
   - Test delta conversion
   - Test timeout handling

6. ✅ Create Dockerfile
   - `security/detector/windowizer/Dockerfile`

7. ✅ Add to docker-compose
   - Update `docker-compose.pipeline.yml`

8. ✅ Update Makefile
   - `make windowizer-build`
   - `make windowizer-run`
   - `make windowizer-logs`

**Deliverables**:
- [ ] Windowizer service implemented
- [ ] Unit tests passing
- [ ] Docker image builds
- [ ] Service runs in compose
- [ ] Documentation updated

**Acceptance Criteria**:
- Windowizer consumes telemetry events
- Windows aggregated correctly
- Deltas computed correctly
- Segments emitted to Kafka
- No memory leaks

---

### Phase 3: GCN Detector Implementation (Week 3-4)

**Goal**: Build and test the GCN detector service

**Tasks**:
1. ✅ Copy GCN source code
   ```bash
   cp -r /path/to/wifi7_gcn_attack_detection/src twin/gnn/detector/gcn_src
   ```

2. ✅ Implement detector service
   - `twin/gnn/detector/detector.py`
   - Model loading
   - Kafka consumer
   - Inference loop
   - Result publishing

3. ✅ Add derived feature computation
   - Reuse `add_derived_features()` from GCN repo

4. ✅ Implement graph building
   - Temporal chain edges
   - PyTorch Geometric Data objects

5. ✅ Add database writer
   - Batch inserts to `gcn_predictions`

6. ✅ Add health endpoint
   - Flask/FastAPI health check

7. ✅ Write unit tests
   - Test model loading
   - Test inference
   - Test graph building

8. ✅ Create Dockerfile
   - `twin/gnn/detector/Dockerfile`
   - Install PyTorch + PyG

9. ✅ Add to docker-compose
   - Mount model registry
   - GPU support (optional)

10. ✅ Update Makefile
    - `make gcn-detector-build`
    - `make gcn-detector-run`
    - `make gcn-detector-logs`

**Deliverables**:
- [ ] Detector service implemented
- [ ] Unit tests passing
- [ ] Docker image builds
- [ ] Service runs in compose
- [ ] Predictions persisted to DB
- [ ] Documentation updated

**Acceptance Criteria**:
- Detector consumes windowed features
- Inference runs successfully
- Predictions accurate (validate against test set)
- Results in DB and Kafka
- No memory leaks

---

### Phase 4: End-to-End Testing (Week 4)

**Goal**: Validate the complete pipeline

**Tasks**:
1. ✅ Run ns-3 simulation
   ```bash
   make ns3-run EXP_ID=20260210-1400-attack-test
   ```

2. ✅ Verify data flow
   - Check telemetry.jsonl
   - Check Kafka topics
   - Check DB tables

3. ✅ Validate predictions
   - Compare against known attack scenarios
   - Check false positive rate

4. ✅ Performance testing
   - Measure throughput
   - Measure latency
   - Identify bottlenecks

5. ✅ Integration tests
   - Test with Normal scenario
   - Test with Attack scenario
   - Test with mixed scenarios

6. ✅ Error injection tests
   - Missing metrics
   - Kafka downtime
   - DB downtime

**Deliverables**:
- [ ] End-to-end test passing
- [ ] Performance benchmarks documented
- [ ] Known issues documented

**Acceptance Criteria**:
- Full pipeline runs without errors
- Predictions match expected outcomes
- Latency < 1s for 256-window segment
- Throughput > 100 segments/sec

---

### Phase 5: Grafana Dashboard (Week 5)

**Goal**: Visualize attack predictions

**Tasks**:
1. ✅ Create dashboard JSON
   - `clab/configs/grafana/dashboards/gcn-attack-detection.json`

2. ✅ Add panels
   - Attack probability timeline
   - Confidence distribution
   - Prediction counts (Normal vs Attack)
   - Model performance metrics

3. ✅ Overlay with existing metrics
   - Show throughput + predictions together
   - Show backoff slots + predictions

4. ✅ Add alerting rules
   - Alert on attack detection
   - Alert on model errors

**Deliverables**:
- [ ] Grafana dashboard created
- [ ] Alerts configured
- [ ] Documentation updated

**Acceptance Criteria**:
- Dashboard loads in Grafana
- Predictions visualized correctly
- Alerts trigger on attack detection

---

### Phase 6: Training Pipeline (Week 5-6)

**Goal**: Enable on-demand model retraining

**Tasks**:
1. ✅ Implement data export script
   - Export labeled experiments from DB
   - Convert to GCN training format

2. ✅ Create training container
   - Dockerfile for training
   - Copy training scripts from GCN repo

3. ✅ Implement training orchestration
   - Makefile targets
   - Configuration management

4. ✅ Add model validation
   - Evaluate on test set
   - Compare with previous version

5. ✅ Implement deployment workflow
   - Update symlink
   - Trigger hot reload

**Deliverables**:
- [ ] Training pipeline implemented
- [ ] Documentation updated

**Acceptance Criteria**:
- Can train new model from command line
- New model deployed without downtime
- Model versioning works correctly

---

### Phase 7: Live Sensor Preparation (Week 6)

**Goal**: Prepare for live sensor integration

**Tasks**:
1. ✅ Document sensor requirements
   - Required metrics
   - Data format
   - Ingestion endpoint

2. ✅ Create sensor adapter template
   - `telemetry/exporters/live_sensor_adapter/`

3. ✅ Add multi-source support
   - Handle ns-3 + live sensors simultaneously
   - Tag by source

**Deliverables**:
- [ ] Sensor requirements documented
- [ ] Adapter template created

**Acceptance Criteria**:
- Documentation complete
- Template runs with mock sensor data

---

## File Structure

```
ndt-wifi7-mlo-security/
├── security/
│   └── detector/
│       └── windowizer/
│           ├── Dockerfile
│           ├── requirements.txt
│           ├── config.yaml
│           ├── windowizer.py          # Main service
│           ├── window_aggregator.py   # Aggregation logic
│           ├── delta_converter.py     # Delta computation
│           ├── segment_builder.py     # Segment buffering
│           ├── kafka_client.py        # Kafka I/O
│           ├── tests/
│           │   ├── test_aggregator.py
│           │   ├── test_delta.py
│           │   └── test_segment.py
│           └── README.md
│
├── twin/
│   ├── gnn/
│   │   ├── detector/
│   │   │   ├── Dockerfile
│   │   │   ├── requirements.txt
│   │   │   ├── config.yaml
│   │   │   ├── detector.py           # Main service
│   │   │   ├── model_loader.py       # Model management
│   │   │   ├── inference_engine.py   # Inference logic
│   │   │   ├── graph_builder.py      # PyG graph creation
│   │   │   ├── feature_processor.py  # Feature engineering
│   │   │   ├── kafka_client.py       # Kafka I/O
│   │   │   ├── db_writer.py          # DB persistence
│   │   │   ├── health_api.py         # Health endpoint
│   │   │   ├── gcn_src/              # Copied from wifi7_gcn_attack_detection
│   │   │   │   ├── models/
│   │   │   │   │   └── gcn.py
│   │   │   │   ├── inference/
│   │   │   │   │   └── detector.py
│   │   │   │   └── data/
│   │   │   │       └── preprocessing.py
│   │   │   ├── tests/
│   │   │   │   ├── test_loader.py
│   │   │   │   ├── test_inference.py
│   │   │   │   └── test_graph.py
│   │   │   └── README.md
│   │   │
│   │   └── trainer/
│   │       ├── Dockerfile
│   │       ├── requirements.txt
│   │       ├── training.yaml
│   │       ├── train.py              # Training script
│   │       ├── data_exporter.py      # Export from DB
│   │       ├── evaluator.py          # Model evaluation
│   │       ├── deployer.py           # Model deployment
│   │       ├── tests/
│   │       └── README.md
│   │
│   └── registry/
│       └── gcn/
│           ├── v1.0.0/
│           │   ├── best_model.pt
│           │   ├── scaler.json
│           │   ├── config.yaml
│           │   ├── metadata.json
│           │   └── test_results.json
│           ├── current -> v1.0.0
│           └── README.md
│
├── clab/configs/
│   ├── udr-db/initdb/
│   │   ├── 001-init.sql
│   │   ├── 002_metrics_constraints.sql
│   │   └── 003_gcn_schema.sql        # NEW: GCN tables
│   │
│   └── grafana/dashboards/
│       └── gcn-attack-detection.json  # NEW: Attack dashboard
│
├── docker-compose.pipeline.yml        # UPDATED: Add windowizer + detector
├── Makefile                           # UPDATED: Add GCN targets
└── docs/
    ├── WP8-GCN-INTEGRATION-PLAN.md   # This file
    └── ADR-GCN-ARCHITECTURE.md       # NEW: Architecture decisions
```

---

## Configuration Management

### Environment Variables

```bash
# Kafka
KAFKA_BROKERS=bus-redpanda:9092
KAFKA_TELEMETRY_TOPIC=wifi7.telemetry.v0_1
KAFKA_WINDOWED_TOPIC=wifi7.ml.windowed_features.v1
KAFKA_PREDICTIONS_TOPIC=wifi7.security.gcn_predictions.v1

# Database
PG_HOST=udr-db
PG_PORT=5432
PG_DB=udr
PG_USER=udr
PG_PASS=udr_pass

# GCN Model
GCN_REGISTRY_PATH=/app/registry
GCN_ACTIVE_VERSION=current
GCN_DEVICE=cpu                         # cpu or cuda
GCN_BATCH_SIZE=32
GCN_USE_DERIVED_FEATURES=true

# Windowizer
WINDOWIZER_SEGMENT_LENGTH=256
WINDOWIZER_WINDOW_INTERVAL_MS=100
WINDOWIZER_TIMEOUT_MS=5000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## Deployment & Orchestration

### Docker Compose Update

```yaml
# docker-compose.pipeline.yml

services:
  harmonizer:
    # ... existing harmonizer config ...

  windowizer:
    image: ndt/windowizer:local
    container_name: ndt-pipeline-windowizer
    restart: unless-stopped
    networks:
      - clab-mgmt
    environment:
      KAFKA_BROKERS: ${KAFKA_BROKERS:-bus-redpanda:9092}
      KAFKA_INPUT_TOPIC: ${KAFKA_TELEMETRY_TOPIC:-wifi7.telemetry.v0_1}
      KAFKA_OUTPUT_TOPIC: ${KAFKA_WINDOWED_TOPIC:-wifi7.ml.windowed_features.v1}
      KAFKA_GROUP: windowizer-gcn-v1
      SEGMENT_LENGTH: ${WINDOWIZER_SEGMENT_LENGTH:-256}
      WINDOW_INTERVAL_MS: ${WINDOWIZER_WINDOW_INTERVAL_MS:-100}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    volumes:
      - ./security/detector/windowizer/config.yaml:/app/config.yaml:ro
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  gcn-detector:
    image: ndt/gcn-detector:local
    container_name: ndt-pipeline-gcn-detector
    restart: unless-stopped
    networks:
      - clab-mgmt
    environment:
      KAFKA_BROKERS: ${KAFKA_BROKERS:-bus-redpanda:9092}
      KAFKA_INPUT_TOPIC: ${KAFKA_WINDOWED_TOPIC:-wifi7.ml.windowed_features.v1}
      KAFKA_OUTPUT_TOPIC: ${KAFKA_PREDICTIONS_TOPIC:-wifi7.security.gcn_predictions.v1}
      KAFKA_GROUP: gcn-detector-v1
      PG_HOST: ${PG_HOST:-udr-db}
      PG_DB: ${PG_DB:-udr}
      PG_USER: ${PG_USER:-udr}
      PG_PASS: ${PG_PASS:-udr_pass}
      GCN_REGISTRY_PATH: /app/registry
      GCN_ACTIVE_VERSION: ${GCN_ACTIVE_VERSION:-current}
      GCN_DEVICE: ${GCN_DEVICE:-cpu}
      GCN_BATCH_SIZE: ${GCN_BATCH_SIZE:-32}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    volumes:
      - ./twin/registry/gcn:/app/registry:ro
      - ./twin/gnn/detector/config.yaml:/app/config.yaml:ro
    ports:
      - "8080:8080"  # Health endpoint
    # Uncomment for GPU support:
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

### Makefile Targets

```makefile
# GCN Windowizer
windowizer-build:
	@echo "Building windowizer image..."
	@docker build -t ndt/windowizer:local security/detector/windowizer/

windowizer-run:
	@echo "Starting windowizer service..."
	@docker compose -f docker-compose.pipeline.yml up -d windowizer

windowizer-stop:
	@docker compose -f docker-compose.pipeline.yml stop windowizer

windowizer-logs:
	@docker compose -f docker-compose.pipeline.yml logs -f windowizer

# GCN Detector
gcn-detector-build:
	@echo "Building GCN detector image..."
	@docker build -t ndt/gcn-detector:local twin/gnn/detector/

gcn-detector-run:
	@echo "Starting GCN detector service..."
	@docker compose -f docker-compose.pipeline.yml up -d gcn-detector

gcn-detector-stop:
	@docker compose -f docker-compose.pipeline.yml stop gcn-detector

gcn-detector-logs:
	@docker compose -f docker-compose.pipeline.yml logs -f gcn-detector

gcn-detector-health:
	@curl http://localhost:8080/health

# GCN Training
gcn-trainer-build:
	@echo "Building GCN trainer image..."
	@docker build -t ndt/gcn-trainer:local twin/gnn/trainer/

gcn-train:
	@echo "Training new GCN model..."
	@docker run --rm \
		-v $(PWD)/twin/registry/gcn:/output \
		-v $(PWD)/data:/data \
		-v $(PWD)/twin/gnn/trainer/training.yaml:/config/training.yaml:ro \
		ndt/gcn-trainer:local

gcn-evaluate:
	@echo "Evaluating model $(MODEL)..."
	@docker run --rm \
		-v $(PWD)/twin/registry/gcn:/models \
		ndt/gcn-trainer:local evaluate --model $(MODEL)

gcn-deploy:
	@echo "Deploying model version $(VERSION)..."
	@ln -sf $(VERSION) twin/registry/gcn/current
	@echo "Model $(VERSION) is now active. Detector will reload."

# Complete GCN Pipeline
gcn-up: windowizer-build gcn-detector-build
	@echo "Starting complete GCN pipeline..."
	@docker compose -f docker-compose.pipeline.yml up -d windowizer gcn-detector

gcn-down:
	@echo "Stopping GCN pipeline..."
	@docker compose -f docker-compose.pipeline.yml stop windowizer gcn-detector

gcn-status:
	@docker compose -f docker-compose.pipeline.yml ps windowizer gcn-detector
	@echo ""
	@echo "Windowizer logs (last 10 lines):"
	@docker compose -f docker-compose.pipeline.yml logs --tail=10 windowizer
	@echo ""
	@echo "GCN Detector logs (last 10 lines):"
	@docker compose -f docker-compose.pipeline.yml logs --tail=10 gcn-detector

# Kafka Topics
kafka-topics-create:
	@echo "Creating Kafka topics..."
	@docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
		rpk topic create wifi7.ml.windowed_features.v1 \
		--partitions 3 --retention 86400s
	@docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
		rpk topic create wifi7.security.gcn_predictions.v1 \
		--partitions 3 --retention 2592000s
	@docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
		rpk topic create wifi7.security.gcn_predictions.dlq \
		--partitions 1 --retention 604800s

kafka-topics-list:
	@docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
		rpk topic list

# End-to-End Test
test-gcn-e2e: ns3-build exporter-build windowizer-build gcn-detector-build
	@echo "Running end-to-end GCN test..."
	@bash tests/gcn_e2e_test.sh
```

---

## Testing Strategy

### Unit Tests

**Windowizer**:
```python
# tests/test_window_aggregator.py
def test_aggregate_metrics():
    """Test window aggregation from raw events"""
    events = [
        {"ts": "2026-01-01T00:00:00.000Z", "metric": "net_throughput_mbps", "value": 120.5},
        {"ts": "2026-01-01T00:00:00.000Z", "metric": "net_avg_delay_ms", "value": 2.1},
        # ... all 13 metrics
    ]
    window = aggregate_window(events)
    assert window["net_throughput_mbps"] == 120.5
    assert len(window) == 13

def test_delta_conversion():
    """Test cumulative counter delta computation"""
    windows = [
        {"mac_total_tx": 1000, "mac_total_rx": 500},
        {"mac_total_tx": 1050, "mac_total_rx": 550},
        {"mac_total_tx": 1120, "mac_total_rx": 610},
    ]
    deltas = apply_deltas(windows, cumulative_keys=["mac_total_tx", "mac_total_rx"])
    assert deltas[0]["mac_total_tx"] == 0   # First window: no previous
    assert deltas[1]["mac_total_tx"] == 50
    assert deltas[2]["mac_total_tx"] == 70
```

**Detector**:
```python
# tests/test_inference.py
def test_model_loading():
    """Test model loads correctly"""
    model = WiFi7AttackDetector.load_from_checkpoint(
        model_path="twin/registry/gcn/v1.0.0/best_model.pt",
        scaler_path="twin/registry/gcn/v1.0.0/scaler.json"
    )
    assert model is not None
    assert model.in_channels == 16

def test_inference_output():
    """Test inference produces valid output"""
    segment = create_test_segment(length=256, attack=True)
    prediction, confidence, probs = model.predict(segment)
    assert prediction in [0, 1]
    assert 0 <= confidence <= 1
    assert len(probs) == 2
    assert abs(sum(probs) - 1.0) < 1e-5
```

### Integration Tests

```bash
# tests/gcn_integration_test.sh

# 1. Start services
make up
make pipeline-up
make gcn-up

# 2. Run ns-3 attack scenario
make ns3-run EXP_ID=20260210-test-attack

# 3. Run exporter
make exporter-run EXP_ID=20260210-test-attack

# 4. Wait for predictions
sleep 30

# 5. Query DB for predictions
psql -h localhost -U udr -d udr -c \
  "SELECT prediction, confidence FROM gcn_predictions WHERE experiment_id='20260210-test-attack';"

# Expected: prediction=1 (attack), confidence > 0.9

# 6. Cleanup
make pipeline-down
make down
```

### Performance Tests

```bash
# tests/gcn_performance_test.sh

# Measure throughput
# - Generate synthetic windowed features
# - Feed to detector
# - Measure segments/sec

# Expected:
# - Throughput > 100 segments/sec (CPU)
# - Throughput > 500 segments/sec (GPU)
# - Latency < 1s per segment
```

---

## Monitoring & Observability

### Logging

**Structured JSON Logs**:
```json
{
  "timestamp": "2026-02-10T14:00:26.123Z",
  "level": "INFO",
  "service": "gcn-detector",
  "message": "Prediction emitted",
  "experiment_id": "20260210-1400-attack-test",
  "segment_id": "seg_0",
  "prediction": 1,
  "confidence": 0.94,
  "inference_time_ms": 12.3
}
```

### Metrics (Optional: Prometheus)

**Windowizer Metrics**:
- `windowizer_events_received_total` (counter)
- `windowizer_windows_created_total` (counter)
- `windowizer_segments_emitted_total` (counter)
- `windowizer_processing_duration_seconds` (histogram)

**Detector Metrics**:
- `gcn_predictions_total{prediction=0|1}` (counter)
- `gcn_inference_duration_seconds` (histogram)
- `gcn_model_load_time_seconds` (gauge)
- `gcn_predictions_confidence` (histogram)

### Health Checks

**Detector Health Endpoint**:
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

### Alerting

**Grafana Alerts**:
1. **Attack Detected**: Alert if `prediction=1` with `confidence > 0.9`
2. **Model Error**: Alert if detector logs errors
3. **Pipeline Lag**: Alert if Kafka consumer lag > 1000 messages

---

## Error Handling & Resilience

### Retry Logic

**Kafka Consumer**:
- On connection failure: Exponential backoff (1s, 2s, 4s, ..., max 60s)
- On deserialization error: Log + skip + DLQ

**Database Writer**:
- On connection failure: Retry 3 times with backoff
- On constraint violation: Log + skip
- Batch inserts with transaction rollback

### Dead Letter Queue

**Purpose**: Capture failed predictions for later analysis

**Topic**: `wifi7.security.gcn_predictions.dlq`

**Message**:
```json
{
  "original_message": { /* windowed features */ },
  "error": "Inference timeout",
  "timestamp": "2026-02-10T14:00:26.123Z",
  "service": "gcn-detector"
}
```

### Graceful Shutdown

```python
# Detector shutdown logic
def shutdown_handler(signum, frame):
    logger.info("Shutdown signal received, flushing buffers...")

    # Stop consuming
    consumer.close()

    # Flush pending predictions to DB
    db_writer.flush()

    # Close DB connection
    db_writer.close()

    logger.info("Shutdown complete")
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)
```

---

## Performance Optimization

### Batching

**Detector**:
- Batch size: 32 segments per inference call
- Trade-off: Latency vs throughput
- Configurable via `GCN_BATCH_SIZE`

**Database Writes**:
- Batch size: 100 predictions per insert
- Use `COPY` or multi-row `INSERT`

### GPU Support

**Dockerfile**:
```dockerfile
FROM pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime

# ... rest of Dockerfile ...
```

**Docker Compose**:
```yaml
gcn-detector:
  # ...
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

**Expected Speedup**:
- CPU: ~100 segments/sec
- GPU: ~500 segments/sec

### Memory Management

- Clear buffers after segment emission
- Use PyTorch `torch.no_grad()` during inference
- Periodically garbage collect

---

## Model Registry & Versioning

### Version Naming

Format: `vMAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (e.g., different input features)
- **MINOR**: Model improvements (e.g., better architecture)
- **PATCH**: Bug fixes or retraining on same architecture

### Deployment Workflow

```bash
# 1. Train new model
make gcn-train OUTPUT_DIR=twin/registry/gcn/v1.1.0

# 2. Evaluate on test set
make gcn-evaluate MODEL=v1.1.0

# 3. Compare with current model
python scripts/compare_models.py --baseline current --candidate v1.1.0

# 4. Deploy if better
make gcn-deploy VERSION=v1.1.0

# 5. Monitor for 24h
# 6. Rollback if issues
make gcn-deploy VERSION=v1.0.0
```

### Hot Reloading

Detector watches `twin/registry/gcn/current` symlink for changes. On change:
1. Load new model in background thread
2. Validate model loads correctly
3. Swap atomically
4. Log version change

---

## Training Pipeline

### Data Sources

1. **Existing Datasets**: `Wifi7_Datasets/` (3 scenarios: Normal, Positive, Negative)
2. **New Experiments**: Export from `public.metrics` with manual labels
3. **Synthetic**: Generate new attack scenarios in ns-3

### Training Workflow

```bash
# Option 1: Train on existing datasets
make gcn-train \
  DATA_DIR=/path/to/Wifi7_Datasets \
  OUTPUT_DIR=twin/registry/gcn/v1.1.0

# Option 2: Export from DB + train
make gcn-export-data \
  EXP_IDS="exp1,exp2,exp3" \
  LABELS="0,1,0" \
  OUTPUT=data/new_training

make gcn-train \
  DATA_DIR=data/new_training \
  OUTPUT_DIR=twin/registry/gcn/v1.1.0
```

### Training Configuration

```yaml
# twin/gnn/trainer/training.yaml
data:
  root: /data
  attack_folder: Attack
  normal_folder: Normal
  train_ratio: 0.70
  val_ratio: 0.15
  test_ratio: 0.15

model:
  in_channels: 16                     # 13 base + 3 derived
  hidden_channels: 64
  num_layers: 2
  dropout: 0.3
  pooling: mean

training:
  batch_size: 32
  learning_rate: 0.001
  weight_decay: 0.0001
  max_epochs: 150
  patience: 20                        # Early stopping
  use_class_weights: true             # Handle imbalance

optimizer:
  type: Adam
  betas: [0.9, 0.999]

scheduler:
  type: ReduceLROnPlateau
  factor: 0.5
  patience: 10
  min_lr: 0.00001

output:
  checkpoint_dir: /output
  log_dir: /logs
  save_best_only: true
```

---

## Live Sensor Integration

### Requirements

**Sensors** (e.g., WiFi routers) must provide:
1. **Metrics**: Same 13 base features as ns-3
2. **Format**: JSONL or JSON
3. **Frequency**: 100ms windows (or configurable)
4. **Transport**: Push to Kafka or HTTP endpoint

### Adapter Template

**Location**: `telemetry/exporters/live_sensor_adapter/`

**Purpose**: Convert sensor-specific format to telemetry contract

**Example**:
```python
# live_sensor_adapter.py

def convert_sensor_data_to_telemetry(sensor_msg):
    """
    Convert sensor message to telemetry format.

    Input (sensor-specific):
    {
        "router_id": "rtr_001",
        "timestamp": 1707580800000,   # Unix ms
        "stats": {
            "tx_packets": 12345,
            "rx_packets": 6789,
            ...
        }
    }

    Output (telemetry contract):
    [
        {
            "experiment_id": "live-rtr_001",
            "ts": "2026-02-10T14:00:00.000Z",
            "entity_id": "rtr_001",
            "metric": "mac_total_tx",
            "value": 12345,
            "unit": "packets",
            "source": "live_sensor"
        },
        ...
    ]
    """
    pass
```

### Deployment

```bash
# Run adapter as separate service
make sensor-adapter-build
make sensor-adapter-run SENSOR_URL=http://router.local/stats
```

### Mixed Source Handling

Detector and Windowizer handle ns-3 and live sensors simultaneously:
- Tag by `source` field
- Separate state per `(experiment_id, entity_id, source)`

---

## Security & Compliance

### Secrets Management

- Never commit secrets to git
- Use environment variables
- Consider HashiCorp Vault for production

### Data Privacy

- Telemetry data may contain sensitive network info
- Ensure DB access controls
- Rotate DB credentials regularly

### Model Security

- Sign model artifacts (checksums in metadata.json)
- Validate checksums on load
- Prevent model tampering

---

## Rollout Plan

### Pre-Production Checklist

- [ ] All Phase 1-6 tasks complete
- [ ] Unit tests passing (>90% coverage)
- [ ] Integration tests passing
- [ ] Performance benchmarks met
- [ ] Documentation complete
- [ ] Code reviewed
- [ ] ADR written and approved

### Production Rollout

**Week 1**: Deploy to staging
- Run with ns-3 simulations
- Monitor for errors
- Validate predictions

**Week 2**: Deploy to production
- Enable for 10% of experiments (canary)
- Monitor metrics and alerts
- Gradually increase to 100%

**Week 3-4**: Stabilization
- Fix bugs
- Optimize performance
- Update documentation

**Week 5+**: Maintenance
- Monitor dashboards
- Retrain model monthly
- Add new features as needed

---

## Success Criteria

### Functional
- [x] GCN detector runs as long-running service
- [ ] Windowizer aggregates telemetry into 256-window segments
- [ ] Detector produces predictions with >95% accuracy on test set
- [ ] Predictions persisted to DB and Kafka
- [ ] Grafana dashboard visualizes attack timeline
- [ ] Model hot-reload works without downtime
- [ ] Training pipeline produces new models on-demand

### Performance
- [ ] Inference latency < 1s per segment (CPU)
- [ ] Throughput > 100 segments/sec (CPU) or >500 (GPU)
- [ ] Windowizer lag < 5s
- [ ] Detector lag < 10s
- [ ] Memory usage < 2GB per service

### Reliability
- [ ] Services run for 7+ days without restart
- [ ] Graceful handling of missing metrics
- [ ] Recovery from Kafka/DB downtime
- [ ] No data loss during failures
- [ ] Logs and metrics available for debugging

### Maintainability
- [ ] Code follows project standards
- [ ] Documentation up-to-date
- [ ] Tests cover critical paths
- [ ] Easy to add new features
- [ ] Clear error messages

---

## Risk Assessment & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Metric misalignment** (ns-3 vs GCN) | High | Medium | Strict validation, schema enforcement |
| **Model accuracy degradation** | High | Low | Continuous monitoring, retraining pipeline |
| **Performance bottleneck** | Medium | Medium | GPU support, batching, profiling |
| **Data leakage** (bias as input) | Critical | Low | Reuse GCN preprocessing, code review |
| **Schema drift** | Medium | Medium | Versioned contracts, migration plan |
| **Kafka downtime** | Medium | Low | Buffering, retry logic, DLQ |
| **DB downtime** | Low | Low | Retry logic, predictions still in Kafka |
| **Model file corruption** | Medium | Low | Checksums, validation on load |

---

## Open Questions & Future Work

### Questions
1. Should windowizer use Redis for shared state (multi-instance)?
2. Should we support real-time alerts (e.g., Slack, email)?
3. How to handle model drift detection?

### Future Enhancements
1. **Multi-entity correlation**: Detect coordinated attacks across multiple STAs
2. **Online learning**: Update model with new labeled data in production
3. **Explainability**: SHAP values or attention weights for predictions
4. **Ensemble models**: Combine GCN with other detectors (e.g., LSTM, Random Forest)
5. **Automated retraining**: Trigger training on performance degradation

---

## References

### Internal Documents
- `docs/BLUEPRINT.md` - Full project plan
- `docs/CURRENT-STATE.md` - Pipeline status
- `docs/ALL-ADRS.md` - Architecture decisions
- `docs/WP4-TELEMETRY-EXPORTER.md` - Exporter details
- `docs/WP5-HARMONIZER.md` - Harmonizer details

### External Resources
- [PyTorch Geometric](https://pytorch-geometric.readthedocs.io/)
- [ns-3 Documentation](https://www.nsnam.org/docs/)
- [Kafka Streams](https://kafka.apache.org/documentation/streams/)
- [TimescaleDB](https://docs.timescale.com/)

### GCN Repository Files
- `/home/cobrakali/github/wifi7_gcn_attack_detection/`
  - `src/models/gcn.py` - Model architecture
  - `src/inference/detector.py` - Inference logic
  - `src/data/preprocessing.py` - Feature engineering
  - `src/data/dataset.py` - PyG dataset
  - `checkpoints/` - Trained model artifacts
  - `requirements.txt` - Python dependencies

---

## Appendix A: Telemetry Metric Mapping

| Telemetry Metric Name | GCN Feature Key | Type | Unit | Notes |
|----------------------|-----------------|------|------|-------|
| `net_throughput_mbps` | `net_throughput_mbps` | Rate | Mbps | Instantaneous |
| `net_avg_delay_ms` | `net_avg_delay_ms` | Average | ms | Per window |
| `net_avg_jitter_ms` | `net_avg_jitter_ms` | Average | ms | Per window |
| `net_packet_loss_ratio` | `net_packet_loss_ratio` | Ratio | - | [0, 1] |
| `net_active_flows` | `net_active_flows` | Count | - | Integer |
| `mac_total_tx` | `mac_total_tx` | Counter | packets | **Cumulative** |
| `mac_total_rx` | `mac_total_rx` | Counter | packets | **Cumulative** |
| `mac_total_ack` | `mac_total_ack` | Counter | packets | **Cumulative** |
| `mac_total_retrans` | `mac_total_retrans` | Counter | packets | **Cumulative** |
| `mac_drop_count` | `mac_drop_count` | Counter | packets | **Cumulative** |
| `phy_drop_count` | `phy_drop_count` | Counter | packets | **Cumulative** |
| `avg_backoff_slots` | `avg_backoff_slots` | Average | slots | Per window |
| `channel_busy_ratio` | `channel_busy_ratio` | Ratio | - | [0, 1] |

**Note**: Cumulative counters must be converted to deltas before inference.

---

## Appendix B: Example Queries

### Query Predictions for an Experiment
```sql
SELECT
    ts_start,
    entity_id,
    prediction,
    confidence,
    probabilities->>'1' AS attack_probability
FROM gcn_predictions
WHERE experiment_id = '20260210-1400-attack-test'
  AND prediction = 1
ORDER BY ts_start;
```

### Count Attacks by Entity
```sql
SELECT
    entity_id,
    COUNT(*) AS attack_count,
    AVG(confidence) AS avg_confidence
FROM gcn_predictions
WHERE experiment_id = '20260210-1400-attack-test'
  AND prediction = 1
GROUP BY entity_id
ORDER BY attack_count DESC;
```

### Model Performance Over Time
```sql
SELECT
    DATE_TRUNC('hour', created_at) AS hour,
    model_version,
    COUNT(*) AS prediction_count,
    AVG(inference_time_ms) AS avg_inference_ms
FROM gcn_predictions
GROUP BY hour, model_version
ORDER BY hour DESC;
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| v1.0.0 | 2026-02-10 | Claude Code | Initial comprehensive plan |
| v1.1.0 | TBD | - | Updates after Phase 1 |

---

**End of Document**
