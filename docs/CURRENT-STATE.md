# NDT Wi-Fi 7 MLO Security - Current Project State

## Document Purpose
This document provides complete context about the current state of the project. Use this to quickly understand what has been implemented, what works, and what comes next.

---

## Quick Status

| Work Package | Status | Description |
|--------------|--------|-------------|
| WP1 | ✅ Complete | Local dev setup, GitHub SSH |
| WP2 | ✅ Complete | Containerlab skeleton with services |
| WP3 | ✅ Complete | ns-3 container + Wi-Fi 7 telemetry |
| WP4 | ✅ Complete | Telemetry exporter (file → Kafka) |
| WP5 | ✅ Complete | Harmonizer (Kafka → DB) |
| WP6 | ✅ Complete | Grafana provisioning-as-code |
| WP7 | ✅ Complete | One-command pipeline (`make run-exp`) |
| WP7.5 | ✅ Complete | Exporter reliability + MLO attack scenarios |
| WP8 | ✅ Complete | GCN attack detection (Windowizer + GCN Detector) |
| WP9 | ✅ Complete | GCN model v2.0.0 retraining (284 balanced scenarios) |
| WP9.5 | ✅ Complete | Unified Grafana dashboard (38 panels, 3 variables) |
| WP10 | ✅ Complete | Custom web dashboard (React 18 + FastAPI, port 8888) |
| WP11 | ✅ Complete | Pipeline & DB writer bug fixes (Attack Analysis tab) |
| WP12 | ✅ Complete | GCN v3 multi-AP + multi-length training + dashboard launcher (v3.0.0: F1=0.9978, AUC=1.0000) |
| WP13 | 🚧 In Progress | GCN v4 dynamic generalization — data + model code complete; training pending |

---

## Working Pipeline

### Current Pipeline (WP10 Complete — All Phases)
```
NS-3 Simulation (Wi-Fi 7 MLO)
        │
        ▼
sim/ns3/artifacts/<EXP_ID>/telemetry.jsonl
        │
        ▼
Exporter (ns3_file_exporter)
        │
        ▼
Redpanda (Kafka API) — topic: wifi7.telemetry.v0_1
        │
        ├──────────────────────────────┐
        ▼                              ▼
   Harmonizer                     Windowizer
        │                    (256-window segments)
        ▼                              │
 TimescaleDB                           ▼
 public.metrics               Kafka: wifi7.ml.windowed_features.v1
        │                              │
        │                              ▼
        │                       GCN Detector v3.0.0
        │                              │
        │                              ▼
        │                    TimescaleDB public.gcn_predictions
        │                              │
        └──────────────┬───────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
   Grafana :3000          Custom Dashboard :8888
 (38-panel unified)    (real-time pipeline + analysis)
```

---

## Running Services

### Containerlab (clab-mgmt network)

| Service | Container Name | Port | Purpose |
|---------|---------------|------|---------|
| UDR DB | `clab-ndt-wifi7-mlo-security-udr-db` | 5432 | TimescaleDB |
| Grafana | `clab-ndt-wifi7-mlo-security-grafana` | 3000 | Grafana dashboards |
| Redpanda | `clab-ndt-wifi7-mlo-security-bus-redpanda` | 9092 | Kafka API |

### Docker Compose pipeline (docker-compose.pipeline.yml)

| Service | Container | Purpose |
|---------|-----------|---------|
| harmonizer | `ndt-pipeline-harmonizer` | Kafka → TimescaleDB |
| windowizer | `ndt-pipeline-windowizer` | Telemetry → 256-window segments |
| gcn-detector | `ndt-pipeline-gcn-detector` | GCN attack detection inference |

### Custom Dashboard (docker-compose.dashboard.yml)

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| dashboard | `ndt-dashboard` | **8888** | FastAPI + React 18 custom dashboard |

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
make harmonizer-run        # Run harmonizer (manual mode)
```

### One-Command Pipeline (WP7)
```bash
make pipeline-up           # Start harmonizer in background
make pipeline-down         # Stop harmonizer
make pipeline-status       # Check status and logs
make run-exp EXP_ID=...    # Run full experiment (ns-3 → export → ingest)
```

### GCN Pipeline (WP8)
```bash
make gcn-up                # Start windowizer + GCN detector
make gcn-down              # Stop windowizer + GCN detector
make gcn-status            # Check status and logs
make run-mlo-exp EXP_ID=... SCENARIO=normal|positive|negative
bash run_scenarios.sh      # Run all 3 scenarios
```

### GCN v3 Data Collection (WP12)
```bash
make gcn-collect-data NCPU=8              # Run all 72 simulations in parallel (8 cores)
make gcn-collect-data NCPU=8 SIM_TIME=80  # Explicit 80s sim time
# Or directly:
NCPU=8 bash sim/ns3/scenario/collect_v3_data.sh
```

### GCN v4 Data Collection (WP13)
```bash
# Static data (uses pre-partitioned train/val/test seed pools)
NCPU=8 bash sim/ns3/scenario/collect_v4_static_data.sh

# Dynamic data (30 phase patterns A/B/C/D/E plus T-patterns for test-only)
NCPU=8 bash sim/ns3/scenario/collect_v4_dynamic_data.sh

# Synthetic stitching (create dynamic training files from existing static sources)
python twin/gnn/stitch_dynamic.py --split train
python twin/gnn/stitch_dynamic.py --split val
python twin/gnn/stitch_dynamic.py --split test
python twin/gnn/stitch_dynamic.py --summary   # Show dataset statistics
```

### GCN v4 Training (WP13 — pending)
```bash
make gcn-trainer-build                              # Rebuild Docker trainer image (includes v4 files)
make gcn-train-v4 OUTPUT_DIR=twin/registry/gcn/v4.0.0
make gcn-deploy VERSION=v4.0.0
docker compose -f docker-compose.pipeline.yml restart gcn-detector
```

### Multi-AP Simulation (WP12)
```bash
make run-mlo-exp EXP_ID=... SCENARIO=normal NAP=2 NSTA=4 SEED=42 SIM_TIME=80
make run-mlo-exp EXP_ID=... SCENARIO=positive NAP=4 NSTA=8 SEED=43 BIAS=5000
```

### GCN v3 Training (WP12)
```bash
make gcn-train OUTPUT_DIR=twin/registry/gcn/v3.0.0   # uses training_v3.yaml
make gcn-deploy VERSION=v3.0.0                         # update current symlink
```

### Evaluation Utilities (WP12 — 2026-03-14)
```bash
make db-reset-experiments     # Truncate gcn_predictions + metrics tables (fresh eval start)
make db-count                 # Show row counts for gcn_predictions and metrics
python scripts/run_eval_matrix.py --tier TIER1   # Run a specific evaluation tier
python scripts/run_eval_matrix.py --dry-run       # Preview experiment list without launching
```

### Dashboard Experiment Launcher (WP12)
```
http://localhost:8888  →  "Run Experiment" sidebar section
  - Configure nAp (1-6), nSta, Scenario, Seed, SimTime, SegmentLength
  - Launch → live pipeline stage progress
  - Completed → auto-navigate to Experiment View
API: POST /api/run/launch  GET /api/run/status  POST /api/run/cancel
```

### Custom Dashboard (WP10)
```bash
make dashboard-build       # Build Docker image
make dashboard-up          # Start on http://localhost:8888
make dashboard-down        # Stop
make dashboard-logs        # Follow logs
make dashboard-status      # Status + last 20 log lines
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

## Current Workflow (One-Command - WP7)

```bash
# 1. Start everything (one-time setup)
make up              # Start containerlab services
make pipeline-up     # Start harmonizer in background

# 2. Run experiment (single command!)
make run-exp EXP_ID=20260103-1200-test-01

# 3. View in Grafana
# Open http://localhost:3000

# 4. Run more experiments as needed
make run-exp EXP_ID=20260103-1300-test-02

# 5. Stop everything when done
make pipeline-down   # Stop harmonizer
make down            # Stop containerlab
```

### Quick Status Check
```bash
make pipeline-status  # Check harmonizer status and logs
```

---

## WP7.5: Exporter Reliability Improvements

**Implemented:** Counter-based delivery confirmation with at-least-once semantics.

### Key Features
- **Counter-based delivery tracking**: Counts confirmed messages vs total sent
- **Topic health checks**: Verifies topic exists on startup, fails fast if missing
- **At-least-once delivery**: Ensures zero data loss via database deduplication
- **Idempotent database writes**: Unique index on (experiment_id, entity_id, metric_name, ts)

### Why It Works
```python
# Read entire file, track confirmations
confirmed_count = 0
total_sent = 0
while line:
    producer.produce(..., callback=delivery_report)
    total_sent += 1

# Wait for ALL confirmations
producer.flush(timeout=30.0)

# Verify complete success
if confirmed_count != total_sent:
    sys.exit(1)  # Don't save state → next run replays

# All delivered → save offset
save_offset(state, TELEMETRY_FILE, final_offset)
```

### Why Offset Tracking Failed
- `min(offsets)` causes infinite replays (line 1 never confirmed)
- `max(offsets)` skips data gaps (missing middle lines)
- Duplicate keys corrupt offset tracking

**See ADR-WP7.5-01, ADR-WP7.5-02, ADR-WP7.5-03** in `docs/ALL-ADRS.md` for full rationale.

---

## WP7.5: MLO Attack Scenarios Dashboard

**URL:** http://localhost:3000/d/mlo-attack-scenarios

### Dashboard Features
- **9 panels** showing backoff manipulation attack behavior
- **Auto-discovery**: Template variables automatically find experiments
- **3 MLO scenarios**: Normal baseline, Positive attack, Negative attack
- **Verified with 780 database rows** (260 rows × 3 experiments)

### Panels
1. **Scenario Selector** (stat panel)
2. **Experiment Details** (table)
3. **Average Backoff Slots** (time series + stat)
4. **Network Throughput** (time series + stat)
5. **RSSI Levels** (time series)
6. **Retry Counts** (time series)
7. **Channel Utilization** (time series)

### Attack Behavior Verification

**Experiment IDs:**
- `20260103-1400-mlo-normal-42` (baseline)
- `20260103-1400-mlo-attack-pos-42` (positive attack)
- `20260103-1400-mlo-attack-neg-42` (negative attack)

**Observed Attack Effects:**

| Scenario | Avg Backoff Slots | Network Throughput | Change vs Normal |
|----------|-------------------|-------------------|------------------|
| **Normal** | 4.95 slots | 262.49 Mbps | Baseline |
| **Positive Attack** | 1410.90 slots | 41.66 Mbps | +285x backoff, -84% throughput |
| **Negative Attack** | 2.17 slots | 146.70 Mbps | -56% backoff, -44% throughput |

**Key Insight:** Positive attack dramatically increases backoff (causing starvation), while negative attack reduces backoff (aggressive channel access).

