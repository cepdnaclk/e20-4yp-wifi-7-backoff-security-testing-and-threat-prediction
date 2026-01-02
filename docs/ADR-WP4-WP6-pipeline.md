# ADR-WP4-WP6: Pipeline Architecture Decisions

## Status
Accepted

## Date
2025-12-23

## Context
WP4-WP6 implemented the telemetry pipeline: ns-3 → Exporter → Kafka → Harmonizer → DB → Grafana. Several architectural decisions were made to ensure reliability, idempotency, and maintainability.

---

## ADR-WP4-01: Telemetry Contract is JSONL (v0.1)

### Decision
JSON Lines file per experiment run with v0.1 schema.

### Rationale
- Easy to generate from simulation
- Easy to stream and replay
- Easy to validate with Pydantic

### Consequence
All ns-3 scenarios must output telemetry in this contract. Schema changes require version bump.

---

## ADR-WP4-02: Exporter Reads File and Publishes to Kafka

### Decision
File→Kafka exporter as separate container service.

### Rationale
- Keeps ns-3 simple (no Kafka client in C++)
- Simplifies debugging (can test exporter independently)
- Supports multiple producers later
- Decouples simulation from transport mechanism

### Implementation
```
telemetry/exporters/ns3_file_exporter/
├── Dockerfile
├── requirements.txt
├── exporter.py
└── README.md
```

### Consequence
Pipeline becomes modular and testable. Need to manage exporter state (offsets).

---

## ADR-WP4-03: Deterministic Kafka Message Key

### Decision
Message key = `experiment_id|entity_id|metric|ts`

### Rationale
- Enables downstream idempotency
- Kafka can dedupe by key if configured
- Harmonizer can safely upsert based on key components
- Same measurement always produces same key

### Implementation
```python
key = f"{record.experiment_id}|{record.entity_id}|{record.metric}|{record.ts}"
producer.send(topic, key=key.encode(), value=line.encode())
```

### Consequence
Re-publishing is safe. Same data = same key = no duplicates downstream.

---

## ADR-WP4-04: Exporter Uses Persisted Offsets

### Decision
Store file read position (byte offset) in persistent state file, keyed by file path.

### Rationale
- Prevents re-publishing same lines on restart
- Survives container restarts
- Can resume after failures
- Per-file tracking handles multiple experiments

### Implementation
```json
// .exporter_state/exporter_state.json
{
  "/artifacts/exp1/telemetry.jsonl": {"offset": 195},
  "/artifacts/exp2/telemetry.jsonl": {"offset": 0}
}
```

### Consequence
- Offset must be per file path (not global)
- Permissions must be handled (run with host user)
- State file must be mounted from host

---

## ADR-WP5-01: Kafka is Ingestion Bus, DB is Query Source

### Decision
Use Kafka for transport/buffering, Postgres/TimescaleDB for storage and querying.

### Rationale
- **Kafka**: Good at buffering, replay, multiple consumers
- **Database**: Good at querying, aggregation, Grafana integration
- **Separation**: Each component does what it's best at
- Grafana works best with SQL databases

### Architecture
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Exporter  │────▶│   Kafka     │────▶│ Harmonizer  │
└─────────────┘     │  (buffer)   │     └──────┬──────┘
                    └─────────────┘            │
                                               ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   Grafana   │◀────│  Database   │
                    │  (query)    │     │  (store)    │
                    └─────────────┘     └─────────────┘
```

### Consequence
Grafana depends on DB ingestion correctness. Kafka is transient, DB is the source of truth.

---

## ADR-WP5-02: Harmonizer Responsible for Validation and Mapping

### Decision
Enforce schema validation and field mapping at the harmonizer boundary.

### Rationale
- Single point of validation (not scattered)
- Database remains clean and queryable
- Can reject bad messages early with clear logging
- Mapping logic is centralized

### Implementation
```python
def process_message(msg):
    data = json.loads(msg.value())
    
    # Validate required fields
    required = ['experiment_id', 'ts', 'entity_id', 'metric', 'value', 'unit', 'source']
    for field in required:
        if field not in data:
            logger.error(f"Missing field: {field}")
            return  # Skip bad message
    
    # Map fields (metric -> metric_name for DB column)
    insert_row(
        experiment_id=data['experiment_id'],
        metric_name=data['metric'],  # Field name mapping
        ...
    )
```

### Consequence
- Harmonizer must reject bad messages and log clearly
- Need monitoring for rejected message count
- Future: dead-letter topic for failed messages

---

## ADR-WP5-03: DB Idempotency Enforced with Unique Index

### Decision
Prevent duplicate rows using unique constraint and upsert (INSERT ... ON CONFLICT) strategy.

### Rationale
- Experiments are often re-run
- Pipeline replay should be safe
- Consistent with deterministic Kafka key strategy
- No manual cleanup needed

### Implementation
```sql
-- Unique constraint
CREATE UNIQUE INDEX uq_metrics_idem 
ON metrics (experiment_id, entity_id, metric_name, ts);

-- Upsert query
INSERT INTO metrics (experiment_id, ts, entity_id, metric_name, value, unit, source)
VALUES ($1, $2, $3, $4, $5, $6, $7)
ON CONFLICT (experiment_id, entity_id, metric_name, ts) 
DO UPDATE SET value = EXCLUDED.value, ingest_time = NOW();
```

### Consequence
- Re-running pipeline is always safe
- Must use upsert, not plain INSERT
- Slightly more complex queries but worth it

---

## ADR-WP6-01: Grafana Provisioning as Code

### Decision
Datasource and dashboard configurations are versioned in repo via provisioning mounts.

### Rationale
- **Reproducibility**: Labs can be recreated identically
- **Onboarding**: New team members get working dashboards immediately
- **Version control**: Dashboard changes tracked in git
- **No manual setup**: No clicking in Grafana UI required

### Implementation
```
clab/configs/grafana/
├── provisioning/
│   ├── datasources/
│   │   └── udr-postgres.yml    # Datasource definition
│   └── dashboards/
│       └── dashboards.yml      # Dashboard provider config
└── dashboards/
    └── *.json                  # Dashboard JSON files
```

### Containerlab Mount
```yaml
grafana:
  binds:
    - configs/grafana/provisioning:/etc/grafana/provisioning:ro
    - configs/grafana/dashboards:/var/lib/grafana/dashboards:ro
```

### Consequence
- Provisioning YAML must be valid (Grafana fails to start otherwise)
- Only ONE datasource can have `isDefault: true`
- Dashboard JSON changes are tracked in git history

---

## Summary: Three Layers of Idempotency

The pipeline implements idempotency at three layers:

| Layer | Mechanism | Purpose |
|-------|-----------|---------|
| **Exporter** | Per-file offset tracking | Don't re-publish same lines |
| **Kafka** | Deterministic message key | Same data = same key |
| **Database** | Unique index + upsert | No duplicate rows |

This means:
- Re-running exporter is safe
- Re-running harmonizer is safe
- Replaying Kafka topic is safe
- The entire pipeline is idempotent

---

## Related Work Packages
- WP4: Telemetry Exporter
- WP5: Harmonizer
- WP6: Grafana Dashboards
