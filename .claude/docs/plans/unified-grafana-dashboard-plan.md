# Implementation Plan: Unified NDT Wi-Fi 7 MLO Security Grafana Dashboard

## Date
2026-02-27

## Objective
Replace the three existing Grafana dashboards (WP6 throughput, WP7.5 MLO scenarios, WP8 GCN detection) with one unified dashboard that consolidates all views into a single coherent page, scoped by a run selector variable. The new dashboard must show raw telemetry, GCN predictions, detection summary stats, confidence scores, model info, inference performance, and per-experiment comparison for a selected run.

## Background
The project currently has three separate dashboards that each cover a subset of the data. As the pipeline matures (WP8 complete, WP9 in progress), operators need a single view to assess both network health and attack detection status for any given experiment run. The unified dashboard also removes confusion about which dashboard to use and ensures all panels share consistent filtering.

Belongs to: WP8 / WP9 observability milestone.

---

## Research Findings Summary

### Existing Dashboards to Replace

| File | UID | Panels | Key Queries |
|------|-----|--------|-------------|
| `clab/configs/grafana/dashboards/wp6-throughput-compare.json` | `ndt-wp6-throughput-compare` | 2 | `net_throughput_mbps` only; `last_n` variable |
| `clab/configs/grafana/dashboards/mlo-attack-scenarios.json` | `mlo-attack-scenarios` | 9 | backoff, throughput, delay, jitter, retrans, channel_busy, active_flows, summary table |
| `clab/configs/grafana/dashboards/gcn-attack-detection.json` | `gcn-attack-detection` | 13 | `gcn_predictions` table: prediction, confidence, probabilities, inference_time_ms, model_version |
| `clab/configs/grafana/dashboards/gcn-attack-detection.json.backup` | same | same | Minor formatting diff only - treat as same |

### Database Schema (Confirmed Live)

#### `metrics` table
```
experiment_id   TEXT NOT NULL
ts              TIMESTAMPTZ NOT NULL
entity_id       TEXT NOT NULL        -- always 'network' in current data
metric_name     TEXT NOT NULL
value           DOUBLE PRECISION NOT NULL
unit            TEXT NOT NULL
source          TEXT NOT NULL        -- always 'ns3'
ingest_time     TIMESTAMPTZ NOT NULL DEFAULT now()
```
Indexes: `(experiment_id, metric_name, ts DESC)`, `(ts DESC)`, unique `(experiment_id, ts, entity_id, metric_name, source)`

**Available metric_name values (all 13 confirmed in DB):**
- `avg_backoff_slots` - key attack indicator
- `channel_busy_ratio`
- `mac_drop_count`
- `mac_total_ack`
- `mac_total_retrans`
- `mac_total_rx`
- `mac_total_tx`
- `net_active_flows`
- `net_avg_delay_ms`
- `net_avg_jitter_ms`
- `net_packet_loss_ratio`
- `net_throughput_mbps`
- `phy_drop_count`

Note: The WP6 dashboard references `throughput_mbps` - this is WRONG. The actual column is `net_throughput_mbps`. The WP6 dashboard was broken for this reason.

#### `gcn_predictions` table
```
id                  BIGINT PRIMARY KEY (with ts_start)
experiment_id       TEXT NOT NULL
entity_id           TEXT NOT NULL      -- always 'network'
segment_id          TEXT NOT NULL      -- 'seg_0', 'seg_1', ...
ts_start            TIMESTAMPTZ NOT NULL
ts_end              TIMESTAMPTZ NOT NULL
window_start_idx    INTEGER NOT NULL
window_end_idx      INTEGER NOT NULL
prediction          INTEGER NOT NULL   -- 0=normal, 1=attack
confidence          DOUBLE PRECISION NOT NULL  -- 0.0-1.0, check constraint
probabilities       JSONB NOT NULL     -- e.g. [0.91, 0.09] (index 0=normal, 1=attack)
model_version       TEXT NOT NULL      -- 'v1.0.0', 'v2.0.0'
model_path          TEXT NOT NULL
inference_time_ms   DOUBLE PRECISION   -- nullable, but ALL rows in DB have a value
source              TEXT NOT NULL DEFAULT 'gcn-detector'
created_at          TIMESTAMPTZ DEFAULT now()
```

#### `snapshots` table
- **Currently empty** (0 rows)
- Columns: id, experiment_id, created_at, topology_json, config_json, git_sha, ns3_version, schema_version
- Not useful for dashboard panels at this time

### Actual Data in DB (Confirmed)

**Experiments present:**
```
20260227-2215-seq1-normal         - 14 experiments total
20260227-2215-seq2-attack-neg       2 runs with YYYYMMDD-HHMM prefix:
20260227-2215-seq3-normal             20260227-2215 (4 exps)
20260227-2215-seq4-attack-pos         20260212-1904 (3 exps)
20260212-1904-normal
20260212-1904-positive            7 "legacy" experiments (no prefix):
20260212-1904-negative              aligned-normal-test-42
20260210-phase4-normal-full         20260210-phase4-*
20260210-phase4-positive-full       20260215-validation-*
20260210-phase4-negative-full
20260215-validation-normal-01
20260215-validation-attack-pos-01
20260215-validation-attack-neg-01
aligned-normal-test-42
```

**Run selector options (what the variable will show):**
```
20260227-2215  -> 4 experiments
20260212-1904  -> 3 experiments
20260210-phase4-positive-full  -> legacy (shown as full experiment_id)
20260210-phase4-normal-full    -> legacy
20260210-phase4-negative-full  -> legacy
20260215-validation-normal-01  -> legacy
20260215-validation-attack-pos-01 -> legacy
20260215-validation-attack-neg-01 -> legacy
aligned-normal-test-42         -> legacy
```

**Key metric facts:**
- `avg_backoff_slots` normal = ~9.7, attack-pos = ~345, attack-neg = ~2.3
- `net_throughput_mbps` normal = ~304 Mbps, attack = ~209 Mbps
- `net_packet_loss_ratio` normal = 0.025, attack-neg = 0.48, attack-pos = 0.33
- All 14 experiments have metrics in ALL 13 metric_name categories

