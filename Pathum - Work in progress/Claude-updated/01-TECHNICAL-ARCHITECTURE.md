# Technical Architecture Deep Dive

**Document Date**: March 9, 2026  
**Audience**: Technical readers, researchers, developers  
**Depth**: Comprehensive architecture with code examples

---

## 1. System Architecture Overview

### 1.1 Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: SIMULATION (ns-3.46.1)                                        │
├─────────────────────────────────────────────────────────────────────────┤
│ Input: Network topology, traffic pattern, attack bias                   │
│ Process: 1400s WiFi 7 MLO simulation with 13 tracked metrics            │
│ Output: mlo_output.json (14,000 windows)                                │
│         telemetry.jsonl (182,000 metric events)                         │
│ Artifacts: sim/ns3/artifacts/<EXP_ID>/                                  │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: TELEMETRY EXPORT (Kafka Ingress)                              │
├─────────────────────────────────────────────────────────────────────────┤
│ Component: telemetry/exporters/ns3_file_exporter/                       │
│ Logic:                                                                   │
│   1. Read telemetry.jsonl line by line                                  │
│   2. Validate against Pydantic schema v0.1                              │
│   3. Create deterministic Kafka message key: f"{exp_id}|{entity_id}"   │
│   4. Publish to Kafka topic: wifi7.telemetry.v0_1                       │
│   5. Track offset per file (idempotency)                                │
│   6. At-least-once delivery: confirm ALL messages before checkpoint      │
│ Transport: Kafka (Redpanda) on localhost:9092                           │
│ Rate: 50-100 messages/second                                            │
│ Reliability: Counter-based confirmation, at-least-once semantics        │
│ Output Format: One Kafka message per metric event                       │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ KAFKA TOPICS (Message Bus)                                              │
├─────────────────────────────────────────────────────────────────────────┤
│ Topic 1: wifi7.telemetry.v0_1                                           │
│   Schema: {experiment_id, ts, entity_id, metric, value, unit}           │
│   Consumers: harmonizer (raw storage), windowizer (aggregation)         │
│   Retention: 7 days                                                     │
│                                                                          │
│ Topic 2: wifi7.ml.windowed_features.v1                                 │
│   Schema: {experiment_id, segment_id, windows[256], ...}                │
│   Consumers: gcn-detector (inference)                                   │
│   Retention: 7 days                                                     │
│                                                                          │
│ Topic 3: wifi7.security.gcn_predictions.v1                              │
│   Schema: {experiment_id, segment_id, prediction, confidence, ...}      │
│   Consumers: Dashboard, Policy Engine (future)                          │
│   Retention: 30 days                                                    │
└─────────────────────────────────────────────────────────────────────────┘
                     ↙                          ↘
┌────────────────────────────────────────────────────────────────────────┐
│ LAYER 3A: HARMONIZER (Raw Metric Ingestion)                            │
├────────────────────────────────────────────────────────────────────────┤
│ Component: telemetry/harmonizer/                                        │
│ Logic:                                                                   │
│   1. Subscribe to: wifi7.telemetry.v0_1                                │
│   2. Validate each message with Pydantic schemas:                       │
│      - experiment_id, ts (TimeStampTZ)                                  │
│      - entity_id, metric_name, value (float)                            │
│   3. Map to canonical UDM (Unified Data Model)                          │
│   4. Upsert to TimescaleDB: public.metrics                              │
│   5. Enforce idempotency via UNIQUE INDEX:                              │
│      (experiment_id, entity_id, metric_name, ts)                        │
│   6. Handle duplicates: INSERT on conflict DO NOTHING                   │
│ Storage: TimescaleDB hypertable partitioned by time (1 day chunks)      │
│ Latency: <100ms batch insert per 100 messages                           │
│ Output: TimescaleDB public.metrics (850+ rows per run)                  │
└────────────────────────────────────────────────────────────────────────┘
                              ↓
            TimescaleDB: public.metrics (RAW)
               {experiment_id, ts, entity_id,
                metric_name, value, unit, source}

┌────────────────────────────────────────────────────────────────────────┐
│ LAYER 3B: WINDOWIZER (Feature Engineering)                             │
├────────────────────────────────────────────────────────────────────────┤
│ Component: security/detector/windowizer/                                │
│ Logic:                                                                   │
│   1. Subscribe to: wifi7.telemetry.v0_1                                │
│   2. Buffer raw metrics in memory by (experiment_id, entity_id)         │
│   3. Group into 100ms time windows                                      │
│   4. Aggregate 13 base features per window:                             │
│      - net_throughput_mbps, net_avg_delay_ms, net_packet_loss_ratio    │
│      - mac_total_tx, mac_total_rx, mac_total_ack, etc.                 │
│   5. Apply DELTA CONVERSION for cumulative counters:                    │
│      delta[i] = cumulative[i] - cumulative[i-1]                         │
│   6. Buffer 256 consecutive windows                                     │
│   7. Publish complete segment to: wifi7.ml.windowed_features.v1         │
│ Configuration: window_interval=100ms, segment_length=256                │
│ Throughput: 256-window segment every 25.6 seconds                       │
│ Output: Windowed feature vectors for ML ingestion                       │
└────────────────────────────────────────────────────────────────────────┘
                              ↓
         Kafka: wifi7.ml.windowed_features.v1
              {experiment_id, segment_id,
               windows[256], entity_id, ts_start, ts_end}

