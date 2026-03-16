# Implementation Plan: MLO Attack Scenarios Grafana Dashboard (v2 - CORRECTED)

## Date
2026-01-05

## Revision History
- **v1 (2026-01-04):** Initial plan with critical issues
- **v2 (2026-01-05):** Corrected version addressing all Codex review findings

## Fixes Applied

This version corrects **5 critical issues** identified by Codex review:

### HIGH SEVERITY FIXES:

1. **Annotation Query SQL Error (Line 493 in v1)**
   - **Problem:** Referenced alias `m` without defining it in FROM clause
   - **Fix:** Changed to CTE approach with proper FROM clause
   - **Impact:** Annotations now render correctly without SQL errors

2. **Hardcoded Experiment IDs (Lines 148, 243, 286 in v1)**
   - **Problem:** Queries hardcoded experiment IDs instead of using `$experiment_filter` variable
   - **Fix:** All queries now use `experiment_id ~ '${experiment_filter:regex}'` pattern
   - **Impact:** Dashboard auto-discovers MLO runs, no manual edits required

### MEDIUM SEVERITY FIXES:

3. **Panel 8 Missing Color Overrides (Line 388 in v1)**
   - **Problem:** `overrides: []` broke scenario color scheme
   - **Fix:** Added series overrides with proper green/red/orange colors
   - **Impact:** Clear visual distinction across all panels

4. **Panel 8 Metric Replacement**
   - **Problem:** `mac_total_tx/rx` always zero (verified via database query)
   - **Fix:** Replaced with `net_active_flows` (30 non-zero data points, range 0-5)
   - **Impact:** Panel now shows meaningful data

5. **Table Panel Misleading Title (Line 409 in v1)**
   - **Problem:** Titled "All Metrics" but only showed 6 of 13 metrics
   - **Fix:** Renamed to "Key Metrics Summary"
   - **Impact:** Accurate documentation

### LOW SEVERITY FIXES:

6. **Invalid Refresh Setting (Line 477 in v1)**
   - **Problem:** `refresh: false` causes Grafana import warnings
   - **Fix:** Changed to `refresh: ""` (proper Grafana format)
   - **Impact:** Clean import without warnings

---

## Objective
Create a comprehensive Grafana dashboard to visualize and compare Wi-Fi 7 MLO backoff manipulation attack scenarios (normal, positive bias, negative bias). The dashboard will enable researchers to understand attack behavior, measure network impact, and identify attack indicators across MLO metrics with **dynamic experiment discovery and zero manual configuration**.

---

## Background
WP7.5 implemented three MLO attack scenarios with complete telemetry pipeline integration:
- **Normal**: Baseline with no attack (avg_backoff_slots: ~5)
- **Positive Bias**: Aggressive transmission attack (+5000 bias, avg_backoff_slots: ~1411)
- **Negative Bias**: Extreme aggressive attack (-5000 bias, avg_backoff_slots: ~2.2)

All 3 scenarios now have complete data in TimescaleDB (260 rows each, 13 metrics per 0.1s window).

**Current Data State (Verified):**
```
20260103-1400-mlo-normal-42:     260 rows (throughput: 262.5 Mbps)
20260103-1400-mlo-attack-pos-42: 260 rows (throughput: 41.7 Mbps, -84%)
20260103-1400-mlo-attack-neg-42: 260 rows (throughput: 146.7 Mbps, -44%)
```

**Attack Impact Observed:**
- Positive bias: Backoff increased 285x, throughput dropped 84%
- Negative bias: Backoff decreased 56%, throughput dropped 44%

**Metric Verification (Panel 8):**
- `mac_total_tx/rx`: Always 0 (verified via DB query - REJECTED)
- `mac_total_ack`: Always 0 (REJECTED)
- `mac_drop_count`: 2 non-zero points only (REJECTED)
- `phy_drop_count`: Always 0 (REJECTED)
- **`net_active_flows`**: 30 non-zero points, range 0-5 (SELECTED) ✅

---

## Prerequisites
- [x] WP7.5 complete - MLO scenarios implemented
- [x] Exporter reliability fix deployed
- [x] All 3 scenarios have data in TimescaleDB
- [x] 13 MLO metrics available
- [x] Grafana provisioning configured (WP6)
- [x] Existing dashboard pattern established (wp6-throughput-compare.json)
- [x] Metric validation completed (mac_total_tx/rx confirmed zero)

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------||
| `clab/configs/grafana/dashboards/mlo-attack-scenarios.json` | Create | Main MLO attack comparison dashboard |
| `docs/WP7-ONE-COMMAND-PIPELINE.md` | Modify | Add dashboard usage documentation |
| `docs/QUICK-REFERENCE.md` | Modify | Add dashboard access info |
| `.claude/docs/context/current-session.md` | Update | Track plan creation |

---

## Implementation Steps

### Step 1: Design Dashboard Layout
**Action:** Define panel organization strategy

**Layout Decision: Metric-focused rows with scenario comparison**
- **Top Row (Hero Metrics):** Attack indicator + primary impact
  - Panel 1: Backoff Slots Comparison (THE attack indicator)
  - Panel 2: Throughput Impact (primary degradation metric)
- **Row 2 (Network Layer):** Network performance degradation
  - Panel 3: Packet Loss Ratio
  - Panel 4: Average Delay
  - Panel 5: Average Jitter
- **Row 3 (MAC Layer):** MAC-level impact
  - Panel 6: Retransmissions
  - Panel 7: Channel Busy Ratio
  - Panel 8: Active Flows (CORRECTED - was MAC Tx/Rx)
- **Row 4 (Statistical Summary):** Aggregate comparison
  - Panel 9: Statistical Summary Table

**Design Rationale:**
- Each panel shows all scenarios as different series (time-aligned comparison)
- Color coding: Green (normal), Red (positive), Orange (negative)
- Focus on 8 key metrics (not all 13 - avoid overwhelming researchers)
- Statistical table provides numerical comparison

**Expected Outcome:**
- Clear visual hierarchy: Attack indicator → Impact → Details
- Time-synchronized panels for correlation analysis
- Researchers can answer: "What does this attack do to the network?"

**Verification:**
- Sketch layout in JSON structure
- Confirm panel count: 9 panels total
- Confirm row structure: 4 rows

---

### Step 2: Configure Template Variables
**Action:** Define dynamic experiment filter with auto-discovery

**CORRECTED Variable Configuration:**

#### experiment_filter (Query-Based Auto-Discovery)
```json
{
  "name": "experiment_filter",
  "type": "query",
  "label": "Experiment Filter",
  "datasource": {
    "type": "postgres",
    "uid": "udr_postgres"
  },
  "query": "SELECT DISTINCT experiment_id FROM metrics WHERE experiment_id ~ '.*-mlo-.*' ORDER BY experiment_id DESC",
  "refresh": 1,
  "includeAll": true,
  "multi": true,
  "allValue": ".*-mlo-.*",
  "current": {
    "text": "All",
    "value": [
      "$__all"
    ],
    "selected": true
  },
  "options": []
}
```

**Key Features:**
- **Auto-discovery:** Query finds all experiment IDs matching MLO pattern
- **Multi-select:** Users can compare specific experiments
- **Regex support:** Uses PostgreSQL regex operator `~` for filtering
- **Refresh on load:** Always shows latest experiments
- **All by default:** Shows all MLO experiments on first load

**Usage in Panel Queries:**
```sql
WHERE experiment_id ~ '${experiment_filter:regex}'
```

**Regex Pattern Handling:**
- Single selection: `20260103-1400-mlo-normal-42` → Exact match
- Multi-selection: `(20260103-1400-mlo-normal-42|20260103-1400-mlo-attack-pos-42)` → OR pattern
- All: `.*-mlo-.*` → Matches any MLO experiment