**GCN prediction facts:**
- Both v1.0.0 and v2.0.0 present; filter to v2.0.0 by default
- `inference_time_ms` populated for ALL rows (avg 2.8-12ms range)
- `confidence` is a 0-1 float (probabilities[1] = attack prob)
- Probabilities JSONB format: array `[normal_prob, attack_prob]`, e.g. `[0.91, 0.09]`
- `(probabilities->>0)::numeric` = normal class probability
- `(probabilities->>1)::numeric` = attack class probability

### No Missing DB Tables or Columns Required
The existing 3 tables contain all information needed for the unified dashboard. No schema changes are required. The `model_version` column in `gcn_predictions` provides the model info required. The `snapshots` table is empty but not needed.

### Provisioning Facts
- Dashboard files mounted at: `clab/configs/grafana/dashboards/` -> `/var/lib/grafana/dashboards/`
- Provider folder in Grafana UI: "NDT"
- Datasource UID: `udr_postgres`
- Grafana credentials: admin/admin
- Changes require Grafana container restart to reload provisioned files

---

## Prerequisites

- [ ] Containerlab running: `make status` shows grafana, udr-db, bus-redpanda containers up
- [ ] Database has data in `metrics` and `gcn_predictions` tables (confirmed above)
- [ ] Datasource `udr_postgres` connected and tested in Grafana UI

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `clab/configs/grafana/dashboards/ndt-unified.json` | Create | The new unified dashboard JSON |
| `clab/configs/grafana/dashboards/wp6-throughput-compare.json` | Delete | Superseded by unified dashboard |
| `clab/configs/grafana/dashboards/mlo-attack-scenarios.json` | Delete | Superseded by unified dashboard |
| `clab/configs/grafana/dashboards/gcn-attack-detection.json` | Delete | Superseded by unified dashboard |
| `clab/configs/grafana/dashboards/gcn-attack-detection.json.backup` | Delete | Backup file no longer needed |
| `clab/configs/grafana/dashboards/README.md` | Modify | Update to document the unified dashboard |

---

## Implementation Steps

### Step 1: Create the Unified Dashboard JSON File

Create `clab/configs/grafana/dashboards/ndt-unified.json` with UID `ndt-unified`.

The complete dashboard structure is specified below.

**Verification:** `jq . clab/configs/grafana/dashboards/ndt-unified.json` exits with code 0.

---

### Step 2: Delete the Three Old Dashboard Files

Remove:
- `clab/configs/grafana/dashboards/wp6-throughput-compare.json`
- `clab/configs/grafana/dashboards/mlo-attack-scenarios.json`
- `clab/configs/grafana/dashboards/gcn-attack-detection.json`
- `clab/configs/grafana/dashboards/gcn-attack-detection.json.backup`

**Verification:** `ls clab/configs/grafana/dashboards/` shows only `ndt-unified.json` and `README.md`.

---

### Step 3: Restart Grafana to Reload Provisioned Dashboards

```bash
docker restart clab-ndt-wifi7-mlo-security-grafana
```

Wait 5-10 seconds for Grafana to start, then open http://localhost:3000.

**Verification:**
- Browse to Grafana -> Dashboards -> NDT folder
- Confirm "NDT Wi-Fi 7 MLO Security - Unified Dashboard" appears
- Confirm the three old dashboards no longer appear
- Open the unified dashboard and select a run from the Run Selector variable

---

### Step 4: Update README.md

Update `clab/configs/grafana/dashboards/README.md` to document:
- The unified dashboard replaces all three prior dashboards
- Access URL: http://localhost:3000/d/ndt-unified
- Panel count and features

**Verification:** README reflects new state accurately.

---

## Complete Dashboard Specification

### Dashboard Metadata

```json
{
  "uid": "ndt-unified",
  "title": "NDT Wi-Fi 7 MLO Security - Unified Dashboard",
  "description": "Unified view of all NDT experiments: raw telemetry, GCN attack predictions, confidence scores, and per-experiment comparison. Filter by Run Selector to scope all panels to a specific run group.",
  "tags": ["ndt", "mlo", "wifi7", "gcn", "security", "unified"],
  "timezone": "UTC",
  "schemaVersion": 39,
  "version": 1,
  "editable": true,
  "refresh": "30s",
  "time": {
    "from": "now-24h",
    "to": "now"
  }
}
```

---

### Template Variables (Run Selector)

**Variable 1: `run_prefix`**

- Type: `query`
- Label: "Run Selector"
- Description: Filter all panels to experiments belonging to this run (YYYYMMDD-HHMM prefix or full experiment ID for legacy)
- Multi-select: false (single run at a time)
- Include All: true (default to All for overview mode)
- Datasource: `udr_postgres`

```sql
SELECT DISTINCT
  CASE
    WHEN experiment_id ~ '^\d{8}-\d{4}'
      THEN regexp_replace(experiment_id, '^(\d{8}-\d{4}).*', '\1')
    ELSE experiment_id
  END AS run_prefix
FROM metrics
ORDER BY 1 DESC
```

This query returns values like `20260227-2215`, `20260212-1904`, `aligned-normal-test-42`, etc.

**Variable 2: `model_version`**

- Type: `query`
- Label: "Model Version"
- Multi-select: false
- Include All: true
- Default: `v2.0.0` (set as current value)
- Datasource: `udr_postgres`

```sql
SELECT DISTINCT model_version FROM gcn_predictions ORDER BY model_version DESC
```

**Run selector filter pattern** (used in WHERE clauses):

For all panels filtering by `${run_prefix}`:
```sql
-- When run_prefix matches YYYYMMDD-HHMM format:
experiment_id LIKE '${run_prefix}%'

-- But since the variable can also be a full experiment_id (legacy):
-- Use the same LIKE pattern - if run_prefix = 'aligned-normal-test-42',
-- then LIKE 'aligned-normal-test-42%' matches exactly that experiment.
```

This single pattern works for both grouped runs and legacy single-experiment IDs.

---

### Dashboard Layout Overview

The dashboard is organized into 5 logical sections (row separators):