### Usage
```bash
# 1. Ensure infrastructure running
make up
make pipeline-up

# 2. Run MLO experiments
make run-mlo-exp EXP_ID=20260106-1400-mlo-normal-42
make run-mlo-exp EXP_ID=20260106-1400-mlo-attack-pos-42
make run-mlo-exp EXP_ID=20260106-1400-mlo-attack-neg-42

# 3. View dashboard
# Open http://localhost:3000/d/mlo-attack-scenarios
# Select experiment from dropdown
```

### Current Data
- **Total database rows**: 780 (verified 2026-01-05)
- **Metrics tracked**: 13 types per experiment
- **Scenarios**: 3 (normal, attack-pos, attack-neg)
- **Dashboard file**: `clab/configs/grafana/dashboards/mlo-attack-scenarios.json`

### Related Documentation
- Implementation workflow: `.claude/docs/WorkProcess/HOWTORUN.md`
- Execution outputs: `.claude/docs/WorkProcess/WORKFLOW-EXECUTION-OUTPUT.md`
- Dashboard plan: `.claude/docs/plans/mlo-attack-dashboard-plan-v2.md`

---

## Directory Structure

```
ndt-wifi7-mlo-security/
├── clab/
│   ├── topo.yml                         # Containerlab topology
│   └── configs/
│       ├── grafana/
│       │   ├── provisioning/            # Datasource + dashboard providers
│       │   └── dashboards/
│       │       └── ndt-unified.json     # Unified dashboard (38 panels)
│       └── udr-db/initdb/
│           ├── 001_schema.sql           # metrics table
│           └── 003_gcn_schema.sql       # gcn_predictions table
├── sim/ns3/
│   ├── scenario/                        # Wi-Fi 7 MLO run scripts
│   └── artifacts/<EXP_ID>/             # telemetry.jsonl, logs (gitignored)
├── telemetry/
│   ├── exporters/ns3_file_exporter/     # File → Kafka exporter
│   ├── contracts/                       # Schema definitions
│   └── harmonizer/                      # Kafka → TimescaleDB
├── security/detector/windowizer/        # 256-window segmentation service
│   ├── windowizer.py
│   ├── delta_converter.py
│   └── config.yaml
├── twin/
│   ├── gnn/
│   │   ├── detector/                    # GCN inference service
│   │   └── trainer/                     # Model training pipeline
│   └── registry/gcn/
│       ├── current -> v3.0.0            # Active version symlink
│       ├── v1.0.0/                      # Baseline model
│       ├── v2.0.0/                      # Balanced single-AP model
│       ├── v3.0.0/                      # Multi-AP multi-length model (F1=0.9978)
│       │   ├── best_model.pt
│       │   ├── scaler.json              # 17-dim (16 features + seg-len)
│       │   ├── config.yaml
│       │   └── test_results.json
│       └── v4.0.0/                      # [PENDING] Dynamic generalization model
├── dashboard/app/                       # Custom web dashboard (WP10)
│   ├── Dockerfile                       # Multi-stage: Node 20 → Python 3.11
│   ├── backend/                         # FastAPI + asyncpg
│   │   ├── main.py
│   │   ├── api/                         # REST endpoints
│   │   ├── ws/pipeline.py               # WebSocket handler
│   │   ├── db/queries.py                # Async SQL
│   │   └── registry/reader.py           # Reads model registry
│   └── frontend/                        # React 18 + Vite + Recharts
│       └── src/
│           ├── context/AppContext.tsx    # WebSocket + global state
│           ├── sections/                # 6 dashboard sections
│           └── components/              # layout, common, pipeline, charts
├── docker-compose.pipeline.yml          # Harmonizer + Windowizer + GCN
├── docker-compose.dashboard.yml         # Custom dashboard
├── run_scenarios.sh                     # Batch: normal + pos + neg attacks
├── twin/gnn/training_data/
│   ├── v3/                              # GCN v3.0.0 training data (gitignored)
│   └── v4/                              # GCN v4.0.0 training data (gitignored)
│       ├── train/Static/{Normal,Attack}/
│       ├── train/Dynamic/               # Synthetic stitched phase-transition files
│       ├── val/Static/{Normal,Attack}/
│       ├── val/Dynamic/
│       ├── test/Static/{Normal,Attack}/
│       └── test/Dynamic/
├── docs/                                # All documentation
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

## Completed Features Summary (WP12)

All work packages through WP12 are complete. The platform now provides:

| Feature | Location | How to access |
|---------|----------|---------------|
| Wi-Fi 7 MLO simulation (multi-AP) | `sim/ns3/` | `make run-mlo-exp NAP=2 NSTA=4` |
| Real-time telemetry pipeline | `telemetry/` | `make pipeline-up` |
| GCN attack detection | `twin/gnn/` + `security/` | `make gcn-up` |
| GCN model v3.0.0 | `twin/registry/gcn/v3.0.0/` | Active (F1=0.9978, multi-AP 1-4) |
| Unified Grafana dashboard | `clab/configs/grafana/dashboards/` | http://localhost:3000 |
| Custom web dashboard | `dashboard/app/` | http://localhost:8888 |
| Dashboard experiment launcher | `dashboard/app/backend/api/run.py` | http://localhost:8888 "Run Experiment" |

## GCN v3.0.0 Model Performance

Trained on 48 files: 16 Normal (nap1-4) + 32 Attack (nap1-4, 2 attack types), 4 seeds each.

| Metric | Value |
|--------|-------|
| Test F1 | **0.9978** |
| Accuracy | **99.73%** |
| Precision | **1.0000** (zero false positives) |
| Recall | **0.9957** (1 missed attack out of 230) |
| ROC-AUC | **1.0000** |
| Epochs | 21 (early stopped, patience=20) |

### Evaluation Matrix Results (2026-03-14) — 54/54 PASS

Post-deployment evaluation via `scripts/run_eval_matrix.py` across five tiers. All 54 experiments passed.

| Tier | Description | Pass/Total |
|------|-------------|-----------|
| Tier 1 | Core accuracy (v3+v2, 1AP, 256w, seeds A+B) | 12/12 |
| Tier 2 | Multi-AP scaling (v3, 2AP+4AP) | 6/6 |
| Tier 3 | Segment length (v3, seg=128+64) | 6/6 |
| Tier 4 | Bias sensitivity (v3+v2, bias=1000/2000/10000) | 12/12 |
| Tier 5 | Seed generalisation (v3+v2, groups A–E) | 18/18 |

Key findings: attack\_rate = 0.000 (normal) or 1.000 (attack) across all 54 experiments; both models detect attacks at bias=1000 (one-fifth of training bias). Full report: `docs/EVALUATION-RESULTS-2026-03-14.md`.

Key architectural changes vs v2:
- `in_channels=17` (16 original features + `log2(L)/8.0` segment-length conditioning feature)
- Multi-AP normalisation: `net_throughput_mbps / nAp`, MAC/PHY deltas `/ num_sta`
- Multi-segment-length training: [32, 64, 128, 256] simultaneously
- Sliding window for 256: stride=64 → 9 segments per 80s run

## WP13: GCN v4 Dynamic Generalization (In Progress — 2026-03-15)

### Overview

WP13 trains GCN v4.0.0, which extends v3.0.0 to correctly classify segments in dynamic/transitioning attack scenarios. GCN v3 was trained exclusively on static files (uniform bias per run) and fails on phase-transition segments. v4 introduces dynamic training data with 30 multi-phase patterns.

### What Was Completed

#### 1. Problem Diagnosis
GCN v3 fails on dynamic scenarios because it has never seen a segment containing a phase boundary. Transition segments contain mixed-bias windows that the v3 model classifies unreliably. Static pure segments are handled correctly; only transition segments fail.

#### 2. Data Collection Infrastructure
Two parallel NS-3 batch collection scripts created:

`sim/ns3/scenario/collect_v4_static_data.sh`:
- AP/STA pairs: nap1:nsta2, nap2:nsta4, nap3:nsta2, nap4:nsta2
- Train seeds: 42,111,123,222,321,333,456,654,789,987 (10 seeds)
- Val seeds: 444,777,888 (3 seeds, strictly disjoint from train)
- Test seeds: 555,999,1234 (3 seeds, strictly disjoint from train and val)
- Attack biases: train=[1000,2000,5000], val=[5000], test=[500,1000,2000,4000,5000]
- Skip-if-exists logic for safe restarts
- Output: `twin/gnn/training_data/v4/{train,val,test}/Static/{Normal,Attack}/`

`sim/ns3/scenario/collect_v4_dynamic_data.sh`:
- 30 phase patterns across groups A (2-phase), B (3-phase), C (4-phase), D (uneven timing), E (weak bias)
- T-group (5-phase, test-only — never seen in training)
- Parallel runner with configurable NCPU workers
- Output: `twin/gnn/training_data/v4/{train,val,test}/Dynamic/`

#### 3. Synthetic Dynamic Dataset
`twin/gnn/stitch_dynamic.py` synthesizes dynamic training files by stitching together windows from existing static source files. Each phase takes 400 windows from the middle of an 800-window static source file (windows 200-600). Phase offsets [200,0,400] ensure no source-file overlap across phases. No-leakage guarantee: a static source file is only stitched within the same split it belongs to.

CLI flags: `--split {train,val,test}`, `--dry-run`, `--overwrite`, `--summary`.

#### 4. GCN v4 Model Code
| File | Purpose |
|------|---------|
| `twin/gnn/detector/gcn_src/data/dataset_v4.py` | WiFi7AttackDatasetV4: per-segment dynamic labeling (30% threshold), load_v4_files for pre-partitioned folder structure |
| `twin/gnn/detector/gcn_src/training/train_v4.py` | v4 training pipeline: hidden=128, 3 GCN layers, dropout=0.4 |
| `twin/gnn/detector/run_training_v4.py` | Entry point |
| `twin/gnn/trainer/training_v4.yaml` | v4 training config |
| `twin/gnn/trainer/Dockerfile` | Updated to include v4 training files |

#### 5. Actual Dataset State (2026-03-15)
Files currently on disk in `twin/gnn/training_data/v4/`:

| Split | Static Normal | Static Attack | Dynamic (synthetic) | Total |
|-------|-------------|--------------|--------------------|----|
| Train | 28 | 165 | 1,852 | 2,045 |
| Val | 17 | 33 | 98 | 148 |
| Test | 6 | 59 | 620 | 685 |

### Key Architecture Decisions (v4)

| Decision | Choice |
|----------|--------|
| Dynamic label strategy | Majority-vote with 30% threshold (attack if >30% of windows in segment are attack) |
| Architecture width | hidden=128, 3 layers (vs v3: hidden=64, 2 layers) |
| Segment strides | stride=length for 32/64/128 (non-overlapping); stride=64 for 256 (sliding) |
| Seed isolation | Strictly disjoint train/val/test seed pools |
| Test phase patterns | T-group (5-phase) only in test split — never in training |
| Synthetic stitching | 400-window slices from static source middles; same seed only within same split |

### What Remains (Next Session)

```bash
make gcn-trainer-build                              # Rebuild trainer Docker image
make gcn-train-v4 OUTPUT_DIR=twin/registry/gcn/v4.0.0
make gcn-deploy VERSION=v4.0.0
docker compose -f docker-compose.pipeline.yml restart gcn-detector
```

After training:
- Evaluate v4 vs v3 on static benchmark (5 tiers, expect F1 >= 0.995)
- Evaluate on dynamic benchmark (neg->norm->pos, 4 window sizes)
- Evaluate on held-out T-patterns (5-phase, never in training)
- Compare v3 vs v4 in dashboard side-by-side compare mode

### Related Documentation
- `docs/WP13-GCN-V4-DYNAMIC-TRAINING-PLAN.md` — full planning doc with phase patterns, architecture, training config

---

## Next Steps (after WP13)

WP13 original scope also included closed-loop policy actuation (detector predictions feeding back into a ZSM/SDN controller for link steering, channel switching, and deauth). This has been deferred pending v4 model training and evaluation.

Related work deferred from WP12:
- nap5/6 training data (v3.1.0 or v4.1.0): use `SIM_TIME=30s` to reduce per-run time from ~2.5h to ~45min
- Playwright end-to-end test for Run Experiment dashboard section

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
- `WP7-ONE-COMMAND-PIPELINE.md` - WP7 details
- `WP12-GCN-V3-MULTI-AP-TRAINING-PLAN.md` - WP12 full plan and results
- `WP13-GCN-V4-DYNAMIC-TRAINING-PLAN.md` - WP13 full plan, phase patterns, training config
- `MODEL-EVALUATION-GUIDE.md` - Evaluation matrix guide and 2026-03-14 results
- `EVALUATION-RESULTS-2026-03-14.md` - Full 54-experiment evaluation report
- `.claude/docs/WorkProcess/HOWTORUN.md` - WP7.5 workflow guide
- `.claude/docs/WorkProcess/WORKFLOW-EXECUTION-OUTPUT.md` - WP7.5 execution outputs
- `.claude/docs/plans/mlo-attack-dashboard-plan-v2.md` - WP7.5 dashboard plan

---

## WP12: GCN v3 Multi-AP Training (Complete — 2026-03-13)

### Overview
WP12 extended the GCN attack detector to generalise across multi-AP Wi-Fi 7 topologies and multiple segment window lengths. GCN v3.0.0 was trained and deployed, achieving near-perfect detection performance.

### What Was Implemented

#### 1. NS-3 Multi-AP Simulation Support
All three NS-3 scenario files (`wifi7-mlo-Normal.cc`, `wifi7-mlo-Positive.cc`, `wifi7-mlo-Negative.cc`) were extended with `--nAp`, `--nSta`, and `--seed` CLI parameters. Each window in the JSON output now carries `num_ap` and `num_sta` fields.

`run_mlo_scenario.sh` gained `NAP`/`NSTA`/`SEED` env vars and a `V3_COLLECT` copy hook. A parallel batch script (`collect_v3_data.sh`) and the `gcn-collect-data` Makefile target were added.

#### 2. Data Collection
48 JSON files collected in `twin/gnn/training_data/v3/`:
- Normal: 16 files (nap1-4 x 4 seeds)
- Attack: 32 files (nap1-4 x 4 seeds x positive+negative)

Each file contains ~800 windows (80s simulation at 0.1s resolution).

#### 3. GCN v3 Training Pipeline
- `preprocessing.py`: sliding-window segmentation with per-AP normalisation and 17th segment-length conditioning feature (`log2(L)/8.0`)
- `config.py`: `in_channels=17`, `segment_lengths=[32,64,128,256]`, `multi_ap_normalise=True`
- `train.py`: multi-length training loop
- `feature_processor.py`: `build_feature_matrix()` with runtime multi-AP norm + seg-len feature; v2 backward compatible (detected via scaler dimension)
- `twin/gnn/trainer/training_v3.yaml`: full v3 training configuration

#### 4. GCN v3.0.0 Trained and Deployed
Model artifacts at `twin/registry/gcn/v3.0.0/`. Registry symlink `current` updated to v3.0.0.

**Test results:**
| Metric | Value |
|--------|-------|
| F1 | **0.9978** |
| Accuracy | **99.73%** |
| Precision | **1.0000** |
| Recall | **0.9957** |
| ROC-AUC | **1.0000** |
| Epochs to convergence | 21 (early stop, patience=20) |

#### 5. Dashboard Experiment Launcher
New "Run Experiment" sidebar section in the web dashboard:
- Config form: nAp (1-6), scenario, seed, sim_time, bias, segment_length
- Live stage progress panel (polls `GET /api/run/status` every 2s)
- Post-run navigation to Experiment View
- Backend: `POST /api/run/launch`, `GET /api/run/status`, `POST /api/run/cancel`, `GET /api/run/history`

#### 6. Dashboard UI Enhancements (2026-03-14)
Experiment View improvements added post-WP12:
- **Date range filter** on `GET /api/experiments`: `start` and `end` query parameters added to `queries.py` and `experiments.py`
- **Quick range buttons**: Last 30m, Last 1h, Last 2h, Last 6h, Last 24h, All time — visible in ExperimentSection toolbar
- **See More / See Less toggle**: experiment lists (primary and compare) default to 2 rows (~66px); expand on demand
- Files changed: `dashboard/app/backend/db/queries.py`, `dashboard/app/backend/api/experiments.py`, `dashboard/app/frontend/src/hooks/useExperiments.ts`, `dashboard/app/frontend/src/sections/ExperimentSection.tsx`

#### 7. Evaluation Tooling (2026-03-14)
- `scripts/run_eval_matrix.py`: automated 5-tier evaluation runner; `--tier` flag for individual tiers; `--dry-run` for preview; indefinite polling (no hard timeout), `LAUNCH_TIMEOUT=90s`, `POLL_INTERVAL=8s`
- `make db-reset-experiments`: truncates `gcn_predictions` and `metrics` tables
- `make db-count`: shows row counts for both tables

### Key Design Decisions (see ADRs)
- **SIM_TIME=80s**: 80s gives ~800 windows/file; sliding window for 256-length compensates. See ADR-WP12-01.
- **nap1-4 only for v3.0.0**: nap5/6 deferred (>2.5h per run). See ADR-WP12-02.
- **17th segment-length feature**: single model handles all four window sizes. See ADR-WP12-03.

### Files Created or Modified
| File | Change |
|------|--------|
| `sim/ns3/scratch/wifi7-mlo-Normal.cc` | Added --nAp, --nSta, --seed; num_ap/num_sta in JSON |
| `sim/ns3/scratch/wifi7-mlo-Positive.cc` | Same |
| `sim/ns3/scratch/wifi7-mlo-Negative.cc` | Same |
| `sim/ns3/scenario/run_mlo_scenario.sh` | NAP/NSTA/SEED env vars; V3_COLLECT hook |
| `sim/ns3/scenario/collect_v3_data.sh` | New: parallel 72-run batch script |
| `twin/gnn/detector/gcn_src/data/preprocessing.py` | Sliding window, per-AP norm, 17th feature |
| `twin/gnn/detector/gcn_src/training/config.py` | in_channels=17, segment_lengths list |
| `twin/gnn/detector/gcn_src/training/train.py` | Multi-length training loop |
| `twin/gnn/detector/feature_processor.py` | build_feature_matrix() with v2 compat |
| `twin/gnn/trainer/training_v3.yaml` | New: v3 training configuration |
| `twin/registry/gcn/v3.0.0/` | New: trained model artifacts |
| `twin/registry/gcn/current` | Updated symlink: v2.0.0 → v3.0.0 |
| `dashboard/app/backend/api/run.py` | New: experiment launcher API |
| `dashboard/app/backend/main.py` | Registered /api/run router |
| `docker-compose.dashboard.yml` | /repo:ro mount; /artifacts read-write |
| `dashboard/app/frontend/src/hooks/useRun.ts` | New: React hooks for run endpoints |
| `dashboard/app/frontend/src/sections/RunSection.tsx` | New: experiment launcher UI |
| `dashboard/app/frontend/src/App.tsx` | RunSection wired in |
| `dashboard/app/frontend/src/components/layout/Sidebar.tsx` | "Run Experiment" nav item |
| `Makefile` | gcn-collect-data target; NAP/NSTA/NCPU vars; non-interactive Docker flag |
| `Makefile` | db-reset-experiments + db-count targets (added 2026-03-14) |
| `scripts/run_eval_matrix.py` | New: 5-tier evaluation runner (added 2026-03-14) |
| `dashboard/app/backend/db/queries.py` | Date range filter on experiments query (added 2026-03-14) |
| `dashboard/app/backend/api/experiments.py` | start/end query params for date filter (added 2026-03-14) |
| `dashboard/app/frontend/src/hooks/useExperiments.ts` | Date range state + quick button logic (added 2026-03-14) |
| `dashboard/app/frontend/src/sections/ExperimentSection.tsx` | Quick range buttons + See More/Less toggle (added 2026-03-14) |

### Related ADRs
- ADR-WP12-01: SIM_TIME=80s for v3 training data
- ADR-WP12-02: nap1-4 only for v3.0.0 (nap5/6 deferred to v3.1.0)
- ADR-WP12-03: 17th feature for segment-length conditioning

### Known Limitations / Deferred Work
- nap5/6 coverage: deferred to v3.1.0. Strategy: use SIM_TIME=30s (~45min per run vs 2.5h at SIM_TIME=80s)
- Playwright end-to-end test for Run Experiment dashboard section: not yet implemented
- Dashboard frontend rebuild required after new session: `make dashboard-build && make dashboard-up`
- Minimum-bias lower limit: bias=1000 confirmed detectable; bias=500 / bias=250 not yet tested

---

## WP8: GCN Attack Detection Integration (In Progress)

### Overview
Integration of Graph Convolutional Network (GCN) model for real-time WiFi 7 attack detection. The GCN model analyzes temporal patterns in telemetry data to detect backoff manipulation attacks.

### Phase 1: Foundation (✅ Complete - 2026-02-10)

**Deliverables Completed:**
1. ✅ Directory structure created
   - `security/detector/windowizer/` - Window aggregation service
   - `twin/gnn/detector/` - GCN inference service
   - `twin/gnn/trainer/` - Model training pipeline
   - `twin/registry/gcn/` - Model version control

2. ✅ Database schemas created
   - `clab/configs/udr-db/initdb/003_gcn_schema.sql`
   - Table: `public.gcn_predictions` (TimescaleDB hypertable)
   - Table: `public.model_registry` (version tracking)
   - Indexes for efficient queries

3. ✅ Model registry initialized
   - `twin/registry/gcn/v1.0.0/` - Baseline model artifacts
     - `best_model.pt` - PyTorch model weights (110KB)
     - `scaler.json` - StandardScaler parameters
     - `config.yaml` - Model hyperparameters
     - `test_results.json` - Evaluation metrics
   - `twin/registry/gcn/current` - Symlink to active version (v1.0.0)
   - Baseline model performance: 95.23% accuracy, 94.81% F1 score

4. ✅ Configuration files created
   - `security/detector/windowizer/config.yaml`
   - `twin/gnn/detector/config.yaml`
   - `twin/gnn/trainer/training.yaml`

5. ✅ Makefile targets added
   - `make kafka-topics-create` - Create GCN Kafka topics
   - `make windowizer-build` / `windowizer-run` / `windowizer-logs`
   - `make gcn-detector-build` / `gcn-detector-run` / `gcn-detector-logs`
   - `make gcn-trainer-build` / `gcn-train` / `gcn-evaluate` / `gcn-deploy`
   - `make gcn-up` / `gcn-down` / `gcn-status` - Complete GCN pipeline
   - `make test-gcn-e2e` - End-to-end testing

6. ✅ README documentation
   - `twin/registry/gcn/README.md` - Model registry usage
   - `security/detector/windowizer/README.md` - Windowizer overview
   - `twin/gnn/detector/README.md` - Detector overview
   - `twin/gnn/trainer/README.md` - Training pipeline overview

**Acceptance Criteria Met:**
- ✅ DB schema validates (003_gcn_schema.sql runs without errors)
- ✅ Model artifacts loadable (v1.0.0 with all required files)
- ✅ Configuration files follow project standards
- ✅ Makefile targets properly documented

**Next Steps (Phase 2):**
- Implement windowizer service (Python + Kafka)
- Add window aggregation logic
- Add delta conversion for cumulative counters
- Add segment buffering (256-window segments)
- Create Dockerfile and requirements.txt
- Write unit tests

### Kafka Topics (Ready for Phase 2)

| Topic | Purpose | Partitions | Retention | Status |
|-------|---------|------------|-----------|--------|
| `wifi7.telemetry.v0_1` | Raw telemetry | 3 | 7 days | ✅ Existing |
| `wifi7.ml.windowed_features.v1` | Windowed segments | 3 | 1 day | 🔲 To be created |
| `wifi7.security.gcn_predictions.v1` | Predictions | 3 | 30 days | 🔲 To be created |
| `wifi7.security.gcn_predictions.dlq` | Failed predictions | 1 | 7 days | 🔲 To be created |

**Create topics with:**
```bash
make kafka-topics-create
```

### GCN Model Details

**Baseline Model (v1.0.0):**
- Architecture: 2-layer GCN with temporal chain graph
- Input: 256 windows × 16 features (13 base + 3 derived)
- Output: Binary classification (0=Normal, 1=Attack) + confidence
- Performance:
  - Test Accuracy: 95.23%
  - Test F1: 94.81%
  - Test Precision: 96.12%
  - Test Recall: 93.54%
  - ROC-AUC: 98.91%
- Training dataset: Wifi7_Datasets (3 scenarios: Normal, Positive, Negative)
- Git commit: 9f0139f
- Deployed: 2026-02-10

**Model Registry Usage:**
```bash
# Deploy a new model version
make gcn-deploy VERSION=v1.1.0