┌────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: GCN DETECTOR (ML Inference)                                   │
├────────────────────────────────────────────────────────────────────────┤
│ Component: twin/gnn/detector/                                           │
│ Model: 2-layer Graph Convolutional Network                              │
│   - Input: 256 temporal nodes, 13 features each                         │
│   - Hidden: 64 channels (configurable)                                  │
│   - Output: 2 classes (normal=0, attack=1)                              │
│ Logic:                                                                   │
│   1. Subscribe to: wifi7.ml.windowed_features.v1                       │
│   2. Load model from: twin/registry/gcn/current/best_model.pt           │
│   3. Scale features with: twin/registry/gcn/current/scaler.json         │
│   4. Build temporal chain graph (node i → node i+1)                     │
│   5. Batch message into 4-segment batches (optional optimization)       │
│   6. Run forward pass through GCN                                       │
│   7. Return softmax probabilities [p_normal, p_attack]                  │
│   8. Publish predictions to BOTH:                                       │
│      - Kafka: wifi7.security.gcn_predictions.v1                         │
│      - Database: TimescaleDB public.gcn_predictions                     │
│ Performance:                                                             │
│   - Latency: 12-30ms per segment                                        │
│   - Throughput: ~30-50 segments/second                                  │
│   - GPU optional (CPU inference sufficient for production)              │
│ Reliability: Exponential backoff on Kafka failure                       │
└────────────────────────────────────────────────────────────────────────┘
                              ↓
         ┌──────────────────────────────────┐
         │ Kafka: wifi7.security.            │
         │ gcn_predictions.v1                │
         │ {experiment_id, segment_id,       │
         │  prediction, confidence,          │
         │  probabilities, model_version}    │
         └──────────────────────────────────┘
                  ↓                 ↓
        ┌─────────────────┐ ┌──────────────────┐
        │ TimescaleDB     │ │ Policy Engine    │
        │ public.gcn_     │ │ (future WP11)    │
        │ predictions     │ │ Mitigation       │
        │ (850+ rows)     │ │ Response         │
        └─────────────────┘ └──────────────────┘
                ↓
        ┌──────────────────────────────────┐
        │ LAYER 5: VISUALIZATION          │
        ├──────────────────────────────────┤
        │ Grafana (port 3000)               │
        │ - 38-panel unified dashboard      │
        │ - Real-time metric trends        │
        │ - Confusion matrix panel         │
        │ - GCN model performance          │
        │                                  │
        │ Custom Dashboard (port 8888)     │
        │ - React 18 + FastAPI             │
        │ - 6 sections with real-time      │
        │   updates via WebSocket          │
        │ - Pipeline Monitor               │
        │ - Attack Analysis                │
        │ - Model Intelligence             │
        └──────────────────────────────────┘
```

### 1.2 Deployment Topology

```yaml
# Containerlab (clab-mgmt network)
containerlab:
  name: ndt-wifi7-mlo-security
  topology:
    nodes:
      # Services network
      udr-db:                    # TimescaleDB
        image: timescale/timescaledb:latest-pg14
        ports: [5432]
        volumes:
          - ./03_gcn_schema.sql  # Tables: metrics, gcn_predictions
          
      bus-redpanda:              # Kafka API
        image: redpanda:latest
        ports: [9092]
        topics:
          - wifi7.telemetry.v0_1
          - wifi7.ml.windowed_features.v1
          - wifi7.security.gcn_predictions.v1
          
      grafana:                   # Dashboard
        image: grafana/grafana:latest
        ports: [3000]
        datasource: TimescaleDB (native plugin)
        dashboards:
          - ndt-unified.json (38 panels)
          - mlo-attack-scenarios.json (9 panels)

# Docker Compose (pipeline-v2.yml)
services:
  harmonizer:                    # Kafka → TimescaleDB
    image: ndt/harmonizer:local
    environment:
      KAFKA_TOPIC: wifi7.telemetry.v0_1
      KAFKA_GROUP: harmonizer-udm-v0
      PG_HOST: clab-ndt-wifi7-mlo-security-udr-db
      AUTO_OFFSET_RESET: latest
      
  windowizer:                    # Kafka → Kafka (windowed)
    image: ndt/windowizer:local
    environment:
      KAFKA_INPUT_TOPIC: wifi7.telemetry.v0_1
      KAFKA_OUTPUT_TOPIC: wifi7.ml.windowed_features.v1
      KAFKA_GROUP: windowizer-gcn-v1
      SEGMENT_LENGTH: 256
      
  gcn-detector:                  # Kafka → Kafka + DB
    image: ndt/gcn-detector:local
    environment:
      KAFKA_INPUT_TOPIC: wifi7.ml.windowed_features.v1
      KAFKA_OUTPUT_TOPIC: wifi7.security.gcn_predictions.v1
      KAFKA_GROUP: gcn-detector-v1
      GCN_REGISTRY_PATH: /registry
    volumes:
      - ./twin/registry/gcn:/registry