```
ROW 0: Summary Stats (y=0, h=4)
  - [0,0] Total Segments   w=3
  - [3,0] Attacks Detected w=3
  - [6,0] Attack Rate %    w=3
  - [9,0] Avg Confidence   w=3
  - [12,0] Avg Inference ms w=3
  - [15,0] Active Model     w=3
  - [18,0] Experiments in Run w=3
  - [21,0] Run Time Range   w=3

ROW 1: Attack Detection (y=4, separator row h=1)
ROW 2: GCN Predictions (y=5-24)
  - [0,5]  Attack Detection Timeline    w=24 h=8
  - [0,13] Prediction Confidence Over Time  w=12 h=8
  - [12,13] Attack Probability Distribution w=12 h=8

ROW 3: Raw Network Telemetry (y=22, separator row h=1)
  - [0,22] Avg Backoff Slots (Key Attack Indicator)  w=12 h=8
  - [12,22] Network Throughput Mbps                  w=12 h=8
  - [0,30] Packet Loss Ratio    w=8 h=8
  - [8,30] Avg Delay ms         w=8 h=8
  - [16,30] Avg Jitter ms       w=8 h=8
  - [0,38] Channel Busy Ratio   w=8 h=8
  - [8,38] MAC Retransmissions  w=8 h=8
  - [16,38] Active Flows        w=8 h=8

ROW 4: Per-Experiment Comparison (y=47, separator row h=1)
  - [0,48] Attack Rate by Experiment (bar gauge)     w=12 h=8
  - [12,48] Avg Confidence by Experiment (bar gauge) w=12 h=8
  - [0,56] Network Metrics Summary Table             w=24 h=10

ROW 5: Inference Performance (y=67, separator row h=1)
  - [0,68] Inference Time Over Time (time series)    w=12 h=8
  - [12,68] Prediction Distribution Pie              w=6  h=8
  - [18,68] Model Performance Summary (stat)         w=6  h=8

ROW 6: Recent Predictions Table (y=77)
  - [0,77] Recent Predictions (table, sortable)      w=24 h=12
```

Total: approximately 24 panels + 5 row separators = 29 elements.

---

### Panel Specifications and SQL Queries

#### Section 0: Summary Stats (Stat Panels, y=0-3)

All summary stats filter by `${run_prefix}` using LIKE and `${model_version}` using direct equality.

**Panel ID 1: Total Segments**
- Type: `stat`
- gridPos: h=4, w=3, x=0, y=0
- Color thresholds: blue < 10 < green < 100 < yellow
- Unit: `short`
- SQL:
```sql
SELECT COUNT(*) as value
FROM gcn_predictions
WHERE experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'
```

**Panel ID 2: Attacks Detected**
- Type: `stat`
- gridPos: h=4, w=3, x=3, y=0
- Color thresholds: green=0 < yellow=1 < orange=10 < red=50
- Unit: `short`
- SQL:
```sql
SELECT COUNT(*) as value
FROM gcn_predictions
WHERE experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'
  AND prediction = 1
```

**Panel ID 3: Attack Rate %**
- Type: `stat`
- gridPos: h=4, w=3, x=6, y=0
- Color thresholds: green=0 < yellow=20 < orange=50 < red=80
- Unit: `percent`
- Decimals: 1
- SQL:
```sql
SELECT ROUND(
  100.0 * SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0),
  1
) as value
FROM gcn_predictions
WHERE experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'
```

Note: `NULLIF(COUNT(*), 0)` prevents division by zero when no data matches.

**Panel ID 4: Avg Confidence**
- Type: `stat`
- gridPos: h=4, w=3, x=9, y=0
- Color thresholds: red < 0.6 < yellow < 0.8 < green
- Unit: `percentunit` (0.0-1.0 range)
- Decimals: 3
- min: 0, max: 1
- SQL:
```sql
SELECT ROUND(AVG(confidence)::numeric, 3) as value
FROM gcn_predictions
WHERE experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'
```

**Panel ID 5: Avg Inference Time (ms)**
- Type: `stat`
- gridPos: h=4, w=3, x=12, y=0
- Color thresholds: green < 50 < yellow < 200 < red
- Unit: `ms`
- Decimals: 1
- SQL:
```sql
SELECT ROUND(AVG(inference_time_ms)::numeric, 1) as value
FROM gcn_predictions
WHERE experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'
  AND inference_time_ms IS NOT NULL
```

**Panel ID 6: Active Model Version**
- Type: `stat`
- gridPos: h=4, w=3, x=15, y=0
- Color: fixed blue background
- textMode: `value`
- SQL:
```sql
SELECT model_version as value
FROM gcn_predictions
WHERE experiment_id LIKE '${run_prefix}%'
ORDER BY created_at DESC
LIMIT 1
```

**Panel ID 7: Experiments in Run**
- Type: `stat`
- gridPos: h=4, w=3, x=18, y=0
- Color: fixed purple (palette-classic)
- Unit: `short`
- Description: "Number of distinct experiments matching the run selector"
- SQL:
```sql
SELECT COUNT(DISTINCT experiment_id) as value
FROM metrics
WHERE experiment_id LIKE '${run_prefix}%'
```

**Panel ID 8: Run Time Range**
- Type: `stat`
- gridPos: h=4, w=3, x=21, y=0
- Color: fixed grey
- textMode: `value_and_name`
- Description: "Earliest and latest data timestamps for selected run"
- SQL:
```sql
SELECT
  'Start: ' || TO_CHAR(MIN(ts) AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI') ||
  ' | End: ' || TO_CHAR(MAX(ts) AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI') as value
FROM metrics
WHERE experiment_id LIKE '${run_prefix}%'
```

---

#### Section 1 Row Separator

**Panel ID 100: Row - GCN Attack Detection**
- Type: `row`
- Title: "GCN Attack Detection"
- collapsed: false
- gridPos: h=1, w=24, x=0, y=4

---

#### Section 2: GCN Predictions