**Time Range:**
- Use Grafana's built-in time picker
- Default: Absolute time range covering 2026-01-04 11:44-11:53
- Note: Simulation timestamps are in 2026 (not "now")

**Expected Outcome:**
- Template variable auto-populates from database
- New experiments appear automatically (no dashboard edits)
- Users can filter to specific scenarios

**Verification:**
```bash
# Test query directly
docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "
  SELECT DISTINCT experiment_id
  FROM metrics
  WHERE experiment_id ~ '.*-mlo-.*'
  ORDER BY experiment_id DESC;
"
# Expected: 3 experiment IDs (normal, pos, neg)
```

---

### Step 3: SQL Query Templates (CORRECTED)
**Action:** Design reusable SQL query patterns with dynamic filtering

**Pattern 1: Time Series with Dynamic Multi-Scenario Comparison**
```sql
-- Template for metric comparison across scenarios
SELECT
  ts AS "time",
  value,
  experiment_id
FROM metrics
WHERE
  $__timeFilter(ts)
  AND metric_name = '<METRIC_NAME>'
  AND experiment_id ~ '${experiment_filter:regex}'
  AND entity_id = 'network'
ORDER BY ts, experiment_id;
```

**Key Changes from v1:**
- ❌ Removed: `AND experiment_id IN ('20260103-1400-mlo-normal-42', ...)`
- ✅ Added: `AND experiment_id ~ '${experiment_filter:regex}'`
- **Impact:** Dynamic filtering, no hardcoded IDs

**Pattern 2: Statistical Comparison Table**
```sql
-- Template for statistical summary
SELECT
  experiment_id,
  metric_name,
  ROUND(AVG(value)::numeric, 2) as avg,
  ROUND(STDDEV(value)::numeric, 2) as stddev,
  ROUND(MIN(value)::numeric, 2) as min,
  ROUND(MAX(value)::numeric, 2) as max
FROM metrics
WHERE
  $__timeFilter(ts)
  AND metric_name IN (
    'avg_backoff_slots',
    'net_throughput_mbps',
    'net_packet_loss_ratio',
    'net_avg_delay_ms',
    'mac_total_retrans',
    'channel_busy_ratio'
  )
  AND experiment_id ~ '${experiment_filter:regex}'
  AND entity_id = 'network'
GROUP BY experiment_id, metric_name
ORDER BY metric_name, experiment_id;
```

**Query Optimization Notes:**
- Always filter by `entity_id = 'network'` (only one entity in MLO data)
- Use `$__timeFilter(ts)` for Grafana time range integration
- Order by `ts, experiment_id` for consistent series rendering
- Use experiment_id as series name for legend
- Use PostgreSQL regex operator `~` (not `=` or `IN`)

**Expected Outcome:**
- Dynamic queries adapt to variable selection
- Consistent query structure across dashboard
- Efficient queries (indexed on ts, experiment_id, metric_name)

**Verification:**
- Test each query pattern in Grafana Query Inspector
- Verify series count matches selected experiments
- Confirm time alignment across queries

---

### Step 4: Build Priority Panels (CORRECTED)
**Action:** Create the 9 key panels in priority order with dynamic queries

#### Panel 1: Backoff Slots Comparison (HERO METRIC)
**Purpose:** Show THE attack indicator - backoff manipulation

**Configuration:**
```json
{
  "id": 1,
  "type": "timeseries",
  "title": "Average Backoff Slots (Attack Indicator)",
  "description": "Shows backoff manipulation: Normal ~5, Positive ~1411 (+285x), Negative ~2.2 (-56%)",
  "datasource": {"type": "postgres", "uid": "udr_postgres"},
  "gridPos": {"h": 10, "w": 12, "x": 0, "y": 0},
  "targets": [{
    "refId": "A",
    "format": "time_series",
    "rawSql": "SELECT ts AS \\"time\\", value, experiment_id FROM metrics WHERE $__timeFilter(ts) AND metric_name = 'avg_backoff_slots' AND experiment_id ~ '${experiment_filter:regex}' AND entity_id = 'network' ORDER BY ts, experiment_id;"
  }],
  "fieldConfig": {
    "defaults": {
      "unit": "slots",
      "color": {"mode": "palette-classic"}
    },
    "overrides": [
      {
        "matcher": {"id": "byRegex", "options": ".*-normal-.*"},
        "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "green"}}]
      },
      {
        "matcher": {"id": "byRegex", "options": ".*-attack-pos-.*"},
        "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}}]
      },
      {
        "matcher": {"id": "byRegex", "options": ".*-attack-neg-.*"},
        "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "orange"}}]
      }
    ]
  },
  "options": {
    "legend": {"displayMode": "table", "placement": "bottom", "showLegend": true, "calcs": ["mean", "max", "min"]},
    "tooltip": {"mode": "multi"}
  }
}
```

**Key Changes from v1:**
- ✅ Query uses `experiment_id ~ '${experiment_filter:regex}'`
- ✅ Color overrides use `byRegex` matcher (works with any experiment ID)
- **Impact:** Works with any MLO experiment, not just hardcoded ones

---

#### Panel 2: Throughput Impact (PRIMARY IMPACT METRIC)
**Purpose:** Show network performance degradation

**Configuration:**
```json
{
  "id": 2,
  "type": "timeseries",
  "title": "Network Throughput (Mbps)",
  "description": "Impact: Normal 262.5 Mbps, Positive 41.7 Mbps (-84%), Negative 146.7 Mbps (-44%)",
  "datasource": {"type": "postgres", "uid": "udr_postgres"},
  "gridPos": {"h": 10, "w": 12, "x": 12, "y": 0},
  "targets": [{
    "refId": "A",
    "format": "time_series",
    "rawSql": "SELECT ts AS \\"time\\", value, experiment_id FROM metrics WHERE $__timeFilter(ts) AND metric_name = 'net_throughput_mbps' AND experiment_id ~ '${experiment_filter:regex}' AND entity_id = 'network' ORDER BY ts, experiment_id;"
  }],
  "fieldConfig": {
    "defaults": {"unit": "Mbps"},
    "overrides": [
      {
        "matcher": {"id": "byRegex", "options": ".*-normal-.*"},
        "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "green"}}]
      },
      {
        "matcher": {"id": "byRegex", "options": ".*-attack-pos-.*"},
        "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}}]
      },
      {
        "matcher": {"id": "byRegex", "options": ".*-attack-neg-.*"},
        "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "orange"}}]
      }
    ]
  },
  "options": {
    "legend": {"displayMode": "table", "placement": "bottom", "showLegend": true, "calcs": ["mean", "last"]},
    "tooltip": {"mode": "multi"}
  }
}
```

---

#### Panel 3: Packet Loss Ratio
**Purpose:** Show quality degradation

**Configuration:** Same structure as Panel 2, but:
- `metric_name = 'net_packet_loss_ratio'`
- `unit = "percentunit"` (0-1 scale)
- Title: "Packet Loss Ratio"
- Description: "Network quality degradation due to backoff manipulation"
- GridPos: `{"h": 8, "w": 8, "x": 0, "y": 10}`
- **CORRECTED Query:** `WHERE ... AND experiment_id ~ '${experiment_filter:regex}' ...`
- **CORRECTED Overrides:** Use `byRegex` matchers

---

#### Panel 4: Average Delay
**Purpose:** Show latency impact

**Configuration:** Same structure, but:
- `metric_name = 'net_avg_delay_ms'`
- `unit = "ms"`
- Title: "Average Packet Delay"
- GridPos: `{"h": 8, "w": 8, "x": 8, "y": 10}`
- **CORRECTED Query:** `WHERE ... AND experiment_id ~ '${experiment_filter:regex}' ...`
- **CORRECTED Overrides:** Use `byRegex` matchers

---

#### Panel 5: Average Jitter
**Purpose:** Show delay variation