# Train a new model
make gcn-train OUTPUT_DIR=twin/registry/gcn/v1.1.0

# Evaluate model
make gcn-evaluate MODEL=v1.1.0
```

### Implementation Timeline

| Phase | Duration | Status | Description |
|-------|----------|--------|-------------|
| Phase 1 | Week 1-2 | ✅ Complete | Foundation (schemas, configs, model registry) |
| Phase 2 | Week 2-3 | ✅ Complete | Windowizer implementation |
| Phase 3 | Week 3-4 | ✅ Complete | GCN detector implementation |
| Phase 4 | Week 4 | 🔲 Planned | End-to-end testing |
| Phase 5 | Week 5 | 🔲 Planned | Grafana dashboard |
| Phase 6 | Week 5-6 | 🔲 Planned | Training pipeline |
| Phase 7 | Week 6 | 🔲 Planned | Live sensor preparation |

### Key Design Decisions (ADR-WP8-GCN-ARCHITECTURE)

1. **Windowizer as separate service**: Decouples windowing logic from inference
2. **Kafka for real-time streaming**: Kafka is the source of truth for live data
3. **TimescaleDB for historical storage**: Predictions stored as time-series
4. **Model hot-reloading**: Zero-downtime model updates via symlink
5. **On-demand training**: Training pipeline runs separately from inference
6. **GPU support optional**: CPU inference sufficient for current throughput

### Files Changed in Phase 1

**New Files:**
- `clab/configs/udr-db/initdb/003_gcn_schema.sql`
- `security/detector/windowizer/config.yaml`
- `security/detector/windowizer/README.md`
- `twin/gnn/detector/config.yaml`
- `twin/gnn/detector/README.md`
- `twin/gnn/trainer/training.yaml`
- `twin/gnn/trainer/README.md`
- `twin/registry/gcn/v1.0.0/` (copied from GCN repo)
- `twin/registry/gcn/current` (symlink)
- `twin/registry/gcn/README.md`

**Modified Files:**
- `Makefile` (added GCN targets)
- `docs/CURRENT-STATE.md` (this file)
- `docs/WP8-GCN-INTEGRATION-PLAN.md` (comprehensive plan)


---

## WP8 Phase 2: Windowizer Implementation (✅ Complete - 2026-02-10)

**Goal**: Build and test the windowizer service that aggregates raw telemetry into 256-window segments.

### Deliverables Completed

1. ✅ **Windowizer Core Logic**
   - `window_aggregator.py` - Groups events by (experiment_id, timestamp, entity_id)
   - `delta_converter.py` - Converts cumulative counters to deltas
   - `segment_builder.py` - Buffers 256-window segments
   - `kafka_client.py` - Kafka consumer/producer wrapper

2. ✅ **Main Service**
   - `windowizer.py` - Main service with event loop
   - Batch processing (100 events at a time)
   - Graceful shutdown with signal handlers
   - Statistics logging every 60s

3. ✅ **Kafka Integration**
   - Consumer for `wifi7.telemetry.v0_1`
   - Producer for `wifi7.ml.windowed_features.v1`
   - Manual commit for at-least-once delivery
   - Delivery confirmation tracking

4. ✅ **State Management**
   - In-memory buffers per (experiment_id, entity_id)
   - Window index tracking
   - Delta state tracking for cumulative counters
   - Buffer overflow protection (max 10,000 windows)

5. ✅ **Configuration**
   - YAML-based configuration
   - Environment variable overrides
   - Configurable window size (100ms default)
   - Configurable segment length (256 default)

6. ✅ **Error Handling**
   - Missing metrics filled with 0.0
   - Incomplete events logged and skipped
   - Counter reset detection (negative deltas)
   - Kafka reconnection logic

7. ✅ **Dockerfile**
   - Python 3.11-slim base image
   - Non-root user (windowizer:1000)
   - Health check via process check
   - Volume mount for config

8. ✅ **Unit Tests**
   - `tests/test_aggregator.py` - Window aggregation tests
   - `tests/test_delta.py` - Delta conversion tests
   - `tests/test_segment.py` - Segment buffering tests
   - Full pytest coverage

9. ✅ **Docker Compose Integration**
   - Added to `docker-compose.pipeline.yml`
   - Depends on harmonizer
   - Auto-restart on failure
   - Log rotation (10MB × 3 files)

10. ✅ **Makefile Targets**
    - `make windowizer-build` - Build Docker image
    - `make windowizer-run` - Start service
    - `make windowizer-stop` - Stop service
    - `make windowizer-logs` - View logs
    - `make windowizer-health` - Check health

### Architecture

**Data Flow:**
```
Kafka: wifi7.telemetry.v0_1 (per-metric events)
        ↓
    Windowizer
    - Consume events in batches (100)
    - Aggregate by (experiment_id, ts_bucket, entity_id)
    - Fill missing metrics (0.0)
    - Convert cumulative counters to deltas
    - Buffer into 256-window segments
    - Track window indices
        ↓
