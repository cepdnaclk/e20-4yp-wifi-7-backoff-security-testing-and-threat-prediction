# Grafana Data Flow — How Data Gets from NS-3 to the Dashboard

This document explains the complete journey from raw simulation data to a visible graph on the Grafana dashboard, including the exact role each file plays.

---

## The Full Pipeline at a Glance

```
NS-3 Simulation
     ↓  writes
telemetry.jsonl
     ↓  read by
Exporter (Python)  →  telemetry/exporters/ns3_file_exporter/exporter.py
     ↓  publishes to
Redpanda (Kafka API)  →  topic: wifi7.telemetry.v0_1
     ↓  consumed by
Harmonizer (Python)  →  telemetry/harmonizer/harmonizer.py
     ↓  INSERT INTO
TimescaleDB (udr-db:5432)  →  table: public.metrics
     ↓  queried by
Grafana (port 3000)  →  renders graphs in browser
```

---

## Step-by-Step Breakdown

### Step 1 — NS-3 writes raw data to a file

The simulation writes every measurement to a plain file:

```
sim/ns3/artifacts/<experiment_id>/telemetry.jsonl
```

Each line is one JSON record:

```json
{
  "experiment_id": "20260101-mlo-normal-42",
  "ts": "2026-01-01T12:00:01Z",
  "entity_id": "network",
  "metric": "throughput_mbps",
  "value": 450.2,
  "unit": "Mbps",
  "source": "ns3",
  "schema_version": "v0.1"
}
```

No YAML involved at this stage. Just a flat text file.

---

### Step 2 — Exporter reads the file and sends to Kafka

**File:** `telemetry/exporters/ns3_file_exporter/exporter.py`

Reads `telemetry.jsonl` line by line and publishes each record to Kafka:

```python
producer.produce("wifi7.telemetry.v0_1", key=..., value=json.dumps(rec))
```

Key behaviours:
- Tracks a **file offset** so it resumes from where it left off (state saved in `/state/exporter_state.json`)
- Does a **broker health check** before publishing — fails fast if Kafka is down or topic missing
- Only saves offset after **all messages are confirmed delivered** (counter-based delivery tracking)

---

### Step 3 — Harmonizer reads Kafka and writes to the database

**File:** `telemetry/harmonizer/harmonizer.py`

Subscribes to the Kafka topic and inserts rows into TimescaleDB:

```python
INSERT INTO public.metrics
  (experiment_id, ts, entity_id, metric_name, value, unit, source)
VALUES ...
ON CONFLICT ... DO UPDATE SET value = EXCLUDED.value
```

Key behaviours:
- Batches inserts (default 200 rows per flush) for efficiency
- Uses `ON CONFLICT ... DO UPDATE` — safe to replay the same data without duplicates
- Only commits Kafka offset after a successful DB flush

Now the data lives in the `metrics` table in **TimescaleDB**.

---

### Step 4 — YAML files configure Grafana to find and display that data

> The YAML files do **not** move data. They tell Grafana **how to connect to the database** and **where to find dashboards** when the container starts.

---

#### `clab/topo.yml` — starts the Grafana container and mounts config folders

```yaml
grafana:
  image: grafana/grafana:latest
  ports: ["3000:3000"]
  env:
    GF_SECURITY_ADMIN_USER: admin
    GF_SECURITY_ADMIN_PASSWORD: admin
  binds:
    - configs/grafana/provisioning:/etc/grafana/provisioning:ro   # ← YAML configs
    - configs/grafana/dashboards:/var/lib/grafana/dashboards:ro   # ← dashboard JSONs
```

The two `binds` mount local folders into the container. Without them, Grafana starts blank — no datasource, no dashboards.

---

#### `clab/configs/grafana/provisioning/datasources/udr-postgres.yml` — database connection

```yaml
datasources:
  - name: UDR-Postgres
    uid: udr_postgres       # ← the ID that dashboard JSON files reference
    type: postgres
    url: udr-db:5432        # ← TimescaleDB container (resolved via clab-mgmt network DNS)
    user: udr
    password: udr_pass
    database: udr
    timescaledb: true       # ← enables time-series optimizations
    isDefault: true
```

Grafana reads this on startup and **opens a live connection to TimescaleDB**. The `uid: udr_postgres` acts as a named handle — every dashboard panel references it to know which database to query.

---

#### `clab/configs/grafana/provisioning/dashboards/provider.yml` — dashboard discovery

```yaml
providers:
  - name: "NDT Dashboards"
    type: file
    options:
      path: /var/lib/grafana/dashboards   # ← scans this folder for .json files
```

Grafana reads this on startup and **auto-loads every `.json` file** it finds in the dashboards folder (which is bind-mounted from `clab/configs/grafana/dashboards/`).

---

#### `clab/configs/grafana/dashboards/*.json` — dashboards with embedded SQL