**Panel ID 10: Attack Detection Timeline**
- Type: `timeseries`
- Title: "Attack Detection Timeline (0=Normal, 1=Attack)"
- Description: "Binary prediction per segment over time. Bar chart: green=normal, red=attack. Color is per experiment_id."
- gridPos: h=8, w=24, x=0, y=5
- drawStyle: `bars`, fillOpacity: 80, lineWidth: 0
- min: 0, max: 1, decimals: 0
- Unit: `short`
- Legend: table, placement bottom, calcs: [sum, mean]
- SQL:
```sql
SELECT
  ts_start AS "time",
  prediction::float as value,
  experiment_id as metric
FROM gcn_predictions
WHERE $__timeFilter(ts_start)
  AND experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'
ORDER BY ts_start, experiment_id
```

Note: Using `$__timeFilter(ts_start)` for Grafana time range integration. Color overrides for experiment_id patterns containing `-normal` (green), `-attack-pos` (red), `-attack-neg` (orange) should be added as field overrides by regexp.

**Field overrides for Panel 10:**
```json
"overrides": [
  {
    "matcher": {"id": "byRegexp", "options": ".*normal.*"},
    "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "green"}}]
  },
  {
    "matcher": {"id": "byRegexp", "options": ".*attack-pos.*"},
    "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}}]
  },
  {
    "matcher": {"id": "byRegexp", "options": ".*attack-neg.*"},
    "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "orange"}}]
  },
  {
    "matcher": {"id": "byRegexp", "options": ".*attack-pos.*|.*positive.*"},
    "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}}]
  },
  {
    "matcher": {"id": "byRegexp", "options": ".*attack-neg.*|.*negative.*"},
    "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "orange"}}]
  }
]
```

**Panel ID 11: Prediction Confidence Over Time**
- Type: `timeseries`
- Title: "Prediction Confidence Over Time"
- Description: "Confidence score per segment. Higher = more certain. Colored by prediction class."
- gridPos: h=8, w=12, x=0, y=13
- Unit: `percentunit`, min: 0, max: 1
- showPoints: always, pointSize: 4
- Legend: table, placement bottom, calcs: [mean, min, max]
- SQL:
```sql
SELECT
  ts_start AS "time",
  confidence as value,
  CONCAT(experiment_id, ' (pred=', prediction, ')') as metric
FROM gcn_predictions
WHERE $__timeFilter(ts_start)
  AND experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'
ORDER BY ts_start
```

**Panel ID 12: Attack Probability Over Time**
- Type: `timeseries`
- Title: "Attack Probability (Class 1) Over Time"
- Description: "Raw attack probability output from GCN model (probabilities[1]). Complements confidence for attack experiments."
- gridPos: h=8, w=12, x=12, y=13
- Unit: `percentunit`, min: 0, max: 1
- fillOpacity: 20
- Legend: table, placement bottom, calcs: [mean, min, max]
- SQL:
```sql
SELECT
  ts_start AS "time",
  (probabilities->>1)::numeric as value,
  experiment_id as metric
FROM gcn_predictions
WHERE $__timeFilter(ts_start)
  AND experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'
ORDER BY ts_start
```

---

#### Section 2 Row Separator

**Panel ID 101: Row - Raw Network Telemetry**
- Type: `row`
- Title: "Raw Network Telemetry"
- collapsed: false
- gridPos: h=1, w=24, x=0, y=21

---

#### Section 3: Raw Network Telemetry

All telemetry panels use `$__timeFilter(ts)` for time range scoping and filter by `experiment_id LIKE '${run_prefix}%'` and `entity_id = 'network'`.

The standard field override pattern for experiment color coding applies to all telemetry panels.

**Standard color override snippet for all telemetry panels:**
```json
"overrides": [
  {
    "matcher": {"id": "byRegexp", "options": ".*normal.*|.*seq.*normal.*"},
    "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "green"}}]
  },
  {
    "matcher": {"id": "byRegexp", "options": ".*positive.*|.*attack-pos.*|.*attack_pos.*"},
    "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}}]
  },
  {
    "matcher": {"id": "byRegexp", "options": ".*negative.*|.*attack-neg.*|.*attack_neg.*"},
    "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "orange"}}]
  }
]
```

**Panel ID 20: Avg Backoff Slots (Key Attack Indicator)**
- Type: `timeseries`
- Title: "Avg Backoff Slots (Attack Indicator)"
- Description: "Primary attack indicator. Normal ~9-10, Positive attack ~345 (+3500%), Negative attack ~2.3 (-77%). High = priority queue monopolization. Low = backoff suppression."
- gridPos: h=8, w=12, x=0, y=22
- Unit: `short`
- Legend: table, placement bottom, calcs: [mean, max, min]
- SQL:
```sql
SELECT
  ts AS "time",
  value,
  experiment_id
FROM metrics
WHERE $__timeFilter(ts)
  AND experiment_id LIKE '${run_prefix}%'
  AND metric_name = 'avg_backoff_slots'
  AND entity_id = 'network'
ORDER BY ts, experiment_id
```

**Panel ID 21: Network Throughput (Mbps)**
- Type: `timeseries`
- Title: "Network Throughput (Mbps)"
- Description: "Aggregate network throughput. Normal ~304 Mbps. Attack scenarios show ~31% reduction."
- gridPos: h=8, w=12, x=12, y=22
- Unit: `Mbps`
- Legend: table, placement bottom, calcs: [mean, last]
- SQL:
```sql
SELECT
  ts AS "time",
  value,
  experiment_id
FROM metrics
WHERE $__timeFilter(ts)
  AND experiment_id LIKE '${run_prefix}%'
  AND metric_name = 'net_throughput_mbps'
  AND entity_id = 'network'
ORDER BY ts, experiment_id
```

**Panel ID 22: Packet Loss Ratio**
- Type: `timeseries`
- Title: "Packet Loss Ratio"
- Description: "Network quality degradation. Normal ~0.025 (2.5%). Attack-neg up to 0.48 (48%). Attack-pos ~0.33 (33%)."
- gridPos: h=8, w=8, x=0, y=30
- Unit: `percentunit`
- Legend: list, placement bottom
- SQL:
```sql
SELECT
  ts AS "time",
  value,
  experiment_id
FROM metrics
WHERE $__timeFilter(ts)
  AND experiment_id LIKE '${run_prefix}%'
  AND metric_name = 'net_packet_loss_ratio'
  AND entity_id = 'network'
ORDER BY ts, experiment_id
```

