# Wi-Fi 7 / MLO Network Digital Twin - Full Implementation Blueprint

## Document Purpose
This document is the complete implementation blueprint for the NDT Wi-Fi 7 MLO Security project. It defines the architecture, components, implementation order, and acceptance criteria for the entire system.

---

## 1. Project Overview

### 1.1 Executive Summary
This project designs and implements a Network Digital Twin (NDT) platform for Wi-Fi 7 (802.11be) with Multi-Link Operation (MLO), focused on detecting, predicting, and mitigating MLO backoff manipulation and related fairness or denial-of-service behaviors.

### 1.2 Core Components
- Real or simulated Wi-Fi 7 fabric (ns-3)
- Telemetry ingestion and harmonization into UDR/UDM
- Simulator federation layer
- AI workflow (GNN-based twin + DL/RL security automation)
- NDT orchestration and closed-loop control (MANO/ZSM principles)
- Actuation back to controllers/APs with guardrails
- Continuous feedback and model improvement

---

## 2. Glossary

| Term | Definition |
|------|------------|
| **Wi-Fi 7 (802.11be / EHT)** | Next generation Wi-Fi standard supporting 320 MHz channels, multi-link, puncturing, and higher modulation schemes |
| **MLO (Multi-Link Operation)** | Station and AP coordinate multiple links (bands/channels) simultaneously |
| **MLD (Multi-Link Device)** | Wi-Fi 7 device supporting MLO |
| **NDT (Network Digital Twin)** | Continuously synchronized digital representation of a live network |
| **UDR (Unified Data Repository)** | Central storage for telemetry, topology, configuration, and simulation outputs |
| **UDM (Unified Data Model)** | Standardized schema and semantics for all data |
| **Harmonizer** | Component that maps vendor/simulator counters into UDM |
| **GNN (Graph Neural Network)** | ML model for graph-structured network data |
| **MANO** | Management and Orchestration for NDT lifecycle |
| **ZSM (Zero-touch Service Management)** | Closed-loop automation framework |
| **Closed Loop** | Observe → Decide → Act → Learn cycle |

---

## 3. Research Questions

- **RQ1:** Can a GNN-based NDT predict per-flow delay, loss, and jitter for Wi-Fi 7 MLO scenarios with acceptable error?
- **RQ2:** Can security analytics reliably detect MLO backoff manipulation patterns?
- **RQ3:** Can a closed-loop policy engine restore fairness under attack while maintaining stability?
- **RQ4:** What is the end-to-end latency of the observe → decide → act → learn loop?

---

## 4. Repository Structure

```
ndt-wifi7-mlo-security/
├── clab/                         # Containerlab topology + node configs
│   ├── topo.yml
│   └── configs/                  # FRR, Kafka, DB, Grafana configs
├── sim/
│   └── ns3/
│       ├── scenario/             # ns-3 code (C++) and run scripts
│       ├── traces/               # trace-to-json generator
│       └── artifacts/            # local outputs (gitignored)
├── telemetry/
│   ├── exporters/                # sidecar exporters (python)
│   ├── contracts/                # message schemas + versioning
│   └── harmonizer/               # raw -> UDM mapping, validators
├── udr/
│   ├── db/                       # migrations, schemas, hypertables
│   ├── api/                      # REST/gRPC service
│   └── feature_store/            # windowed aggregates jobs
├── security/
│   ├── detector/                 # baseline + DL later
│   ├── policy/                   # intent selection + constraints
│   └── actuation/                # sim-only actuation adapter
├── twin/
│   ├── gnn/                      # training + inference service
│   └── registry/                 # model metadata/versioning
├── dashboard/
│   ├── grafana/                  # dashboards JSON, provisioning
│   └── app/                      # optional custom UI
├── experiments/
│   ├── scenarios/                # experiment matrix definitions
│   ├── runner/                   # run orchestration scripts
│   └── results/                  # generated results (gitignored)
├── docs/
│   ├── adr/                      # architecture decisions
│   └── runbooks/                 # how to run, debug, contribute
├── docker/                       # Dockerfiles for each component
├── .claude/                      # Claude Code agent configuration
├── Makefile
└── .github/workflows/            # CI
```

---

## 5. System Architecture

### 5.1 High-Level Flow

```
Physical/Simulated Wi-Fi 7 Fabric (ns-3)
    │
    ▼
Telemetry Exporters + Harmonization
    │
    ▼
Unified Data Repository (UDR) + Unified Data Model (UDM)
    │
    ├──────────────────┬──────────────────┐
    ▼                  ▼                  ▼
AI Workflow      Simulation         NDT MANO +
(GNN Twin +      Framework          ZSM Closed
DL/RL Security)  (ns-3)             Loops
    │                  │                  │
    └──────────────────┴──────────────────┘
                       │
                       ▼
              Actuation on Controllers/APs
                       │
                       ▼
              Closed-Loop Feedback
                       │
                       ▼
              Unified Dashboard (Grafana)
```

### 5.2 Two-Layer Runtime Architecture

**Layer 1: Lab Services (Containerlab)**
- Postgres/TimescaleDB (UDR)
- Redpanda (Kafka API)
- Grafana
- Harmonizer
- Exporter

**Layer 2: Simulation (Separate Container)**
- ns-3 runner
- Produces telemetry artifacts
- Does not depend on containerlab directly

**Interface Contract:**
- JSONL telemetry file per run (`telemetry.jsonl`)
- Exported to Kafka, then to DB

---

## 6. Data Collection Framework