**Configuration:** Same structure, but:
- `metric_name = 'net_avg_jitter_ms'`
- `unit = "ms"`
- Title: "Average Jitter"
- GridPos: `{"h": 8, "w": 8, "x": 16, "y": 10}`
- **CORRECTED Query:** `WHERE ... AND experiment_id ~ '${experiment_filter:regex}' ...`
- **CORRECTED Overrides:** Use `byRegex` matchers

---

#### Panel 6: MAC Retransmissions
**Purpose:** Show MAC-level impact

**Configuration:** Same structure, but:
- `metric_name = 'mac_total_retrans'`
- `unit = "short"` (count)
- Title: "MAC Layer Retransmissions"
- Description: "Retransmission count indicates contention/collision rate"
- GridPos: `{"h": 8, "w": 8, "x": 0, "y": 18}`
- **CORRECTED Query:** `WHERE ... AND experiment_id ~ '${experiment_filter:regex}' ...`
- **CORRECTED Overrides:** Use `byRegex` matchers

---

#### Panel 7: Channel Busy Ratio
**Purpose:** Show contention indicator

**Configuration:** Same structure, but:
- `metric_name = 'channel_busy_ratio'`
- `unit = "percentunit"`
- Title: "Channel Busy Ratio"
- Description: "Channel utilization and contention level"
- GridPos: `{"h": 8, "w": 8, "x": 8, "y": 18}`
- **CORRECTED Query:** `WHERE ... AND experiment_id ~ '${experiment_filter:regex}' ...`
- **CORRECTED Overrides:** Use `byRegex` matchers

---

#### Panel 8: Active Flows (CORRECTED - Replaced MAC Tx/Rx)
**Purpose:** Show network activity level

**Rationale for Metric Change:**
- **Rejected:** `mac_total_tx/rx` - Always 0 (verified via database query)
- **Rejected:** `mac_total_ack` - Always 0
- **Rejected:** `mac_drop_count` - Only 2 non-zero points
- **Rejected:** `phy_drop_count` - Always 0
- **SELECTED:** `net_active_flows` - 30 non-zero points, range 0-5, meaningful variation

**Configuration:**
```json
{
  "id": 8,
  "type": "timeseries",
  "title": "Network Active Flows",
  "description": "Number of active flows (range 0-5). Indicates network activity level during attack scenarios.",
  "datasource": {"type": "postgres", "uid": "udr_postgres"},
  "gridPos": {"h": 8, "w": 8, "x": 16, "y": 18},
  "targets": [{
    "refId": "A",
    "format": "time_series",
    "rawSql": "SELECT ts AS \\"time\\", value, experiment_id FROM metrics WHERE $__timeFilter(ts) AND metric_name = 'net_active_flows' AND experiment_id ~ '${experiment_filter:regex}' AND entity_id = 'network' ORDER BY ts, experiment_id;"
  }],
  "fieldConfig": {
    "defaults": {"unit": "short"},
    "overrides": [
      {
        "matcher": {"id": "byRegex", "options": ".*-normal-.*"},
        "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "green"}}]
      },
      {
        "matcher": {"id": "byRegex", "options": ".*-attack-pos-.*"},
        "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}}]
      },
      {
        "matcher": {"id": "byRegex", "options": ".*-attack-neg-.*"},
        "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "orange"}}]
      }
    ]
  },
  "options": {
    "legend": {"displayMode": "table", "placement": "bottom"},
    "tooltip": {"mode": "multi"}
  }
}
```

**Key Changes from v1:**
- ❌ Removed: Dual-query TX/RX approach
- ✅ Added: Single metric `net_active_flows` with verified data
- ✅ Added: Color overrides (was missing in v1)
- ✅ Added: Dynamic query with `experiment_filter`

**Verification Query:**
```bash
docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "
  SELECT
    experiment_id,
    COUNT(*) FILTER (WHERE value <> 0) AS non_zero_points,
    ROUND(AVG(value)::numeric, 2) AS avg_flows,
    MIN(value) AS min_flows,
    MAX(value) AS max_flows
  FROM metrics
  WHERE metric_name = 'net_active_flows'
    AND experiment_id LIKE '20260103-1400-mlo%'
  GROUP BY experiment_id
  ORDER BY experiment_id;
"
```

---

#### Panel 9: Statistical Summary Table (CORRECTED)
**Purpose:** Numerical comparison across key metrics

**Configuration:**
```json
{
  "id": 9,
  "type": "table",
  "title": "Key Metrics Summary",
  "description": "Statistical comparison of 6 key metrics across selected scenarios",
  "datasource": {"type": "postgres", "uid": "udr_postgres"},
  "gridPos": {"h": 10, "w": 24, "x": 0, "y": 26},
  "targets": [{
    "refId": "A",
    "format": "table",
    "rawSql": "SELECT experiment_id, metric_name, ROUND(AVG(value)::numeric, 2) as avg, ROUND(STDDEV(value)::numeric, 2) as stddev, ROUND(MIN(value)::numeric, 2) as min, ROUND(MAX(value)::numeric, 2) as max FROM metrics WHERE $__timeFilter(ts) AND metric_name IN ('avg_backoff_slots', 'net_throughput_mbps', 'net_packet_loss_ratio', 'net_avg_delay_ms', 'mac_total_retrans', 'channel_busy_ratio') AND experiment_id ~ '${experiment_filter:regex}' AND entity_id = 'network' GROUP BY experiment_id, metric_name ORDER BY metric_name, experiment_id;"
  }],
  "transformations": [
    {
      "id": "organize",
      "options": {
        "excludeByName": {},
        "indexByName": {
          "experiment_id": 0,
          "metric_name": 1,
          "avg": 2,
          "stddev": 3,
          "min": 4,
          "max": 5
        },
        "renameByName": {
          "experiment_id": "Experiment",
          "metric_name": "Metric",
          "avg": "Average",
          "stddev": "Std Dev",
          "min": "Min",
          "max": "Max"
        }
      }
    }
  ],
  "options": {
    "showHeader": true,
    "sortBy": [{"displayName": "Metric", "desc": false}]
  }
}
```

**Key Changes from v1:**
- ✅ Title: "Key Metrics Summary" (was "All Metrics" - misleading)
- ✅ Query uses `experiment_id ~ '${experiment_filter:regex}'`
- **Impact:** Accurate title, dynamic filtering

---

**Panel Summary - All Corrections Applied:**
- 9 panels created with consistent styling
- ✅ All panels use dynamic `${experiment_filter:regex}` (no hardcoded IDs)
- ✅ All panels have color overrides (green/red/orange)
- ✅ Panel 8 uses verified metric (`net_active_flows` not `mac_total_tx/rx`)
- ✅ Table panel has accurate title ("Key Metrics Summary")
- Time-aligned data across all panels

**Verification:**
- Load dashboard in Grafana
- Verify all panels render without errors
- Check time alignment (hover over panels simultaneously)
- Confirm color coding matches scenarios
- Verify legend calculations (mean, max, min)
- Test experiment filter dropdown

---

### Step 5: Configure Dashboard Metadata (CORRECTED)
**Action:** Set dashboard-level configuration