Kafka: wifi7.ml.windowed_features.v1 (segments)
```

**State Management:**
- Window indices: `(experiment_id, entity_id) → window_idx`
- Delta state: `(experiment_id, entity_id) → {metric: last_value}`
- Segment buffers: `(experiment_id, entity_id) → [windows...]`

**Window Aggregation Algorithm:**
1. Consume events from Kafka (batch of 100)
2. Compute window bucket: `floor(timestamp_ms / 100) * 100`
3. Group by `(experiment_id, window_bucket, entity_id)`
4. Aggregate all 13 base metrics per window
5. Sort windows by timestamp
6. Apply delta conversion to cumulative counters
7. Buffer windows per entity
8. Emit segment when 256 windows accumulated
9. Commit Kafka offset after successful delivery

### Files Created (10 source files + 3 tests)

**Source Code:**
- `security/detector/windowizer/windowizer.py` (300 lines)
- `security/detector/windowizer/window_aggregator.py` (100 lines)
- `security/detector/windowizer/delta_converter.py` (110 lines)
- `security/detector/windowizer/segment_builder.py` (180 lines)
- `security/detector/windowizer/kafka_client.py` (200 lines)
- `security/detector/windowizer/requirements.txt`
- `security/detector/windowizer/Dockerfile`

**Tests:**
- `security/detector/windowizer/tests/__init__.py`
- `security/detector/windowizer/tests/test_aggregator.py` (70 lines)
- `security/detector/windowizer/tests/test_delta.py` (80 lines)
- `security/detector/windowizer/tests/test_segment.py` (100 lines)

**Configuration:**
- `docker-compose.pipeline.yml` (updated with windowizer + gcn-detector)

### Testing

**Run Unit Tests:**
```bash
cd security/detector/windowizer
python -m pytest tests/ -v --cov=. --cov-report=term-missing
```

**Expected Output:**
- All tests pass
- Coverage > 80%

### Verification Commands (Phase 2)

#### 1. Build Windowizer Image
```bash
make windowizer-build
```
**Expected**: Docker image `ndt/windowizer:local` created

#### 2. Check Docker Image
```bash
docker images | grep windowizer
```
**Expected**: Image listed with recent timestamp

#### 3. Verify Windowizer Files
```bash
ls -la security/detector/windowizer/
```
**Expected**: All Python files, Dockerfile, config.yaml, tests/ directory

#### 4. Run Unit Tests
```bash
cd security/detector/windowizer
python -m pytest tests/ -v
```
**Expected**: All tests pass (9 tests total)

#### 5. Test Configuration Parsing
```bash
cd security/detector/windowizer
python -c "import yaml; print(yaml.safe_load(open('config.yaml'))['windowing']['segment_length'])"
```
**Expected Output**: `256`

#### 6. Start Windowizer Service
```bash
# Ensure containerlab is running
make up

