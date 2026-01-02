# WP5: Harmonizer (Kafka → UDR Database)

## Status: ✅ COMPLETED

## Overview
WP5 implemented the harmonizer service that consumes telemetry from Kafka and inserts it into the UDR database (Postgres/TimescaleDB).

---

## What Was Implemented

### 1. Harmonizer Service
**Path:** `telemetry/harmonizer/`

```
telemetry/harmonizer/
├── Dockerfile
├── requirements.txt
├── harmonizer.py
└── README.md
```

### 2. Behavior
- Kafka consumer reads from `wifi7.telemetry.v0_1`
- Validates payload and required fields
- Inserts into `public.metrics` table
- Uses upsert strategy for idempotency

### 3. Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BROKERS` | `bus-redpanda:9092` | Kafka broker |
| `KAFKA_TOPIC` | `wifi7.telemetry.v0_1` | Source topic |
| `KAFKA_GROUP` | `harmonizer-udm-v0` | Consumer group |
| `AUTO_OFFSET_RESET` | `latest` | Where to start (use `earliest` for replay) |
| `PG_HOST` | `udr-db` | Database host |
| `PG_DB` | `udr` | Database name |
| `PG_USER` | `udr` | Database user |
| `PG_PASS` | `udr_pass` | Database password |
| `BATCH_SIZE` | `100` | Records per batch insert |

---

## Acceptance Criteria (All Met)

| Criteria | Status |
|----------|--------|
| Harmonizer image builds | ✅ |
| Consumes from Kafka topic | ✅ |
| Validates message schema | ✅ |
| Inserts into DB | ✅ |
| Idempotent (no duplicates) | ✅ |
| Logs ingestion count | ✅ |

---

## Key Commands

```bash
# Build harmonizer image
make harmonizer-build
# or
docker build -t ndt/harmonizer:local telemetry/harmonizer

# Run harmonizer (continuous)
make harmonizer-run

# Run with replay from beginning
docker run --rm \
  --network clab-mgmt \
  -e KAFKA_GROUP=harmonizer-udm-v0-replay \
  -e AUTO_OFFSET_RESET=earliest \
  ndt/harmonizer:local

# Verify DB inserts
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "SELECT * FROM metrics ORDER BY ts DESC LIMIT 5;"
```

---

## Database Schema

### metrics Table
```sql
CREATE TABLE metrics (
    experiment_id TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    entity_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL,
    source TEXT NOT NULL,
    ingest_time TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX metrics_ts_idx ON metrics (ts DESC);
CREATE INDEX ix_metrics_exp_metric_ts ON metrics (experiment_id, metric_name, ts);
CREATE UNIQUE INDEX uq_metrics_idem ON metrics (experiment_id, entity_id, metric_name, ts);
```

### Verification
```bash
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "\d metrics"
```

---

## Problems Solved

### Problem 1: Harmonizer Runs But DB Doesn't Change
**Cause:** Kafka consumer group already consumed those messages.

**Solution:**
- Use a new consumer group: `KAFKA_GROUP=harmonizer-udm-v0-test1`
- Set `AUTO_OFFSET_RESET=earliest` for replay
- Or produce new messages (new experiment)

### Problem 2: Duplicate Inserts
**Cause:** Re-running harmonizer without idempotency.

**Solution:**
- Unique constraint on `(experiment_id, entity_id, metric_name, ts)`
- Use INSERT ... ON CONFLICT DO UPDATE (upsert)

### Problem 3: Connection Refused to DB
**Cause:** Not on same Docker network.

**Solution:** Use `--network clab-mgmt`.

---

## Implementation Details

