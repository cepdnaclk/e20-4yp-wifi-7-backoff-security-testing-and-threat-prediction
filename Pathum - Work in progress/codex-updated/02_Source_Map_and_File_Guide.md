# Source Map and File Guide (Updated)

Use this file as a navigation index when drafting the final report.

## 1. Top-Level Orientation

- `README.md`: project-level architecture and command flow.
- `Makefile`: operational command backbone (build/run/stop).
- `run_scenarios.sh`: replay-style scenario runner with DB report.

---

## 2. Infrastructure and Data Plane

- `clab/topo.yml`: containerlab services and exposed ports.
- `docker-compose.pipeline.yml`: harmonizer + windowizer + detector runtime services.
- `docker-compose.dashboard.yml`: custom dashboard service.

DB schema:
- `clab/configs/udr-db/initdb/001-init.sql` (metrics table + hypertable)
- `clab/configs/udr-db/initdb/002_metrics_constraints.sql` (idempotency indexes)
- `clab/configs/udr-db/initdb/003_gcn_schema.sql` (gcn_predictions + model_registry)

---

## 3. Simulation and Scenario Logic

Scenario scripts:
- `sim/ns3/scenario/run_mlo_scenario.sh`
- `sim/ns3/scenario/convert_mlo_json_to_jsonl.sh`
- `sim/ns3/scenario/run_wifi_example_and_export.sh`

ns-3 MLO C++ files:
- `sim/ns3/scratch/wifi7-mlo-Normal.cc`
- `sim/ns3/scratch/wifi7-mlo-Positive.cc`
- `sim/ns3/scratch/wifi7-mlo-Negative.cc`

What to extract for paper:
- network topology assumptions,
- bias injection mechanism,
- KPI trace instrumentation,
- window interval and simulation-time settings.

---

## 4. Telemetry Pipeline Components

Exporter:
- `telemetry/exporters/ns3_file_exporter/exporter.py`

Harmonizer:
- `telemetry/harmonizer/harmonizer.py`

Windowizer:
- `security/detector/windowizer/windowizer.py`
- `security/detector/windowizer/window_aggregator.py`
- `security/detector/windowizer/delta_converter.py`
- `security/detector/windowizer/segment_builder.py`
- `security/detector/windowizer/kafka_client.py`
- `security/detector/windowizer/config.yaml`

GCN detector:
- `twin/gnn/detector/detector.py`
- `twin/gnn/detector/model_loader.py`
- `twin/gnn/detector/feature_processor.py`
- `twin/gnn/detector/graph_builder.py`
- `twin/gnn/detector/inference_engine.py`
- `twin/gnn/detector/db_writer.py`
- `twin/gnn/detector/health_api.py`
- `twin/gnn/detector/config.yaml`

Model architecture source:
- `twin/gnn/detector/gcn_src/models/gcn.py`

Model registry:
- `twin/registry/gcn/v1.0.0/`
- `twin/registry/gcn/v2.0.0/`
- `twin/registry/gcn/v2.1.0/`
- `twin/registry/gcn/current`

---

## 5. Dashboard (Evidence Presentation Layer)

Backend API and SQL:
- `dashboard/app/backend/main.py`
- `dashboard/app/backend/db/queries.py`
- `dashboard/app/backend/api/experiments.py`
- `dashboard/app/backend/api/models.py`
- `dashboard/app/backend/api/analysis.py`
- `dashboard/app/backend/api/pipeline.py`
- `dashboard/app/backend/ws/pipeline.py`
- `dashboard/app/backend/registry/reader.py`

Frontend structure:
- `dashboard/app/frontend/src/App.tsx`
- sections: `PipelineSection.tsx`, `ExperimentSection.tsx`, `ModelSection.tsx`, `RunHistorySection.tsx`, `AttackSection.tsx`, `NetworkHealthSection.tsx`
- context/hooks/types under `dashboard/app/frontend/src/context`, `hooks`, `types`

Paper usage:
- screenshots/figures for real-time monitoring, run history, confusion trends.

---

## 6. Project Documentation (Narrative History)

High-value docs:
- `docs/CURRENT-STATE.md`
- `docs/QUICK-REFERENCE.md`
- `docs/BLUEPRINT.md`
- `docs/ALL-ADRS.md`

WP milestones:
- `docs/WP1-...` through `docs/WP10-...`

Critical model/debug timeline docs:
- `docs/WP8-LIVE-TEST-FINAL-SUMMARY.md`
- `docs/WP8-FINAL-RECOMMENDATION.md`
- `docs/GCN-MODEL-ANALYSIS.md`
- `docs/PIPELINE-FIX-SUMMARY.md`
- `docs/GCN-MODEL-v2.1.0-DEPLOYMENT.md`
- `docs/ROOT-CAUSE-ANALYSIS-COMPLETE.md`

Operational notes:
- `docs/codex/4YP/*.md`

---

## 7. Training Data and Automation Scripts

Data folders:
- `training_data/`
- `training_data_extended/`

Manifests:
- `training_data/manifest_pilot.csv`
- `training_data_extended/manifest.csv`

Automation scripts:
- `scripts/generate_pilot_data.sh`
- `scripts/generate_pilot_data_fast.sh`
- `scripts/generate_pilot_parallel.sh`
- `scripts/generate_extended_dataset.sh`
- `scripts/prepare_pilot_dataset.sh`
- `scripts/prepare_full_dataset.sh`
- `scripts/train_pilot_model.sh`
- `scripts/train_full_model.sh`
- monitors: `scripts/monitor_pilot_progress.sh`, `scripts/monitor_parallel.sh`

---

## 8. Your Added Research Notes (Pathum WIP)

Literature:
- `Pathum - Work in progress/Literature review.pdf`
- `Pathum - Work in progress/Literature review.txt`

New explanatory notes:
- `Pathum - Work in progress/Readme-Files/Datasets/*.md`
- `Pathum - Work in progress/Readme-Files/GNNs/*.md`
- `Pathum - Work in progress/Readme-Files/MLOs/*.md`

These are strong narrative support documents for the methodology and discussion chapters.

---

## 9. Where to Pull What for the Final Paper

- **Problem framing + research gap**: literature review + `BLUEPRINT.md`.
- **System architecture**: README + docker/clab + pipeline code.
- **Attack modeling mechanics**: ns-3 scratch + MLO notes.
- **Data engineering and telemetry contract**: exporter/harmonizer/windowizer + ADRs.
- **ML methodology**: detector/gcn sources + training scripts + model registry.
- **Experimental results and setbacks**: WP8/WP9/GCN analysis docs.
- **Operationalization and observability**: Grafana + custom dashboard files.
- **Limitations/threats**: inconsistencies across docs, artifacts, manifests, and model-version claims.

