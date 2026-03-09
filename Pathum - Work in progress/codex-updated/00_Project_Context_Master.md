# Project Context Master (Updated)

## 1. Snapshot and Purpose

- **Project**: `ndt-wifi7-mlo-security`
- **Primary research theme**: Digital twin-based threat prediction for **Wi-Fi 7 MLO backoff manipulation**
- **Snapshot date**: 2026-03-09
- **This file is for**: giving another AI (or reviewer) a complete and accurate technical context to draft your final report/research paper.

This repository is a full-stack experimental platform that combines:
1. Wi-Fi 7 MLO simulation in ns-3.
2. Telemetry streaming through Kafka/Redpanda.
3. TimescaleDB storage and analytics.
4. GCN-based attack detection.
5. Grafana + custom React/FastAPI dashboard visualization.

---

## 2. Core Research Problem

Your literature review frames a clear gap:

- Wi-Fi 7 MLO introduces complex stateful MAC behavior (packet steering, multi-link coordination, per-link backoff interactions).
- Existing work emphasizes throughput/latency optimization, not adversarial exploitation of these mechanisms.
- Backoff manipulation is treated as a performance anomaly in prior work, but can be weaponized as a security exploit.
- Existing digital twin work is mostly operations/performance-oriented, not high-fidelity security threat prediction for MLO attack patterns.

### Practical research question represented by this codebase

Can an NDT pipeline ingest real/simulated Wi-Fi 7 MLO telemetry and detect backoff-manipulation attacks in near real time, with acceptable false-positive behavior for operational use?

---

## 3. System Implemented (End-to-End)

## 3.1 Infrastructure Layer

- **Containerlab topology** (`clab/topo.yml`) starts:
  - `bus-redpanda` (Kafka API, port 9092)
  - `udr-db` (TimescaleDB/Postgres, port 5432)
  - `grafana` (port 3000)
- Shared Docker network: `clab-mgmt`

## 3.2 Simulation Layer

- ns-3 Wi-Fi 7 MLO scenarios in:
  - `sim/ns3/scratch/wifi7-mlo-Normal.cc`
  - `sim/ns3/scratch/wifi7-mlo-Positive.cc`
  - `sim/ns3/scratch/wifi7-mlo-Negative.cc`
- Scenario launcher:
  - `sim/ns3/scenario/run_mlo_scenario.sh`
- Converts ns-3 JSON window output to telemetry contract JSONL:
  - `sim/ns3/scenario/convert_mlo_json_to_jsonl.sh`

## 3.3 Telemetry Pipeline

1. **Exporter** (`telemetry/exporters/ns3_file_exporter/exporter.py`)
   - Reads `telemetry.jsonl` from `sim/ns3/artifacts/<EXP_ID>/`.
   - Publishes to topic `wifi7.telemetry.v0_1`.
   - Uses deterministic key: `experiment_id|entity_id|metric|ts`.
   - Uses **counter-based delivery confirmation** and state file offsets.

2. **Harmonizer** (`telemetry/harmonizer/harmonizer.py`)
   - Consumes telemetry topic.
   - Validates payload.
   - Upserts to `public.metrics` in TimescaleDB.

3. **Windowizer** (`security/detector/windowizer/*.py`)
   - Aggregates per-metric events into complete windows.
   - Fills missing metrics per strategy.
   - Converts cumulative counters to delta features.
   - Buffers into fixed length segments (`segment_length=256`).
   - Publishes to `wifi7.ml.windowed_features.v1`.

4. **GCN Detector** (`twin/gnn/detector/*.py`)
   - Loads model artifacts from `twin/registry/gcn/<version>/`.
   - Builds temporal graph per segment.
   - Applies scaler + feature processor.
   - Infers class (0 normal, 1 attack).
   - Writes results to Kafka and `public.gcn_predictions`.

## 3.4 Visualization Layer

- **Grafana** dashboards (pre-provisioned JSON):
  - Unified dashboard (`ndt-unified`)
  - GCN dashboard (`gcn-attack-detection`)
  - MLO scenario dashboard (`mlo-attack-scenarios`)
