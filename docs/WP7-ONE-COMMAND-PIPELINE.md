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

---

## WP7.5: MLO Attack Scenarios

WP7.5 added three Wi-Fi 7 MLO (Multi-Link Operation) backoff manipulation scenarios for GNN dataset generation and pipeline integration.

### Available Scenarios

| Scenario | Make Target | Source File | Bias | Purpose |
|----------|-------------|-------------|------|---------|
| Normal | `run-mlo-normal` | wifi7-mlo-Normal.cc | 0 | Baseline (no attack) |
| Positive | `run-mlo-positive` | wifi7-mlo-Positive.cc | +5000 | Aggressive transmission attack |
| Negative | `run-mlo-negative` | wifi7-mlo-Negative.cc | -5000 | Extreme aggressive attack |

### MLO Metrics (13 per 0.1s window)

**Network Layer:**
- `net_throughput_mbps` - Aggregate throughput
- `net_avg_delay_ms` - Average packet delay
- `net_avg_jitter_ms` - Delay variation
- `net_packet_loss_ratio` - Loss ratio
- `net_active_flows` - Number of active flows

**MAC Layer:**
- `mac_total_tx` - Total transmitted frames
- `mac_total_rx` - Total received frames
- `mac_total_ack` - Total ACKs received
- `mac_total_retrans` - Retransmission count
- `mac_drop_count` - MAC layer drops

**PHY Layer:**
- `phy_drop_count` - PHY layer drops
- `avg_backoff_slots` - Average backoff (key attack indicator)
- `channel_busy_ratio` - Channel utilization

### Running MLO Scenarios

```bash
# Prerequisites (if not already running)
make up
make pipeline-up

# Run individual scenarios
make run-mlo-normal EXP_ID=20260103-1400-mlo-normal-42
make run-mlo-positive EXP_ID=20260103-1400-mlo-attack-pos-42
make run-mlo-negative EXP_ID=20260103-1400-mlo-attack-neg-42

# Or run with full pipeline (simulation + exporter)
make run-mlo-exp EXP_ID=20260103-1400-mlo-normal-42 SCENARIO=normal
make run-mlo-exp EXP_ID=20260103-1400-mlo-attack-pos-42 SCENARIO=positive
```

### Output Artifacts

Each MLO run creates these files in `sim/ns3/artifacts/<EXP_ID>/`:

| File | Purpose |
|------|---------|
| `meta.txt` | Run metadata (scenario, bias, seed, timestamps) |
| `mlo_output.json` | Original JSON array (for GNN training) |
| `telemetry.jsonl` | Pipeline-compatible JSONL (for Kafka/DB) |
| `ns3_stdout.log` | Simulation stdout |
| `ns3_stderr.log` | Simulation stderr |

### Comparing Attack Scenarios

```bash
# Run all three scenarios
make run-mlo-exp EXP_ID=20260103-1500-mlo-normal-42 SCENARIO=normal
make run-mlo-exp EXP_ID=20260103-1500-mlo-attack-pos-42 SCENARIO=positive
make run-mlo-exp EXP_ID=20260103-1500-mlo-attack-neg-42 SCENARIO=negative

# Compare in database
docker exec -it clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "
  SELECT experiment_id, metric_name, AVG(value) as avg_value
  FROM metrics
  WHERE experiment_id LIKE '20260103-1500-mlo-%'
  AND metric_name IN ('net_throughput_mbps', 'avg_backoff_slots', 'channel_busy_ratio')
  GROUP BY experiment_id, metric_name
  ORDER BY metric_name, experiment_id;
"
```

### Architecture

```
wifi7-mlo-*.cc (ns-3)
    │
    ▼ --jsonPath=mlo_output.json
JSON Array Output
    │
    ▼ convert_mlo_json_to_jsonl.sh
telemetry.jsonl (JSONL format)
    │
    ▼ Exporter → Kafka
WP7 Pipeline (Harmonizer → DB → Grafana)
```

**Key Design Decision:** Keep both outputs:
- JSON array → GNN training workflow (preserved)
- JSONL → Pipeline integration (new)

### Files Added

| File | Purpose |
|------|---------|
| `sim/ns3/scenario/run_mlo_scenario.sh` | Scenario runner script |
| `sim/ns3/scenario/convert_mlo_json_to_jsonl.sh` | JSON → JSONL converter |