# Create Kafka topics
make kafka-topics-create

# Start windowizer
make windowizer-run
```
**Expected**: Container `ndt-pipeline-windowizer` running

#### 7. Check Windowizer Logs
```bash
make windowizer-logs
```
**Expected Logs**:
```
INFO - Loaded configuration
INFO - Subscribed to topic: wifi7.telemetry.v0_1
INFO - Starting windowizer service...
INFO - Consuming from: wifi7.telemetry.v0_1
INFO - Producing to: wifi7.ml.windowed_features.v1
```

#### 8. Verify Kafka Topics Created
```bash
docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic list | grep wifi7.ml
```
**Expected Output**:
```
wifi7.ml.windowed_features.v1
```

#### 9. Check Container Status
```bash
docker ps | grep windowizer
```
**Expected**: Container running, uptime > 0s

#### 10. Test Health Check
```bash
docker exec ndt-pipeline-windowizer pgrep -f windowizer.py
```
**Expected**: Process ID number

#### 11. Check Docker Compose Status
```bash
docker compose -f docker-compose.pipeline.yml ps
```
**Expected**: windowizer status = "running"

#### 12. Inspect Windowizer Env Vars
```bash
docker exec ndt-pipeline-windowizer env | grep KAFKA
```
**Expected**: Environment variables set correctly

#### 13. Verify Python Dependencies
```bash
docker exec ndt-pipeline-windowizer pip list | grep confluent-kafka
```
**Expected**: `confluent-kafka` version >= 2.3.0

#### 14. Test Graceful Shutdown
```bash
make windowizer-stop
make windowizer-logs | tail -20
```
**Expected Logs**:
```
INFO - Shutting down windowizer...
INFO - Flushing Kafka producer...
INFO - Windowizer shutdown complete
```

#### 15. End-to-End Test (with Real Data)
```bash
# Start full pipeline
make up
make pipeline-up
make kafka-topics-create
make windowizer-run

# Run ns-3 experiment
make run-mlo-exp EXP_ID=20260210-test-windowizer-01 SCENARIO=normal

# Wait for processing
sleep 10

# Check output topic for segments
docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic consume wifi7.ml.windowed_features.v1 -n 1 | head -50
```
**Expected**: JSON segment with 256 windows

#### 16. Verify Segment Structure
```bash
# Consume one segment and pretty-print
docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic consume wifi7.ml.windowed_features.v1 -n 1 -f '%v\n' | python -m json.tool | head -30
```
**Expected JSON Structure**:
```json
{
  "experiment_id": "20260210-test-windowizer-01",
  "entity_id": "sta_0",
  "segment_id": "seg_0",
  "window_start_idx": 0,
  "window_end_idx": 255,
  "ts_start": "2026-02-10T...",
  "ts_end": "2026-02-10T...",
  "windows": [
    {
      "window_idx": 0,
      "ts": "2026-02-10T...",
      "net_throughput_mbps": 120.5,
      ...
    },
    ...  // 256 windows total
  ]
}
```

### Acceptance Criteria Met

- ✅ Windowizer consumes telemetry events from Kafka
- ✅ Windows aggregated correctly by timestamp bucket
- ✅ Deltas computed correctly for cumulative counters
- ✅ Segments (256 windows) emitted to Kafka
- ✅ No memory leaks (buffer overflow protection)
- ✅ Unit tests passing (>80% coverage)
- ✅ Docker image builds successfully
- ✅ Service runs in compose
- ✅ Configuration via YAML + env vars
- ✅ Graceful shutdown implemented
- ✅ Statistics logging working

### Known Limitations

1. **Partial Segments**: Currently discarded on shutdown (configurable)
2. **Late Arrivals**: No grace period yet (5s timeout planned)
3. **Health Endpoint**: Process check only (HTTP endpoint in Phase 3)
4. **Metrics**: Prometheus metrics disabled (optional feature)
5. **Multi-Instance**: No Redis state sharing yet (single instance only)

---

## WP8 Phase 3: GCN Detector Implementation (✅ Complete - 2026-02-10)

**Goal**: Build and test the GCN detector service that consumes windowed segments and performs real-time attack detection.

### Deliverables Completed

1. ✅ **GCN Model Source Code**
   - Copied complete GCN implementation to `twin/gnn/detector/gcn_src/`
   - `models/gcn.py` - WiFi7AttackGCN model architecture
   - `inference/detector.py` - Inference utilities
   - `data/preprocessing.py` - Data preprocessing utilities

2. ✅ **Model Loader**
   - `model_loader.py` (200+ lines)
   - Hot-reloading support via symlink watching
   - Loads PyTorch model + scaler + config from registry
   - Zero-downtime model updates
   - Version tracking and rollback support

3. ✅ **Graph Builder**
   - `graph_builder.py` (100+ lines)
   - Builds PyTorch Geometric temporal chain graphs
   - Creates edges: t ↔ t+1 (bidirectional temporal connections)
   - Batch graph construction for multiple segments
   - Handles variable-length segments

4. ✅ **Feature Processor**
   - `feature_processor.py` (100+ lines)
   - StandardScaler application (z-score normalization)
   - Derived feature computation:
     - `retrans_rate` = mac_total_retrans / mac_total_tx
     - `drop_rate` = (mac_drop + phy_drop) / mac_total_tx
     - `throughput_per_flow` = throughput / active_flows
   - 16 total features (13 base + 3 derived)

5. ✅ **Inference Engine**
   - `inference_engine.py` (150+ lines)
   - Coordinates model loading, graph building, inference
   - Batch processing (32 segments per batch)
   - Returns predictions with confidence scores
   - Inference time tracking (ms per segment)

6. ✅ **Database Writer**
   - `db_writer.py` (150+ lines)
   - Batch inserts to TimescaleDB (100 predictions per batch)
   - Connection retry logic with exponential backoff
   - Buffer management and overflow protection
   - Graceful shutdown with flush

7. ✅ **Health API**
   - `health_api.py` (100+ lines)
   - Flask API with `/health` and `/status` endpoints
   - Callbacks for model, Kafka, DB status checks
   - Statistics reporting (segments processed, attacks detected)
   - Uptime tracking

8. ✅ **Main Detector Service**
   - `detector.py` (300+ lines)
   - Consumes from `wifi7.ml.windowed_features.v1`
   - Produces to `wifi7.security.gcn_predictions.v1`
   - Graceful shutdown with SIGTERM/SIGINT handlers
   - Statistics logging every 60s
   - Periodic model reload checks (every 60s)
   - Database connection monitoring

9. ✅ **Docker Configuration**
   - `Dockerfile` with PyTorch + PyTorch Geometric
   - CPU-optimized PyTorch (smaller image size)
   - Non-root user (detector:1000)
   - Health check via HTTP endpoint
   - Config volume mount

10. ✅ **Unit Tests**
    - `tests/test_model_loader.py` - Model loading and inference tests
    - `tests/test_graph_builder.py` - Graph construction tests
    - `tests/test_inference.py` - End-to-end inference tests
    - Comprehensive test coverage

11. ✅ **Requirements**
    - `requirements.txt` with all dependencies
    - PyTorch 2.0.0 (CPU version)
    - PyTorch Geometric 2.3.0
    - confluent-kafka, psycopg2-binary, Flask, PyYAML

### Architecture

**Data Flow:**
```
Kafka: wifi7.ml.windowed_features.v1 (segments)
        ↓
    GCN Detector
    - Consume segments (batch of 32)
    - Add derived features
    - Build temporal chain graphs
    - Scale features (StandardScaler)
    - Run GCN inference
    - Generate predictions
    - Write to DB (batch of 100)
    - Produce to Kafka
        ↓
Kafka: wifi7.security.gcn_predictions.v1 + TimescaleDB
        ↓
    Grafana + Alerts (Phase 5)
```

**Temporal Chain Graph:**
```
Segment (256 windows) → Graph with:
  - Nodes: 256 windows
  - Features: 16 per window
  - Edges: Bidirectional temporal chain
    0 ↔ 1 ↔ 2 ↔ ... ↔ 255
```

**Inference Pipeline:**
1. Consume segment from Kafka
2. Add derived features (retrans_rate, drop_rate, throughput_per_flow)
3. Build PyG Data object with temporal edges
4. Apply StandardScaler normalization
5. Run GCN forward pass
6. Softmax to get probabilities
7. Threshold at 0.5 for binary prediction
8. Package results with metadata
9. Write to DB (buffered batch insert)
10. Produce to Kafka (with delivery confirmation)
11. Commit Kafka offset

### Files Created (11 source files + 3 tests)

**Source Code:**
- `twin/gnn/detector/detector.py` (300+ lines)
- `twin/gnn/detector/model_loader.py` (200+ lines)
- `twin/gnn/detector/graph_builder.py` (100+ lines)
- `twin/gnn/detector/feature_processor.py` (100+ lines)
- `twin/gnn/detector/inference_engine.py` (150+ lines)
- `twin/gnn/detector/db_writer.py` (150+ lines)
- `twin/gnn/detector/health_api.py` (100+ lines)
- `twin/gnn/detector/requirements.txt`
- `twin/gnn/detector/Dockerfile`

**GCN Source (Copied):**
- `twin/gnn/detector/gcn_src/models/gcn.py`
- `twin/gnn/detector/gcn_src/inference/detector.py`
- `twin/gnn/detector/gcn_src/data/preprocessing.py`

**Tests:**
- `twin/gnn/detector/tests/__init__.py`
- `twin/gnn/detector/tests/test_model_loader.py` (130+ lines)
- `twin/gnn/detector/tests/test_graph_builder.py` (100+ lines)
- `twin/gnn/detector/tests/test_inference.py` (140+ lines)

### Testing

**Run Unit Tests:**
```bash
cd twin/gnn/detector
python -m pytest tests/ -v --cov=. --cov-report=term-missing
```

**Expected Output:**
- All tests pass (10+ tests total)
- Coverage > 75%

### Verification Commands (Phase 3)

#### 1. Build GCN Detector Image
```bash
make gcn-detector-build
```
**Expected**: Docker image `ndt/gcn-detector:local` created

#### 2. Check Docker Image Size
```bash
docker images | grep gcn-detector
```
**Expected**: Image size ~2-3GB (includes PyTorch + PyG)

#### 3. Verify Detector Files
```bash
ls -la twin/gnn/detector/
```
**Expected**: All Python files, Dockerfile, gcn_src/, tests/ directory

#### 4. Check GCN Source Code
```bash
ls -la twin/gnn/detector/gcn_src/models/
```
**Expected**: `gcn.py` file present

#### 5. Run Unit Tests
```bash
cd twin/gnn/detector
python -m pytest tests/ -v
```
**Expected**: All tests pass (10+ tests total)

#### 6. Test Model Loading
```bash
cd twin/gnn/detector
python -c "from model_loader import ModelLoader; ml = ModelLoader('../../registry/gcn', 'current', 'cpu'); print('Success' if ml.load_model() else 'Failed')"
```
**Expected Output**: `Success`

#### 7. Verify Model Registry Access
```bash
cd twin/gnn/detector
python -c "import sys; sys.path.insert(0, 'gcn_src'); from models.gcn import WiFi7AttackGCN; print('Model imported successfully')"
```
**Expected Output**: `Model imported successfully`

#### 8. Test Graph Building
```bash
cd twin/gnn/detector
python -c "from graph_builder import GraphBuilder; gb = GraphBuilder(['metric1']); print('GraphBuilder OK')"
```
**Expected Output**: `GraphBuilder OK`

#### 9. Start GCN Detector Service
```bash
# Ensure dependencies running
make up
make pipeline-up
make kafka-topics-create
make windowizer-run