**Dashboard JSON Structure:**
```json
{
  "uid": "mlo-attack-scenarios",
  "title": "NDT WP7.5 - MLO Attack Scenarios Comparison",
  "description": "Comparison of Wi-Fi 7 MLO backoff manipulation attacks: Normal (baseline), Positive Bias (+5000), Negative Bias (-5000). Dashboard auto-discovers MLO experiments from database.",
  "tags": ["ndt", "mlo", "wifi7", "attack", "backoff", "wp7"],
  "timezone": "UTC",
  "schemaVersion": 39,
  "version": 1,
  "editable": true,
  "refresh": "",
  "time": {
    "from": "2026-01-04T11:44:00.000Z",
    "to": "2026-01-04T11:53:00.000Z"
  },
  "timepicker": {
    "refresh_intervals": ["5s", "10s", "30s", "1m"],
    "time_options": ["5m", "15m", "1h", "6h", "12h", "24h"]
  },
  "annotations": {
    "list": [
      {
        "name": "Experiment Start Times",
        "datasource": {"type": "postgres", "uid": "udr_postgres"},
        "enable": true,
        "iconColor": "rgba(0, 211, 255, 1)",
        "query": "WITH exp_starts AS ( SELECT experiment_id, MIN(ts) as start_time FROM metrics WHERE experiment_id ~ '${experiment_filter:regex}' GROUP BY experiment_id ) SELECT start_time as time, experiment_id as text, 'experiment' as tags FROM exp_starts ORDER BY start_time"
      }
    ]
  },
  "templating": {
    "list": [
      {
        "name": "experiment_filter",
        "type": "query",
        "label": "Experiment Filter",
        "datasource": {
          "type": "postgres",
          "uid": "udr_postgres"
        },
        "query": "SELECT DISTINCT experiment_id FROM metrics WHERE experiment_id ~ '.*-mlo-.*' ORDER BY experiment_id DESC",
        "refresh": 1,
        "includeAll": true,
        "multi": true,
        "allValue": ".*-mlo-.*",
        "current": {
          "text": "All",
          "value": ["$__all"],
          "selected": true
        },
        "options": []
      }
    ]
  },
  "panels": [
    // ... panels from Step 4
  ]
}
```

**Key Changes from v1:**
- ✅ `refresh: ""` (was `refresh: false` - invalid)
- ✅ Annotation query uses CTE with proper FROM clause (was missing alias `m`)
- ✅ Template variable is query-based (was custom with hardcoded IDs)
- ✅ Description mentions auto-discovery feature

**Key Configuration Notes:**
- **Time range:** Absolute time (2026-01-04 11:44-11:53 UTC) covering all 3 experiments
- **Refresh:** Empty string (proper Grafana format, no warnings)
- **Tags:** Enables discovery in Grafana dashboard search
- **Schema version:** 39 (matches existing WP6 dashboard)
- **Annotations:** CTE-based query for experiment start times (FIXED SQL error)
- **UID:** `mlo-attack-scenarios` (stable reference)

**Expected Outcome:**
- Dashboard loads with correct time range
- No "No Data" errors (time range covers data)
- Dashboard appears in "NDT" folder (from provisioning config)
- Tags enable search: "mlo", "attack", "wifi7"
- Experiment filter auto-populates

**Verification:**
- Navigate to dashboard via Grafana UI
- Check time range picker shows absolute times
- Verify all panels have data
- Test template variable dropdown (should show 3 experiments)

---

### Step 6: Testing Strategy (CORRECTED)
**Action:** Comprehensive dashboard validation

#### Test 1: Data Presence Verification
```bash
# Verify all metrics appear in all panels
# Expected: No "No Data" errors in any panel

# Open dashboard: http://localhost:3000/d/mlo-attack-scenarios
# Check each panel:
# - Panel 1: Backoff slots (3 series visible)
# - Panel 2: Throughput (3 series visible)
# - Panel 3-8: All show 3 series
# - Panel 9: Table with 18 rows (3 experiments × 6 metrics)
```

**Pass Criteria:**
- All 9 panels render data
- Each time series panel shows exactly 3 series (one per scenario)
- Statistical table shows 18 rows
- No Grafana query errors in browser console

---

#### Test 2: Dynamic Experiment Filter
**NEW TEST - Critical for v2 validation**

```bash
# Verify experiment filter auto-discovery
# Steps:
# 1. Open dashboard - variable should auto-populate
# 2. Check dropdown shows 3 experiments
# 3. Select only "normal" scenario
# 4. Verify only green series appears in all panels
# 5. Select "All"
# 6. Verify all 3 series return

# Add new experiment
make run-mlo-exp EXP_ID=20260105-1000-mlo-test-99 SCENARIO=normal

# Refresh dashboard (Ctrl+R)
# Expected: New experiment appears in dropdown automatically
```

**Pass Criteria:**
- Dropdown auto-populates on dashboard load
- Shows all MLO experiments from database
- Multi-select works correctly
- "All" option shows all scenarios
- New experiments appear after dashboard refresh (no manual edits)

---

#### Test 3: Time Alignment Check
```bash
# Verify all panels show same time window
# Expected: Hovering over any panel shows data for same timestamp across all panels

# Steps:
# 1. Hover over Panel 1 (Backoff Slots) at a specific time
# 2. Note the timestamp shown in tooltip
# 3. Hover over Panel 2 (Throughput) at visually similar x-position
# 4. Verify timestamp matches

# Alternative: Use Grafana's "Shared crosshair" feature
# Settings → Dashboard Settings → Time Options → Graph Tooltip: Shared crosshair
```

**Pass Criteria:**
- All panels synchronized to same time range
- Shared crosshair shows consistent timestamps
- X-axis labels aligned across panels

---

#### Test 4: Color Coding Verification
```bash
# Verify scenario color scheme
# Expected:
# - Normal (.*-normal-.*): Green
# - Positive (.*-attack-pos-.*): Red
# - Negative (.*-attack-neg-.*): Orange

# Visual check in legend and line colors
# Test with different experiment IDs (not just 20260103-1400-mlo-*)
```

**Pass Criteria:**
- Legend colors match scenario types
- Line colors consistent across all panels
- Regex matchers work with any experiment ID (not just hardcoded ones)
- Visually distinct (no confusion between series)

---

#### Test 5: Panel 8 Data Validation
**NEW TEST - Verify metric replacement**

```bash
# Verify net_active_flows shows meaningful data
docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "
  SELECT
    experiment_id,
    COUNT(*) FILTER (WHERE value <> 0) AS non_zero_points,
    ROUND(AVG(value)::numeric, 2) AS avg_flows,
    MIN(value) AS min_flows,
    MAX(value) AS max_flows
  FROM metrics
  WHERE metric_name = 'net_active_flows'
    AND experiment_id LIKE '20260103-1400-mlo%'
  GROUP BY experiment_id
  ORDER BY experiment_id;
"
# Expected: 30 non-zero points, range 0-5

# Visual check in Panel 8
# Expected: Time series showing flow count variations
```

**Pass Criteria:**
- Panel 8 shows non-zero data
- Series has meaningful variation (not flat line)
- Tooltip shows flow count values (0-5 range)
- Color coding applied correctly

---

#### Test 6: Annotation Query Validation
**NEW TEST - Verify SQL fix**

```bash
# Verify annotations render without errors
# Steps:
# 1. Open dashboard
# 2. Check browser console for SQL errors (should be none)
# 3. Look for vertical annotation lines at experiment start times
# 4. Hover over annotation markers - should show experiment ID

# Test annotation query directly
docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "
  WITH exp_starts AS (
    SELECT experiment_id, MIN(ts) as start_time
    FROM metrics
    WHERE experiment_id ~ '.*-mlo-.*'
    GROUP BY experiment_id
  )
  SELECT start_time, experiment_id
  FROM exp_starts
  ORDER BY start_time;
"
# Expected: 3 rows with experiment IDs and start times
```

**Pass Criteria:**
- No SQL errors in browser console
- Annotation markers visible on panels
- Hover tooltip shows correct experiment ID
- CTE query executes successfully

---

#### Test 7: Statistical Accuracy Validation
```bash
# Verify statistical table matches database
# Compare table values with direct database query

docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "
SELECT
  experiment_id,
  metric_name,
  ROUND(AVG(value)::numeric, 2) as avg,
  ROUND(STDDEV(value)::numeric, 2) as stddev,
  ROUND(MIN(value)::numeric, 2) as min,
  ROUND(MAX(value)::numeric, 2) as max
FROM metrics
WHERE metric_name IN ('avg_backoff_slots', 'net_throughput_mbps')
  AND experiment_id LIKE '20260103-1400-mlo%'
GROUP BY experiment_id, metric_name
ORDER BY metric_name, experiment_id;
"

# Compare output with Panel 9 (Statistical Summary Table)
```