### Files Modified

| File | Change |
|------|--------|
| `sim/ns3/scratch/wifi7-mlo-*.cc` | Fixed to use `jsonPath` CLI arg |
| `Makefile` | Added `run-mlo-*` targets |

---

## MLO Attack Scenarios Dashboard

**Access:** http://localhost:3000/d/mlo-attack-scenarios

**Purpose:** Compare Wi-Fi 7 MLO backoff manipulation attacks and measure network impact.

**Key Feature:** Dashboard auto-discovers MLO experiments from database - no manual configuration required.

### Available Panels

| # | Panel | Purpose |
|---|-------|---------|
| 1 | Average Backoff Slots | **Attack indicator** - shows manipulation (Normal ~5, Positive ~1411, Negative ~2.2) |
| 2 | Network Throughput | **Primary impact** - Normal 262.5 Mbps, Positive 41.7 Mbps (-84%), Negative 146.7 Mbps (-44%) |
| 3 | Packet Loss Ratio | Quality degradation |
| 4 | Average Delay | Latency impact |
| 5 | Average Jitter | Delay variation |
| 6 | MAC Retransmissions | Contention/collision rate |
| 7 | Channel Busy Ratio | Channel utilization |
| 8 | Network Active Flows | Network activity level (0-5 range) |
| 9 | Key Metrics Summary | Statistical table (avg, stddev, min, max) |

### Dynamic Experiment Filter

The dashboard automatically discovers all MLO experiments using a query-based template variable:

```sql
SELECT DISTINCT experiment_id FROM metrics WHERE experiment_id ~ '.*-mlo-.*' ORDER BY experiment_id DESC
```

**How it works:**
- New experiments appear automatically after dashboard refresh (Ctrl+R)
- Multi-select dropdown allows comparing specific scenarios
- "All" option shows all MLO experiments
- No manual dashboard edits required

### Color Coding

| Scenario | Color | Regex Pattern |
|----------|-------|---------------|
| Normal (baseline) | Green | `.*-normal-.*` |
| Positive attack (+5000) | Red | `.*-attack-pos-.*` |
| Negative attack (-5000) | Orange | `.*-attack-neg-.*` |

### Usage

```bash
# Run all three scenarios
make run-mlo-exp EXP_ID=20260105-1600-mlo-normal-42 SCENARIO=normal
make run-mlo-exp EXP_ID=20260105-1600-mlo-attack-pos-42 SCENARIO=positive
make run-mlo-exp EXP_ID=20260105-1600-mlo-attack-neg-42 SCENARIO=negative

# Open dashboard
# http://localhost:3000/d/mlo-attack-scenarios

# Refresh dashboard (Ctrl+R) to see new experiments
# Use experiment filter dropdown to select specific runs
```

### Interpreting Results

**Attack Indicator (Panel 1 - Backoff Slots):**
- Normal baseline: ~5 slots
- Positive bias: 100x-300x increase (aggressive early transmission)
- Negative bias: 50%-90% decrease (extremely aggressive)

**Impact Metrics:**
- Throughput (Panel 2): Primary measure of attack success
- Packet Loss (Panel 3): Secondary quality indicator
- Delay/Jitter (Panels 4-5): Tertiary QoS impact
- Retransmissions (Panel 6): MAC layer stress indicator

**Research Questions Answered:**
1. How does backoff manipulation affect throughput? → See Panel 1 vs Panel 2 correlation
2. What's the impact on packet loss? → Panel 3 shows quality degradation
3. Which metrics are most sensitive? → Panel 9 statistical table shows variance
4. Can we visually distinguish attacks? → Color-coded time series make patterns obvious

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No data in panels | Adjust time range to cover experiment timestamps (use absolute: 2026-01-04 11:44-11:53) |
| Only 1-2 series visible | Check experiment filter dropdown - select "All" |
| Time series not aligned | Verify all experiments have same time window length |
| New experiments don't appear | Refresh dashboard (Ctrl+R) - they auto-discover |

---

## Next Steps (→ WP8)

- Multi-scenario support (scenario registry)
- Parameterized experiment runs
- Scenario-specific ns-3 configurations
- Baseline vs attack scenario comparison