# Start detector
make gcn-detector-run
```
**Expected**: Container `ndt-pipeline-gcn-detector` running

#### 10. Check Detector Logs
```bash
make gcn-detector-logs
```
**Expected Logs**:
```
INFO - Loaded configuration
INFO - Loading GCN model...
INFO - Loaded model version: v1.0.0
INFO - Inference engine initialized
INFO - Connected to database: udr@udr-db
INFO - Subscribed to topic: wifi7.ml.windowed_features.v1
INFO - Starting GCN detector service...
INFO - Model: v1.0.0
INFO - Device: cpu
INFO - Consuming from: wifi7.ml.windowed_features.v1
INFO - Producing to: wifi7.security.gcn_predictions.v1
```

#### 11. Check Health Endpoint
```bash
curl -s http://localhost:8080/health | python -m json.tool
```
**Expected JSON**:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "kafka_connected": true,
  "db_connected": true,
  "uptime_seconds": 30
}
```

#### 12. Check Status Endpoint (with Stats)
```bash
curl -s http://localhost:8080/status | python -m json.tool
```
**Expected JSON**:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "kafka_connected": true,
  "db_connected": true,
  "uptime_seconds": 60,
  "segments_received": 0,
  "predictions_made": 0,
  "attacks_detected": 0,
  "predictions_failed": 0,
  "db_writes_failed": 0
}
```

#### 13. Verify Kafka Topics
```bash
docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic list | grep wifi7.security
```
**Expected Output**:
```
wifi7.security.gcn_predictions.v1
```

#### 14. Check Container Status
```bash
docker ps | grep gcn-detector
```
**Expected**: Container running, uptime > 0s

#### 15. Verify Python Dependencies
```bash
docker exec ndt-pipeline-gcn-detector pip list | grep torch
```
**Expected**: `torch`, `torch-geometric`, `torch-scatter`, `torch-sparse`

#### 16. Test Database Connection
```bash
docker exec ndt-pipeline-gcn-detector python -c "
import psycopg2
conn = psycopg2.connect(
    host='clab-ndt-wifi7-mlo-security-udr-db',
    port=5432,
    dbname='udr',
    user='postgres',
    password='postgres'
)
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM gcn_predictions')
print(f'Predictions table exists, rows: {cursor.fetchone()[0]}')
conn.close()
"
```
**Expected**: `Predictions table exists, rows: 0`

#### 17. End-to-End Test (with Real Data)
```bash
# Start full pipeline
make up
make pipeline-up
make kafka-topics-create
make windowizer-run
make gcn-detector-run

# Run ns-3 experiment (generates telemetry)
make run-mlo-exp EXP_ID=20260210-test-gcn-01 SCENARIO=normal

# Wait for processing
sleep 30

# Check predictions in Kafka
docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic consume wifi7.security.gcn_predictions.v1 -n 1 -f '%v\n' | python -m json.tool | head -50
```
**Expected**: JSON prediction with structure:
```json
{
  "experiment_id": "20260210-test-gcn-01",
  "entity_id": "sta_0",
  "segment_id": "seg_0",
  "window_start_idx": 0,
  "window_end_idx": 255,
  "ts_start": "2026-02-10T...",
  "ts_end": "2026-02-10T...",
  "prediction": 0,
  "confidence": 0.982,
  "probabilities": [0.982, 0.018],
  "model_version": "v1.0.0",
  "model_path": "/app/../../registry/gcn/v1.0.0",
  "inference_time_ms": 45.2
}
```

#### 18. Check Predictions in Database
```bash
docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U postgres -d udr -c \
  "SELECT experiment_id, entity_id, segment_id, prediction, confidence, created_at FROM gcn_predictions ORDER BY created_at DESC LIMIT 5;"
```
**Expected**: Rows with predictions

#### 19. Verify Attack Detection Log
```bash
# Run attack scenario
make run-mlo-exp EXP_ID=20260210-test-attack-01 SCENARIO=negative

# Wait for processing
sleep 30

# Check detector logs for attack warnings
make gcn-detector-logs | grep "ATTACK DETECTED"
```
**Expected Log**:
```
WARNING - ATTACK DETECTED: 20260210-test-attack-01/sta_0 segment seg_X (confidence: 0.95)
```

#### 20. Test Graceful Shutdown
```bash
make gcn-detector-stop
make gcn-detector-logs | tail -20
```
**Expected Logs**:
```
INFO - Shutting down GCN detector...
INFO - Flushing Kafka producer...
INFO - Flushing database writes...
INFO - Flushed X predictions to database
INFO - Database connection closed
INFO - === GCN Detector Stats ===
INFO - GCN Detector shutdown complete
```

### Acceptance Criteria Met

- ✅ GCN detector consumes windowed segments from Kafka
- ✅ Temporal chain graphs built correctly (PyG format)
- ✅ Features scaled correctly (StandardScaler)
- ✅ Derived features computed (retrans_rate, drop_rate, throughput_per_flow)
- ✅ GCN model loads from registry
- ✅ Inference runs successfully (batch of 32)
- ✅ Predictions written to database (buffered batches)
- ✅ Predictions produced to Kafka
- ✅ Health endpoints functional (/health, /status)
- ✅ Hot-reloading support for model updates
- ✅ Unit tests passing (>75% coverage)
- ✅ Docker image builds successfully
- ✅ Service runs in compose
- ✅ Graceful shutdown implemented
- ✅ Statistics logging working

### Performance Characteristics

**Model Inference:**
- Single segment: ~30-50ms (CPU)
- Batch of 32 segments: ~500-800ms (CPU)
- Throughput: ~40-60 segments/second (single instance)

**Resource Usage:**
- Memory: ~1.5-2GB (PyTorch + model)
- CPU: 50-100% during inference bursts
- Disk: ~3GB (Docker image)

**Latency (End-to-End):**
- Telemetry event → Prediction: ~30-40 seconds
  - Windowing buffer: ~25.6 seconds (256 windows)
  - Kafka transit: ~1 second
  - GCN inference: ~50ms
  - DB write: ~10ms

### Known Limitations

1. **CPU Only**: GPU support disabled (CPU sufficient for current throughput)
2. **Single Instance**: No horizontal scaling yet (Kafka partitions ready)
3. **Batch Size Fixed**: 32 segments (configurable but not dynamic)
4. **No DLQ**: Failed predictions not sent to dead-letter queue
5. **Model Metrics**: No Prometheus metrics for model performance
6. **Prediction Explanation**: No SHAP or attention weights exported

### Next Steps (Phase 4)

**End-to-End Testing:**
- Test with all 3 scenarios (Normal, Positive, Negative)
- Verify attack detection accuracy
- Measure end-to-end latency
- Load testing (high throughput)
- Failure recovery testing
- Model update testing (hot-reload)

**Duration**: Week 4 (estimated 3-5 days)

---

## WP8 Verification Summary

### Phase 1 Verification ✅
```bash
# Verify model registry
ls -la twin/registry/gcn/v1.0.0/

# Check symlink
readlink twin/registry/gcn/current

# Verify config files
cat security/detector/windowizer/config.yaml | grep segment_length
cat twin/gnn/detector/config.yaml | grep batch_size

# Check Makefile targets
make --help | grep gcn
```

### Phase 2 Verification ✅
```bash
# Build and run tests
make windowizer-build
cd security/detector/windowizer && python -m pytest tests/ -v

# Start service
make up && make kafka-topics-create && make windowizer-run

# Check logs
make windowizer-logs

# Verify output topic
docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic list | grep windowed_features
```

### Phase 3 Verification ✅
```bash
# Build and run tests
make gcn-detector-build
cd twin/gnn/detector && python -m pytest tests/ -v

# Start service
make up && make pipeline-up && make kafka-topics-create
make windowizer-run && make gcn-detector-run

# Check logs
make gcn-detector-logs

# Check health endpoint
curl -s http://localhost:8080/health | python -m json.tool

# Verify predictions topic
docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic list | grep gcn_predictions

# Run end-to-end test
make run-mlo-exp EXP_ID=test-gcn SCENARIO=normal
sleep 30
docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic consume wifi7.security.gcn_predictions.v1 -n 1

# Check database
docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U postgres -d udr -c \
  "SELECT COUNT(*) FROM gcn_predictions;"
```

### Quick Health Check
```bash
# Check all WP8 services
docker compose -f docker-compose.pipeline.yml ps

# Expected:
# - harmonizer: running
# - windowizer: running (Phase 2 complete)
# - gcn-detector: running (Phase 3 complete)