### 6.1 What to Collect (Wi-Fi 7 / MLO)
- Per-link RSSI, SNR
- EHT MCS and RU allocation maps
- Puncturing usage
- BSS coloring density, OBSS-PD events
- Channel utilization
- Per-AC queue stats (length, drops, dequeue rates)
- Retries, PER, FEC indicators
- EMLSR and MLO decisions, link failovers
- DFS and mute windows
- Deauth and disassoc counters
- L2 and L3 counters
- Controller logs and policy events

### 6.2 Telemetry Contract (v0.1)

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

### 6.3 Kafka Topics
- `wifi7.telemetry.v0_1` - Main telemetry topic
- Future: `wifi7.rf.perlink`, `wifi7.mlo.events`, `wifi7.mac.qos`, `wifi7.security.signals`

---

## 7. UDR Database Schema

### 7.1 metrics Table (Hypertable)
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

### 7.2 snapshots Table
```sql
CREATE TABLE snapshots (
    experiment_id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    topology_json JSONB,
    config_json JSONB,
    git_sha TEXT,
    ns3_version TEXT,
    schema_version TEXT
);
```

### 7.3 Future Tables
- `events` - MLO events, security alerts
- `intents` - Policy actions and results
- `features` - Windowed aggregates for ML

---

## 8. Work Package Definitions

### WP1: Local Dev Setup
- GitHub SSH access
- Repository creation
- Basic tooling

### WP2: Containerlab Skeleton
- `clab/topo.yml` with services
- Postgres/TimescaleDB
- Grafana provisioning
- Makefile targets

### WP3: ns-3 Integration
- ns-3.46.1 container
- Baseline Wi-Fi scenario
- Telemetry JSONL output
- Artifact structure

### WP4: Telemetry Exporter
- File → Kafka exporter
- Telemetry contract v0.1
- Per-file offset tracking

### WP5: Harmonizer
- Kafka → DB ingestion
- Schema validation
- Idempotent upserts

### WP6: Grafana Dashboards
- Datasource provisioning
- Basic metrics visualization
- Multi-experiment comparison

### WP7: One-Command Pipeline
- Long-running services
- `make pipeline-up/down`
- `make run-exp`

### WP8: Multi-Scenario Support
- Scenario registry
- Scenario parameter in telemetry
- Makefile scenario selector

### WP9: Enhanced Telemetry Model
- Additional labels/fields
- DB schema extension
- Grafana variables

### WP10: Production Hygiene
- State management
- Git hygiene
- Health checks

### WP11: CI/CD
- GitHub Actions
- Image builds
- Pipeline tests

### WP12+: AI/Security
- Feature store
- Baseline detector
- Policy engine
- GNN twin
- Closed-loop actuation

---

## 9. Implementation Order (Critical Path)

```
1. Lab up (Containerlab + Kafka + DB + Grafana)
2. ns-3 baseline outputs JSONL
3. Exporter publishes to Kafka
4. Harmonizer writes to UDR
5. Feature store
6. Attack scenarios + dataset
7. Baseline detector
8. Policy + actuation + rollback
9. Dashboard polished
10. GNN twin training + inference
11. Full evaluation harness
```

---

## 10. Evaluation Metrics

### 10.1 Twin Prediction Accuracy
- Delay prediction error (MAPE/MAE)
- Loss prediction error
- Jitter prediction error
- Generalization to unseen topologies

### 10.2 Detection Quality
- Precision, Recall, F1
- ROC-AUC
- Mean Time to Detect (MTTD)

### 10.3 Mitigation Effectiveness
- Throughput retained under attack
- Fairness restored (Jain's index)
- Time to recover
- Oscillation/rollback frequency

### 10.4 System Overhead
- CPU/memory of twin inference
- Telemetry overhead
- End-to-end loop latency

---

## 11. Key Commands Reference

```bash
# Containerlab
make up                    # Deploy lab
make down                  # Destroy lab
make status                # Check status
make logs                  # View logs

# ns-3
make ns3-build             # Build ns-3 image
make ns3-run EXP_ID=...    # Run baseline
make ns3-run-example EXP_ID=...  # Run wifi example

# Pipeline
make exporter-build        # Build exporter image
make exporter-run EXP_ID=...     # Run exporter
make harmonizer-build      # Build harmonizer image
make harmonizer-run        # Run harmonizer

# Combined (WP7+)
make pipeline-up           # Start all services
make run-exp EXP_ID=... SCENARIO=...  # Run experiment
make pipeline-down         # Stop all services

# Verification
docker exec -it clab-...-udr-db psql -U udr -d udr -c "SELECT * FROM metrics LIMIT 5;"
docker exec -it clab-...-bus-redpanda rpk topic consume wifi7.telemetry.v0_1 -n 5
```

---

## 12. Versioning Conventions

- **Schema versions:** `telemetry/contracts/v0.1/`, `v0.2/`, etc.
- **Experiment IDs:** `YYYYMMDD-HHMM-<scenario>-<seed>`
- **Model versions:** `twin/registry/<model>/<date>-<git_sha>.json`

---

## 13. Git Workflow

- **main:** Always runnable
- **Feature branches:** `feat/<wp>-<description>`
- **PR required** with:
  - Updated runbook note
  - "How to test" section
  - Evidence screenshot/log

---

## 14. Timeline

### Semester 7
- Architecture finalized
- Threat model and requirements
- Containerlab backbone
- Basic ns-3 Wi-Fi 7 MLO scenario
- Telemetry pipeline to UDR

### Semester 8
- GNN twin prototype
- Anomaly detector
- Full attack scenarios
- Closed-loop with ZSM
- Final dissertation and demo
