# Windowizer Service

The windowizer service aggregates raw telemetry events into windowed feature segments for GCN inference.

## Purpose

Consume per-metric telemetry events from Kafka, group them by time windows, apply delta conversion to cumulative counters, and emit complete segments (256 windows) to the GCN detector.

## Data Flow

```
Kafka: wifi7.telemetry.v0_1
        (per-metric events)
              ↓
        Windowizer
    - Group by (experiment_id, ts, entity_id)
    - Aggregate 13 base features per window
    - Convert cumulative counters to deltas
    - Buffer into segments (L=256 windows)
              ↓
Kafka: wifi7.ml.windowed_features.v1
        (segment batches)
```

## Configuration

See `config.yaml` for full configuration options.

Key settings:
- `segment_length`: 256 (number of windows per segment)
- `window_interval_ms`: 100 (0.1s window size)
- `timeout_ms`: 5000 (wait time for incomplete windows)

## Building

```bash
make windowizer-build
```

## Running

```bash
# Start as background service
make windowizer-run

# View logs
make windowizer-logs

# Stop service
make windowizer-stop
```

## Implementation Status

**Phase 1 (Foundation)**: ✅ Configuration created
**Phase 2 (Implementation)**: 🔲 Not started

## Files

- `config.yaml`: Service configuration
- `Dockerfile`: Container definition (to be created in Phase 2)
- `requirements.txt`: Python dependencies (to be created in Phase 2)
- `windowizer.py`: Main service (to be created in Phase 2)
- `window_aggregator.py`: Aggregation logic (to be created in Phase 2)
- `delta_converter.py`: Delta computation (to be created in Phase 2)
- `segment_builder.py`: Segment buffering (to be created in Phase 2)
- `kafka_client.py`: Kafka I/O (to be created in Phase 2)
- `tests/`: Unit tests (to be created in Phase 2)