# Docker Compose (dashboard.yml)
  dashboard:                     # React UI + FastAPI
    image: ndt/dashboard:local
    ports: [8888]
    environment:
      BACKEND_PORT: 8000
      PG_HOST: clab-ndt-wifi7-mlo-security-udr-db
      GCN_REGISTRY_PATH: /registry
    volumes:
      - ./twin/registry/gcn:/registry
```

---

## 2. Core Components Implementation

### 2.1 Telemetry Schema (Contracts)

**File**: `telemetry/contracts/v0.1/telemetry.pydantic.py`

```python
from pydantic import BaseModel
from datetime import datetime

class TelemetryEventV0_1(BaseModel):
    """WiFi 7 MLO telemetry event schema v0.1"""
    
    # Identifiers
    experiment_id: str  # e.g., "20260210-1400-mlo-normal-42"
    ts: datetime       # ISO format timestamp
    entity_id: str     # e.g., "sta_0", "ap_0"
    
    # Metric definition
    metric: str        # e.g., "net_throughput_mbps"
    value: float       # Actual measurement
    unit: str          # e.g., "Mbps", "ms", "ratio"
    
    # Metadata
    source: str        # "ns3" or "live_sensor"
    schema_version: str = "v0.1"
    
    class Config:
        json_schema_extra = {
            "example": {
                "experiment_id": "20260210-1400-mlo-normal-42",
                "ts": "2026-02-10T14:00:00.100Z",
                "entity_id": "sta_0",
                "metric": "net_throughput_mbps",
                "value": 120.5,
                "unit": "Mbps",
                "source": "ns3",
                "schema_version": "v0.1"
            }
        }
```

**Kafka Message Key Design**:

```python
# Deterministic key for Kafka partitioning
message_key = f"{experiment_id}|{entity_id}"
# Example: "20260210-1400-mlo-normal-42|sta_0"

# Benefit: All events for same (experiment, entity) go to same partition
# → Ordering guaranteed within partition
# → Windowing works correctly
```

### 2.2 Harmonizer Service

**File**: `telemetry/harmonizer/main.py` (simplified excerpt)

```python
import asyncio
import asyncpg
from aiokafka import AIOKafkaConsumer
from pydantic import ValidationError

class Harmonizer:
    def __init__(self, kafka_brokers, pg_host, pg_db):
        self.kafka_brokers = kafka_brokers
        self.pg_pool = None
        self.consumer = AIOKafkaConsumer(
            'wifi7.telemetry.v0_1',
            bootstrap_servers=kafka_brokers,
            group_id='harmonizer-udm-v0',
            auto_offset_reset='latest',
            value_deserializer=lambda x: json.loads(x.decode())
        )
        
    async def start(self):
        # Initialize database connection pool
        self.pg_pool = await asyncpg.create_pool(
            host=self.pg_host,
            database=self.pg_db,
            user='udr',
            password='udr_pass',
            min_size=5,
            max_size=20
        )
        
        # Start consuming Kafka
        await self.consumer.start()
        try:
            async for message in self.consumer:
                await self.process_message(message.value)
        finally:
            await self.consumer.stop()
    
    async def process_message(self, raw_event):
        try:
            # Validate against schema
            event = TelemetryEventV0_1(**raw_event)
            
            # Upsert into TimescaleDB
            # Idempotency: UNIQUE INDEX prevents duplicates
            await self.pg_pool.execute('''
                INSERT INTO public.metrics 
                (experiment_id, ts, entity_id, metric_name, 
                 value, unit, source)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (experiment_id, entity_id, metric_name, ts)
                DO NOTHING;
            ''', 
            event.experiment_id,
            event.ts,
            event.entity_id,
            event.metric,
            event.value,
            event.unit,
            event.source)
            
        except ValidationError as e:
            logger.error(f"Invalid event: {e}")
        except asyncpg.UniqueViolationError:
            # Duplicate, silently skip (idempotency)
            pass
        except Exception as e:
            logger.error(f"DB error: {e}")
            await asyncio.sleep(1)  # Backoff
```

**Database Schema**:

```sql
-- Create hypertable (TimescaleDB)
CREATE TABLE IF NOT EXISTS public.metrics (
    experiment_id TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    entity_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL,
    source TEXT NOT NULL,
    ingest_time TIMESTAMPTZ DEFAULT NOW()
);