### Harmonizer Core Logic
```python
def process_message(msg):
    data = json.loads(msg.value())
    
    # Validate required fields
    required = ['experiment_id', 'ts', 'entity_id', 'metric', 'value', 'unit', 'source']
    for field in required:
        if field not in data:
            raise ValueError(f"Missing field: {field}")
    
    # Insert with upsert
    cursor.execute("""
        INSERT INTO metrics (experiment_id, ts, entity_id, metric_name, value, unit, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (experiment_id, entity_id, metric_name, ts) 
        DO UPDATE SET value = EXCLUDED.value, ingest_time = NOW()
    """, (
        data['experiment_id'],
        data['ts'],
        data['entity_id'],
        data['metric'],
        data['value'],
        data['unit'],
        data['source']
    ))
```

### Consumer Group Behavior
```
┌─────────────────────────────────────────────────────────────┐
│                    Kafka Consumer Groups                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Group: harmonizer-udm-v0                                   │
│  ├── Partition 0: offset 150 (committed)                    │
│  │                                                          │
│  │   Next run starts from offset 150                        │
│  │   Messages 0-149 will NOT be re-consumed                 │
│                                                             │
│  Group: harmonizer-udm-v0-replay (new group)                │
│  ├── Partition 0: offset 0 (no commits)                     │
│  │                                                          │
│  │   With AUTO_OFFSET_RESET=earliest                        │
│  │   Starts from offset 0 (all messages)                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ┌─────────────────────────────────────────┐               │
│  │         Redpanda (Kafka API)            │               │
│  │         Topic: wifi7.telemetry.v0_1     │               │
│  └─────────────────┬───────────────────────┘               │
│                    │                                        │
│                    ▼                                        │
│  ┌─────────────────────────────────────────┐               │
│  │            Harmonizer                    │               │
│  │                                          │               │
│  │  1. Consume messages                     │               │
│  │  2. Validate schema                      │               │
│  │  3. Map fields to UDM                    │               │
│  │  4. Upsert to database                   │               │
│  │  5. Commit offset                        │               │
│  └─────────────────┬───────────────────────┘               │
│                    │                                        │
│                    ▼                                        │
│  ┌─────────────────────────────────────────┐               │
│  │         UDR Database (TimescaleDB)      │               │
│  │         Table: public.metrics           │               │
│  └─────────────────────────────────────────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Idempotency Design

### Three Layers of Protection

1. **Deterministic Kafka Key** (WP4)
   - Key: `experiment_id|entity_id|metric|ts`
   - Same message = same key

2. **Unique DB Constraint**
   - `UNIQUE (experiment_id, entity_id, metric_name, ts)`
   - Prevents duplicate rows

3. **Upsert Strategy**
   - `INSERT ... ON CONFLICT DO UPDATE`
   - Re-running is safe

---

## Replay Behavior

| Scenario | How to Replay |
|----------|---------------|
| Re-process all messages | New consumer group + `earliest` |
| Re-process recent | Reset offsets in Kafka |
| Skip to latest | Default behavior |

```bash
# Full replay
docker run --rm --network clab-mgmt \
  -e KAFKA_GROUP=harmonizer-replay-$(date +%s) \
  -e AUTO_OFFSET_RESET=earliest \
  ndt/harmonizer:local
```

---

## Verification

```bash
# 1. Check messages in Kafka
docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic consume wifi7.telemetry.v0_1 -o oldest -n 5

# 2. Run harmonizer
make harmonizer-run

# 3. Check DB
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "SELECT experiment_id, ts, metric_name, value FROM metrics ORDER BY ts DESC LIMIT 5;"

# Expected output:
#  experiment_id  |          ts           | metric_name    | value
# ----------------+-----------------------+----------------+-------
#  20251223-test  | 2025-12-23 12:00:00+00| throughput_mbps| 117.5
```

---

## Related ADRs
- ADR-WP5-01: Kafka is ingestion bus, DB is query source
- ADR-WP5-02: Harmonizer responsible for validation and mapping
- ADR-WP5-03: DB idempotency enforced with unique index

---

## Next Steps (→ WP6)
- Configure Grafana datasource
- Create dashboards for metrics visualization
- Add experiment comparison panels
