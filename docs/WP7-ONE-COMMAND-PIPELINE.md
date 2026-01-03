# WP7: One-Command Pipeline

## Status: ✅ COMPLETED

## Overview
WP7 automated the manual multi-step pipeline into a one-command workflow. The harmonizer now runs as a background service via Docker Compose, and experiments can be run with a single `make run-exp` command.

---

## What Was Implemented

### 1. Docker Compose for Pipeline Services
**File:** `docker-compose.pipeline.yml`

Manages the harmonizer as a long-running background service that continuously consumes from Kafka and writes to TimescaleDB.

```yaml
version: '3.8'

networks:
  clab-mgmt:
    external: true  # Created by containerlab

services:
  harmonizer:
    image: ndt/harmonizer:local
    container_name: ndt-pipeline-harmonizer
    restart: unless-stopped
    networks:
      - clab-mgmt
    environment:
      KAFKA_BROKERS: ${KAFKA_BROKERS:-bus-redpanda:9092}
      KAFKA_TOPIC: ${KAFKA_TOPIC:-wifi7.telemetry.v0_1}
      KAFKA_GROUP: ${KAFKA_GROUP:-harmonizer-udm-v0}
      AUTO_OFFSET_RESET: ${AUTO_OFFSET_RESET:-latest}
      PG_HOST: ${PG_HOST:-udr-db}
      PG_DB: ${PG_DB:-udr}
      PG_USER: ${PG_USER:-udr}
      PG_PASS: ${PG_PASS:-udr_pass}
      BATCH_SIZE: ${BATCH_SIZE:-100}
```

### 2. Makefile Automation
**New targets added to `Makefile`:**

| Target | Purpose |
|--------|---------|
| `pipeline-up` | Start harmonizer as background service |
| `pipeline-down` | Stop harmonizer |
| `pipeline-status` | Check status and view logs |
| `run-exp` | Run complete experiment end-to-end |

### 3. Workflow Comparison

**Before (WP6):**
```bash
# Required 3 separate commands and a dedicated terminal
make ns3-run-example EXP_ID=20260103-test-01
make exporter-run EXP_ID=20260103-test-01
make harmonizer-run  # In separate terminal, kept running
```

**After (WP7):**
```bash
# One-time setup (starts harmonizer in background)
make pipeline-up

# Run experiments with a single command
make run-exp EXP_ID=20260103-test-01

# When done
make pipeline-down
```

---

## Acceptance Criteria (All Met)

| Criteria | Status |
|----------|--------|
| `docker-compose.pipeline.yml` exists | ✅ |
| `make pipeline-up` starts harmonizer | ✅ |
| `make pipeline-down` stops cleanly | ✅ |
| `make pipeline-status` shows status | ✅ |
| `make run-exp` runs full pipeline | ✅ |
| Multiple experiments run sequentially | ✅ |
| Data appears in database | ✅ |
| Data visible in Grafana | ✅ |

---

## Key Commands

```bash
# Start everything
make up              # Containerlab services (Kafka, DB, Grafana)
make pipeline-up     # Pipeline services (harmonizer)

# Run experiment (one command!)
make run-exp EXP_ID=20260103-1200-test-01

# Check status
make pipeline-status

# Stop everything
make pipeline-down   # Stop harmonizer
make down            # Stop containerlab
```

---

## Complete Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                     WP7: AUTOMATED PIPELINE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  make pipeline-up  (once)                                │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │  Harmonizer (background, docker-compose)           │  │   │
│  │  │  Continuously: Kafka → DB                          │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  make run-exp EXP_ID=...  (per experiment)              │   │
│  │                                                          │   │
│  │  [1/3] ns-3 simulation                                   │   │
│  │         │                                                │   │
│  │         ▼ telemetry.jsonl                               │   │
│  │  [2/3] Exporter → Kafka                                  │   │
│  │         │                                                │   │
│  │         ▼ (harmonizer picks up automatically)           │   │
│  │  [3/3] Wait 5s for DB ingestion                         │   │
│  │         │                                                │   │
│  │         ▼                                                │   │
│  │  Done! View in Grafana                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Problems Solved

### Problem 1: Manual Harmonizer Management
**Before:** Required a dedicated terminal to run `make harmonizer-run`
**Solution:** Docker Compose manages harmonizer with `restart: unless-stopped`

### Problem 2: Multi-Step Workflow
**Before:** Three separate commands needed for each experiment
**Solution:** `make run-exp` combines all steps into one command

### Problem 3: No Status Visibility
**Before:** Had to manually check if harmonizer was running
**Solution:** `make pipeline-status` shows service status and recent logs

---

## Verification

```bash
# 1. Start the pipeline
make up
make pipeline-up

# 2. Check harmonizer is running
make pipeline-status

# 3. Run a test experiment
make run-exp EXP_ID=20260103-test-01

# 4. Verify data in database
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "SELECT COUNT(*) FROM metrics WHERE experiment_id='20260103-test-01';"

# 5. View in Grafana
# Open http://localhost:3000

# 6. Clean up
make pipeline-down
make down
```

---

## Troubleshooting

### Harmonizer Won't Start
**Error:** Network "clab-mgmt" not found
**Solution:** Run `make up` first to create containerlab network

### Harmonizer Keeps Restarting
**Cause:** Kafka or DB not ready yet
**Solution:**
1. Check with `docker logs ndt-pipeline-harmonizer`
2. `restart: unless-stopped` will retry automatically

### Data Not Appearing in DB
**Check:**
1. Is harmonizer running? `make pipeline-status`
2. Is data in Kafka? Check exporter output
3. Consumer group offset? New consumer group starts at `latest`

### Exporter State Issues
**Error:** Exporter publishes nothing
**Solution:** Delete `.exporter_state/exporter_state.json` and re-run

---

## Architecture Notes

### Why Docker Compose for Harmonizer?
- Long-running service (not one-shot like exporter)
- Needs `restart: unless-stopped` for reliability
- Cleaner than manual `docker run` in terminal
- Follows ADR-0004: Config as code

### Why Not Compose for Exporter?
- One-shot task per experiment
- Needs dynamic `EXP_ID` parameter
- State management requires host volume mounts
- Better as `docker run` with Makefile

### External Network Pattern
- Uses `external: true` for `clab-mgmt`
- Network created by containerlab (`make up`)
- Compose doesn't try to manage it
- Containerlab must start first

---

## Related ADRs

Consider creating:
- ADR-WP7-01: Use Docker Compose for Long-Running Pipeline Services

---

## Deprecated Targets

The following target is deprecated:
```bash
make run-wifi-pipeline  # DEPRECATED - use make run-exp instead
```

This target will be removed in WP8.

---

## Next Steps (→ WP8)

- Multi-scenario support (scenario registry)
- Parameterized experiment runs
- Scenario-specific ns-3 configurations
- Baseline vs attack scenario comparison
