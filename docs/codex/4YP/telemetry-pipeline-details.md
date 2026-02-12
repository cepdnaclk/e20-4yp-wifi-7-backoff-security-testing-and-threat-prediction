# Telemetry Pipeline Details (Latest Status, Exporter Duty, DB Ingestion)

## What Was Done Last (From Project Docs)

Based on `docs/CURRENT-STATE.md` and `docs/WP7-ONE-COMMAND-PIPELINE.md`, the most recent completed work is:

- **WP7: One-command pipeline** is complete. The harmonizer runs as a background
  service via `docker-compose.pipeline.yml`, and `make run-exp` now runs the full
  ns-3 -> exporter -> DB ingestion flow in one command.
- **WP7.5: MLO attack scenarios** were added on top of WP7. This includes new
  MLO scenario runner scripts, JSON -> JSONL conversion, and Makefile targets
  (`run-mlo-normal`, `run-mlo-positive`, `run-mlo-negative`, `run-mlo-exp`).
- **Next up is WP8**, which is documented as multi-scenario support and related
  automation (not yet done).

In other words, the latest documented work is the end-to-end pipeline
automation plus the MLO scenario integration that feeds that pipeline.

## Exporter Duty (What It Does)

The exporter is the bridge between files on disk and the pipeline. Its duties
are documented in `docs/WP4-TELEMETRY-EXPORTER.md` and implemented in
`telemetry/exporters/ns3_file_exporter/exporter.py`.

Core responsibilities:

1. **Read `telemetry.jsonl` continuously**
   - File path comes from `TELEMETRY_FILE`.
   - It seeks to a saved byte offset, so it only publishes new lines.

2. **Parse and validate each JSON line**
   - Uses a Pydantic schema (`TelemetryRecord`).
   - Adds defaults for `source` and `schema_version` if missing.
   - Normalizes timestamps to ISO-8601 strings.

3. **Publish each line to Kafka (Redpanda)**
   - Topic defaults to `wifi7.telemetry.v0_1`.
   - Message key is deterministic: `experiment_id|entity_id|metric|ts`.
   - This key enables idempotency downstream.

4. **Persist per-file offsets**
   - State file defaults to `/state/exporter_state.json`.
   - On the host, this is `.exporter_state/exporter_state.json`.
   - Offsets are stored per telemetry file path so multiple experiments can be
     exported without collisions.

Net effect: the exporter is a reliable file-to-Kafka publisher with stateful
resume, making the pipeline safe to rerun.

## What Happens After `telemetry.jsonl` Is Created

`telemetry.jsonl` is created by ns-3 run scripts:

- **Baseline / Wi-Fi example**: scripts in `sim/ns3/scenario/` write a simple
  JSONL file with one or more metrics.
- **MLO scenarios**: `run_mlo_scenario.sh` produces `mlo_output.json` and then
  runs `convert_mlo_json_to_jsonl.sh`, which expands each window into multiple
  metric lines (13 metrics per 0.1s window).

Once `telemetry.jsonl` exists, the pipeline proceeds like this:

1. **Exporter reads `telemetry.jsonl`**
   - It publishes each JSONL line to Kafka (Redpanda).
   - If it is restarted, it resumes from the last saved file offset.

2. **Kafka stores messages on `wifi7.telemetry.v0_1`**
   - Data is durable on the topic until consumers process it.

3. **Harmonizer consumes from Kafka**
   - Runs as a background service in WP7 (`make pipeline-up`).
   - Validates and parses messages.
   - Maps `metric` -> `metric_name` for the DB.
   - Batches inserts and upserts rows into the database.

4. **Grafana reads from the DB**
   - Dashboards query the `metrics` table in TimescaleDB.

If the exporter is not run, data remains only on disk. If the harmonizer is not
running, data sits in Kafka until it is started.

## Is Simulation Data Saved in the DB? How?

Yes, simulation data is saved in the **TimescaleDB** database, but only after
the exporter publishes telemetry and the harmonizer consumes it.

### Where it lands

The harmonizer inserts rows into:

- **Table:** `public.metrics`
- **Schema fields:**
  - `experiment_id`
  - `ts` (timestamp)
  - `entity_id`
  - `metric_name`
  - `value`
  - `unit`
  - `source`
  - `ingest_time` (default NOW())

The table is created in `clab/configs/udr-db/initdb/001-init.sql`, and its
unique idempotency index is in
`clab/configs/udr-db/initdb/002_metrics_constraints.sql`.

### How it is saved

The harmonizer (`telemetry/harmonizer/harmonizer.py`):

- Consumes Kafka messages in batches (`BATCH_SIZE`).
- Parses JSON into a typed record.
- Converts `ts` into a DB-friendly timestamp.
- Executes an upsert:
  - `INSERT ... ON CONFLICT (experiment_id, ts, entity_id, metric_name, source)`
  - Updates `value` and `unit` on conflict.
- Commits Kafka offsets only after the DB insert succeeds.

### What gets stored (examples)

**Wi-Fi example runs:**
- Usually one JSONL record per run -> one row in `metrics`.

**MLO scenarios:**
- Each 0.1s window is expanded into 13 metrics.
- That means 13 rows per window, each with the same `ts` and `experiment_id`.

### What is not stored in the DB

Files like `meta.txt`, `ns3_stdout.log`, `ns3_stderr.log`, and the raw
`mlo_output.json` are stored only in
`sim/ns3/artifacts/<EXP_ID>/`. Only the JSONL metrics are sent into Kafka and
saved to the database.

## End-to-End Summary (ASCII)

```
ns-3 run
  -> sim/ns3/artifacts/<EXP_ID>/telemetry.jsonl
  -> exporter publishes JSONL lines to Kafka
  -> harmonizer consumes Kafka and upserts rows into TimescaleDB
  -> Grafana queries the metrics table
```