**Panel ID 23: Avg Packet Delay (ms)**
- Type: `timeseries`
- Title: "Average Packet Delay (ms)"
- Description: "End-to-end packet delivery latency. Increases under attack conditions."
- gridPos: h=8, w=8, x=8, y=30
- Unit: `ms`
- Legend: list, placement bottom
- SQL:
```sql
SELECT
  ts AS "time",
  value,
  experiment_id
FROM metrics
WHERE $__timeFilter(ts)
  AND experiment_id LIKE '${run_prefix}%'
  AND metric_name = 'net_avg_delay_ms'
  AND entity_id = 'network'
ORDER BY ts, experiment_id
```

**Panel ID 24: Avg Jitter (ms)**
- Type: `timeseries`
- Title: "Average Jitter (ms)"
- Description: "Delay variation. Higher jitter indicates contention instability from backoff manipulation."
- gridPos: h=8, w=8, x=16, y=30
- Unit: `ms`
- Legend: list, placement bottom
- SQL:
```sql
SELECT
  ts AS "time",
  value,
  experiment_id
FROM metrics
WHERE $__timeFilter(ts)
  AND experiment_id LIKE '${run_prefix}%'
  AND metric_name = 'net_avg_jitter_ms'
  AND entity_id = 'network'
ORDER BY ts, experiment_id
```

**Panel ID 25: Channel Busy Ratio**
- Type: `timeseries`
- Title: "Channel Busy Ratio"
- Description: "Channel utilization (0-1). Normal ~0.79. Attack-neg increases to ~0.89 (channel overloaded). Attack-pos drops to ~0.41 (channel monopolized by attacker)."
- gridPos: h=8, w=8, x=0, y=38
- Unit: `percentunit`
- Legend: list, placement bottom
- SQL:
```sql
SELECT
  ts AS "time",
  value,
  experiment_id
FROM metrics
WHERE $__timeFilter(ts)
  AND experiment_id LIKE '${run_prefix}%'
  AND metric_name = 'channel_busy_ratio'
  AND entity_id = 'network'
ORDER BY ts, experiment_id
```

**Panel ID 26: MAC Retransmissions**
- Type: `timeseries`
- Title: "MAC Layer Retransmissions"
- Description: "Cumulative retransmission count. Elevated retransmissions indicate contention and collision from backoff manipulation."
- gridPos: h=8, w=8, x=8, y=38
- Unit: `short`
- Legend: list, placement bottom
- SQL:
```sql
SELECT
  ts AS "time",
  value,
  experiment_id
FROM metrics
WHERE $__timeFilter(ts)
  AND experiment_id LIKE '${run_prefix}%'
  AND metric_name = 'mac_total_retrans'
  AND entity_id = 'network'
ORDER BY ts, experiment_id
```

**Panel ID 27: Active Flows**
- Type: `timeseries`
- Title: "Active Network Flows"
- Description: "Count of active flows in the network (typical range 0-5). Shows network activity level."
- gridPos: h=8, w=8, x=16, y=38
- Unit: `short`
- Legend: list, placement bottom
- SQL:
```sql
SELECT
  ts AS "time",
  value,
  experiment_id
FROM metrics
WHERE $__timeFilter(ts)
  AND experiment_id LIKE '${run_prefix}%'
  AND metric_name = 'net_active_flows'
  AND entity_id = 'network'
ORDER BY ts, experiment_id
```

---

#### Section 3 Row Separator

**Panel ID 102: Row - Per-Experiment Comparison**
- Type: `row`
- Title: "Per-Experiment Comparison (Run Summary)"
- collapsed: false
- gridPos: h=1, w=24, x=0, y=46

---

#### Section 4: Per-Experiment Comparison

**Panel ID 30: Attack Rate by Experiment (Bar Gauge)**
- Type: `bargauge`
- Title: "Attack Rate by Experiment (%)"
- Description: "Attack detection rate per experiment in the selected run. 0% = all normal, 100% = all attack."
- gridPos: h=8, w=12, x=0, y=47
- orientation: horizontal
- displayMode: gradient
- Unit: `percent`, min: 0, max: 100
- Color thresholds: green=0 < yellow=20 < orange=50 < red=80
- SQL (format=table):
```sql
SELECT
  experiment_id as metric,
  ROUND(
    100.0 * SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0),
    1
  ) as value
FROM gcn_predictions
WHERE experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'
GROUP BY experiment_id
ORDER BY experiment_id
```

**Panel ID 31: Avg Confidence by Experiment (Bar Gauge)**
- Type: `bargauge`
- Title: "Avg Confidence by Experiment"
- Description: "Average GCN prediction confidence per experiment. High confidence means the model is certain about its classification (whether normal or attack)."
- gridPos: h=8, w=12, x=12, y=47
- orientation: horizontal
- displayMode: gradient
- Unit: `percentunit`, min: 0, max: 1
- Color thresholds: red < 0.6 < yellow < 0.8 < green
- SQL (format=table):
```sql
SELECT
  experiment_id as metric,
  ROUND(AVG(confidence)::numeric, 3) as value
FROM gcn_predictions
WHERE experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'
GROUP BY experiment_id
ORDER BY experiment_id
```

**Panel ID 32: Network Metrics Summary Table**
- Type: `table`
- Title: "Network Metrics Summary (Per Experiment)"
- Description: "Statistical summary of 6 key metrics across all experiments in the run. Enables side-by-side comparison."
- gridPos: h=10, w=24, x=0, y=55
- SQL (format=table):
```sql
SELECT
  experiment_id as "Experiment",
  metric_name as "Metric",
  ROUND(AVG(value)::numeric, 2) as "Avg",
  ROUND(STDDEV(value)::numeric, 2) as "StdDev",
  ROUND(MIN(value)::numeric, 2) as "Min",
  ROUND(MAX(value)::numeric, 2) as "Max"
FROM metrics
WHERE experiment_id LIKE '${run_prefix}%'
  AND metric_name IN (
    'avg_backoff_slots',
    'net_throughput_mbps',
    'net_packet_loss_ratio',
    'net_avg_delay_ms',
    'net_avg_jitter_ms',
    'channel_busy_ratio'
  )
  AND entity_id = 'network'
GROUP BY experiment_id, metric_name
ORDER BY metric_name, experiment_id
```

