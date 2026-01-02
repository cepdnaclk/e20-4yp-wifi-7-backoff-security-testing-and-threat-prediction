# WP4: Telemetry Exporter (ns-3 Artifacts → Kafka)

## Status: ✅ COMPLETED

## Overview
WP4 implemented the telemetry exporter that reads ns-3 telemetry files and publishes them to Kafka (Redpanda).

---

## What Was Implemented

### 1. Exporter Service
**Path:** `telemetry/exporters/ns3_file_exporter/`

```
telemetry/exporters/ns3_file_exporter/
├── Dockerfile
├── requirements.txt
├── exporter.py
└── README.md
```

### 2. Behavior
- Reads `TELEMETRY_FILE` continuously (polling mode)
- Parses each JSON line
- Validates shape using Pydantic (`TelemetryRecord`)
- Normalizes timestamps into ISO format
- Produces messages to Kafka topic

### 3. Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEMETRY_FILE` | Required | Path to telemetry.jsonl |
| `KAFKA_BROKERS` | `bus-redpanda:9092` | Kafka broker address |
| `KAFKA_TOPIC` | `wifi7.telemetry.v0_1` | Target topic |

### 4. Kafka Message Key
Deterministic key for idempotency:
```
experiment_id|entity_id|metric|ts
```

### 5. Offset Tracking
**State file:** `/state/exporter_state.json` (container) → `.exporter_state/` (host)

```json
{
  "/path/to/telemetry.jsonl": {
    "offset": 195
  }
}
```

**Key improvement:** State is stored per telemetry file path, not globally.

---

## Acceptance Criteria (All Met)

| Criteria | Status |
|----------|--------|
| Exporter image builds | ✅ |
| Publishes to Redpanda topic | ✅ |
| Messages have correct schema | ✅ |
| Offset tracking works | ✅ |
| No duplicate publishing | ✅ |

---

## Key Commands

```bash
# Build exporter image
make exporter-build
# or
docker build -t ndt/ns3-exporter:local telemetry/exporters/ns3_file_exporter

# Run exporter for specific experiment
make exporter-run EXP_ID=20251223-0300-wifi-example-44

# Verify messages in Kafka
docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic consume wifi7.telemetry.v0_1 --brokers localhost:9092 -o oldest -n 50
```

---

## Problems Solved

### Problem 1: resume_offset=195 and Nothing Published
**Symptom:** Exporter logs show `resume_offset=195` but no messages appear.

**Cause:** 
- Old state file had global offset `{"offset": 195}`
- Many telemetry files have first record around that size
- Exporter started at end-of-file

**Solution:**
- Store offsets per file path
- Or delete/reset `.exporter_state/exporter_state.json`

### Problem 2: Root-Owned State Files
**Symptom:** `rm: cannot remove ... Permission denied`

**Cause:** Container ran as root.

**Solution:** Run with `--user "$(id -u):$(id -g)"`.

### Problem 3: Exporter Can't Find Kafka
**Cause:** Not on same Docker network as Redpanda.

**Solution:** Use `--network clab-mgmt` or containerlab network name.

---

## Implementation Details

### Telemetry Contract v0.1
```python
class TelemetryRecord(BaseModel):
    experiment_id: str
    ts: str  # ISO timestamp
    source: str = "ns3"
    schema_version: str = "v0.1"
    entity_id: str
    metric: str
    value: float
    unit: str
```

### Exporter Core Logic
```python
def process_file(filepath: str, state: dict):
    offset = state.get(filepath, {}).get("offset", 0)
    
    with open(filepath, 'r') as f:
        f.seek(offset)
        for line in f:
            record = TelemetryRecord.parse_raw(line)
            key = f"{record.experiment_id}|{record.entity_id}|{record.metric}|{record.ts}"
            producer.send(KAFKA_TOPIC, key=key.encode(), value=line.encode())
        
        state[filepath] = {"offset": f.tell()}
    
    save_state(state)
```

### Makefile Target
```makefile
exporter-run:
	docker run --rm \
	  --network clab-mgmt \
	  --user "$(shell id -u):$(shell id -g)" \
	  -v $(PWD)/sim/ns3/artifacts:/artifacts:ro \
	  -v $(PWD)/.exporter_state:/state \
	  -e TELEMETRY_FILE=/artifacts/$(EXP_ID)/telemetry.jsonl \
	  ndt/ns3-exporter:local
```

---

## Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  sim/ns3/artifacts/<EXP_ID>/telemetry.jsonl                 │
│                          │                                   │
│                          ▼                                   │
│  ┌─────────────────────────────────────────┐                │
│  │         ns3_file_exporter               │                │
│  │                                         │                │
│  │  1. Read JSONL file                     │                │
│  │  2. Parse & validate (Pydantic)         │                │
│  │  3. Create deterministic key            │                │
│  │  4. Publish to Kafka                    │                │
│  │  5. Update offset state                 │                │
│  └─────────────────┬───────────────────────┘                │
│                    │                                         │
│                    ▼                                         │
│  ┌─────────────────────────────────────────┐                │
│  │         Redpanda (Kafka API)            │                │
│  │         Topic: wifi7.telemetry.v0_1     │                │
│  └─────────────────────────────────────────┘                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## State File Behavior

| Scenario | Behavior |
|----------|----------|
| New file | Start from offset 0 |
| Same file, new lines | Continue from last offset |
| File shrinks (reset) | Should reset to 0 (WP10 improvement) |
| Different file path | Independent offset tracking |

---

## Runtime Requirements

1. **Network:** Must be on `clab-mgmt` network to reach Redpanda
2. **Permissions:** Run with host user to avoid root-owned files
3. **Mounts:**
   - Artifacts directory (read-only)
   - State directory (read-write)

---

## Verification

```bash
# 1. Run ns-3 experiment
make ns3-run-example EXP_ID=20251223-test-01

# 2. Run exporter
make exporter-run EXP_ID=20251223-test-01

# 3. Check Kafka topic
docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic consume wifi7.telemetry.v0_1 -o oldest -n 10

# Expected output:
# {"experiment_id":"20251223-test-01","ts":"...","source":"ns3",...}
```

---

## Related ADRs
- ADR-WP4-01: Telemetry contract is JSONL (v0.1)
- ADR-WP4-02: Exporter reads file and publishes to Kafka
- ADR-WP4-03: Deterministic Kafka message key
- ADR-WP4-04: Exporter uses persisted offsets

---

## Next Steps (→ WP5)
- Build harmonizer to consume Kafka
- Validate and insert into UDR database
- Implement idempotent upserts