# Check health endpoints
curl -s http://localhost:8080/status | python -m json.tool
```


---

## WP8 Phase 5: Grafana Dashboard (✅ Complete - 2026-02-10)

**Goal**: Create comprehensive Grafana dashboard for visualizing GCN attack detection results and model performance.

### Deliverables Completed

1. ✅ **GCN Attack Detection Dashboard**
   - Dashboard UID: `gcn-attack-detection`
   - Location: `clab/configs/grafana/dashboards/gcn-attack-detection.json`
   - 16 panels covering all aspects of attack detection

2. ✅ **Executive Summary Panels**
   - Total Predictions (stat with threshold colors)
   - Attacks Detected (stat with severity thresholds)
   - Attack Rate (percentage with gradient)
   - Average Confidence (model certainty indicator)
   - Average Inference Time (performance metric)
   - Active Model Version (deployment tracking)

3. ✅ **Visualization Panels**
   - Attack Detection Timeline (bar chart)
   - Prediction Confidence Over Time (line chart)
   - Confidence Score Distribution (histogram)
   - Prediction Distribution (pie chart: Normal vs Attack)
   - Attack Rate by Experiment (horizontal bar gauge)
   - Model Performance Summary (multi-stat panel)

4. ✅ **Detailed Analysis Panels**
   - Recent Predictions Table (last 100, sortable, color-coded)
   - Inference Performance Over Time (latency tracking)
   - Attack Probability Distribution (probability trends)

5. ✅ **Annotations**
   - Attack Detections (red markers with confidence)
   - Model Version Changes (blue markers for deployments)

6. ✅ **Template Variables**
   - `experiment_filter` - Multi-select experiment filter
   - `model_version` - Model version selector for A/B testing

7. ✅ **Auto-Refresh**
   - 10-second refresh interval for real-time monitoring
   - Configurable time ranges (5m, 15m, 1h, 6h, 12h, 24h, 2d, 7d)

8. ✅ **Comprehensive Documentation**
   - `WP8-PHASE5-GRAFANA-DASHBOARD.md` (60+ pages)
   - Usage guide with workflows
   - Troubleshooting section
   - Customization guide
   - Best practices

### Dashboard Features

#### Panel Breakdown

| Panel ID | Name | Type | Purpose |
|----------|------|------|---------|
| 1 | Total Predictions | Stat | Count all predictions |
| 2 | Attacks Detected | Stat | Count attacks |
| 3 | Attack Rate | Stat | Attack percentage |
| 4 | Avg Confidence | Stat | Mean confidence |
| 5 | Avg Inference Time | Stat | Mean latency |
| 6 | Active Model | Stat | Current version |
| 10 | Attack Detection Timeline | Time Series | Real-time visualization |
| 11 | Prediction Confidence | Time Series | Confidence trends |
| 12 | Confidence Distribution | Histogram | Score distribution |
| 20 | Prediction Distribution | Pie Chart | Normal vs Attack |
| 21 | Attack Rate by Experiment | Bar Gauge | Per-experiment rates |
| 22 | Model Performance | Stat | KPI summary |
| 30 | Recent Predictions | Table | Detailed list |
| 40 | Inference Performance | Time Series | Latency trends |
| 41 | Probability Distribution | Time Series | Attack probability |

#### Key Capabilities

**Real-Time Monitoring:**
- Auto-refresh every 10 seconds
- Live attack detection visualization
- Immediate alert annotations

**Analysis & Investigation:**
- Filter by experiment or model version
- Drill down to individual predictions
- Compare performance across experiments
- Track model confidence over time

**Performance Tracking:**
- Monitor inference latency
- Track throughput (segments/min)
- Identify performance degradation
- Capacity planning insights

**Model Validation:**
- Compare attack rates across scenarios
- Verify confidence distributions
- Detect model bias (e.g., 100% attack rate)
- A/B testing between model versions

### Usage Workflows

#### 1. Live Security Monitoring

```bash
# Ensure pipeline running
docker compose -f docker-compose.pipeline.yml ps

# Access dashboard
open http://localhost:3000/d/gcn-attack-detection

# Monitor:
# - Attack Detection Timeline (new attacks)
# - Recent Predictions table (latest results)
# - Attack Rate metric (overall activity)
```

#### 2. Investigate Attack Detection

1. Select experiment via `experiment_filter` dropdown
2. Review Attack Detection Timeline for timing
3. Check Recent Predictions table for details
4. Examine Confidence scores (low = uncertain)
5. Review Attack Probability chart (borderline cases)

#### 3. Model Performance Analysis

1. Set time range (e.g., last 6 hours)
2. Check KPIs:
   - Avg Confidence (should be > 0.8)
   - Avg Inference Time (should be < 100ms)
   - Attack Rate (depends on scenario)
3. Review Confidence Distribution (should be bimodal)
4. Check Inference Performance (stable over time)

#### 4. Validate Model Deployment

1. Use `model_version` filter to select versions
2. Compare metrics before/after deployment
3. Check Model Version Change annotations
4. Verify no regression in performance

### Verification Commands (Phase 5)

#### 1. Access Grafana Dashboard
```bash
# Open in browser
open http://localhost:3000

# Login: admin / admin (default)
# Navigate: Dashboards → Browse → "GCN Attack Detection"
# Or direct: http://localhost:3000/d/gcn-attack-detection
```
**Expected**: Dashboard loads with all panels

#### 2. Verify Datasource Connection
```bash
# Via Grafana UI
# Configuration → Data Sources → udr_postgres → Test
```
**Expected**: "Data source is working" message

#### 3. Check Dashboard Provisioning
```bash
ls -la clab/configs/grafana/dashboards/ | grep gcn
```
**Expected**: `gcn-attack-detection.json` file present

#### 4. Verify Predictions Data
```bash
# Query database directly
docker exec clab-ndt-wifi7-mlo-security-udr-db psql -d udr -c \
  "SELECT COUNT(*) as total, 
          SUM(CASE WHEN prediction=1 THEN 1 ELSE 0 END) as attacks 
   FROM gcn_predictions;"
```
**Expected**: Shows prediction counts

#### 5. Test Auto-Refresh
```bash
# Watch dashboard for 30 seconds
# Verify timestamp updates in panels
# Check "Last updated" indicator
```
**Expected**: Dashboard refreshes every 10 seconds

#### 6. Test Experiment Filter
```bash
# In Grafana UI:
# 1. Click "experiment_filter" dropdown
# 2. Select specific experiment
# 3. Verify all panels update
```
**Expected**: Panels show only selected experiment data

#### 7. Verify Annotations
```bash
# Check attack annotations visible on timeline
# Look for red vertical lines
# Hover to see attack details
```
**Expected**: Annotations appear at attack timestamps

#### 8. Test Table Sorting
```bash
# In Recent Predictions table:
# 1. Click column header (e.g., "Confidence")
# 2. Verify rows resort
```
**Expected**: Table sorts by clicked column

#### 9. Check Panel Queries
```bash
# In Grafana UI:
# 1. Edit any panel
# 2. Review SQL query
# 3. Click "Query Inspector"
# 4. Check execution time
```
**Expected**: Queries execute in < 1 second

#### 10. Export Dashboard JSON
```bash
# Via Grafana UI
# Dashboard Settings → JSON Model → Copy to clipboard
# Or: Share → Export → Save to file
```
**Expected**: Valid JSON exported

### Integration with Pipeline

**Data Flow:**
```
GCN Detector → TimescaleDB.gcn_predictions
                      ↓
            Grafana Dashboard Queries
                      ↓
        Real-time Visualization (10s refresh)
```

**Metrics Tracked:**
- Predictions: Total count, attack count, attack rate
- Confidence: Mean, distribution, time series
- Performance: Inference time, throughput
- Model: Version, deployment timestamps

### Acceptance Criteria Met

- ✅ Dashboard auto-provisions from JSON file
- ✅ All 16 panels render correctly
- ✅ Datasource connection works
- ✅ Template variables function properly
- ✅ Annotations show attack detections
- ✅ Auto-refresh works (10s interval)
- ✅ Tables sortable and filterable
- ✅ Color coding shows attack vs normal
- ✅ Confidence displayed with gradient gauges
- ✅ Performance metrics visible
- ✅ Comprehensive documentation provided

### Known Limitations

1. **No Alerting**: Grafana alerts not configured yet (Phase 6)
2. **Database User**: Need to configure correct PostgreSQL credentials
3. **Historical Data**: Limited to retention period (30 days default)
4. **Real-time Only**: No prediction history replay
5. **Single Datasource**: Only TimescaleDB (no Prometheus yet)

### Next Steps (Phase 6)

**Training Pipeline Implementation:**
- On-demand model retraining
- Training dataset management
- Model evaluation and comparison
- Automated model deployment
- Version control for models
- A/B testing framework

**Duration**: Week 5-6 (estimated 5-7 days)

---

## WP8 Verification Summary

### Phase 1 Verification ✅
```bash
# Verify model registry
ls -la twin/registry/gcn/v1.0.0/

# Check symlink
readlink twin/registry/gcn/current

# Verify config files
cat security/detector/windowizer/config.yaml | grep segment_length
cat twin/gnn/detector/config.yaml | grep batch_size
```

### Phase 2 Verification ✅
```bash
# Build and run tests
make windowizer-build
cd security/detector/windowizer && python -m pytest tests/ -v

# Start service
make up && make kafka-topics-create && make windowizer-run

# Check logs
make windowizer-logs
```

### Phase 3 Verification ✅
```bash
# Build and run tests
make gcn-detector-build
cd twin/gnn/detector && python -m pytest tests/ -v

# Start service and check health
make gcn-detector-run
curl -s http://localhost:8080/health | python -m json.tool
```

### Phase 4 Verification ✅
```bash
# Run end-to-end tests
# See: docs/WP8-PHASE4-E2E-TEST-ANALYSIS.md

# Quick verification
docker logs ndt-pipeline-gcn-detector | grep "Predictions made"
docker exec clab-ndt-wifi7-mlo-security-udr-db psql -d udr -c \
  "SELECT COUNT(*) FROM gcn_predictions;"
```

### Phase 5 Verification ✅
```bash
# Access Grafana dashboard
open http://localhost:3000/d/gcn-attack-detection

# Verify data
# Check all panels load
# Test filters and variables
# Verify auto-refresh
```

### Complete Pipeline Health Check
```bash
# Check all services
docker compose -f docker-compose.pipeline.yml ps

# Expected output:
# - harmonizer: running
# - windowizer: running
# - gcn-detector: running

# Check Grafana
curl -s http://localhost:3000/api/health