Transformations:
- `organize` transform to set column order and rename headers

---

#### Section 4 Row Separator

**Panel ID 103: Row - Inference Performance & Model Info**
- Type: `row`
- Title: "Inference Performance & Model Info"
- collapsed: false
- gridPos: h=1, w=24, x=0, y=65

---

#### Section 5: Inference Performance

**Panel ID 40: Inference Time Over Time**
- Type: `timeseries`
- Title: "GCN Inference Time per Segment (ms)"
- Description: "Time taken by the GCN model to classify each segment. Expected range 1-20ms. Spikes may indicate resource contention."
- gridPos: h=8, w=12, x=0, y=66
- Unit: `ms`, min: 0
- Legend: list, placement bottom, calcs: [mean, max]
- SQL:
```sql
SELECT
  ts_start AS "time",
  inference_time_ms as value,
  experiment_id as metric
FROM gcn_predictions
WHERE $__timeFilter(ts_start)
  AND experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'
  AND inference_time_ms IS NOT NULL
ORDER BY ts_start
```

**Panel ID 41: Prediction Distribution (Pie Chart)**
- Type: `piechart`
- Title: "Prediction Distribution (Normal vs Attack)"
- Description: "Overall proportion of normal vs attack predictions across the selected run."
- gridPos: h=8, w=6, x=12, y=66
- pieType: donut
- displayLabels: [name, percent]
- Legend: table, placement right, values: [value, percent]
- SQL (format=table):
```sql
SELECT
  CASE WHEN prediction = 0 THEN 'Normal' ELSE 'Attack' END as metric,
  COUNT(*) as value
FROM gcn_predictions
WHERE experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'
GROUP BY prediction
ORDER BY prediction
```
Field overrides: `Normal` -> fixedColor green, `Attack` -> fixedColor red.

**Panel ID 42: Model Performance Summary (Stat)**
- Type: `stat`
- Title: "Model Summary"
- Description: "Key model metrics for the selected run and model version."
- gridPos: h=8, w=6, x=18, y=66
- textMode: `value_and_name`
- colorMode: `background`
- orientation: vertical
- Multiple targets (refIds A-E) producing a stat list:
  - A: Total segments (count)
  - B: Avg confidence (percentage string)
  - C: Avg inference time (ms string)
  - D: Unique experiments
  - E: Active model version
- SQLs:
```sql
-- refId A
SELECT COUNT(*) as value, 'Total Segments' as metric
FROM gcn_predictions
WHERE experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'

-- refId B
SELECT CONCAT(ROUND(AVG(confidence)::numeric * 100, 1), '%') as value,
       'Avg Confidence' as metric
FROM gcn_predictions
WHERE experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'

-- refId C
SELECT CONCAT(ROUND(AVG(inference_time_ms)::numeric, 1), ' ms') as value,
       'Avg Inference' as metric
FROM gcn_predictions
WHERE experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'
  AND inference_time_ms IS NOT NULL

-- refId D
SELECT COUNT(DISTINCT experiment_id)::text as value,
       'Experiments' as metric
FROM gcn_predictions
WHERE experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'

-- refId E
SELECT model_version as value, 'Active Model' as metric
FROM gcn_predictions
WHERE experiment_id LIKE '${run_prefix}%'
ORDER BY created_at DESC
LIMIT 1
```

---

#### Section 5 Row Separator

**Panel ID 104: Row - Recent Predictions**
- Type: `row`
- Title: "Recent Predictions Log"
- collapsed: false
- gridPos: h=1, w=24, x=0, y=74

---

#### Section 6: Recent Predictions Table

**Panel ID 50: Recent Predictions**
- Type: `table`
- Title: "Recent GCN Predictions (Last 200)"
- Description: "Latest segment-level GCN predictions. Confidence displayed as gauge bar. Prediction colored green/red."
- gridPos: h=12, w=24, x=0, y=75
- SQL (format=table):
```sql
SELECT
  experiment_id       AS "Experiment",
  entity_id           AS "Entity",
  segment_id          AS "Segment",
  ts_start            AS "Start Time",
  ts_end              AS "End Time",
  CASE WHEN prediction = 0 THEN 'Normal' ELSE 'Attack' END AS "Prediction",
  ROUND(confidence::numeric, 3)                             AS "Confidence",
  CONCAT(
    '[',
    ROUND((probabilities->>0)::numeric, 3), ', ',
    ROUND((probabilities->>1)::numeric, 3),
    ']'
  )                                                         AS "Probabilities [Normal, Attack]",
  ROUND(inference_time_ms::numeric, 1)                      AS "Inference (ms)",
  model_version                                             AS "Model",
  created_at                                                AS "Detected At"
FROM gcn_predictions
WHERE experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'
ORDER BY created_at DESC
LIMIT 200
```

Field overrides:
- `Prediction` column: displayMode = `color-background`, value mappings: Normal->green, Attack->red
- `Confidence` column: displayMode = `gradient-gauge`, unit = percentunit, min=0, max=1, thresholds: red < 0.7 < yellow < 0.9 < green

---

### Annotations

**Annotation 1: Attack Detections**
- Name: "Attack Detections"
- Datasource: `udr_postgres`
- iconColor: `rgba(255, 96, 96, 1)` (red)
- SQL:
```sql
SELECT
  ts_start as time,
  CONCAT('Attack: ', segment_id, ' exp=', experiment_id, ' conf=', ROUND(confidence::numeric, 2)) as text,
  'attack' as tags
FROM gcn_predictions
WHERE $__timeFilter(ts_start)
  AND experiment_id LIKE '${run_prefix}%'
  AND model_version ~ '${model_version:regex}'
  AND prediction = 1
ORDER BY ts_start
```