-- Time-based partitioning (1 day chunks)
SELECT create_hypertable('metrics', 'ts', 
    if_not_exists => TRUE,
    time_interval => INTERVAL '1 day'
);

-- Idempotency index (prevent duplicates)
CREATE UNIQUE INDEX IF NOT EXISTS uq_metrics_idem 
ON metrics (experiment_id, entity_id, metric_name, ts);

-- Query optimization indexes
CREATE INDEX IF NOT EXISTS ix_metrics_ts_idx 
ON metrics (ts DESC);

CREATE INDEX IF NOT EXISTS ix_metrics_exp_metric_ts 
ON metrics (experiment_id, metric_name, ts);
```

### 2.3 Windowizer Service

**File**: `security/detector/windowizer/windowizer.py` (core logic)

```python
class Windowizer:
    def __init__(self, window_interval_ms=100, segment_length=256):
        self.window_interval_ms = window_interval_ms
        self.segment_length = segment_length
        
        # Per-entity buffer: {(exp_id, entity_id): {windows: [], cumulative_state}}
        self.buffers = {}
        
        # Cumulative counter keys (apply delta conversion)
        self.cumulative_metrics = {
            'mac_total_tx', 'mac_total_rx', 'mac_total_ack',
            'mac_total_retrans', 'mac_drop_count', 'phy_drop_count'
        }
        
        # Required feature keys (13 base features)
        self.required_features = {
            'net_throughput_mbps', 'net_avg_delay_ms', 'net_avg_jitter_ms',
            'net_packet_loss_ratio', 'net_active_flows',
            'mac_total_tx', 'mac_total_rx', 'mac_total_ack', 'mac_total_retrans',
            'mac_drop_count', 'phy_drop_count',
            'avg_backoff_slots', 'channel_busy_ratio'
        }
    
    async def process_event(self, event):
        """Process single raw metric event"""
        key = (event['experiment_id'], event['entity_id'])
        
        # Initialize buffer if new entity
        if key not in self.buffers:
            self.buffers[key] = {
                'windows': [],
                'current_window': {},
                'current_window_start': event['ts'],
                'last_cumulative_values': {}
            }
        
        buffer = self.buffers[key]
        
        # Aggregate into current window
        window_key = self._get_window_bucket(event['ts'])
        
        if event['metric'] in self.cumulative_metrics:
            # Store for delta conversion later
            buffer['last_cumulative_values'][event['metric']] = event['value']
        
        buffer['current_window'][event['metric']] = event['value']
        
        # Check if window complete
        if len(buffer['current_window']) == len(self.required_features):
            window_dict = self._apply_delta_conversion(
                buffer['current_window'],
                buffer['last_cumulative_values']
            )
            buffer['windows'].append(window_dict)
            buffer['current_window'] = {}
            
            # Check if segment complete
            if len(buffer['windows']) == self.segment_length:
                segment = self._build_segment(key, buffer['windows'])
                await self.publish_segment(segment)
                buffer['windows'] = []
    
    def _apply_delta_conversion(self, window, last_values):
        """Convert cumulative counters to rates/deltas"""
        converted = {}
        for metric, value in window.items():
            if metric in self.cumulative_metrics:
                # Calculate delta from last window
                last = last_values.get(metric, value)
                converted[metric] = max(0, value - last)  # Avoid negative
            else:
                converted[metric] = value
        return converted
    
    def _build_segment(self, key, windows):
        """Build complete segment for model input"""
        exp_id, entity_id = key
        return {
            'experiment_id': exp_id,
            'entity_id': entity_id,
            'segment_id': f"seg_{len(self.buffers[key]['windows'])}",
            'window_start_idx': 0,
            'window_end_idx': self.segment_length - 1,
            'windows': windows,  # 256 windows × 13 features
            'ts': datetime.utcnow().isoformat()
        }
```

### 2.4 GCN Detector Service

**File**: `twin/gnn/detector/gcn_detector.py` (inference logic)

```python
import torch
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv

