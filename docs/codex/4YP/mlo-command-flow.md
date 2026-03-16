# MLO Command Flow (Simple, End-to-End)

This note explains what happens at each layer when you run these commands:

```
# Start services (if not running)
make up
make pipeline-up

# Run individual scenarios
make run-mlo-normal EXP_ID=20260103-1400-mlo-normal-42
make run-mlo-positive EXP_ID=20260103-1400-mlo-attack-pos-42
make run-mlo-negative EXP_ID=20260103-1400-mlo-attack-neg-42

# Or with full pipeline (sim + exporter)
make run-mlo-exp EXP_ID=20260103-test-01 SCENARIO=normal
```

## Naming conventions you see in EXP_ID

- The EXP_ID is just a label used to name folders and tag telemetry records.
- Format used in docs: `YYYYMMDD-HHMM-scenario-seed`.
- The last number (example: `-42`) is a convention to show the seed, but it is not parsed.
- The actual seed is controlled separately (default is `SEED=42`).

## Layer 1: Lab infrastructure (Containerlab)

### `make up`

What it does:
- Runs `containerlab deploy` with `clab/topo.yml`.
- Starts the core lab containers: Redpanda (Kafka API), UDR DB (Postgres/Timescale), Grafana.
- Creates the shared Docker network `clab-mgmt` used by all pipeline containers.
- Provides the DNS names that other containers use (for example `bus-redpanda`, `udr-db`).

Why it matters:
- Later steps depend on `clab-mgmt` for networking and service discovery.
- Kafka and the DB must exist before exporter and harmonizer can do anything useful.
- This is the "always-on" infrastructure layer; everything else attaches to it.

## Layer 2: Pipeline service (Harmonizer)

### `make pipeline-up`

What it does:
- Runs `docker-compose -f docker-compose.pipeline.yml up -d`.
- Starts the harmonizer container in the background with `restart: unless-stopped`.
- Connects to Kafka and the UDR DB over `clab-mgmt`.
- Uses env vars from `docker-compose.pipeline.yml` to point at:
  - Kafka brokers: `bus-redpanda:9092`
  - Kafka topic: `wifi7.telemetry.v0_1`
  - DB host: `udr-db`

What harmonizer does:
- Subscribes to the Kafka topic and continuously consumes messages.
- Normalizes records and writes them to the `metrics` table in UDR.
- Runs as a long-lived service so you don't have to start it every run.

Why it matters:
- It must be running before you publish telemetry if you want automatic DB ingestion.
- If it's not running, data will sit in Kafka until you start it later.

## Layer 3: Simulation (ns-3 in a Docker image)

### `make run-mlo-normal` / `make run-mlo-positive` / `make run-mlo-negative`

What the Makefile does:
- Runs the `ndt/ns3:local` Docker image (isolated ns-3 environment).
- Mounts the repo into `/work` inside the container.
- Calls: `/work/sim/ns3/scenario/run_mlo_scenario.sh <EXP_ID> <SCENARIO> <SEED>`.
- Sets the seed from `SEED` (default 42), not from the EXP_ID string.

What the scenario script does:
1. Writes metadata to `sim/ns3/artifacts/<EXP_ID>/meta.txt`.
2. Copies the scenario source file into ns-3 scratch:
   - normal -> `wifi7-mlo-Normal.cc`
   - positive -> `wifi7-mlo-Positive.cc`
   - negative -> `wifi7-mlo-Negative.cc`
3. Sets scenario bias (0 / +5000 / -5000 by default) and simulation time.
4. Runs ns-3 and writes `mlo_output.json` in the experiment artifacts directory.
5. Validates JSON output and converts it into pipeline-ready `telemetry.jsonl`.
6. Logs stdout/stderr to files for debugging.

Artifacts produced per run:
- `sim/ns3/artifacts/<EXP_ID>/meta.txt`
- `sim/ns3/artifacts/<EXP_ID>/mlo_output.json`
- `sim/ns3/artifacts/<EXP_ID>/telemetry.jsonl`
- `sim/ns3/artifacts/<EXP_ID>/ns3_stdout.log`
- `sim/ns3/artifacts/<EXP_ID>/ns3_stderr.log`

Important detail:
- The simulation seed defaults to 42 (unless `SEED=...` is passed to make).
- EXP_ID naming does not change the seed by itself.
- The scenario choice changes the behavior of the ns-3 model (attack bias).

## Layer 4: Telemetry export (ns3_file_exporter)

### `make run-mlo-exp EXP_ID=... SCENARIO=...`

This target combines the simulation and exporter:
1. Runs the simulation (`run-mlo-<scenario>`).
2. Runs the exporter (`make exporter-run EXP_ID=...`).

What the exporter does:
- Reads `sim/ns3/artifacts/<EXP_ID>/telemetry.jsonl`.
- Publishes each line as a Kafka message to `wifi7.telemetry.v0_1`.
- Uses a deterministic Kafka key (experiment_id|entity_id|metric|ts).
- Tracks offsets in `.exporter_state/` so it does not re-send old lines.

Why it matters:
- Without this step, telemetry stays on disk and never reaches Kafka.
- This is the bridge between simulation output and the live pipeline.

## Layer 5: Kafka and Harmonizer ingestion

What happens after export:
- Redpanda (Kafka API) stores the telemetry messages on the topic.
- Harmonizer consumes those messages and writes rows into the UDR database.
- Grafana dashboards read from the UDR DB to visualize the experiment.

Outcome:
- Your experiment is now queryable in Postgres and visible in Grafana.

## Why there are two types of commands

You will see two styles because they serve different needs:

1) Scenario-only commands (simulation only)

```
make run-mlo-normal EXP_ID=...
make run-mlo-positive EXP_ID=...
make run-mlo-negative EXP_ID=...
```

What they do:
- Run just the ns-3 simulation and generate artifacts on disk.
- Do not publish telemetry to Kafka.
- Useful when you want only raw outputs (e.g., GNN training JSON) or you want to inspect logs before sending data into the pipeline.

2) Full pipeline command (simulation + exporter)

```
make run-mlo-exp EXP_ID=20260103-1400-mlo-normal-42 SCENARIO=normal
make run-mlo-exp EXP_ID=20260103-1400-mlo-attack-pos-42 SCENARIO=positive
make run-mlo-exp EXP_ID=20260103-1400-mlo-attack-neg-42 SCENARIO=negative

```

What it does:
- Runs the same simulation as above (based on `SCENARIO`).
- Immediately publishes `telemetry.jsonl` to Kafka so harmonizer can ingest it.
- Useful for end-to-end runs where you want data in the DB and Grafana with one command.

Summary:
- Use scenario-only commands when you want "generate artifacts only."
- Use `run-mlo-exp` when you want "generate artifacts + push to pipeline."

## End-to-end picture

```
ns-3 simulation
  -> artifacts/<EXP_ID>/telemetry.jsonl
  -> exporter publishes to Kafka
  -> harmonizer consumes from Kafka
  -> UDR database
  -> Grafana dashboards
```
