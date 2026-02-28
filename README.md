# NDT Wi-Fi 7 MLO Security — Network Digital Twin

A production-grade **Network Digital Twin (NDT)** for Wi-Fi 7 / Multi-Link Operation (MLO) security research. Detects backoff manipulation attacks in real-time using a Graph Convolutional Network (GCN) and visualises results through both a Grafana analytics layer and a custom neumorphic web dashboard.

---

## What This Is

This platform simulates Wi-Fi 7 MLO traffic with [ns-3](https://www.nsnam.org/), streams telemetry through a Kafka-based pipeline, runs GCN-based attack detection, and surfaces everything in a live dashboard.

```
NS-3 Simulation
      │
      ▼
telemetry.jsonl  (13 metrics, 260+ events/run)
      │
      ▼
Exporter ──► Redpanda (Kafka API) ──► Harmonizer ──► TimescaleDB
                                                          │
                                       Windowizer ◄───────┘
                                     (256-window segments)
                                            │
                                            ▼
                                       GCN Detector v2.0.0
                                            │
                 ┌──────────────────────────┤
                 ▼                          ▼
          Grafana :3000          Custom Dashboard :8888
      (analytics + history)   (real-time pipeline monitor)
```

**Attack types simulated:**

| Scenario | Backoff Bias | Observed Effect |
|----------|-------------|-----------------|
| Normal | 0 | Baseline Wi-Fi 7 MLO behaviour |
| Positive attack | +5000 | +285× backoff slots, −84% throughput |
| Negative attack | −5000 | −56% backoff slots, −44% throughput |

**GCN model (v2.0.0):** 2-layer GCN · 256-window segments · 13 features · trained on 284 balanced scenarios · binary classifier (normal / attack)

---

## Prerequisites

| Dependency | Version | Purpose |
|------------|---------|---------|
| Docker | 24+ | All containers |
| Docker Compose | v2 | Orchestration |
| [Containerlab](https://containerlab.dev/) | 0.56+ | Network topology |
| GNU Make | any | Task runner |
| ~10 GB disk | — | ns-3 image + artifacts |
| ~4 GB RAM free | — | Pipeline services |

Install Containerlab:
```bash
bash -c "$(curl -sL https://get.containerlab.dev)"
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone git@github.com:<your-org>/ndt-wifi7-mlo-security.git
cd ndt-wifi7-mlo-security
```

### 2. Build all images

```bash
make ns3-build          # ns-3.46.1 Wi-Fi 7 simulator  (~3–5 min)
make exporter-build     # Telemetry file → Kafka exporter
make harmonizer-build   # Kafka → TimescaleDB harmonizer
make windowizer-build   # Telemetry → 256-window segments
make gcn-detector-build # GCN attack detection inference
make dashboard-build    # FastAPI + React custom dashboard
```

### 3. Start the infrastructure

```bash
make up             # Deploy Containerlab topology
                    # Starts: TimescaleDB :5432, Redpanda :9092, Grafana :3000
make pipeline-up    # Start harmonizer + windowizer + GCN detector (background)
make dashboard-up   # Start custom dashboard on :8888
```

### 4. Run your first experiment

```bash
EXP_ID="$(date +%Y%m%d-%H%M)-mlo-normal-42"
make run-mlo-exp EXP_ID=$EXP_ID SCENARIO=normal
```

### 5. Open the dashboards

| Dashboard | URL | What you see |
|-----------|-----|-------------|
| **Custom Dashboard** | http://localhost:8888 | Real-time pipeline, GCN predictions, attack analysis |
| **Grafana** | http://localhost:3000 | Historical analytics, metric trends, unified view |

Default Grafana credentials: `admin` / `admin`

---

## Running Attack Scenarios

### Individual scenarios

```bash
# Baseline (no attack)
make run-mlo-exp EXP_ID="$(date +%Y%m%d-%H%M)-mlo-normal-42"   SCENARIO=normal

# Positive attack (+5000 bias → backoff starvation)
make run-mlo-exp EXP_ID="$(date +%Y%m%d-%H%M)-mlo-attack-pos"  SCENARIO=positive

# Negative attack (-5000 bias → aggressive channel access)
make run-mlo-exp EXP_ID="$(date +%Y%m%d-%H%M)-mlo-attack-neg"  SCENARIO=negative
```

### Batch run — all three scenarios at once

```bash
bash run_scenarios.sh
```

### Experiment ID format

```
YYYYMMDD-HHMM-<scenario>-<seed>
Example: 20260228-1400-mlo-normal-42
```

After each run, predictions appear in the custom dashboard's **Pipeline Monitor** activity feed and in Grafana's unified dashboard within seconds.

---

## Custom Dashboard (Port 8888)

A React 18 + FastAPI application with a **Soft UI / Neumorphism** design. Served from Docker, it connects live to TimescaleDB via WebSocket (2-second poll).

### Six sections

| Section | What it shows |
|---------|---------------|
| **Pipeline Monitor** | Live stage status (NS-3 → Exporter → Kafka → Windowizer → GCN → DB), per-stage counters, real-time activity feed |
| **Experiment View** | KPI cards (segments, attack rate, confidence), metric evolution chart, segment-level prediction table |
| **Model Intelligence** | F1 / accuracy / precision / recall / AUC bar chart, confusion matrix, inference latency percentiles, model registry list |
| **Run History** | All experiments with pass/fail indicator, attack-rate bar chart, sortable table |
| **Attack Analysis** | TP / TN / FP / FN breakdown, confidence histogram (normal vs attack), detection rate by experiment type |
| **Network Health** | All 13 telemetry metrics with trend arrows; click any card to expand the time-series chart |

### Dashboard commands

```bash
make dashboard-build    # Build Docker image (ndt/dashboard:local)
make dashboard-up       # Start on http://localhost:8888
make dashboard-down     # Stop
make dashboard-logs     # Follow live logs
make dashboard-status   # Status + recent log lines
```

---

## Grafana Dashboards (Port 3000)

### Unified dashboard — 38 panels

URL: `http://localhost:3000/d/ndt-unified`

Covers: pipeline stage counters · active GCN model version · experiment run history with attack rates · GCN predictions timeline · per-experiment metric drill-down · model performance summary (F1, accuracy, confusion matrix) · all 13 raw telemetry metrics

### Template variables

| Variable | Purpose |
|----------|---------|
| `run_prefix` | Filter experiments by name prefix (`%` = show all) |
| `model_version` | Filter predictions by model version |
| `experiment_selector` | Select one experiment for drill-down charts |

---

## GCN Attack Detection

### How it works

1. **Windowizer** reads raw telemetry from Kafka topic `wifi7.telemetry.v0_1`, applies delta conversion on cumulative counters, buffers 256-event windows, and publishes feature vectors to `wifi7.ml.windowed_features.v1`
2. **GCN Detector** reads windowed feature vectors, runs inference with the active model (`twin/registry/gcn/current`), and writes predictions to `gcn_predictions` in TimescaleDB
3. **Custom dashboard** queries predictions every 2 seconds via WebSocket; Grafana dashboards refresh every 10 seconds

### GCN model v2.0.0 (production)

```
Architecture:   2-layer Graph Convolutional Network (GCN)
Window size:    256 samples per segment
Features:       13 (backoff_slots, throughput_mbps, packet_loss_rate,
                    delay_ms, channel_busy_ratio, retry_count,
                    link1_usage, link2_usage, mcs_index, rssi_dbm,
                    snr_db, queue_depth, jitter_ms)
Classes:        0 = normal traffic  /  1 = backoff manipulation attack
Training data:  284 scenarios, balanced 50-50 (normal / attack)
Data source:    Pipeline-generated (matches production distribution)
Bias coverage:  50 → 10,000 (all subtlety levels)
```

### Model registry

```
twin/registry/gcn/
├── current          → v2.0.0   (active version symlink)
├── v1.0.0/          Original baseline model
└── v2.0.0/          Production model (balanced, pipeline-trained)
    ├── best_model.pt
    ├── scaler.json
    ├── config.yaml
    └── test_results.json
```

Deploy a new version:
```bash
make gcn-deploy VERSION=v2.0.0
```

---

## Full Command Reference

### Infrastructure

```bash
make up              # Deploy Containerlab (DB, Redpanda, Grafana)
make down            # Destroy Containerlab
make status          # Check container status
make logs            # Tail all logs
```

### Pipeline services

```bash
make pipeline-up        # Start harmonizer in background
make pipeline-down      # Stop harmonizer
make pipeline-status    # Logs and status

make gcn-up             # Start windowizer + GCN detector
make gcn-down           # Stop windowizer + GCN detector
make gcn-status         # Logs and status
```

### Experiments

```bash
make run-exp EXP_ID=...                         # ns-3 + export + ingest (generic)
make run-mlo-exp EXP_ID=... SCENARIO=normal     # MLO normal traffic
make run-mlo-exp EXP_ID=... SCENARIO=positive   # MLO positive attack
make run-mlo-exp EXP_ID=... SCENARIO=negative   # MLO negative attack
bash run_scenarios.sh                           # All three scenarios
```

### Build

```bash
make ns3-build           # ns-3.46.1 image
make exporter-build      # Exporter image
make harmonizer-build    # Harmonizer image
make windowizer-build    # Windowizer image
make gcn-detector-build  # GCN detector image
make dashboard-build     # Custom dashboard image
```

### Dashboard

```bash
make dashboard-up        # http://localhost:8888
make dashboard-down
make dashboard-logs
make dashboard-status
```

### Database

```bash
# Connect
docker exec -it clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr

# Useful queries
SELECT COUNT(*) FROM metrics;
SELECT COUNT(*) FROM gcn_predictions;
SELECT experiment_id, COUNT(*) AS segs,
       ROUND(AVG(confidence)::numeric,3) AS avg_conf
  FROM gcn_predictions GROUP BY experiment_id ORDER BY 1;

# Fresh start (clears data, not training artifacts)
TRUNCATE metrics; TRUNCATE gcn_predictions;
```

---

## Project Structure

```
ndt-wifi7-mlo-security/
├── clab/
│   ├── topo.yml                         # Containerlab topology
│   └── configs/
│       ├── grafana/dashboards/          # ndt-unified.json (38 panels)
│       └── udr-db/initdb/              # DB schema migrations (003_gcn_schema.sql)
├── sim/ns3/
│   ├── scenario/                        # Wi-Fi 7 MLO C++ scenarios + run scripts
│   └── artifacts/<EXP_ID>/              # telemetry.jsonl, logs (gitignored)
├── telemetry/
│   ├── exporters/ns3_file_exporter/     # File → Kafka exporter
│   └── harmonizer/                      # Kafka → TimescaleDB
├── security/detector/windowizer/        # 256-window segmentation service
├── twin/
│   ├── gnn/detector/                    # GCN inference service
│   ├── gnn/trainer/                     # Model training pipeline
│   └── registry/gcn/                    # Model version registry
│       ├── current -> v2.0.0            # Active symlink
│       ├── v1.0.0/                      # Baseline model
│       └── v2.0.0/                      # Production model
├── dashboard/app/                       # Custom web dashboard
│   ├── Dockerfile                       # Multi-stage: Node 20 → Python 3.11
│   ├── backend/                         # FastAPI + asyncpg (Python)
│   └── frontend/                        # React 18 + Vite + Recharts
├── docker-compose.pipeline.yml          # Harmonizer + Windowizer + GCN
├── docker-compose.dashboard.yml         # Custom dashboard
├── run_scenarios.sh                     # Batch scenario runner
├── training_data/                       # GCN training data (gitignored)
├── docs/
│   ├── CURRENT-STATE.md                 # ← Authoritative project state
│   ├── QUICK-REFERENCE.md               # Command cheat sheet
│   ├── BLUEPRINT.md                     # Full implementation plan
│   ├── ALL-ADRS.md                      # Architecture decisions
│   └── WP*.md                           # Per-work-package documentation
├── uiprojectsummary.md                  # Custom dashboard implementation log
└── Makefile
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Exporter publishes nothing | `rm -f .exporter_state/exporter_state.json` then re-run |
| Harmonizer: no DB rows | Use a new consumer group with `AUTO_OFFSET_RESET=earliest` |
| GCN detector: no predictions | Verify Windowizer is running and consuming telemetry |
| Grafana: no data | Check time range — simulation timestamps are historical (use "Last 1 year" or absolute range) |
| Dashboard: `db: unavailable` | Run `make up` first; the `clab-mgmt` network must exist |
| Permission denied on artifacts | Add `--user "$(id -u):$(id -g)"` to docker run |
| Port already in use | Check 3000, 5432, 8888, 9092 are free before `make up` |

---

## Work Package Status

| WP | Description | Status |
|----|-------------|--------|
| WP1 | Local dev setup, GitHub SSH | ✅ Complete |
| WP2 | Containerlab skeleton (DB, Kafka, Grafana) | ✅ Complete |
| WP3 | ns-3.46.1 Wi-Fi 7 simulation + telemetry | ✅ Complete |
| WP4 | Telemetry exporter (file → Kafka) | ✅ Complete |
| WP5 | Harmonizer (Kafka → TimescaleDB) | ✅ Complete |
| WP6 | Grafana provisioning-as-code | ✅ Complete |
| WP7 | One-command pipeline (`make run-exp`) | ✅ Complete |
| WP7.5 | Exporter reliability + MLO attack scenarios | ✅ Complete |
| WP8 | GCN attack detection (Windowizer + GCN Detector) | ✅ Complete |
| WP9 | GCN model v2.0.0 retraining (284 balanced scenarios) | ✅ Complete |
| WP9.5 | Unified Grafana dashboard (38 panels, 3 variables) | ✅ Complete |
| WP10 | Custom web dashboard (React 18 + FastAPI, port 8888) | ✅ Complete |

---

## Documentation Index

| File | Purpose |
|------|---------|
| `docs/CURRENT-STATE.md` | Complete authoritative project state |
| `docs/QUICK-REFERENCE.md` | One-page command cheat sheet |
| `docs/BLUEPRINT.md` | Full implementation blueprint |
| `docs/ALL-ADRS.md` | All architecture decisions |
| `docs/WP8-SUMMARY.md` | GCN integration details |
| `docs/WP9-GCN-MODEL-RETRAINING-PLAN.md` | v2.0.0 model retraining plan |
| `uiprojectsummary.md` | Custom dashboard implementation log |