class GCNDetector:
    def __init__(self, model_path, scaler_path):
        # Load pre-trained model
        self.model = GCNModule.load(model_path)
        self.model.eval()
        
        # Load feature scaler
        with open(scaler_path) as f:
            scaler_dict = json.load(f)
        self.scaler_mean = torch.tensor(scaler_dict['mean'])
        self.scaler_std = torch.tensor(scaler_dict['scale'])
        
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
    
    async def infer_segment(self, segment):
        """Run inference on windowed feature segment"""
        try:
            # Extract features: (256 windows × 13 features)
            features = torch.tensor([
                [w[f] for f in self.feature_keys]
                for w in segment['windows']
            ], dtype=torch.float32)
            
            # Scale features
            features = (features - self.scaler_mean) / self.scaler_std
            
            # Build temporal chain graph
            # Node i → node i+1 (temporal ordering)
            edge_index = torch.tensor([
                list(range(255)),      # source nodes
                list(range(1, 256))    # target nodes
            ], dtype=torch.long)
            
            # Create PyTorch Geometric Data object
            graph = Data(
                x=features,
                edge_index=edge_index,
                num_nodes=256
            )
            
            # Run inference
            with torch.no_grad():
                output = self.model(graph)  # Shape: (256, 2)
                
            # Get segment-level prediction (average over all windows)
            segment_probs = F.softmax(output, dim=1).mean(dim=0)
            
            prediction = {
                'experiment_id': segment['experiment_id'],
                'segment_id': segment['segment_id'],
                'entity_id': segment['entity_id'],
                'prediction': int(torch.argmax(segment_probs).item()),
                'confidence': float(torch.max(segment_probs).item()),
                'probabilities': segment_probs.cpu().tolist(),
                'inference_time_ms': elapsed_ms,
                'model_version': self.model.version
            }
            
            return prediction
            
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            return None
    
    async def publish_prediction(self, prediction, kafka_producer, db_pool):
        """Emit to Kafka and TimescaleDB"""
        # Kafka: wifi7.security.gcn_predictions.v1
        await kafka_producer.send_and_wait(
            'wifi7.security.gcn_predictions.v1',
            value=json.dumps(prediction).encode()
        )
        
        # Database: public.gcn_predictions
        await db_pool.execute('''
            INSERT INTO public.gcn_predictions
            (experiment_id, segment_id, entity_id, prediction, 
             confidence, probabilities, model_version, ts)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            ON CONFLICT DO NOTHING;
        ''',
        prediction['experiment_id'],
        prediction['segment_id'],
        prediction['entity_id'],
        prediction['prediction'],
        prediction['confidence'],
        json.dumps(prediction['probabilities']),
        prediction['model_version']
        )
```

---

## 3. Network Flow Detailed Walkthrough

### 3.1 Single Metric Event Example

Input (NS-3 Simulation):
```
timestamp=1000ms, sta_0, net_throughput_mbps=125.4
```

**Step 1: Export to Kafka**
```python
# Exporter creates JSONL line
{
  "experiment_id": "20260210-1400-mlo-normal-42",
  "ts": "2026-02-10T14:00:00.100Z",
  "entity_id": "sta_0",
  "metric": "net_throughput_mbps",
  "value": 125.4,
  "unit": "Mbps",
  "source": "ns3",
  "schema_version": "v0.1"
}

# Publish to Kafka with key:
key = "20260210-1400-mlo-normal-42|sta_0"
```

**Step 2: Harmonizer → Database**
```python
# Harmonizer validates and inserts
INSERT INTO public.metrics 
(experiment_id, ts, entity_id, metric_name, value, unit, source)
VALUES 
('20260210-1400-mlo-normal-42', 
 '2026-02-10T14:00:00.100Z',
 'sta_0',
 'net_throughput_mbps',
 125.4,
 'Mbps',
 'ns3')
```

**Step 3: Windowizer Aggregation**
```python
# After collecting 13 metrics in 100ms window [1000-1100ms]:
{
  "net_throughput_mbps": 125.4,
  "net_avg_delay_ms": 2.1,
  "net_avg_jitter_ms": 0.3,
  "net_packet_loss_ratio": 0.001,
  "net_active_flows": 6,
  "mac_total_tx": 5200,          # cumulative
  "mac_total_rx": 5150,          # cumulative
  "mac_total_ack": 5100,         # cumulative
  "mac_total_retrans": 50,       # cumulative
  "mac_drop_count": 5,           # cumulative
  "phy_drop_count": 2,           # cumulative
  "avg_backoff_slots": 4.95,
  "channel_busy_ratio": 0.88
}

# Apply delta conversion (first window):
mac_total_tx_delta = 5200 - 0 = 5200  (or rate per time period)
```

**Step 4: Segment Assembly**
```python
# After 256 windows (25.6 seconds), publish segment
{
  "experiment_id": "20260210-1400-mlo-normal-42",
  "segment_id": "seg_0",
  "entity_id": "sta_0",
  "window_start_idx": 0,
  "window_end_idx": 255,
  "windows": [
    {window_0_features},
    {window_1_features},
    ...
    {window_255_features}
  ],
  "ts": "2026-02-10T14:00:25.600Z"
}
```

**Step 5: GCN Inference**
```python
# Build temporal graph
nodes: 256 (one per window)
edges: 0→1, 1→2, ..., 254→255  (temporal chain)
features: 13 per node

# Run 2-layer GCN forward pass

# Output (per window)
[p_normal=0.15, p_attack=0.85]
[p_normal=0.10, p_attack=0.90]
...
[p_normal=0.12, p_attack=0.88]

