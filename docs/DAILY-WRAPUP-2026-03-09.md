# Daily Wrap-Up - 2026-03-09

## Context and Objectives
Today focused on getting the WP9 custom dashboard to reflect true **live pipeline behavior** while running NS-3 scenarios, and reducing experiment friction for fast validation loops.

Main goals covered:
- Run normal + attack scenarios repeatedly with new configs/seeds.
- Reduce long run time and make one-segment testing practical.
- Ensure detector writes predictions per segment (no 100-row wait).
- Show real stage activity in UI (especially NS-3 while generating).
- Make Live Activity Feed show GCN predictions as they happen.

---

## What Was Changed

### 1) Dashboard: active stage and progress UX (Data Flow)
Implemented explicit stage metadata, current stage tracking, and progress bar behavior.

Changed files:
- `dashboard/app/frontend/src/sections/PipelineSection.tsx`
- `dashboard/app/frontend/src/components/pipeline/PipelineFlowDiagram.tsx`
- `dashboard/app/frontend/src/components/pipeline/stageMeta.ts` (new)

What it now does:
- Shows `Current Stage` and `Pipeline Progress` in Data Flow.
- Marks nodes as `RUNNING NOW`, `RUNNING`, `COMPLETE`, `IDLE`.
- Highlights active/current stage instead of static counters only.

---

### 2) Dashboard backend: better stage-state semantics
Improved stage state logic and prediction event querying.

Changed file:
- `dashboard/app/backend/db/queries.py`

Changes:
- Final DB stage is no longer permanently active after first prediction.
- Added scoped new-prediction query support by `experiment_id`.
- Added runtime status overlay support (see section 4 below).

---

### 3) WebSocket pipeline updates for real-time feed behavior
Changed file:
- `dashboard/app/backend/ws/pipeline.py`

Changes:
- Poll interval reduced (2s -> 1s earlier, then to 0.5s in final pass).
- Added small event backfill on connect (`BACKFILL_EVENTS=20`) so feed is not blank after reconnect.
- New prediction polling is now scoped to the latest active experiment id.

Result:
- Live Activity Feed now consistently shows GCN events (verified with `seg_0 -> ATTACK ...`).

---

### 4) Real NS-3 live status signaling (not DB-inferred)
Root cause found: dashboard had no direct signal from NS-3 runtime, so stage looked idle while simulation was still generating.

Implemented runtime status files and backend consumption:

Changed files:
- `sim/ns3/scenario/run_mlo_scenario.sh`
- `dashboard/app/backend/runtime/status.py` (new)
- `dashboard/app/backend/runtime/__init__.py` (new)
- `dashboard/app/backend/db/queries.py`
- `docker-compose.dashboard.yml`

Behavior now:
- NS-3 runner writes:
  - per-experiment `pipeline_status.json`
  - global active marker `.pipeline_active.json`
- Dashboard backend reads active marker with freshness threshold.
- UI shows `ns3` active + live window count while JSON file is still growing.

Also fixed two runner bugs discovered during rollout:
- `grep -c` empty-match arithmetic issue.
- Zombie child process loop hang (`kill -0` edge case).

---

### 5) Exporter streaming/exit behavior for faster test cycles
Changed files:
- `telemetry/exporters/ns3_file_exporter/exporter.py`
- `Makefile`

Changes:
- Added `MAX_MESSAGES_PER_CYCLE` (chunked publish).
- Added `RUN_CONTINUOUS` toggle; default run-once exits when idle.
- Added stream-friendly make target:
  - `run-mlo-exp-stream` with chunked exporter settings.
- Added exporter env passthroughs in Makefile.

Result:
- Experiment commands no longer hang waiting forever in exporter loop.
- Better pseudo-streaming behavior for dashboard testing.

---

### 6) Detector DB writes: per-segment flush and timestamp correctness
Changed files:
- `twin/gnn/detector/config.yaml`
- `twin/gnn/detector/db_writer.py`

Changes:
- `database.batch_insert_size` set to `1`.
- Writer enforces `batch_size >= 1`.
- Insert now sets `created_at` explicitly (`datetime.now(timezone.utc)`) per prediction.

Why this matters:
- Predictions are inserted immediately per segment.
- Stage timing and feed timestamps now reflect actual prediction time.

---

### 7) Runtime and scenario tuning
Changed files:
- `Makefile`
- `sim/ns3/scenario/run_mlo_scenario.sh`

Changes:
- Added `SIM_TIME` propagation across MLO make targets.
- Default simulation time changed from long run (1400s) to shorter testing-friendly defaults used today (`50s`, then `26s` for one-segment-oriented runs).

---

## Scenarios Executed Today

### Replay set (earlier in session)
- `20260309-192542-normal-replay`
- `20260309-192542-attack-neg-replay`
- `20260309-192542-attack-pos-replay`

### Calibration/short runs
- `20260309-calib50-normal`
- `20260309-195058-mlo-normal-601`
- `20260309-195600-mlo-normal-701`

### Final validated 3-scenario batch (latest)
- `20260309-2055-mlo-normal-821`
- `20260309-2058-mlo-attack-pos-822`
- `20260309-2102-mlo-attack-neg-823`

Observed DB summary for final batch:

| experiment_id | metrics | segments | attack_preds | avg_conf | last_created |
|---|---:|---:|---:|---:|---|
| 20260309-2055-mlo-normal-821 | 3380 | 1 | 0 | 0.8734 | 2026-03-09 14:52:28+00 |
| 20260309-2058-mlo-attack-pos-822 | 3380 | 1 | 1 | 0.9992 | 2026-03-09 14:53:30+00 |
| 20260309-2102-mlo-attack-neg-823 | 3360 | 1 | 1 | 0.9982 | 2026-03-09 14:56:17+00 |

Note: negative scenario ended with 3360 metrics persisted (expected JSONL was 3380). This is documented as observed behavior in this run.

---

## Validation Performed
- Dashboard rebuilt/restarted multiple times after backend/frontend changes.
- GCN detector image rebuilt/restarted after DB writer changes.
- API checks:
  - `/api/pipeline/status` used repeatedly during runs.
- DB checks:
  - `metrics` and `gcn_predictions` queried per experiment id.
- UI checks:
  - Playwright snapshots validated that:
    - NS-3 stage is shown active during generation.
    - Live Activity Feed contains GCN events (`seg_0 -> ATTACK ...`).

---

## Current Known Issues
- `windowizer` container still reports `unhealthy` due healthcheck definition/tooling mismatch (service itself continues processing).
- Some experiment counts may lag briefly due ingestion cadence and batching behavior in downstream services.

---

## Net Outcome
By end of day, the pipeline monitor now behaves as expected for live demos:
- NS-3 activity is visible while simulation is running.
- GCN prediction events appear in Live Activity Feed in near real time.
- One-segment scenario loops are practical for repeated normal/attack dashboard validation.