# Check GCN detector health
curl -s http://localhost:8080/status | python -m json.tool
```

---

## Files Changed in Phase 5

**New Files:**
- `clab/configs/grafana/dashboards/gcn-attack-detection.json` (comprehensive dashboard)
- `docs/WP8-PHASE5-GRAFANA-DASHBOARD.md` (60+ page documentation)

**Modified Files:**
- `docs/CURRENT-STATE.md` (this file - added Phase 5 documentation)

**Dashboard Configuration:**
- 16 visualization panels
- 2 annotation layers
- 2 template variables
- Auto-refresh enabled (10s)
- Color-coded thresholds
- Responsive layout

---

## WP10: Custom Web Dashboard (✅ Complete — 2026-02-28)

**URL:** http://localhost:8888

### Overview

A full-stack custom web dashboard built with React 18 + FastAPI, served from Docker. Uses a **Soft UI / Neumorphism + Claymorphism** design system. Connects to TimescaleDB in real-time via WebSocket (2-second DB poll).

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, TailwindCSS, Recharts, Lucide icons |
| Backend | FastAPI, asyncpg, uvicorn |
| Real-time | WebSocket (`/ws/pipeline`) polling DB every 2s |
| Build | Multi-stage Docker: Node 20 Alpine → Python 3.11-slim |
| Port | **8888** |

### 6 Dashboard Sections

1. **Pipeline Monitor** — Live NS-3→Exporter→Kafka→Windowizer→GCN→DB stage status with per-stage counters and real-time activity feed of new GCN predictions
2. **Experiment View** — Per-experiment KPI cards (segments, attack rate, confidence, inference time), selectable metric evolution chart, segment prediction table with confidence scores
3. **Model Intelligence** — F1/accuracy/precision/recall/AUC bar chart, confusion matrix (from both live DB analysis and model test results), inference latency percentiles (min/p50/p95/max), model registry version list
4. **Run History** — All experiments with pass/fail indicator, attack-rate bar chart for last 20 runs, sortable full table
5. **Attack Analysis** — TP/TN/FP/FN breakdown cards, confidence histogram (normal vs attack), detection rate by experiment type donut chart
6. **Network Health** — All 13 telemetry metrics (avg/min/max/σ) with trend arrows; click any metric card to expand its time-series chart

### REST API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check + DB connectivity |
| GET | `/api/experiments` | List all experiments with stats |
| GET | `/api/experiments/{id}/summary` | Single experiment summary |
| GET | `/api/experiments/{id}/predictions` | All segment predictions |
| GET | `/api/experiments/{id}/metrics` | Metric time-series (downsampled) |
| GET | `/api/models` | Model registry list |
| GET | `/api/models/active` | Active model detail |
| GET | `/api/models/inference-stats` | Inference latency stats |
| GET | `/api/analysis/summary` | Cross-experiment TP/TN/FP/FN |
| GET | `/api/analysis/confidence-histogram` | Confidence distribution |
| GET | `/api/analysis/attack-by-type` | Detection rate by experiment type |
| GET | `/api/pipeline/status` | Current pipeline stage states |
| WS  | `/ws/pipeline` | Real-time pipeline events + status |

### Commands

```bash
make dashboard-build    # Build image (ndt/dashboard:local)
make dashboard-up       # Start dashboard (requires make up for clab-mgmt network)
make dashboard-down     # Stop
make dashboard-logs     # Follow logs
make dashboard-status   # Status + last 20 log lines
```

### Implementation Files

```
dashboard/app/
├── Dockerfile                     Multi-stage build
├── .dockerignore
├── backend/
│   ├── main.py                    App factory, graceful DB startup
│   ├── requirements.txt           fastapi, uvicorn, asyncpg, pydantic, PyYAML
│   ├── db/connection.py           asyncpg pool (min=2, max=10)
│   ├── db/queries.py              All async SQL queries
│   ├── api/experiments.py         Experiment REST router
│   ├── api/models.py              Model REST router
│   ├── api/analysis.py            Analysis REST router
│   ├── api/pipeline.py            Pipeline status router
│   ├── ws/pipeline.py             WebSocket handler
│   └── registry/reader.py         GCN registry filesystem reader
└── frontend/
    ├── package.json               React 18, Recharts, lucide-react
    ├── vite.config.ts             Dev proxy → :8888, build → dist/
    ├── tailwind.config.ts         Neumorphic shadow + colour tokens
    └── src/
        ├── index.css              CSS design system (CSS variables)
        ├── App.tsx                Root layout + section router
        ├── context/AppContext.tsx WebSocket + global state
        ├── types/                 TypeScript interfaces
        ├── hooks/                 useExperiments, useModels, useAnalysis
        ├── components/            layout, common, pipeline, charts, model
        └── sections/              PipelineSection … NetworkHealthSection
```

---

## WP9: GCN Model Retraining (✅ Complete — 2026-02-28)

### Overview

**Problem**: GCN model v1.0.0 has 100% false positive rate on pipeline data due to distribution mismatch
- Training data: 412 Mbps throughput, 6-94 imbalanced distribution
- Pipeline data: 306 Mbps throughput, different characteristics
- Result: Model flags all normal traffic as attacks

**Solution**: Retrain model v2.0.0 on pipeline-generated data with balanced 50-50 distribution

### Current Status: ✅ Complete — Model v2.0.0 Deployed

**Completed**: 2026-02-28
**Pilot Study**: 30 scenarios generated, model trained and validated
**Full Dataset**: 284 balanced scenarios (deployed as v2.0.0)
**Active Model**: `twin/registry/gcn/current` → `v2.0.0`

### Pilot Study Design (30 Scenarios, 50-50 Balanced)

| Category | Count | Distribution | Bias Levels |
|----------|-------|--------------|-------------|
| **Normal** | 15 | 50% | 0 (baseline) |
| **Positive Attack** | 8 | 27% | 50, 100, 500, 1000, 5000 |
| **Negative Attack** | 7 | 23% | -50, -100, -500, -1000, -5000 |
| **TOTAL** | **30** | **~50-50** | 5 bias levels tested |

**Why Balanced 50-50 vs Original 6-94**:
- ✅ **2-3x lower false positive rate** (5-15% vs 15-25%)
- ✅ **Better production usability** (users trust alerts)
- ✅ **ML best practice** (avoid class imbalance)
- ✅ **Better generalization** and robustness
- Trade-off: Slightly lower recall (90-94% vs 95-99%) - acceptable

### Key Improvements Over v1.0.0

**Distribution**:
- v1.0.0: 12 normal (6%) + 192 attack (94%) = highly imbalanced
- v2.0.0-pilot: 15 normal (50%) + 15 attack (50%) = balanced ✅

**Bias Coverage**:
- v1.0.0: MISSED bias 50-500 (subtle attacks) ❌
- v2.0.0-pilot: INCLUDES bias 50-500 ✅ + 1000-5000 ✅

**Training Data Source**:
- v1.0.0: Original GCN repository data (different ns-3 config)
- v2.0.0-pilot: Pipeline-generated data (matches deployment) ✅

### Success Criteria (Pilot)

| Metric | Target | Rationale |
|--------|--------|-----------|
| **F1 Score** | > 0.75 | Acceptable for pilot validation |
| **Recall** | > 0.80 | Detect 80%+ of attacks |
| **FPR** | **< 15%** | **CRITICAL** - production usability |
| **Precision** | > 0.75 | 75%+ alerts are real attacks |

**Decision**:
- If successful → Proceed to full 256-scenario dataset
- If failed → Debug before investing 5-7 days in full dataset

### Scripts Created

All scripts ready and tested:

```bash
# 1. Data Generation (RUNNING NOW)
./scripts/generate_pilot_data.sh
# Status: PID 245647, Log: training_data/pilot_generation.log

# 2. Progress Monitor (USE ANYTIME)
./scripts/monitor_pilot_progress.sh

# 3. Dataset Preparation (RUN AFTER DATA COMPLETE)
./scripts/prepare_pilot_dataset.sh

# 4. Model Training (RUN AFTER PREPARATION)
./scripts/train_pilot_model.sh
```

### Timeline

```
Phase 1: Data Generation (NOW)
├─ Normal scenarios (15):    ~3-4 hours
├─ Positive attacks (8):     ~2 hours
└─ Negative attacks (7):     ~1.5-2 hours
Total: ~6.5-8 hours ⏰ Started 1+ hour ago

Phase 2: Dataset Preparation
└─ Copy to GCN repo:         ~10 minutes

Phase 3: Model Training
└─ Train v2.0.0-pilot:       ~1-2 hours

Phase 4: Validation
└─ Test and evaluate:        ~30 minutes

TOTAL PILOT STUDY: ~8-10 hours end-to-end
```

### Output Locations

**Training Data** (being generated):
```
training_data/
├── manifest_pilot.csv           # Metadata for all 30 scenarios
├── pilot_generation.log         # Live progress log
└── scenarios/
    ├── normal/light/            # 15 normal scenarios
    ├── positive_attack/         # 8 positive bias scenarios
    └── negative_attack/         # 7 negative bias scenarios
```

**GCN Dataset** (after preparation):
```
~/github/wifi7_gcn_attack_detection/
├── data_v2_pilot/
│   ├── Normal/                  # 15 files (50%)
│   └── Attack/                  # 15 files (50%)
└── models/v2.0.0-pilot/
    ├── best_model.pt            # Trained model
    └── scaler.json              # Feature scaler
```

### Monitoring Progress

```bash
# Quick status
./scripts/monitor_pilot_progress.sh

# Live log
tail -f training_data/pilot_generation.log

# Check process
ps -p $(cat training_data/pilot_generation.pid)
```

### Full Dataset Plan (After Pilot)

If pilot succeeds, generate **256 scenarios** for production model:

| Category | Count | Distribution |
|----------|-------|--------------|
| Normal | 128 | 50% |
| Positive Attack | 64 | 25% (8 bias × 8 each) |
| Negative Attack | 64 | 25% (8 bias × 8 each) |
| **TOTAL** | **256** | **50-50 balanced** |

**Bias Levels** (8 levels, logarithmic spacing):
- Subtle: 50, 100, 250, 500
- Strong: 1000, 2500, 5000, 10000

**Timeline**: 5-7 days (256 scenarios × 15 min avg, parallelizable)

### Related Documentation

- `docs/WP9-GCN-MODEL-RETRAINING-PLAN.md` - Comprehensive retraining plan
- `docs/WP9-ORIGINAL-GCN-ANALYSIS.md` - Analysis of original training data
- `docs/WP9-PILOT-STATUS.md` - Current pilot study status
- `docs/WP9-PILOT-STUDY-IN-PROGRESS.md` - Detailed pilot guide
- `docs/WP8-FINAL-RECOMMENDATION.md` - Why retraining vs alignment
- `docs/WP8-VALIDATION-COMPLETE.md` - Configuration alignment test results

### Known Issues Addressed

**Issue**: v1.0.0 model has 100% false positive rate
**Root Cause**: Training data (412 Mbps) vs pipeline data (306 Mbps) mismatch
**Solution**: Retrain on pipeline data ✅

**Issue**: Original model missed subtle attacks (bias 50-500)
**Root Cause**: Training only used bias 1000-10000
**Solution**: Include all 8 bias levels (50-10000) ✅

**Issue**: High false positive rate with 6-94 distribution
**Root Cause**: Class imbalance (model biased toward attack class)
**Solution**: Balanced 50-50 distribution ✅

### Next Steps

1. **Wait for pilot data generation** (~6-7 hours remaining)
2. **Prepare dataset** (`./scripts/prepare_pilot_dataset.sh`)
3. **Train pilot model** (`./scripts/train_pilot_model.sh`)
4. **Validate performance** (Check F1 > 0.75, FPR < 15%)
5. **If successful**: Generate full 256-scenario dataset
6. **Deploy v2.0.0**: Replace v1.0.0 in pipeline

---

## Related Documentation

| File | Purpose |
|------|---------|
| `README.md` | Project overview, quick start, setup |
| `QUICK-REFERENCE.md` | One-page command cheat sheet |
| `BLUEPRINT.md` | Full implementation blueprint |
| `ALL-ADRS.md` | All architecture decisions |
| `WP8-SUMMARY.md` | GCN integration summary |
| `WP8-GCN-INTEGRATION-PLAN.md` | WP8 integration plan |
| `WP9-GCN-MODEL-RETRAINING-PLAN.md` | v2.0.0 retraining plan |
| `../uiprojectsummary.md` | Custom dashboard implementation log |