- **Custom dashboard** (`dashboard/app`) on port 8888:
  - FastAPI backend + React frontend + WebSocket feed.
  - Sections: Pipeline, Experiment, Model, Run History, Attack Analysis, Network Health.

---

## 4. Data and Feature Model

## 4.1 Raw telemetry contract

Each metric event includes:
- `experiment_id`, `ts`, `source`, `schema_version`, `entity_id`, `metric`, `value`, `unit`

## 4.2 Metrics collected (13 key metrics)

- `net_throughput_mbps`
- `net_avg_delay_ms`
- `net_avg_jitter_ms`
- `net_packet_loss_ratio`
- `net_active_flows`
- `mac_total_tx`
- `mac_total_rx`
- `mac_total_ack`
- `mac_total_retrans`
- `mac_drop_count`
- `phy_drop_count`
- `avg_backoff_slots`
- `channel_busy_ratio`

## 4.3 Windowizer/detector feature alignment

Cumulative MAC/PHY counters are converted to delta fields for model compatibility:
- `mac_total_tx` -> `mac_tx_delta`
- `mac_total_rx` -> `mac_rx_delta`
- `mac_total_ack` -> `mac_ack_delta`
- `mac_total_retrans` -> `mac_retrans_delta`
- `mac_drop_count` -> `mac_drop_delta`
- `phy_drop_count` -> `phy_drop_delta`

Derived features in detector:
- `retrans_rate`
- `drop_rate`
- `throughput_per_flow`

Total model input dimension in practice: **16 features**.

---

## 5. Attack Modeling Logic in Simulations

Your MLO notes and C++ scripts show this design:

- Attack manipulates **minimum contention window (MinCw)** through bias.
- Positive bias increases waiting/aggressiveness penalty.
- Negative bias decreases contention window (more aggressive access).
- Negative-bias underflow bug was handled with clamp logic (`newCw=0` floor).

Scenario orchestration from `run_mlo_scenario.sh`:
- `normal` default bias `0`
- `positive` default bias `+5000`
- `negative` default bias `-5000`

JSON window output is converted to JSONL and then fed to pipeline.

---

## 6. Key Experimental/Engineering Milestones (from docs)

- **WP1-WP7**: baseline infra, ns-3 integration, exporter/harmonizer, one-command pipeline.
- **WP7.5**: attack scenario integration and exporter reliability hardening.
- **WP8**: windowizer + GCN detector integration.
- **WP9**: retraining plans and production model iteration.
- **WP10**: dashboard and operational troubleshooting.

### Important observed progression

1. Early integrated tests reported good plumbing but high false positives.
2. Field-name mismatches between windowizer output and detector inputs were fixed.
3. Additional retraining/deployment docs report v2.1.0 improvements.
4. Root-cause documents then identify training-distribution mismatch as a deeper problem (normal traffic distribution realism issue).

This means your paper can present a realistic engineering story:
- It was not a single clean success.
- It was iterative debugging across data contract, feature contract, and model generalization.

---

## 7. New Files You Added and How They Fit

You added `Pathum - Work in progress/Readme-Files` with 3 groups:

## 7.1 `Datasets/`

These files document:
- dataset schema consistency,
- descriptive statistics differences between normal and attack,
- anomaly signatures (delay/loss/throughput/backoff shifts),
- class-imbalance and data quality commentary.

## 7.2 `GNNs/`

These files capture:
- GNN methodology narrative (graph windows, feature vectors, classification),
- coding-quality interpretation,
- iterative experimental logging mindset,
- replication guide language.

## 7.3 `MLOs/`

These files capture:
- project-level simulation rationale,
- scenario script mechanics,
- KPI instrumentation methodology,
- code evolution narrative,
- reproducibility guidance for backoff manipulation modeling.

These are highly useful for your thesis/report narrative chapters because they convert code details into explainable prose.

---

## 8. Current Dataset Artifacts in Repository