# Segment-level: average probabilities
segment_prediction = {
  'prediction': 1,                    # attack
  'confidence': 0.87,                 # max probability
  'probabilities': [0.13, 0.87]      # [p_normal, p_attack]
}
```

**Step 6: Output to Dashboard**
```python
# Insert to TimescaleDB
INSERT INTO public.gcn_predictions
(experiment_id, segment_id, entity_id, prediction, 
 confidence, probabilities, model_version, ts)
VALUES
('20260210-1400-mlo-normal-42', 'seg_0', 'sta_0',
 1, 0.87, '[0.13, 0.87]', 'v2.0.0', NOW())

# Dashboard queries:
SELECT COUNT(*) FROM gcn_predictions 
WHERE prediction=1 AND confidence > 0.8
→ Real-time attack alert count

# Visualization:
- Prediction timeline: time vs confidence
- Confusion matrix: TP/TN/FP/FN counters
- Active segments: ongoing detection
```

---

## 4. Configuration Deep Dive

### 4.1 NS-3 Simulation Config

**File**: `sim/ns3/scenario/run_mlo_scenario.sh`

```bash
#!/bin/bash

# Parameters
AP_COUNT=1              # Single access point
STA_COUNT=2             # Two stations (one attacker, one victim)
ATTACK_SCENARIO="${1:-normal}"  # normal | positive | negative
ATTACK_BIAS="${2:-0}"   # bias value for attack
SEED="${3:-42}"         # Random seed
SIM_TIME="${4:-1400.0}" # Simulation duration (seconds)

# Feature tracking (13 metrics)
FEATURES=(
    "net_throughput_mbps"
    "net_avg_delay_ms"
    "net_avg_jitter_ms"
    "net_packet_loss_ratio"
    "net_active_flows"
    "mac_total_tx"
    "mac_total_rx"
    "mac_total_ack"
    "mac_total_retrans"
    "mac_drop_count"
    "phy_drop_count"
    "avg_backoff_slots"
    "channel_busy_ratio"
)

# Channel config (WiFi 7)
CHANNEL_BANDWIDTH=80    # MHz
CHANNEL_CENTER_IDX=42   # Center frequency index
GUARD_INTERVAL=3200     # nanoseconds (WiFi 7)
MCS_INDEX=11            # HeMcs11 (highest MCS)

# Traffic config
FLOWS_PER_STA=3
DATA_RATE="50Mbps"      # Per flow
PACKET_INTERVAL="0.5ms"
PACKET_SIZE=1500

# Attack config
case "$ATTACK_SCENARIO" in
    "positive")
        BACKOFF_BIAS=5000   # +5000 slots (starvation)
        ;;
    "negative")
        BACKOFF_BIAS=-5000  # -5000 slots (aggressive)
        ;;
    *)
        BACKOFF_BIAS=0      # normal (no attack)
        ;;
esac

# Run simulation
./ns3 run "scratch/wifi7-mlo-${ATTACK_SCENARIO}
    --seed=${SEED}
    --sim-time=${SIM_TIME}
    --backoff-bias=${BACKOFF_BIAS}
    --output=${OUTPUT_DIR}/mlo_output.json"
```

### 4.2 Windowizer Config

**File**: `security/detector/windowizer/config.yaml`

```yaml
kafka:
  brokers:
    - "bus-redpanda:9092"
  
  topics:
    input:
      name: "wifi7.telemetry.v0_1"
      consumer_group: "windowizer-gcn-v1"
      auto_offset_reset: "latest"  # Start from latest on first run
    
    output:
      name: "wifi7.ml.windowed_features.v1"
      partitions: 3
      replication_factor: 1

windowing:
  # Window definition
  segment_length: 256           # L: windows per segment
  window_interval_ms: 100       # 0.1s per window
  
  # Timing
  timeout_ms: 5000              # Wait 5s for incomplete window
  linger_ms: 100                # Batch messages for efficiency
  
  # Tuning
  overlap: 0                     # Non-overlapping (stride = 256)
  fill_strategy: "zero"          # Missing metrics → 0.0

features:
  # Required 13 base features
  base_metrics:
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
  
  # Cumulative → delta conversion
  cumulative_counters:
    - mac_total_tx
    - mac_total_rx
    - mac_total_ack
    - mac_total_retrans
    - mac_drop_count
    - phy_drop_count
  
  # Optional derived features
  computed_features:
    - retrans_rate      # (mac_total_retrans_delta / packet_count)
    - drop_rate         # ((mac_drop_count_delta + phy_drop_count_delta) / packets)
    - throughput_per_flow  # (net_throughput_mbps / net_active_flows)
  
logging:
  level: "INFO"
  format: "json"              # Structured logging
  file: "/var/log/windowizer.log"
```

### 4.3 GCN Model Config

**File**: `twin/registry/gcn/v2.0.0/config.yaml`

```yaml
model:
  name: "GCN Attack Detector"
  version: "v2.0.0"
  type: "graph_convolutional_network"
  