**Annotation 2: Experiment Start Times**
- Name: "Experiment Starts"
- Datasource: `udr_postgres`
- iconColor: `rgba(0, 211, 255, 1)` (cyan)
- SQL:
```sql
SELECT
  MIN(ts) as time,
  CONCAT('Start: ', experiment_id) as text,
  'experiment' as tags
FROM metrics
WHERE experiment_id LIKE '${run_prefix}%'
GROUP BY experiment_id
ORDER BY MIN(ts)
```

---

## Key Design Decisions

### Decision 1: LIKE operator for run_prefix filtering instead of regex

**Rationale:** The run_prefix variable returns either a `YYYYMMDD-HHMM` prefix OR a full legacy experiment_id. Using `experiment_id LIKE '${run_prefix}%'` works for both cases:
- `LIKE '20260227-2215%'` matches all 4 experiments in that run
- `LIKE 'aligned-normal-test-42%'` matches exactly that one experiment

This is simpler and more performant than regex on indexed columns.

**Important:** The `$__timeFilter()` macro is used where `ts` or `ts_start` is available, but the run_prefix LIKE clause is the primary filter. The time picker in the dashboard helps narrow down the view but is secondary to run selection.

### Decision 2: Default time range set to `now-24h` to `now`

**Rationale:** Experiments run within the current day/session. The time picker helps but the run selector is the primary navigation mechanism. When "All" is selected for run_prefix, the time picker constrains what's shown.

### Decision 3: Model version filter uses regex (same as existing gcn dashboard)

**Rationale:** `model_version ~ '${model_version:regex}'` with allValue `.*` matches all versions when "All" is selected, matching the existing pattern. Default should be `v2.0.0` since v1.0.0 data is superseded.

### Decision 4: Separate run_prefix from experiment_id in the variable

**Rationale:** The existing dashboards use `experiment_filter` with multi-select to pick individual experiments. The new dashboard uses a single `run_prefix` to group experiments by run, which is the natural operator workflow (run a set of experiments, then review them together). This is more useful than picking individual experiments.

### Decision 5: Include the `$__timeFilter()` macro only on time-series panels, not on stat panels

**Rationale:** Stat panels should aggregate ALL data for the selected run regardless of the dashboard time range. Time-series panels need the time filter for proper windowing and rendering. This gives consistent summaries while still allowing time-range filtering for trend views.

---

## Missing DB Fields and Tables Assessment

| Requirement | Status | Notes |
|-------------|--------|-------|
| Run selector (experiment groups) | AVAILABLE | Use `LIKE` on existing `experiment_id` column with prefix matching |
| Raw telemetry (throughput, delay, jitter, loss, backoff, channel_busy) | AVAILABLE | All 13 metric types confirmed in `metrics` table |
| GCN predictions (prediction, confidence) | AVAILABLE | `gcn_predictions` table has all fields |
| Attack detection summary (total, count, rate %) | AVAILABLE | Computed from `gcn_predictions` with COUNT/SUM |
| Confidence scores (avg/min/max per experiment) | AVAILABLE | Computed from `confidence` column |
| Model info (which model is active) | AVAILABLE | `model_version` column in `gcn_predictions` |
| Inference performance (ms per segment) | AVAILABLE | `inference_time_ms` column, 100% populated |
| Per-experiment comparison | AVAILABLE | GROUP BY experiment_id queries |
| Run metadata (start time, topology, git SHA) | PARTIAL | `snapshots` table exists but is EMPTY; timestamps available from `metrics` and `gcn_predictions` |
| Model registry / performance history | MISSING | No dedicated table; only `model_version` string in predictions |

**No schema changes required.** The `snapshots` table being empty is acceptable - the "Run Time Range" stat panel uses MIN/MAX timestamps from `metrics` instead.

**Optional future enhancement:** A `model_registry` table could store training metrics (F1, FP rate) per model version, enabling a "Model Performance History" panel. This is out of scope for this dashboard task.

---

## Potential Issues and Mitigations

### Issue 1: Time range mismatch for older experiments

**Problem:** The default time range `now-24h` to `now` will show nothing for experiments from Feb 10-12, 2026.

**Mitigation:** Add a note in the dashboard description. The `$__timeFilter()` macro on time-series panels uses the dashboard time picker. Users must set the time range to cover the experiment data. Stat panels (without `$__timeFilter`) will always show data for the selected run prefix regardless of time range.

**Alternative:** Use `now-7d` as the default time range to cover recent experiments.

### Issue 2: LIKE filtering and index usage

**Problem:** `experiment_id LIKE '20260227-2215%'` may not use the existing index `ix_metrics_exp_metric_ts` effectively if the query planner chooses a full scan.

**Mitigation:** PostgreSQL supports LIKE prefix patterns with B-tree indexes when using `text_pattern_ops`. The current index does NOT use this operator class. However, with ~387,000 total rows, full scans complete in milliseconds on TimescaleDB. Performance is acceptable without index changes.

**Optional:** Create a new index `CREATE INDEX ix_metrics_exp_id ON metrics (experiment_id text_pattern_ops)` if needed for performance. This is not required at current data volumes.

### Issue 3: Grafana variable `run_prefix` with "All" selected

**Problem:** When "All" is selected, `LIKE '${run_prefix}%'` becomes `LIKE '%'` which matches everything. This is the desired behavior (show all data).

**Mitigation:** Set `allValue` to `%` in the variable definition. Then use `experiment_id LIKE '${run_prefix}'` (without the appended `%`). Alternatively, keep the `%` suffix and set allValue to blank (which makes `LIKE '%'`). The simplest approach: set allValue to `%` and use `experiment_id LIKE '${run_prefix}'` in queries.

**Recommended approach:**
- Set `allValue: "%"` in the variable definition
- Use `experiment_id LIKE '${run_prefix}'` in WHERE clauses (no extra `%`)
- For specific prefix selection (e.g. `20260227-2215`), the query becomes `LIKE '20260227-2215'` which only matches that exact string - this is WRONG.

**Corrected approach:** Use regex for the run filter to handle both cases:
```sql
experiment_id ~ ('^' || regexp_replace('${run_prefix}', '([.^$*+?()[\]{}|\\])', '\\\1', 'g') || '($|-)')
```