**Pass Criteria:**
- Table values match database query (within rounding)
- All 6 metrics appear in table
- 3 experiments per metric (18 rows total)
- Table title is "Key Metrics Summary" (not "All Metrics")

---

**Overall Testing Checklist (CORRECTED):**
- [ ] Test 1: Data presence (all panels show data)
- [ ] **Test 2: Dynamic experiment filter (NEW - critical for v2)**
- [ ] Test 3: Time alignment (synchronized panels)
- [ ] Test 4: Color coding (green/red/orange with regex matchers)
- [ ] **Test 5: Panel 8 data validation (NEW - verify net_active_flows)**
- [ ] **Test 6: Annotation query validation (NEW - verify SQL fix)**
- [ ] Test 7: Statistical accuracy (matches DB)

---

### Step 7: Documentation Updates
**Action:** Update project documentation with dashboard usage

#### Update 1: WP7-ONE-COMMAND-PIPELINE.md
**Location:** `docs/WP7-ONE-COMMAND-PIPELINE.md`
**Section:** Add new section after "WP7.5: MLO Attack Scenarios"

```markdown
### MLO Attack Scenarios Dashboard

**Access:** http://localhost:3000/d/mlo-attack-scenarios

**Purpose:** Compare Wi-Fi 7 MLO backoff manipulation attacks and measure network impact.

**Key Feature:** Dashboard auto-discovers MLO experiments from database - no manual configuration required.

#### Available Scenarios
- **Normal**: Baseline with no attack (green)
- **Positive Bias**: Aggressive transmission attack (+5000, red)
- **Negative Bias**: Extreme aggressive attack (-5000, orange)

#### Dynamic Experiment Filter

The dashboard automatically discovers all MLO experiments from the database using a query-based template variable:

```sql
SELECT DISTINCT experiment_id FROM metrics WHERE experiment_id ~ '.*-mlo-.*' ORDER BY experiment_id DESC
```

**How it works:**
- New experiments appear automatically after dashboard refresh
- Multi-select dropdown allows comparing specific scenarios
- "All" option shows all MLO experiments
- No manual dashboard edits required

#### Key Panels

1. **Average Backoff Slots** (Attack Indicator)
   - Shows backoff manipulation: Normal ~5, Positive ~1411 (+285x), Negative ~2.2 (-56%)

2. **Network Throughput** (Primary Impact)
   - Impact: Normal 262.5 Mbps, Positive 41.7 Mbps (-84%), Negative 146.7 Mbps (-44%)

3. **Packet Loss Ratio** (Quality Degradation)
   - Shows quality degradation due to backoff manipulation

4. **Average Delay** (Latency Impact)
   - Packet delivery latency changes

5. **Average Jitter** (Delay Variation)
   - Delay consistency impact

6. **MAC Retransmissions** (MAC Layer Impact)
   - Retransmission count indicates contention/collision rate

7. **Channel Busy Ratio** (Contention Indicator)
   - Channel utilization and contention level

8. **Network Active Flows** (Activity Level)
   - Number of active flows (0-5 range) indicating network activity

9. **Key Metrics Summary** (Statistical Comparison)
   - Avg/StdDev/Min/Max for 6 key metrics across scenarios

#### Usage

```bash
# Run all three scenarios
make run-mlo-exp EXP_ID=20260105-1500-mlo-normal-42 SCENARIO=normal
make run-mlo-exp EXP_ID=20260105-1500-mlo-attack-pos-42 SCENARIO=positive
make run-mlo-exp EXP_ID=20260105-1500-mlo-attack-neg-42 SCENARIO=negative

# Open dashboard
# http://localhost:3000/d/mlo-attack-scenarios

# Refresh dashboard (Ctrl+R) to see new experiments
# Use experiment filter dropdown to select specific runs
```

#### Interpreting Results

**Attack Indicator:**
- Backoff slots manipulation is THE key indicator
- Positive bias: 100x-300x increase (aggressive early transmission)
- Negative bias: 50%-90% decrease (extremely aggressive)

**Impact Metrics:**
- Throughput: Primary measure of attack success
- Packet Loss: Secondary quality indicator
- Delay/Jitter: Tertiary QoS impact
- Retransmissions: MAC layer stress indicator

**Research Questions Answered:**
1. How does backoff manipulation affect throughput? → See Panel 1 vs Panel 2 correlation
2. What's the impact on packet loss? → Panel 3 shows quality degradation
3. Which metrics are most sensitive? → Panel 9 statistical table shows variance
4. Can we visually distinguish attacks? → Color-coded time series make patterns obvious

#### Troubleshooting

| Issue | Solution |
|-------|----------|
| No data in panels | Adjust time range to cover experiment timestamps (use absolute, not relative) |
| Only 1-2 series visible | Check experiment filter dropdown - select "All" |
| Time series not aligned | Verify all experiments have same time window length |
| Statistical table empty | Check metric names in query match database (case-sensitive) |
| New experiments don't appear | Refresh dashboard (Ctrl+R) - they auto-discover |
```

**Expected Outcome:**
- WP7 documentation includes complete dashboard usage guide
- Researchers know how to use dynamic experiment filter
- Troubleshooting guide prevents common issues

---

#### Update 2: QUICK-REFERENCE.md
**Location:** `docs/QUICK-REFERENCE.md`
**Section:** Add to "Grafana Dashboards" section

```markdown
### Grafana Dashboards

| Dashboard | URL | Purpose |
|-----------|-----|---------|
| Throughput Comparison | http://localhost:3000/d/ndt-wp6-throughput-compare | Compare throughput across experiments |
| **MLO Attack Scenarios** | http://localhost:3000/d/mlo-attack-scenarios | Compare MLO backoff manipulation attacks (WP7.5) |

#### MLO Attack Dashboard
- **Experiment Filter:** Auto-discovers MLO runs from database (refresh to see new experiments)
- **Time Range:** Use absolute time, not relative (data is historical)
- **Scenarios:** Green=Normal, Red=Positive Attack, Orange=Negative Attack
- **Key Metric:** Backoff slots (Panel 1) shows attack indicator
- **Impact Metric:** Throughput (Panel 2) shows degradation
```

**Expected Outcome:**
- Quick reference includes dashboard URLs
- Key usage notes readily available
- Dynamic filter feature highlighted

---

#### Update 3: Session Context
**Location:** `.claude/docs/context/current-session.md`

Add to "Completed Recently" section:
```markdown
- Created MLO attack scenarios Grafana dashboard implementation plan v2 (CORRECTED)
- Fixed 6 critical issues from Codex review (annotation SQL, hardcoded IDs, Panel 8 metric, color overrides, table title, refresh setting)
- Implemented dynamic experiment discovery with query-based template variable
- Verified Panel 8 replacement metric (net_active_flows) has meaningful data
- Plan includes 9 panels, 7 test scenarios, full documentation
- Ready for implementation: mlo-attack-dashboard-plan-v2.md
```

**Expected Outcome:**
- Session context updated with v2 plan creation
- Next session knows corrected plan is ready

---

## Integration Points

### With Existing WP6 Dashboard
- Reuses same datasource: `UDR-Timescale` (uid: `udr_postgres`)
- Follows same JSON structure pattern as `wp6-throughput-compare.json`
- Uses same provisioning mechanism (`clab/configs/grafana/provisioning/`)
- Auto-loaded into "NDT" folder via dashboard provider