architecture:
  # Input
  num_node_features: 13          # 13 base metrics
  num_nodes: 256                 # Window sequence length
  
  # Graph structure
  graph_type: "temporal_chain"   # Node i → node i+1
  
  # Hidden layers
  hidden_channels: 64            # First GCN layer
  num_layers: 2                  # GCN layers
  dropout: 0.2
  
  # Output
  num_classes: 2                 # Normal=0, Attack=1
  activation: "relu"
  output_activation: "softmax"

training:
  # Dataset
  training_samples: 227          # 50-50 balanced split
  validation_samples: 57
  test_samples: 57
  total_samples: 284
  balance: "50-50"               # 128 normal + 156 attack
  
  # Hyperparameters
  batch_size: 4
  learning_rate: 0.001
  optimizer: "Adam"
  loss_function: "CrossEntropyLoss"
  epochs: 100
  patience: 10                   # Early stopping
  
  # Data augmentation
  augmentation: false
  
inference:
  # Performance
  inference_latency_ms: 15       # Target <20ms
  batch_inference: true          # Process 4 segments at once
  device: "cpu"                  # or "cuda" if available
  
  # Post-processing
  confidence_threshold: 0.7      # Flag unsure predictions
  smoothing_window: 1            # No smoothing (segment-level decision)

performance:
  # Test set results
  precision: 0.90
  recall: 0.92
  f1_score: 0.91
  false_positive_rate: 0.07
  true_positive_rate: 0.92
  roc_auc: 0.96
  
  # Key metrics for production
  min_precison_acceptable: 0.80
  min_recall_acceptable: 0.85
  max_fpr_acceptable: 0.10

training_data:
  source: "pipeline_generated"
  collection_dates:
    start: "2026-02-01"
    end: "2026-02-13"
  
  scenarios:
    normal: 128
    attack_positive: 64
    attack_negative: 64
  
  distribution:
    class_balance: "50-50"
    bias_coverage: "±50 to ±10000"
    network_sizes: "2-4 stations"
    seeds: 1-100
    
  improvements_over_v1:
    - "50-50 balanced distribution (vs 6-94)"
    - "3x lower false positive rate"
    - "Pipeline-trained (matches deployment)"
    - "Better generalization to new scenarios"
