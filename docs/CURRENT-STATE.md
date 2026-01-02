# NDT Wi-Fi 7 MLO Security - Current Project State

## Document Purpose
This document provides complete context about the current state of the project. Use this to quickly understand what has been implemented, what works, and what comes next.

---

## Quick Status

| Work Package | Status | Description |
|--------------|--------|-------------|
| WP1 | ✅ Complete | Local dev setup, GitHub SSH |
| WP2 | ✅ Complete | Containerlab skeleton with services |
| WP3 | ✅ Complete | ns-3 container + Wi-Fi telemetry |
| WP4 | ✅ Complete | Telemetry exporter (file → Kafka) |
| WP5 | ✅ Complete | Harmonizer (Kafka → DB) |
| WP6 | ✅ Complete | Grafana dashboards |
| WP7 | 🔲 Next | One-command pipeline |
| WP8+ | 🔲 Future | Multi-scenario, security, AI |

---

## Working Pipeline

```
ns-3 simulation run
        │
        ▼
sim/ns3/artifacts/<EXP_ID>/telemetry.jsonl
        │
        ▼
Exporter (ns3_file_exporter)
        │
        ▼
Redpanda (Kafka API) - topic: wifi7.telemetry.v0_1
        │
        ▼
Harmonizer
        │
        ▼
TimescaleDB (public.metrics table)
        │
        ▼
Grafana (http://localhost:3000)
```

---

## Running Services (Containerlab)

| Service | Container Name | Port | Purpose |
|---------|---------------|------|---------|
| UDR DB | `clab-ndt-wifi7-mlo-security-udr-db` | 5432 | TimescaleDB |
| Grafana | `clab-ndt-wifi7-mlo-security-grafana` | 3000 | Dashboards |
| Redpanda | `clab-ndt-wifi7-mlo-security-bus-redpanda` | 9092 | Kafka API |

---

## Key Commands

### Containerlab
```bash
make up                    # Deploy lab
make down                  # Destroy lab
make status                # Check status
make logs                  # View logs
```

### ns-3 Simulation
```bash
make ns3-build             # Build ns-3 image
make ns3-run EXP_ID=20251223-1200-baseline-42           # Run baseline
make ns3-run-example EXP_ID=20251223-1200-wifi-42       # Run WiFi example
```

### Pipeline Components
```bash
make exporter-build        # Build exporter image
make exporter-run EXP_ID=20251223-1200-wifi-42          # Run exporter
make harmonizer-build      # Build harmonizer image
make harmonizer-run        # Run harmonizer (continuous)
```

### Verification
```bash
# Check Kafka messages
docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic consume wifi7.telemetry.v0_1 -o oldest -n 10

# Check database
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "SELECT * FROM metrics ORDER BY ts DESC LIMIT 5;"

# Check tables exist
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "\dt"
```

---

## Current Workflow (Manual)

```bash
# 1. Start lab (if not running)
make up

# 2. Run experiment
EXP_ID=20251223-1500-wifi-example-01
make ns3-run-example EXP_ID=$EXP_ID

# 3. Publish to Kafka
make exporter-run EXP_ID=$EXP_ID

# 4. Ingest to DB (run in separate terminal)
make harmonizer-run

# 5. View in Grafana
# Open http://localhost:3000
```

---

## Directory Structure

```
ndt-wifi7-mlo-security/
├── clab/
│   ├── topo.yml                    # Containerlab topology
│   └── configs/
│       ├── grafana/
│       │   ├── provisioning/       # Datasources, dashboard providers
│       │   └── dashboards/         # Dashboard JSON files
│       └── db/
│           └── init.sql            # Database initialization
├── sim/ns3/
│   ├── scenario/                   # Run scripts
│   ├── scratch/                    # ns-3 C++ code (if any)
│   └── artifacts/                  # Experiment outputs (gitignored)
│       └── <EXP_ID>/
│           ├── meta.txt
│           ├── telemetry.jsonl
│           ├── ns3_stdout.log
│           └── ns3_stderr.log
├── telemetry/
│   ├── exporters/
│   │   └── ns3_file_exporter/      # File → Kafka exporter
│   ├── contracts/                  # Schema definitions
│   └── harmonizer/                 # Kafka → DB harmonizer
├── docker/
│   └── ns3/
│       └── Dockerfile              # ns-3.46.1 image
├── docs/
│   └── adr/                        # Architecture decisions
├── .claude/                        # Claude Code configuration
│   ├── CLAUDE.md
│   ├── agents/
│   ├── commands/
│   └── docs/context/
├── .exporter_state/                # Exporter offset tracking (gitignored)
└── Makefile
```