### With Database Schema
- Queries `metrics` table (established in WP5)
- Uses existing indexes: `ix_metrics_exp_metric_ts`
- Leverages unique constraint: `uq_metrics_idem`
- No schema changes needed
- **NEW:** Uses regex pattern matching on experiment_id

### With MLO Scenarios
- Displays data from WP7.5 MLO scenarios
- Expects experiment IDs matching pattern: `.*-mlo-.*`
- Entity ID: Always `network` (single aggregated entity)
- 13 metrics available, dashboard shows 8 key metrics
- **NEW:** Auto-discovers experiments via database query

### With Telemetry Pipeline
- Reads data ingested by harmonizer
- No direct Kafka integration (Grafana queries DB only)
- Real-time updates if harmonizer is running (new experiments appear after refresh)
- Historical analysis for past experiments

---

## Potential Issues

### Issue 1: Regex Variable Not Escaping Special Characters
**Problem:** Variable may pass invalid regex if experiment ID contains special characters
**Impact:** Query errors or no data shown
**Solution:**
- Current regex pattern `.*-mlo-.*` is safe (only matches known format)
- Future: Validate experiment ID format in exporter
- Consider using exact match if regex causes issues

**Mitigation:**
```json
// If regex causes issues, use simpler LIKE pattern
"query": "SELECT DISTINCT experiment_id FROM metrics WHERE experiment_id LIKE '%-mlo-%' ORDER BY experiment_id DESC"
```

---

### Issue 2: Dashboard JSON Complexity
**Problem:** Hand-editing JSON is error-prone (missing commas, brackets)
**Impact:** Dashboard fails to load, Grafana logs show parsing errors
**Solution:**
- Use Grafana UI to create initial panels, then export JSON
- Validate JSON with `python3 -m json.tool dashboard.json`
- Use JSON editor with syntax highlighting

**Verification Command:**
```bash
# Validate dashboard JSON
cat clab/configs/grafana/dashboards/mlo-attack-scenarios.json | python3 -m json.tool > /dev/null && echo "Valid JSON" || echo "Invalid JSON"
```

---

### Issue 3: Color Overrides Not Working with Regex
**Problem:** Series colors don't match expected scheme if regex matchers fail
**Impact:** Visual confusion between scenarios
**Solution:**
- Use exact regex patterns: `.*-normal-.*`, `.*-attack-pos-.*`, `.*-attack-neg-.*`
- Test with different experiment IDs (not just hardcoded ones)
- Fallback: Use `byName` matcher with full experiment ID if needed

**Debug:**
```json
// Correct matcher syntax
{
  "matcher": {
    "id": "byRegex",
    "options": ".*-normal-.*"
  },
  "properties": [{
    "id": "color",
    "value": {"mode": "fixed", "fixedColor": "green"}
  }]
}
```

---

### Issue 4: Statistical Table Shows Unexpected Results
**Problem:** Table aggregations don't match expectations
**Impact:** Misleading numerical comparisons
**Solution:**
- Verify GROUP BY includes all necessary fields
- Check for NULL values in data (STDDEV can be NULL if only 1 row)
- Use COALESCE for NULL handling if needed

**Debug Query:**
```sql
-- Check for data anomalies
SELECT
  metric_name,
  COUNT(*) as row_count,
  COUNT(DISTINCT experiment_id) as experiments,
  COUNT(value) as non_null_values,
  COUNT(*) - COUNT(value) as null_values
FROM metrics
WHERE experiment_id ~ '.*-mlo-.*'
GROUP BY metric_name
ORDER BY metric_name;
```

---

### Issue 5: Query Performance with Large Dataset
**Problem:** Dashboard loads slowly if many MLO experiments exist
**Impact:** Poor user experience, timeout errors
**Solution:**
- Current dataset: 780 rows (very small, no issue)
- Future: Add LIMIT to template variable query (e.g., "LIMIT 20")
- Consider adding time range filter to variable query

**Optimized Variable Query:**
```sql
-- Show only latest 20 MLO experiments
SELECT DISTINCT experiment_id
FROM metrics
WHERE experiment_id ~ '.*-mlo-.*'
ORDER BY experiment_id DESC
LIMIT 20;
```

---

### Issue 6: Annotation Query Performance
**Problem:** CTE annotation query runs on every panel render
**Impact:** Dashboard performance degradation
**Solution:**
- Current dataset: 3 experiments, fast query
- Future: Consider disabling annotations if > 10 experiments
- Test with larger datasets

**Alternative Annotation Approach:**
```sql
-- Simpler query without CTE (if performance issues occur)
SELECT
  MIN(ts) as time,
  experiment_id as text,
  'experiment' as tags
FROM metrics
WHERE experiment_id ~ '${experiment_filter:regex}'
GROUP BY experiment_id
```

---

### Issue 7: Grafana Schema Version Mismatch
**Problem:** Dashboard created with newer Grafana version may not work
**Impact:** Panels don't render correctly or dashboard fails to load
**Solution:**
- Match schema version to existing dashboard (39)
- Test import on actual Grafana instance
- Check Grafana logs for compatibility warnings

**Verification:**
```bash
# Check Grafana version
docker exec clab-ndt-wifi7-mlo-security-grafana grafana-cli --version

# Expected: Grafana version matching schema 39 (v9.x or v10.x)
```

---

## ADR Candidates

### ADR-WP7.5-04: Query-Based Template Variables for Experiment Discovery
**Context:** Dashboard needs to show MLO experiments without manual configuration

**Decision:** Use query-based template variable that discovers experiments via database regex query, not hardcoded custom variable

**Rationale:**
- Eliminates manual dashboard edits when new experiments run
- Researchers can discover all MLO data automatically
- Multi-select enables flexible scenario comparison
- Regex pattern `.*-mlo-.*` matches naming convention
- Slight performance overhead acceptable (< 100ms query)

**Consequences:**
- Database query runs on dashboard load/refresh
- Requires consistent experiment ID naming (enforced by make targets)
- "All" option uses regex, not exact match (may include unintended experiments)
- Template variable refresh adds ~100ms to dashboard load time

---

### ADR-WP7.5-05: Regex-Based Color Overrides for Dynamic Scenario Matching
**Context:** Need color coding that works with any experiment ID, not just hardcoded ones

**Decision:** Use `byRegex` matchers (`.*-normal-.*`, `.*-attack-pos-.*`, `.*-attack-neg-.*`) instead of `byName` with exact experiment IDs

**Rationale:**
- Works with any experiment ID following naming convention
- Eliminates need to update dashboard for new experiments
- Supports research workflow: run new experiments, see correct colors automatically
- Regex patterns align with experiment ID format: `<date>-<time>-mlo-<scenario>-<seed>`

**Consequences:**
- Requires strict experiment ID naming convention
- Regex mismatches result in default colors (not critical failure)
- Slightly more verbose JSON (regex patterns in every panel)
- Future experiments must follow naming pattern or colors won't apply

---

### ADR-WP7.5-06: Replace mac_total_tx/rx with net_active_flows (Panel 8)
**Context:** Panel 8 designed to show transmission rates, but mac_total_tx/rx always zero

**Decision:** Replace Panel 8 metric with `net_active_flows` after database verification

**Rationale:**
- `mac_total_tx/rx`: Always 0 (verified via query on 780 rows)
- `mac_total_ack`: Always 0 (alternative rejected)
- `mac_drop_count`: Only 2 non-zero points (too sparse)
- `phy_drop_count`: Always 0 (alternative rejected)
- `net_active_flows`: 30 non-zero points, range 0-5, meaningful variation
- Shows network activity level (complements throughput metric)

**Consequences:**
- Panel 8 now shows flow count instead of transmission rates
- Dashboard has 7 network-layer metrics, 2 MAC-layer metrics (vs original 6:3 split)
- Future: May revisit if ns-3 simulation adds MAC tx/rx tracking
- Documentation updated to reflect metric change

---