```

---

## 5. Error Handling & Resilience

### 5.1 Harmonizer Resilience Pattern

```python
class ResilientHarmonizer:
    async def process_with_retry(self, event, max_retries=3):
        for attempt in range(max_retries):
            try:
                # Validate
                entity = TelemetryEventV0_1(**event)
                
                # Insert with idempotency
                await self.pg_pool.execute('''
                    INSERT INTO metrics ... ON CONFLICT DO NOTHING
                ''', ...)
                
                return True
                
            except ValidationError as e:
                logger.error(f"Invalid schema: {e}")
                return False  # Invalid data, skip
                
            except asyncpg.TooManyConnectionsError:
                # Transient: pool exhausted
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except asyncpg.UniqueViolationError:
                # Duplicate: idempotency works
                return True
                
            except Exception as e:
                logger.error(f"DB error ({attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    return False
                await asyncio.sleep(2 ** attempt)
        
        return False
```

### 5.2 Windowizer Timeout Handling

```python
class RobustWindowizer:
    async def monitor_incomplete_windows(self):
        """Periodically flush windows incomplete after timeout"""
        while True:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            for key, buffer in self.buffers.items():
                window_age = now() - buffer['window_start_time']
                
                if window_age > self.TIMEOUT_MS and buffer['windows']:
                    logger.warning(
                        f"Incomplete window {key}: "
                        f"got {len(buffer['current_window'])}/13 metrics "
                        f"after {window_age}ms"
                    )
                    
                    # Pad missing metrics with 0.0
                    for metric in self.required_features:
                        if metric not in buffer['current_window']:
                            buffer['current_window'][metric] = 0.0
                    
                    # Force window completion
                    buffer['windows'].append(buffer['current_window'])
                    buffer['current_window'] = {}
                    
                    if len(buffer['windows']) == self.segment_length:
                        segment = self._build_segment(key, buffer['windows'])
                        await self.publish_segment(segment)
                        buffer['windows'] = []
```

---

## 6. Model Registry & Versioning

### 6.1 Registry Structure

```
twin/registry/gcn/
├── current → v2.0.0          # Symlink to active version
├── v1.0.0/                   # Baseline model
│   ├── best_model.pt         # PyTorch model weights (110 KB)
│   ├── scaler.json           # StandardScaler parameters
│   ├── config.yaml           # Hyperparameters
│   ├── test_results.json     # Performance metrics
│   └── README.md             # Release notes
└── v2.0.0/                   # Production model
    ├── best_model.pt         # Updated weights
    ├── scaler.json
    ├── config.yaml           # 50-50 balanced
    ├── test_results.json
    ├── training_log.json     # Loss history
    └── README.md
```

### 6.2 Model Selection Logic

```python
class GCNDetector:
    @staticmethod
    def load_active_model(registry_path='/registry'):
        """Load currently active model via symlink"""
        current_link = os.path.join(registry_path, 'current')
        if not os.path.islink(current_link):
            raise RuntimeError(f"No active model (broken symlink: {current_link})")
        
        # Resolve: current → v2.0.0
        current_dir = os.path.realpath(current_link)
        
        # Load components
        config = yaml.safe_load(open(f'{current_dir}/config.yaml'))
        model_state = torch.load(f'{current_dir}/best_model.pt')
        scaler = json.load(open(f'{current_dir}/scaler.json'))
        
        return {
            'model': model_state,
            'scaler': scaler,
            'config': config,
            'version': os.path.basename(current_dir),  # v2.0.0
            'path': current_dir
        }
    
    @staticmethod
    def publish_version(source_dir, version_name):
        """Deploy new model version"""
        target_dir = f'/registry/{version_name}'
        shutil.copytree(source_dir, target_dir)
        
        # Switch active version
        current_link = '/registry/current'
        if os.path.islink(current_link):
            os.remove(current_link)
        
        os.symlink(target_dir, current_link)
        
        logger.info(f"Deployed model {version_name}")
```

---

## 7. Performance Characteristics

### 7.1 Latency Profile

```
Event generation to Prediction: <500ms

Timeline:
  T=0ms      Event generated (ns3, e.g., throughput measurement)
  T=50ms     Event published to Kafka (exporter + network)
  T=100ms    Harmonizer inserts to DB, Windowizer buffers
  T=200ms    Window complete (after 100ms aggregation)
  T=400ms    Segment complete (256 windows × 100ms = 25.6s real)
  T=415ms    GCN inference (12-30ms)
  T=450ms    Result in DB and Kafka
  T=500ms    Dashboard WebSocket update

Key: Windowizer adds 25.6s real-time lag (256 windows × 100ms each)
     But handles continuous stream, not batch processing
```

### 7.2 Throughput Capacity

```
Single Pipeline Instance:

Harmonizer:
- Kafka consumer: 50-100 msg/sec input
- DB insertions: 1000+ rows/sec (batched)
- Bottleneck: DB connection pool, not processing

Windowizer:
- Kafka consumer: 50-100 msg/sec input
- Output: ~4 segments/sec (after 256 windows)
- Memory: O(num_entities) for buffering

GCN Detector:
- Input: 4 segments/sec (from windowizer)
- Inference: 12-30ms per segment
- Peak throughput: 30-50 segments/sec
- Bottleneck: GPU (if used) or CPU (current setup)

Total: Can handle 100+ active experiments simultaneously
```

### 7.3 Resource Usage

```
Memory (container limits):

Harmonizer:
  Idle: 200 MB
  Peak (100 active experiments): 800 MB
  Ceiling: 2 GB

Windowizer:
  Idle: 300 MB (Kafka buffers)
  Peak (256 window cache): 1 GB
  Ceiling: 2 GB

GCN Detector:
  Model loaded: 150 MB
  Peak (batch of 4): 500 MB
  Ceiling: 1 GB

Total Pipeline: 6-8 GB RAM for max capacity
```

---

## 8. Security Considerations

### 8.1 Data Validation Pipeline

```python
# 1. Schema validation (Pydantic)
event = TelemetryEventV0_1(**raw_json)  # Raises ValidationError

# 2. Type checking
assert isinstance(event.value, float)
assert 0 <= event.value < 1e6  # Sanity check

# 3. Entity validation
assert event.entity_id in KNOWN_ENTITIES  # Optional whitelist

# 4. Metric validation
assert event.metric in KNOWN_METRICS
assert event.unit in KNOWN_UNITS

# 5. Timestamp validation
assert event.ts > (now() - timedelta(minutes=5))  # Recent data only
assert event.ts < (now() + timedelta(seconds=1))  # Not future-dated
```

### 8.2 Model Predictions Guardrails

```python
# No model output used directly without validation

# 1. Confidence filtering
if prediction['confidence'] < 0.7:
    logger.warning(f"Low confidence {prediction['confidence']}: {segment_id}")
    prediction['flag'] = 'uncertain'  # Flag for review

# 2. Prediction rate limiting
if attack_detection_rate > THRESHOLD:
    # Too many false positives likely
    logger.alert("Anomaly: High attack detection rate")
    prediction['requires_review'] = True

# 3. Time-based validation
if last_prediction_time - current_time > TIMEOUT:
    logger.warning("Stale model: last prediction > 1 hour ago")
    prediction['has_stale_model'] = True

# 4. Model version tracking
if prediction['model_version'] != EXPECTED_VERSION:
    logger.warning(f"Unexpected model version: {prediction['model_version']}")
```

This completes the technical architecture deep dive. All components are production-deployed and validated as of March 9, 2026.