This is overly complex. The simplest correct approach is:
- Keep `allValue` empty (Grafana uses `$__all`)
- Use `${run_prefix:regex}` in queries: `experiment_id ~ '${run_prefix:regex}'`
- Set the actual variable options as prefixes in the SQL to include a `.*` suffix

**Final recommended approach (matching existing dashboard patterns):**
```sql
-- Variable SQL:
SELECT DISTINCT
  CASE
    WHEN experiment_id ~ '^\d{8}-\d{4}'
      THEN regexp_replace(experiment_id, '^(\d{8}-\d{4}).*', '\1') || '.*'
    ELSE experiment_id
  END AS run_prefix
FROM metrics
ORDER BY 1 DESC

-- Panel WHERE clause:
AND experiment_id ~ '${run_prefix:regex}'
```

The variable values include `.*` at the end (e.g. `20260227-2215.*`), so `${run_prefix:regex}` becomes `20260227-2215.*` which is a valid regex prefix match. For legacy experiments, the value is the full ID (e.g. `aligned-normal-test-42`) without `.*`, so it matches exactly. Set `allValue: ".*"`.

### Issue 4: Grafana `$__timeFilter()` with `ts_start` column in gcn_predictions

**Problem:** The `gcn_predictions` table's primary time column is `ts_start`, not `ts`. Grafana's `$__timeFilter()` macro requires specifying the correct column.

**Mitigation:** Use `$__timeFilter(ts_start)` explicitly in all GCN prediction queries, matching the existing `gcn-attack-detection.json` pattern.

### Issue 5: `probabilities` JSONB format

**Problem:** `probabilities->>0` and `probabilities->>1` extract array elements as text. Casting `::numeric` is needed.

**Confirmed working:** The existing `gcn-attack-detection.json` already uses this pattern. The format is confirmed as a JSON array: `[0.91, 0.09]`.

### Issue 6: Multiple model versions for same experiment

**Problem:** `aligned-normal-test-42` has predictions from both `v1.0.0` (107 rows) and `v2.0.0` (2327 rows). Without filtering, summary stats will double-count.

**Mitigation:** All GCN panels filter by `model_version ~ '${model_version:regex}'`. Default to `v2.0.0`.

---

## Integration Points

- **Grafana provisioning:** Dashboard JSON is auto-loaded from `/var/lib/grafana/dashboards/` (mounted from `clab/configs/grafana/dashboards/`). Provider config at `clab/configs/grafana/provisioning/dashboards/provider.yml` is unchanged.
- **Datasource:** UID `udr_postgres` connects to `udr-db:5432`, database `udr`, user `udr`, password `udr_pass`. This datasource is already configured and working.
- **TimescaleDB:** The `metrics` table is a hypertable (has 2 child tables per the schema output). TimescaleDB is enabled in the Grafana datasource config. All queries are standard PostgreSQL-compatible.

---

## Testing Strategy

- [ ] Manual: After Grafana restart, open http://localhost:3000 and navigate to NDT folder
- [ ] Manual: Confirm only the unified dashboard appears (old 3 gone)
- [ ] Manual: Select `20260227-2215` in Run Selector variable; verify all 4 experiments appear in panels
- [ ] Manual: Select `20260212-1904`; verify 3 experiments appear
- [ ] Manual: Select `All`; verify summary stats aggregate across all experiments
- [ ] Manual: Select `v2.0.0` in Model Version; verify GCN panels filter correctly
- [ ] Manual: Stat panels (IDs 1-8) should show data regardless of time range setting
- [ ] Manual: Time series panels should respond to time picker adjustments
- [ ] Manual: "Recent Predictions" table shows 200 rows sorted by created_at DESC
- [ ] Verify: `jq . ndt-unified.json` passes (valid JSON)
- [ ] Verify: No "No data" errors in panels when correct time range is set
- [ ] Verify: Attack Rate by Experiment bar gauge shows 0% for normal experiments and 100% for attack experiments (for run `20260227-2215`)

**Test run `20260227-2215` expected values:**

| Experiment | Expected Prediction | Attack Rate | Avg Backoff |
|------------|--------------------|----|-------------|
| seq1-normal | Normal (0) | 0% | ~9.74 |
| seq2-attack-neg | Attack (1) | 100% | ~2.29 |
| seq3-normal | Normal (0) | 0% | ~9.74 |
| seq4-attack-pos | Attack (1) | 100% | ~345.39 |

---

## ADR Candidates

### ADR: Unified Dashboard Replaces Three Specialized Dashboards

**Decision:** Consolidate WP6, WP7.5, and WP8 dashboards into a single `ndt-unified` dashboard.

**Rationale:**
- Operators need a single point of truth for experiment assessment
- All three dashboards query the same datasource; their separation was a result of incremental WP development, not a deliberate design choice
- A unified dashboard with a run selector is more ergonomic than navigating between 3 dashboards

**Status:** Proposed - document as ADR-WP6-02 or ADR-UNIFIED-01 after implementation.

### ADR: Run Selector Uses Regex Prefix Matching

**Decision:** The `run_prefix` variable stores values with `.*` suffix (e.g., `20260227-2215.*`) for prefixed runs and bare IDs for legacy experiments. Panels use `experiment_id ~ '${run_prefix:regex}'`.

**Rationale:** The LIKE approach has edge cases with Grafana's `allValue`. Regex is consistent with existing dashboard patterns (WP7.5 and WP8 both use `~ '${experiment_filter:regex}'`). The `.*` suffix in variable values cleanly handles prefix matching without special allValue logic.

---

## Related Documentation

- `clab/configs/grafana/dashboards/README.md` - Update after implementation
- `docs/WP6-GRAFANA-DASHBOARDS.md` - Note that WP6 dashboard is superseded
- `docs/WP8-PHASE5-GRAFANA-DASHBOARD.md` - Note that WP8 dashboard is superseded
- `docs/CURRENT-STATE.md` - Update dashboard section to reference unified dashboard
- `docs/ALL-ADRS.md` - Add new ADR after implementation