## Related Documentation

### Existing Documentation to Reference
- `docs/WP6-GRAFANA-DASHBOARDS.md` - Dashboard creation guide
- `docs/WP7-ONE-COMMAND-PIPELINE.md` - MLO scenarios documentation
- `docs/ALL-ADRS.md` - Architecture decisions
- `clab/configs/grafana/dashboards/wp6-throughput-compare.json` - Existing dashboard pattern

### Documentation to Update After Implementation
- `docs/WP7-ONE-COMMAND-PIPELINE.md` - Add dashboard usage section (Step 7)
- `docs/QUICK-REFERENCE.md` - Add dashboard URL and quick tips (Step 7)
- `docs/CURRENT-STATE.md` - Update WP7.5 status to include dashboard
- `.claude/docs/context/current-session.md` - Mark plan complete (Step 7)
- `docs/ALL-ADRS.md` - Add ADRs WP7.5-04, -05, -06

### Future Documentation (WP8+)
- Consider creating separate guide: `docs/GRAFANA-DASHBOARD-GUIDE.md`
- Include dashboard design patterns, SQL query templates
- Document how to create new dashboards for future scenarios

---

## Implementation Checklist

### Pre-Implementation
- [x] Read this plan completely
- [ ] Verify Grafana is running: `docker ps | grep grafana`
- [ ] Verify database has MLO data: `make pipeline-status` or direct query
- [ ] Check Grafana version compatibility
- [ ] Review existing dashboard: `wp6-throughput-compare.json`

### Dashboard Creation
- [ ] Create `mlo-attack-scenarios.json` file
- [ ] Add dashboard metadata (uid, title, tags, time range)
- [ ] **Add query-based template variable (experiment_filter)**
- [ ] Create Panel 1: Backoff Slots (attack indicator) with dynamic query
- [ ] Create Panel 2: Throughput (primary impact) with dynamic query
- [ ] Create Panel 3: Packet Loss with dynamic query
- [ ] Create Panel 4: Average Delay with dynamic query
- [ ] Create Panel 5: Average Jitter with dynamic query
- [ ] Create Panel 6: Retransmissions with dynamic query
- [ ] Create Panel 7: Channel Busy Ratio with dynamic query
- [ ] **Create Panel 8: Active Flows (CORRECTED metric) with dynamic query**
- [ ] **Create Panel 9: Key Metrics Summary (CORRECTED title) with dynamic query**
- [ ] Validate JSON syntax: `python3 -m json.tool dashboard.json`
- [ ] **Add regex-based color overrides (byRegex matcher) to all panels**
- [ ] Configure legend settings (show mean/max/min)
- [ ] Set panel descriptions
- [ ] **Add CTE-based annotation query (FIXED SQL error)**

### Testing
- [ ] Test 1: Data presence verification
- [ ] **Test 2: Dynamic experiment filter (NEW - critical)**
- [ ] Test 3: Time alignment check
- [ ] **Test 4: Color coding verification (regex matchers)**
- [ ] **Test 5: Panel 8 data validation (net_active_flows)**
- [ ] **Test 6: Annotation query validation (CTE syntax)**
- [ ] Test 7: Statistical accuracy validation

### Documentation
- [ ] Update `docs/WP7-ONE-COMMAND-PIPELINE.md` with dashboard section
- [ ] Update `docs/QUICK-REFERENCE.md` with dashboard URL
- [ ] Update `.claude/docs/context/current-session.md`
- [ ] Create ADR-WP7.5-04 (query-based variables)
- [ ] Create ADR-WP7.5-05 (regex color overrides)
- [ ] Create ADR-WP7.5-06 (Panel 8 metric replacement)

### Post-Implementation
- [ ] Take screenshot of dashboard for documentation
- [ ] Run full test suite (all 7 tests)
- [ ] Verify dashboard appears in Grafana "NDT" folder
- [ ] Test with fresh Grafana session (clear browser cache)
- [ ] Update `docs/ALL-ADRS.md` with new ADRs
- [ ] **Verify new experiments auto-discover after dashboard refresh**

---

## Time Estimates

| Phase | Task | Estimated Time |
|-------|------|----------------|
| **Phase 1** | Dashboard structure and metadata | 30 minutes |
| **Phase 2** | Create 9 panels (JSON) with dynamic queries | 2-3 hours |
| **Phase 3** | Color overrides (regex) and formatting | 1 hour |
| **Phase 4** | Testing (all 7 scenarios including new tests) | 1.5-2 hours |
| **Phase 5** | Documentation updates | 1 hour |
| **Phase 6** | ADR creation (3 new ADRs) | 45 minutes |
| **Total** | **6-7.5 hours** |

**Recommended Approach:**
- Day 1 (2-3 hours): Create dashboard structure + template variable + first 3 panels
- Day 1 (1-2 hours): Complete remaining 6 panels with dynamic queries
- Day 2 (1.5 hours): Testing (focus on dynamic filter, Panel 8, annotations)
- Day 2 (1.75 hours): Documentation and ADRs

---

## Success Criteria

### Functional Requirements
- [ ] Dashboard loads without errors in Grafana
- [ ] All 9 panels display data for 3 scenarios
- [ ] **Experiment filter auto-discovers MLO runs from database**
- [ ] Time-aligned data across all panels
- [ ] Color coding: Green (normal), Red (positive), Orange (negative) using regex matchers
- [ ] **Panel 8 shows net_active_flows with meaningful data**
- [ ] **Table panel titled "Key Metrics Summary" (not "All Metrics")**
- [ ] **Annotations render without SQL errors**
- [ ] **New experiments appear after dashboard refresh**

### Research Questions Answered
- [ ] How does backoff manipulation affect throughput? → Panel 1 vs Panel 2 correlation visible
- [ ] What's the impact on packet loss? → Panel 3 shows degradation
- [ ] Which metrics are most sensitive? → Panel 9 statistical variance analysis
- [ ] Can we visually distinguish attacks? → Color-coded patterns obvious

### Documentation Requirements
- [ ] Dashboard usage documented in WP7 docs
- [ ] Quick reference includes dashboard URL
- [ ] ADRs created for key decisions (3 new ADRs)
- [ ] Troubleshooting guide available
- [ ] **Dynamic filter feature documented**

### User Experience
- [ ] Researchers can load dashboard without assistance
- [ ] Visual distinction between scenarios is obvious
- [ ] Attack indicator (backoff) clearly highlighted
- [ ] Impact metrics (throughput, loss) easy to interpret
- [ ] **No manual configuration required for new experiments**

---

## Rollback Plan

If dashboard implementation fails:

1. **Invalid JSON:**
   - Validate with `python3 -m json.tool`
   - Compare with working `wp6-throughput-compare.json`
   - Check Grafana logs: `docker logs clab-ndt-wifi7-mlo-security-grafana`

2. **No Data in Panels:**
   - Verify database has data: Direct SQL query
   - Check time range: Use absolute time covering experiments
   - Test query in Grafana Query Inspector
   - **Check experiment filter variable is set to "All"**

3. **Template Variable Not Populating:**
   - Test query directly in database
   - Check datasource UID matches (`udr_postgres`)
   - Verify regex pattern syntax
   - Fallback: Use custom variable with hardcoded IDs (v1 approach)

4. **Dashboard Won't Load:**
   - Remove dashboard file temporarily
   - Restart Grafana: `docker restart clab-ndt-wifi7-mlo-security-grafana`
   - Check provisioning logs

5. **Complete Rollback:**
   - Delete `mlo-attack-scenarios.json`
   - Revert documentation changes
   - Use v1 plan as fallback (with known issues documented)

---

## Next Steps After Implementation

1. **User Feedback:**
   - Share dashboard with researchers
   - Gather feedback on panel selection
   - Identify missing metrics or views
   - Test dynamic filter with real research workflow