### 8.1 Pilot dataset folder (`training_data`)

Observed local counts:
- `normal`: 14 JSON files
- `positive_attack`: 8 JSON files
- `negative_attack`: 7 JSON files
- **Total**: 29 JSON files

Pilot manifest (`training_data/manifest_pilot.csv`) also lists 29 scenarios.

### 8.2 Extended dataset folder (`training_data_extended`)

Observed local counts:
- `normal`: 123 JSON files
- `positive_attack`: 68 JSON files
- `negative_attack`: 64 JSON files
- **Total**: 255 JSON files

Extended manifest groups to:
- `normal=123`, `positive=70`, `negative=64`, `total=257`

Interpretation:
- There are small consistency gaps between folder contents and manifest counts (255 vs 257).
- Training-prep scripts in repo reference combined totals around 284 scenarios (pilot+extended).

For paper writing, report this as an implementation-reality point: manifests and final staged files are close but not perfectly synchronized.

---

## 9. Model Registry and Versioning State

Registry folders present:
- `v1.0.0`
- `v2.0.0`
- `v2.1.0`

Important nuance:
- `twin/registry/gcn/current` in this workspace is a plain text file with `v2.0.0` rather than a symlink.
- Backend dashboard reader supports file-based current-version fallback.
- Detector `ModelLoader` is symlink-oriented but can still read direct version paths when configured explicitly.

Test metric files in `v1.0.0`, `v2.0.0`, `v2.1.0` appear identical in this checkout (same JSON metrics), while docs narrate distinct performance behavior across versions. That mismatch should be treated carefully in final claims.

---

## 10. Known Inconsistencies and Residual Risks (Important for Report Integrity)

Use this section explicitly in your limitations/threats-to-validity.

1. **Documentation drift**:
- Some README/status docs still say components are “not started” while code exists.

2. **Model narrative drift**:
- Different docs claim different active/best versions and outcomes (v2.0.0 vs v2.1.0 vs retrain-required).

3. **Dataset count drift**:
- Pilot/extended manifests vs actual copied JSON counts are slightly inconsistent.

4. **Front-end/back-end API naming mismatches in current code**:
- Some frontend hooks expect routes/field names that differ from backend route names (hyphen vs underscore, response key differences).

5. **Symlink portability issue**:
- Registry `current` being file-based in Windows checkout can behave differently from Linux symlink assumptions.

These do not invalidate the project, but they matter for transparent reporting.

---

## 11. What Your Final Paper Can Strongly Claim

Given the repository evidence, your strongest defensible claims are:

1. A complete digital-twin pipeline for Wi-Fi 7 MLO telemetry-to-detection was implemented.
2. Backoff manipulation can be represented as controlled bias in ns-3 and traced through MAC/PHY/network KPIs.
3. The project produced a substantial iterative workflow across simulation, data engineering, ML inference, and dashboard observability.
4. False-positive behavior and distribution-shift issues were actively diagnosed at pipeline and model levels.
5. The project demonstrates both technical feasibility and practical challenges of security-focused NDT for Wi-Fi 7 MLO.

---

## 12. Recommended Structure for Final Report/Paper (Aligned to This Repo)

1. Introduction and motivation (Wi-Fi 7 MLO complexity + security gap)
2. Literature synthesis (your PDF + added notes)
3. Digital twin architecture and implementation
4. Attack model and simulation methodology
5. Telemetry/feature engineering and data pipeline
6. GCN model design and deployment lifecycle
7. Experimental results + debugging chronology
8. Threats to validity / limitations / reproducibility
9. Conclusion and future work

---

## 13. Reproducibility Command Backbone (from project workflow)

- `make up`
- `make pipeline-up`
- `make gcn-up`
- `make dashboard-up`
- `make run-mlo-exp EXP_ID=<...> SCENARIO=normal|positive|negative`
- `make pipeline-status`
- `make gcn-status`
- `make dashboard-status`

Stop stack:
- `make gcn-down`
- `make dashboard-down`
- `make pipeline-down`
- `make down`