Each dashboard JSON file contains panels. Each panel specifies:
1. Which datasource to use (matched by `uid`)
2. What SQL to run
3. How to render the result

Example from `wp6-throughput-compare.json`:

```json
"datasource": {
  "type": "postgres",
  "uid": "udr_postgres"
},
"rawSql": "SELECT ts AS \"time\", value, experiment_id
           FROM metrics
           WHERE $__timeFilter(ts)
             AND metric_name = 'throughput_mbps'
           ORDER BY 1;"
```

Grafana macros used in SQL:
- `$__timeFilter(ts)` — automatically injects `ts BETWEEN <from> AND <to>` based on the dashboard time picker
- `${experiment_filter:regex}` — value of a template variable dropdown, populated by a separate SQL query
- `${last_n}` — custom dropdown variable with hardcoded options (5, 10, 20, 50)

When you open a dashboard in the browser, Grafana runs the SQL, gets the rows back, and renders the graph.

---

## Database Schema (what Grafana queries)

**Table: `public.metrics`** — defined in `clab/configs/udr-db/initdb/001-init.sql`

```sql
CREATE TABLE metrics (
  experiment_id  text,            -- e.g. "20260101-mlo-normal-42"
  ts             timestamptz,     -- time column (hypertable partition key)
  entity_id      text,            -- e.g. "network", "link-0", "station-0"
  metric_name    text,            -- e.g. "throughput_mbps", "avg_backoff_slots"
  value          double precision,
  unit           text,
  source         text,            -- e.g. "ns3"
  ingest_time    timestamptz
);

-- Converted to a TimescaleDB hypertable (partitioned by ts automatically)
SELECT create_hypertable('metrics', 'ts', if_not_exists => TRUE);
```

Performance indexes (from `002_metrics_constraints.sql`):
- `uq_metrics_idem` — unique index on `(experiment_id, ts, entity_id, metric_name, source)` — prevents duplicates on replay
- `ix_metrics_exp_metric_ts` — query index on `(experiment_id, metric_name, ts DESC)` — speeds up dashboard queries

---

## Dashboard Files and What They Show

| File | Dashboard Title | Key Metric |
|------|----------------|------------|
| `wp6-throughput-compare.json` | NDT WP6 - Throughput (Last N Experiments) | `throughput_mbps` |
| `mlo-attack-scenarios.json` | NDT WP7.5 - MLO Attack Scenarios Comparison | `avg_backoff_slots`, throughput, packet loss |
| `gcn-attack-detection.json` | GCN Attack Detection | ML model detection scores |

---

## Complete File Dependency Chain

```
topo.yml
  └─ starts Grafana container
  └─ mounts provisioning/ folder into /etc/grafana/provisioning/
       └─ udr-postgres.yml  →  Grafana opens connection to udr-db:5432
       └─ provider.yml      →  Grafana scans /var/lib/grafana/dashboards/
  └─ mounts dashboards/ folder into /var/lib/grafana/dashboards/
       └─ wp6-throughput-compare.json
       └─ mlo-attack-scenarios.json
       └─ gcn-attack-detection.json
            └─ each panel: datasource uid="udr_postgres", runs SQL on metrics table
                 └─ metrics table ← rows written by harmonizer.py
                      └─ harmonizer.py ← consumes from Kafka topic wifi7.telemetry.v0_1
                           └─ Kafka ← messages published by exporter.py
                                └─ exporter.py ← reads telemetry.jsonl
                                     └─ telemetry.jsonl ← written by NS-3 simulation
```

---

## Common "No Data" Issues and Causes

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Graph empty, no error | Time range does not cover when data was ingested | Adjust dashboard time picker |
| "Datasource not found" | UID in dashboard JSON does not match `udr-postgres.yml` | Ensure both use `udr_postgres` |
| Datasource connects but no rows | Harmonizer never ran or failed mid-way | Run harmonizer, check its logs |
| Harmonizer ran but rows missing | Exporter state file has stale offset | Delete `.exporter_state/exporter_state.json` |
| Grafana shows wrong datasource | Two datasource files conflict | Check both `datasource.yml` and `udr-postgres.yml` |

---

## Key Concepts Summary

| Concept | Explanation |
|---------|------------|
| **Grafana Provisioning** | Grafana auto-configures from YAML files at startup — no manual UI clicks needed |
| **Datasource UID** | A string identifier (`udr_postgres`) linking dashboard panels to a specific DB connection |
| **TimescaleDB hypertable** | PostgreSQL table auto-partitioned by time — enables fast time-range queries |
| **Container DNS** | Services resolve each other by container name (`udr-db`, `bus-redpanda`) on the `clab-mgmt` network |
| **Bind mount** | A folder on the host mapped into the container — changes to host files are reflected immediately |
| **`$__timeFilter(ts)`** | Grafana macro that injects the dashboard time range into SQL as a `WHERE` clause |