2. **Dashboard Enhancements:**
   - Add more sophisticated annotations (attack thresholds, phase markers)
   - Create "detailed" version with all 13 metrics
   - Add impact percentage calculations (vs baseline)
   - Consider adding statistical significance tests

3. **Future Dashboards (WP8+):**
   - Multi-scenario comparison (beyond 3 experiments)
   - Real-time attack detection dashboard
   - GNN prediction vs actual comparison
   - Temporal attack pattern analysis

4. **Automation:**
   - Alert rules for anomalous patterns
   - Automated report generation
   - Dashboard versioning for different research phases

---

## References

- WP6 Dashboard Documentation: `docs/WP6-GRAFANA-DASHBOARDS.md`
- WP7 MLO Scenarios: `docs/WP7-ONE-COMMAND-PIPELINE.md` (WP7.5 section)
- Existing Dashboard Pattern: `clab/configs/grafana/dashboards/wp6-throughput-compare.json`
- Grafana Provisioning: `clab/configs/grafana/provisioning/dashboards/provider.yml`
- Database Schema: `docs/CURRENT-STATE.md` (Database Schema section)
- Architecture Decisions: `docs/ALL-ADRS.md` (ADR-WP6-01)
- Codex Review: User feedback identifying 6 critical issues (2026-01-05)

---

## Appendix A: Complete SQL Queries (CORRECTED)

### Query 1: Backoff Slots Time Series (Dynamic)
```sql
SELECT
  ts AS "time",
  value,
  experiment_id
FROM metrics
WHERE
  $__timeFilter(ts)
  AND metric_name = 'avg_backoff_slots'
  AND experiment_id ~ '${experiment_filter:regex}'
  AND entity_id = 'network'
ORDER BY ts, experiment_id;
```

### Query 2: Key Metrics Summary (Dynamic)
```sql
SELECT
  experiment_id,
  metric_name,
  ROUND(AVG(value)::numeric, 2) as avg,
  ROUND(STDDEV(value)::numeric, 2) as stddev,
  ROUND(MIN(value)::numeric, 2) as min,
  ROUND(MAX(value)::numeric, 2) as max
FROM metrics
WHERE
  $__timeFilter(ts)
  AND metric_name IN (
    'avg_backoff_slots',
    'net_throughput_mbps',
    'net_packet_loss_ratio',
    'net_avg_delay_ms',
    'mac_total_retrans',
    'channel_busy_ratio'
  )
  AND experiment_id ~ '${experiment_filter:regex}'
  AND entity_id = 'network'
GROUP BY experiment_id, metric_name
ORDER BY metric_name, experiment_id;
```

### Query 3: Impact Percentage vs Baseline (Future Enhancement)
```sql
WITH baseline AS (
  SELECT
    metric_name,
    AVG(value) as baseline_value
  FROM metrics
  WHERE experiment_id ~ '.*-mlo-normal-.*'
    AND metric_name IN ('net_throughput_mbps', 'avg_backoff_slots')
    AND entity_id = 'network'
  GROUP BY metric_name
),
attack_values AS (
  SELECT
    experiment_id,
    metric_name,
    AVG(value) as attack_value
  FROM metrics
  WHERE experiment_id ~ '.*-mlo-attack-(pos|neg)-.*'
    AND metric_name IN ('net_throughput_mbps', 'avg_backoff_slots')
    AND entity_id = 'network'
  GROUP BY experiment_id, metric_name
)
SELECT
  av.experiment_id,
  av.metric_name,
  ROUND(av.attack_value::numeric, 2) as attack_value,
  ROUND(b.baseline_value::numeric, 2) as baseline_value,
  ROUND(((av.attack_value - b.baseline_value) / b.baseline_value * 100)::numeric, 1) as pct_change
FROM attack_values av
JOIN baseline b ON av.metric_name = b.metric_name
ORDER BY av.metric_name, av.experiment_id;
```

### Query 4: Annotation Query (CTE-Based, CORRECTED)
```sql
WITH exp_starts AS (
  SELECT
    experiment_id,
    MIN(ts) as start_time
  FROM metrics
  WHERE experiment_id ~ '${experiment_filter:regex}'
  GROUP BY experiment_id
)
SELECT
  start_time as time,
  experiment_id as text,
  'experiment' as tags
FROM exp_starts
ORDER BY start_time;
```

### Query 5: Metric Data Verification (Testing)
```sql
-- Check if metric has non-zero data
SELECT
  metric_name,
  COUNT(*) FILTER (WHERE value <> 0) AS non_zero_points,
  ROUND(AVG(value)::numeric, 2) AS avg_v,
  ROUND(MIN(value)::numeric, 2) AS min_v,
  ROUND(MAX(value)::numeric, 2) AS max_v
FROM metrics
WHERE experiment_id ~ '.*-mlo-.*'
  AND metric_name IN ('mac_total_tx', 'mac_total_rx', 'net_active_flows')
GROUP BY metric_name
ORDER BY metric_name;
```

---

## Appendix B: Color Palette Reference

| Scenario | Color Name | Hex Code | RGB | Use Case |
|----------|------------|----------|-----|----------|
| Normal | Green | `#73BF69` | (115, 191, 105) | Baseline, healthy state |
| Positive Attack | Red | `#F2495C` | (242, 73, 92) | High severity, alert |
| Negative Attack | Orange | `#FF9830` | (255, 152, 48) | Medium severity, warning |

**Grafana Built-in Colors:**
- Use `fixedColor: "green"` for green
- Use `fixedColor: "red"` for red
- Use `fixedColor: "orange"` for orange

**Regex Matcher Patterns:**
- Normal: `.*-normal-.*`
- Positive: `.*-attack-pos-.*`
- Negative: `.*-attack-neg-.*`

**Accessibility Note:**
- Green/Red/Orange palette is distinguishable for most colorblind types
- For deuteranopia (red-green colorblind), use additional visual cues (line style, markers)
- Future enhancement: Add line style overrides (solid, dashed, dotted)

---

## Plan Summary

**Created:** 2026-01-05 (v2)
**Supersedes:** mlo-attack-dashboard-plan.md (v1, 2026-01-04)
**WP:** WP7.5 (MLO Attack Scenarios)
**Estimated Effort:** 6-7.5 hours
**Prerequisites Met:** Yes (all data in DB, pipeline working, metrics verified)
**Complexity:** Medium-High (9 panels, dynamic queries, comprehensive testing)

**Key Improvements from v1:**
1. ✅ Fixed annotation query SQL error (CTE approach)
2. ✅ Replaced hardcoded experiment IDs with dynamic `${experiment_filter:regex}`
3. ✅ Added color overrides to Panel 8
4. ✅ Replaced Panel 8 metric (`mac_total_tx/rx` → `net_active_flows`)
5. ✅ Corrected table panel title ("All Metrics" → "Key Metrics Summary")
6. ✅ Fixed invalid refresh setting (`false` → `""`)

**Key Decisions:**
1. Use query-based template variable for auto-discovery
2. Use regex-based color overrides (`byRegex` matcher)
3. Replace mac_total_tx/rx with net_active_flows (verified non-zero data)
4. Focus on 8 key metrics (not all 13)
5. Use absolute time range (not relative)

**Deliverables:**
1. `mlo-attack-scenarios.json` dashboard (CORRECTED version)
2. Documentation updates (WP7, QUICK-REFERENCE)
3. 3 new ADRs (query variables, regex colors, Panel 8 metric)
4. Enhanced 7-test validation suite

**Next Session Should:**
1. Implement dashboard JSON (Steps 1-5) - use v2 corrections
2. Run enhanced testing suite (Step 6) - focus on new tests
3. Update documentation (Step 7)
4. Create 3 new ADRs
5. Verify dynamic filter works with new experiments

---

**End of Implementation Plan v2 (CORRECTED)**
"}