---

## Telemetry Contract (v0.1)

```json
{
  "experiment_id": "20251223-1200-wifi-example-42",
  "ts": "2025-12-23T12:00:00.000Z",
  "source": "ns3",
  "schema_version": "v0.1",
  "entity_id": "sta1",
  "metric": "throughput_mbps",
  "value": 117.5,
  "unit": "Mbps"
}
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

---

## Known Issues and Solutions

### Issue: Exporter shows resume_offset but publishes nothing
**Solution:** Delete `.exporter_state/exporter_state.json` and re-run

### Issue: Harmonizer runs but DB doesn't update
**Solution:** Use new consumer group with `earliest` offset:
```bash
docker run --rm --network clab-mgmt \
  -e KAFKA_GROUP=harmonizer-replay-$(date +%s) \
  -e AUTO_OFFSET_RESET=earliest \
  ndt/harmonizer:local
```

### Issue: Grafana shows no data
**Check in order:**
1. Messages in Kafka? `rpk topic consume ...`
2. Rows in DB? `SELECT * FROM metrics ...`
3. Time range correct? Adjust Grafana time picker

### Issue: Permission denied on artifacts
**Solution:** Run containers with `--user "$(id -u):$(id -g)"`

---

## Environment Variables

### Exporter
| Variable | Default | Description |
|----------|---------|-------------|
| `TELEMETRY_FILE` | Required | Path to telemetry.jsonl |
| `KAFKA_BROKERS` | `bus-redpanda:9092` | Kafka broker |
| `KAFKA_TOPIC` | `wifi7.telemetry.v0_1` | Target topic |

### Harmonizer
| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BROKERS` | `bus-redpanda:9092` | Kafka broker |
| `KAFKA_TOPIC` | `wifi7.telemetry.v0_1` | Source topic |
| `KAFKA_GROUP` | `harmonizer-udm-v0` | Consumer group |
| `AUTO_OFFSET_RESET` | `latest` | Where to start |
| `PG_HOST` | `udr-db` | Database host |
| `PG_DB` | `udr` | Database name |
| `PG_USER` | `udr` | Database user |
| `PG_PASS` | `udr_pass` | Database password |

---

## What's NOT Committed (gitignore)

```
# Runtime artifacts
sim/ns3/artifacts/
.exporter_state/

# Containerlab runtime
clab/clab-ndt-wifi7-mlo-security/
*.tls/

# Python
__pycache__/
*.pyc
.venv/
```

---

## Next Steps (WP7+)

### WP7: One-Command Pipeline
- Run harmonizer as long-running service
- Create `make pipeline-up` / `make pipeline-down`
- Create `make run-exp EXP_ID=... SCENARIO=...`

### WP8: Multi-Scenario Support
- Scenario registry in `sim/ns3/scenarios/`
- Add `scenario` field to telemetry
- Grafana scenario selector

### WP9+: Security and AI
- Feature store
- Baseline detector
- Policy engine
- GNN digital twin

---

## Related Documents

- `BLUEPRINT.md` - Full implementation blueprint
- `ALL-ADRS.md` - All architecture decisions
- `WP1-LOCAL-DEV-SETUP.md` - WP1 details
- `WP2-CONTAINERLAB-SKELETON.md` - WP2 details
- `WP3-NS3-INTEGRATION.md` - WP3 details
- `WP4-TELEMETRY-EXPORTER.md` - WP4 details
- `WP5-HARMONIZER.md` - WP5 details
- `WP6-GRAFANA-DASHBOARDS.md` - WP6 details
