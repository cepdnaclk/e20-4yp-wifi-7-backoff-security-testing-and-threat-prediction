# Implementation Plan: MLO Attack Scenarios Grafana Dashboard

## Date
2026-01-04

## Objective
Create a comprehensive Grafana dashboard to visualize and compare Wi-Fi 7 MLO backoff manipulation attack scenarios (normal, positive bias, negative bias). The dashboard will enable researchers to understand attack behavior, measure network impact, and identify attack indicators across 13 MLO metrics.

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

## Prerequisites
- [x] WP7.5 complete - MLO scenarios implemented
- [x] Exporter reliability fix deployed
- [x] All 3 scenarios have data in TimescaleDB
- [x] 13 MLO metrics available
- [x] Grafana provisioning configured (WP6)
- [x] Existing dashboard pattern established (wp6-throughput-compare.json)

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------||
| `clab/configs/grafana/dashboards/mlo-attack-scenarios.json` | Create | Main MLO attack comparison dashboard |
| `docs/WP7-ONE-COMMAND-PIPELINE.md` | Modify | Add dashboard usage documentation |
| `docs/QUICK-REFERENCE.md` | Modify | Add dashboard access info |
| `.claude/docs/context/current-session.md` | Update | Track plan creation |

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
  - Panel 8: MAC Tx/Rx Rates
- **Row 4 (Statistical Summary):** Aggregate comparison
  - Panel 9: Statistical Summary Table

**Design Rationale:**
- Each panel shows all 3 scenarios as different series (time-aligned comparison)
- Color coding: Green (normal), Red (positive), Orange (negative)
- Focus on key 8 metrics (not all 13 - avoid overwhelming researchers)
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

### Step 2: Create Template Variables
**Action:** Define dashboard variables for flexibility

**Variables to Create:**
1. **`experiment_filter`** (Query variable)
   - Type: Custom or Query
   - Options: Dropdown with all MLO experiment IDs
   - Default: Latest 3 MLO experiments
   - Purpose: Allow filtering to specific experiment runs

2. **`time_window`** (Built-in time range)
   - Use Grafana's native time picker
   - Default: Absolute time range covering 2026-01-04 11:44-11:53
   - Note: Simulation timestamps are in 2026 (not "now")

3. **Optional: `metric_aggregation`** (Custom)
   - Options: "AVG", "MAX", "MIN"
   - Default: "RAW" (show raw time series)
   - Purpose: Future enhancement for aggregated views

**Implementation Notes:**
- NO entity_id filter needed (all experiments use entity_id='network')
- Time range MUST be absolute, not relative (data is in past)
- Experiment filter should use regex pattern match on experiment_id

**Expected Outcome:**
- Template variables section at top of dashboard
- Queries use `$experiment_filter` variable
- Time range correctly covers simulation window

**Verification:**
```json
"templating": {
  "list": [
    {
      "name": "experiment_filter",
      "type": "custom",
      "query": "20260103-1400-mlo-normal-42,20260103-1400-mlo-attack-pos-42,20260103-1400-mlo-attack-neg-42",
      "current": {
        "text": "All",
        "value": "$__all"
      },
      "includeAll": true,
      "multi": true
    }
  ]
}
```

---

### Step 3: Create SQL Query Templates
**Action:** Design reusable SQL query patterns

**Pattern 1: Time Series with Multi-Scenario Comparison**
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
  AND experiment_id IN (
    '20260103-1400-mlo-normal-42',
    '20260103-1400-mlo-attack-pos-42',
    '20260103-1400-mlo-attack-neg-42'
  )
  AND entity_id = 'network'
ORDER BY ts, experiment_id;
```

**Pattern 2: Statistical Comparison Table**
```sql
-- Template for statistical summary
SELECT
  experiment_id,
  AVG(value) as avg_value,
  STDDEV(value) as stddev_value,
  MIN(value) as min_value,
  MAX(value) as max_value,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value) as median_value
FROM metrics
WHERE
  $__timeFilter(ts)
  AND metric_name = '<METRIC_NAME>'
  AND experiment_id IN (
    '20260103-1400-mlo-normal-42',
    '20260103-1400-mlo-attack-pos-42',
    '20260103-1400-mlo-attack-neg-42'
  )
  AND entity_id = 'network'
GROUP BY experiment_id
ORDER BY experiment_id;
```

**Pattern 3: Impact Percentage Calculation**
```sql
-- Template for showing degradation vs baseline
WITH baseline AS (
  SELECT AVG(value) as baseline_value
  FROM metrics
  WHERE metric_name = '<METRIC_NAME>'
    AND experiment_id = '20260103-1400-mlo-normal-42'
),
attack_values AS (
  SELECT
    experiment_id,
    AVG(value) as attack_value
  FROM metrics
  WHERE metric_name = '<METRIC_NAME>'
    AND experiment_id IN ('20260103-1400-mlo-attack-pos-42', '20260103-1400-mlo-attack-neg-42')
  GROUP BY experiment_id
)
SELECT
  av.experiment_id,
  av.attack_value,
  b.baseline_value,
  ((av.attack_value - b.baseline_value) / b.baseline_value * 100) as pct_change
FROM attack_values av, baseline b;
```

**Query Optimization Notes:**
- Always filter by `entity_id = 'network'` (only one entity in MLO data)
- Use `$__timeFilter(ts)` for Grafana time range integration
- Order by `ts, experiment_id` for consistent series rendering
- Use experiment_id as series name for legend

**Expected Outcome:**
- 3 reusable SQL patterns for all panels
- Consistent query structure across dashboard
- Efficient queries (indexed on ts, experiment_id, metric_name)

**Verification:**
- Test each query pattern in Grafana Query Inspector
- Verify 3 series returned (one per scenario)
- Confirm time alignment across queries

---

### Step 4: Build Priority Panels
**Action:** Create the 9 key panels in priority order

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
    "rawSql": "SELECT ts AS \"time\", value, experiment_id FROM metrics WHERE $__timeFilter(ts) AND metric_name = 'avg_backoff_slots' AND experiment_id IN ('20260103-1400-mlo-normal-42', '20260103-1400-mlo-attack-pos-42', '20260103-1400-mlo-attack-neg-42') AND entity_id = 'network' ORDER BY ts, experiment_id;"
  }],
  "fieldConfig": {
    "defaults": {
      "unit": "slots",
      "color": {"mode": "palette-classic"}
    },
    "overrides": [
      {"matcher": {"id": "byName", "options": "20260103-1400-mlo-normal-42"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "green"}}]},
      {"matcher": {"id": "byName", "options": "20260103-1400-mlo-attack-pos-42"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}}]},
      {"matcher": {"id": "byName", "options": "20260103-1400-mlo-attack-neg-42"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "orange"}}]}
    ]
  },
  "options": {
    "legend": {"displayMode": "table", "placement": "bottom", "showLegend": true, "calcs": ["mean", "max", "min"]},
    "tooltip": {"mode": "multi"}
  }
}
```

**Key Features:**
- Color overrides: Green (normal), Red (positive), Orange (negative)
- Legend shows mean/max/min for quick statistical comparison
- Multi-tooltip for easy cross-scenario comparison
- Description includes observed values

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
    "rawSql": "SELECT ts AS \"time\", value, experiment_id FROM metrics WHERE $__timeFilter(ts) AND metric_name = 'net_throughput_mbps' AND experiment_id IN ('20260103-1400-mlo-normal-42', '20260103-1400-mlo-attack-pos-42', '20260103-1400-mlo-attack-neg-42') AND entity_id = 'network' ORDER BY ts, experiment_id;"
  }],
  "fieldConfig": {
    "defaults": {"unit": "Mbps"},
    "overrides": [
      {"matcher": {"id": "byName", "options": "20260103-1400-mlo-normal-42"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "green"}}]},
      {"matcher": {"id": "byName", "options": "20260103-1400-mlo-attack-pos-42"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}}]},
      {"matcher": {"id": "byName", "options": "20260103-1400-mlo-attack-neg-42"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "orange"}}]}
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

---

#### Panel 4: Average Delay
**Purpose:** Show latency impact

**Configuration:** Same structure, but:
- `metric_name = 'net_avg_delay_ms'`
- `unit = "ms"`
- Title: "Average Packet Delay"
- GridPos: `{"h": 8, "w": 8, "x": 8, "y": 10}`

---

#### Panel 5: Average Jitter
**Purpose:** Show delay variation

**Configuration:** Same structure, but:
- `metric_name = 'net_avg_jitter_ms'`
- `unit = "ms"`
- Title: "Average Jitter"
- GridPos: `{"h": 8, "w": 8, "x": 16, "y": 10}`

---

#### Panel 6: MAC Retransmissions
**Purpose:** Show MAC-level impact

**Configuration:** Same structure, but:
- `metric_name = 'mac_total_retrans'`
- `unit = "short"` (count)
- Title: "MAC Layer Retransmissions"
- Description: "Retransmission count indicates contention/collision rate"
- GridPos: `{"h": 8, "w": 8, "x": 0, "y": 18}`

---

#### Panel 7: Channel Busy Ratio
**Purpose:** Show contention indicator

**Configuration:** Same structure, but:
- `metric_name = 'channel_busy_ratio'`
- `unit = "percentunit"`
- Title: "Channel Busy Ratio"
- Description: "Channel utilization and contention level"
- GridPos: `{"h": 8, "w": 8, "x": 8, "y": 18}`

---

#### Panel 8: MAC Tx/Rx Rates
**Purpose:** Show transmission activity

**Configuration:**
```json
{
  "id": 8,
  "type": "timeseries",
  "title": "MAC Transmission Rates",
  "datasource": {"type": "postgres", "uid": "udr_postgres"},
  "gridPos": {"h": 8, "w": 8, "x": 16, "y": 18},
  "targets": [
    {
      "refId": "A",
      "format": "time_series",
      "rawSql": "SELECT ts AS \"time\", value, CONCAT(experiment_id, ' - TX') as metric FROM metrics WHERE $__timeFilter(ts) AND metric_name = 'mac_total_tx' AND experiment_id IN ('20260103-1400-mlo-normal-42', '20260103-1400-mlo-attack-pos-42', '20260103-1400-mlo-attack-neg-42') AND entity_id = 'network' ORDER BY ts, experiment_id;"
    },
    {
      "refId": "B",
      "format": "time_series",
      "rawSql": "SELECT ts AS \"time\", value, CONCAT(experiment_id, ' - RX') as metric FROM metrics WHERE $__timeFilter(ts) AND metric_name = 'mac_total_rx' AND experiment_id IN ('20260103-1400-mlo-normal-42', '20260103-1400-mlo-attack-pos-42', '20260103-1400-mlo-attack-neg-42') AND entity_id = 'network' ORDER BY ts, experiment_id;"
    }
  ],
  "fieldConfig": {
    "defaults": {"unit": "short"},
    "overrides": []
  },
  "options": {
    "legend": {"displayMode": "table", "placement": "bottom"},
    "tooltip": {"mode": "multi"}
  }
}
```

**Note:** Combines TX and RX on same panel (6 series total)

---

#### Panel 9: Statistical Summary Table
**Purpose:** Numerical comparison across all key metrics

**Configuration:**
```json
{
  "id": 9,
  "type": "table",
  "title": "Statistical Summary (All Metrics)",
  "datasource": {"type": "postgres", "uid": "udr_postgres"},
  "gridPos": {"h": 10, "w": 24, "x": 0, "y": 26},
  "targets": [{
    "refId": "A",
    "format": "table",
    "rawSql": "SELECT experiment_id, metric_name, AVG(value) as avg, STDDEV(value) as stddev, MIN(value) as min, MAX(value) as max FROM metrics WHERE $__timeFilter(ts) AND metric_name IN ('avg_backoff_slots', 'net_throughput_mbps', 'net_packet_loss_ratio', 'net_avg_delay_ms', 'mac_total_retrans', 'channel_busy_ratio') AND experiment_id IN ('20260103-1400-mlo-normal-42', '20260103-1400-mlo-attack-pos-42', '20260103-1400-mlo-attack-neg-42') AND entity_id = 'network' GROUP BY experiment_id, metric_name ORDER BY metric_name, experiment_id;"
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

**Expected Outcome:**
- 9 panels created with consistent styling
- All panels use same color scheme (green/red/orange)
- Time-aligned data across all panels
- Statistical summary provides numerical comparison

**Verification:**
- Load dashboard in Grafana
- Verify all panels render without errors
- Check time alignment (hover over panels simultaneously)
- Confirm color coding matches scenarios
- Verify legend calculations (mean, max, min)

---

### Step 5: Configure Dashboard Metadata
**Action:** Set dashboard-level configuration

**Dashboard JSON Structure:**
```json
{
  "uid": "mlo-attack-scenarios",
  "title": "NDT WP7.5 - MLO Attack Scenarios Comparison",
  "description": "Comparison of Wi-Fi 7 MLO backoff manipulation attacks: Normal (baseline), Positive Bias (+5000), Negative Bias (-5000)",
  "tags": ["ndt", "mlo", "wifi7", "attack", "backoff", "wp7"],
  "timezone": "UTC",
  "schemaVersion": 39,
  "version": 1,
  "editable": true,
  "refresh": false,
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
        "name": "Attack Scenarios",
        "datasource": {"type": "postgres", "uid": "udr_postgres"},
        "enable": true,
        "iconColor": "red",
        "query": "SELECT DISTINCT ts as time, experiment_id as text, 'Experiment Start' as tags FROM metrics WHERE experiment_id IN ('20260103-1400-mlo-normal-42', '20260103-1400-mlo-attack-pos-42', '20260103-1400-mlo-attack-neg-42') AND ts = (SELECT MIN(ts) FROM metrics WHERE experiment_id = m.experiment_id) ORDER BY ts"
      }
    ]
  },
  "templating": {
    "list": [
      {
        "name": "experiment_filter",
        "type": "custom",
        "label": "Experiments",
        "query": "20260103-1400-mlo-normal-42,20260103-1400-mlo-attack-pos-42,20260103-1400-mlo-attack-neg-42",
        "current": {
          "text": "All",
          "value": "$__all"
        },
        "includeAll": true,
        "multi": true,
        "options": []
      }
    ]
  },
  "panels": [
    // ... panels from Step 4
  ]
}
```

**Key Configuration Notes:**
- **Time range:** Absolute time (2026-01-04 11:44-11:53 UTC) covering all 3 experiments
- **Refresh:** Disabled (historical data, no real-time updates needed)
- **Tags:** Enables discovery in Grafana dashboard search
- **Schema version:** 39 (matches existing WP6 dashboard)
- **Annotations:** Optional markers for experiment start times
- **UID:** `mlo-attack-scenarios` (stable reference)

**Expected Outcome:**
- Dashboard loads with correct time range
- No "No Data" errors (time range covers data)
- Dashboard appears in "NDT" folder (from provisioning config)
- Tags enable search: "mlo", "attack", "wifi7"

**Verification:**
- Navigate to dashboard via Grafana UI
- Check time range picker shows absolute times
- Verify all panels have data
- Test template variable dropdown

---

### Step 6: Add Dashboard Annotations (Optional Enhancement)
**Action:** Add visual markers for key events

**Annotation 1: Experiment Boundaries**
```sql
-- Mark start/end of each experiment
SELECT
  ts as time,
  CASE
    WHEN ts = (SELECT MIN(ts) FROM metrics WHERE experiment_id = m.experiment_id)
    THEN CONCAT('START: ', experiment_id)
    WHEN ts = (SELECT MAX(ts) FROM metrics WHERE experiment_id = m.experiment_id)
    THEN CONCAT('END: ', experiment_id)
  END as text,
  'boundary' as tags
FROM metrics m
WHERE experiment_id IN (
  '20260103-1400-mlo-normal-42',
  '20260103-1400-mlo-attack-pos-42',
  '20260103-1400-mlo-attack-neg-42'
)
  AND (
    ts = (SELECT MIN(ts) FROM metrics WHERE experiment_id = m.experiment_id)
    OR ts = (SELECT MAX(ts) FROM metrics WHERE experiment_id = m.experiment_id)
  )
ORDER BY ts;
```

**Annotation 2: Attack Thresholds (Future)**
```sql
-- Mark when backoff slots exceed normal threshold
SELECT
  ts as time,
  CONCAT('Backoff anomaly: ', value, ' slots') as text,
  'attack' as tags
FROM metrics
WHERE metric_name = 'avg_backoff_slots'
  AND value > 10  -- Threshold: 2x normal baseline
ORDER BY ts;
```

**Expected Outcome:**
- Visual vertical lines on panels marking experiment boundaries
- Hover tooltip shows experiment name
- Optional: Color-coded annotations (green/red/orange)

**Note:** This is optional - may clutter the view. Test with users first.

---

### Step 7: Testing Strategy
**Action:** Comprehensive dashboard validation

#### Test 1: Data Presence Verification
```bash
# Verify all metrics appear in all panels
# Expected: No "No Data" errors in any panel

# Open dashboard: http://localhost:3000
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

#### Test 2: Time Alignment Check
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

#### Test 3: Color Coding Verification
```bash
# Verify scenario color scheme
# Expected:
# - Normal (20260103-1400-mlo-normal-42): Green
# - Positive (20260103-1400-mlo-attack-pos-42): Red
# - Negative (20260103-1400-mlo-attack-neg-42): Orange

# Visual check in legend and line colors
```

**Pass Criteria:**
- Legend colors match scenario types
- Line colors consistent across all panels
- Visually distinct (no confusion between series)

---

#### Test 4: Attack Pattern Identification
```bash
# Verify attack indicators are visible
# Expected:
# - Panel 1 (Backoff): Positive scenario shows 285x higher values
# - Panel 2 (Throughput): Attack scenarios show significant degradation
# - Statistical table confirms numerical differences

# Query for confirmation:
docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "
SELECT
  CASE
    WHEN experiment_id LIKE '%normal%' THEN 'Normal'
    WHEN experiment_id LIKE '%pos%' THEN 'Positive'
    WHEN experiment_id LIKE '%neg%' THEN 'Negative'
  END as scenario,
  AVG(CASE WHEN metric_name = 'avg_backoff_slots' THEN value END) as avg_backoff,
  AVG(CASE WHEN metric_name = 'net_throughput_mbps' THEN value END) as avg_throughput
FROM metrics
WHERE experiment_id LIKE '20260103-1400-mlo%'
GROUP BY scenario
ORDER BY scenario;
"
```

**Pass Criteria:**
- Backoff manipulation clearly visible in Panel 1
- Throughput degradation clearly visible in Panel 2
- Statistical table shows 100%+ difference in backoff values

---

#### Test 5: Template Variable Functionality
```bash
# Verify experiment filter works
# Steps:
# 1. Open dashboard
# 2. Click "Experiments" dropdown at top
# 3. Deselect "Normal" scenario
# 4. Verify only Positive and Negative series appear
# 5. Re-select all
```

**Pass Criteria:**
- Dropdown shows all 3 experiments
- Deselecting scenarios removes series from panels
- "All" option shows all scenarios
- Multi-select works correctly

---

#### Test 6: Time Range Adjustment
```bash
# Verify time picker works
# Steps:
# 1. Change time range to "Last 1 hour" (relative)
# 2. Expected: No data (experiments are in past)
# 3. Revert to absolute time range (2026-01-04 11:44-11:53)
# 4. Expected: Data appears again
```

**Pass Criteria:**
- Absolute time range shows data
- Relative time range shows no data (expected)
- Time picker saves preferences per user

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

---

**Overall Testing Checklist:**
- [ ] Test 1: Data presence (all panels show data)
- [ ] Test 2: Time alignment (synchronized panels)
- [ ] Test 3: Color coding (green/red/orange)
- [ ] Test 4: Attack patterns (visible differences)
- [ ] Test 5: Template variables (filtering works)
- [ ] Test 6: Time range (absolute vs relative)
- [ ] Test 7: Statistical accuracy (matches DB)

---

### Step 8: Documentation Updates
**Action:** Update project documentation with dashboard usage

#### Update 1: WP7-ONE-COMMAND-PIPELINE.md
**Location:** `docs/WP7-ONE-COMMAND-PIPELINE.md`
**Section:** Add new section after "WP7.5: MLO Attack Scenarios"

```markdown
### MLO Attack Scenarios Dashboard

**Access:** http://localhost:3000/d/mlo-attack-scenarios

**Purpose:** Compare Wi-Fi 7 MLO backoff manipulation attacks and measure network impact.

#### Available Scenarios
- **Normal**: Baseline with no attack (green)
- **Positive Bias**: Aggressive transmission attack (+5000, red)
- **Negative Bias**: Extreme aggressive attack (-5000, orange)

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

8. **MAC Tx/Rx Rates** (Transmission Activity)
   - Combined transmission and reception rates

9. **Statistical Summary** (Numerical Comparison)
   - Avg/StdDev/Min/Max for all key metrics across scenarios

#### Usage

```bash
# Run all three scenarios
make run-mlo-exp EXP_ID=20260104-1500-mlo-normal-42 SCENARIO=normal
make run-mlo-exp EXP_ID=20260104-1500-mlo-attack-pos-42 SCENARIO=positive
make run-mlo-exp EXP_ID=20260104-1500-mlo-attack-neg-42 SCENARIO=negative

# Open dashboard
# http://localhost:3000/d/mlo-attack-scenarios

# Adjust time range to cover new experiments
# Use absolute time range, not relative (data is in past)
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
```

**Expected Outcome:**
- WP7 documentation includes complete dashboard usage guide
- Researchers know how to interpret results
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
- **Time Range:** Use absolute time, not relative (data is historical)
- **Scenarios:** Green=Normal, Red=Positive Attack, Orange=Negative Attack
- **Key Metric:** Backoff slots (Panel 1) shows attack indicator
- **Impact Metric:** Throughput (Panel 2) shows degradation
```

**Expected Outcome:**
- Quick reference includes dashboard URLs
- Key usage notes readily available

---

#### Update 3: Session Context
**Location:** `.claude/docs/context/current-session.md`

Add to "Completed Recently" section:
```markdown
- Created MLO attack scenarios Grafana dashboard implementation plan
- Plan includes 9 panels, 7 test scenarios, full documentation
- Ready for implementation: mlo-attack-dashboard-plan.md
```

**Expected Outcome:**
- Session context updated with plan creation
- Next session knows dashboard plan is ready

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

### With MLO Scenarios
- Displays data from WP7.5 MLO scenarios
- Expects experiment IDs: `<date>-<time>-mlo-<scenario>-<seed>`
- Entity ID: Always `network` (single aggregated entity)
- 13 metrics available, dashboard shows 8 key metrics

### With Telemetry Pipeline
- Reads data ingested by harmonizer
- No direct Kafka integration (Grafana queries DB only)
- Real-time updates if harmonizer is running (new experiments appear)
- Historical analysis for past experiments

---

## Potential Issues

### Issue 1: Time Range Mismatch
**Problem:** Users expect "Last 6 hours" to show data, but experiments are in the past
**Impact:** Dashboard shows "No Data" errors
**Solution:**
- Default to absolute time range covering known experiments
- Add clear documentation: "Use absolute time range"
- Consider adding dashboard variable for "common experiment dates"

**Mitigation:**
```json
"time": {
  "from": "2026-01-04T11:44:00.000Z",
  "to": "2026-01-04T11:53:00.000Z"
},
"timepicker": {
  "hidden": false,
  "nowDelay": "",
  "refresh_intervals": []
}
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

### Issue 3: Color Overrides Not Working
**Problem:** Series colors don't match expected scheme (green/red/orange)
**Impact:** Visual confusion between scenarios
**Solution:**
- Use exact experiment_id strings in matcher (not regex)
- Check field name in matcher matches legend name
- Test with single panel first before copying to all panels

**Debug:**
```json
// Correct matcher syntax
{
  "matcher": {
    "id": "byName",
    "options": "20260103-1400-mlo-normal-42"
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
WHERE experiment_id LIKE '20260103-1400-mlo%'
GROUP BY metric_name
ORDER BY metric_name;
```

---

### Issue 5: Too Many Metrics Overwhelm Dashboard
**Problem:** Showing all 13 metrics creates cluttered dashboard
**Impact:** Difficult to identify key insights
**Solution:**
- Focus on 8 key metrics (implemented in plan)
- Group related metrics (network/MAC/PHY layers)
- Use statistical table for comprehensive numerical view
- Consider creating separate "detailed" dashboard for all 13 metrics

**Alternative Approach:**
- Create dropdown variable to select metric category: "Network", "MAC", "PHY", "All"
- Show/hide panel rows based on selection

---

### Issue 6: New Experiments Don't Appear Automatically
**Problem:** Dashboard template variable hardcodes experiment IDs
**Impact:** Users must manually edit dashboard to add new experiments
**Solution:** Use query-based template variable instead of custom

**Improved Template Variable:**
```json
{
  "name": "experiment_filter",
  "type": "query",
  "datasource": {"type": "postgres", "uid": "udr_postgres"},
  "query": "SELECT DISTINCT experiment_id FROM metrics WHERE experiment_id LIKE '%mlo%' ORDER BY experiment_id DESC LIMIT 20;",
  "refresh": 1,  // On dashboard load
  "includeAll": true,
  "multi": true
}
```

**Trade-off:** Query-based variable adds DB query overhead but provides automatic discovery

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

### ADR-WP7.5-01: MLO Dashboard Focuses on Attack Indicator and Impact Metrics
**Context:** 13 MLO metrics available, need to decide what to show

**Decision:** Dashboard shows 8 key metrics: backoff slots (attack indicator), throughput (primary impact), loss/delay/jitter (QoS impact), retransmissions/channel busy (MAC impact), statistical summary

**Rationale:**
- Backoff slots is THE attack indicator (100x-300x variation)
- Throughput is primary impact metric (up to 84% degradation)
- Focusing on 8 metrics prevents overwhelming researchers
- Statistical table provides access to numerical comparison
- Can create detailed dashboard later if needed

**Consequences:**
- 5 metrics excluded from main view: `net_active_flows`, `mac_total_ack`, `mac_drop_count`, `phy_drop_count`, `mac_total_tx/rx` (shown combined)
- Researchers must query database directly for excluded metrics
- Future dashboard can show all 13 if needed

---

### ADR-WP7.5-02: Use Absolute Time Range for Historical Attack Analysis
**Context:** MLO experiment data is historical (past timestamps), not real-time

**Decision:** Default dashboard to absolute time range covering known experiments, not relative time range like "Last 6 hours"

**Rationale:**
- Experiments run at specific past times (2026-01-04 11:44-11:53)
- Relative time ranges (e.g., "now-6h") would show no data
- Absolute time range guarantees data visibility
- New experiments require time range adjustment (acceptable trade-off)

**Consequences:**
- Users must manually adjust time range for new experiments
- Consider query-based time range variable for automation
- Documentation must explain time range behavior
- Dashboard not suitable for real-time monitoring (as designed)

---

### ADR-WP7.5-03: Use Color Coding for Visual Attack Distinction
**Context:** Need clear visual distinction between attack scenarios

**Decision:** Use color-coded series: Green (Normal/Baseline), Red (Positive Attack/High Severity), Orange (Negative Attack/Medium Severity)

**Rationale:**
- Green universally recognized as "good/normal"
- Red indicates "alert/attack/degradation"
- Orange indicates "warning/attack/moderate"
- Color consistency across all panels aids comprehension
- Accessible color palette (not red/green colorblind problematic for 3-way comparison)

**Consequences:**
- Must implement color overrides in all panels (more verbose JSON)
- Legend entries must match exact experiment_id strings
- Consider accessibility: Add patterns/shapes for colorblind users in future
- Color scheme documented in dashboard description

---

## Related Documentation

### Existing Documentation to Reference
- `docs/WP6-GRAFANA-DASHBOARDS.md` - Dashboard creation guide
- `docs/WP7-ONE-COMMAND-PIPELINE.md` - MLO scenarios documentation
- `docs/ALL-ADRS.md` - Architecture decisions
- `clab/configs/grafana/dashboards/wp6-throughput-compare.json` - Existing dashboard pattern

### Documentation to Update After Implementation
- `docs/WP7-ONE-COMMAND-PIPELINE.md` - Add dashboard usage section
- `docs/QUICK-REFERENCE.md` - Add dashboard URL and quick tips
- `docs/CURRENT-STATE.md` - Update WP7.5 status to include dashboard
- `.claude/docs/context/current-session.md` - Mark plan complete

### Future Documentation (WP8+)
- Consider creating separate guide: `docs/GRAFANA-DASHBOARD-GUIDE.md`
- Include dashboard design patterns, SQL query templates
- Document how to create new dashboards for future scenarios

---

## Implementation Checklist

### Pre-Implementation
- [ ] Read this plan completely
- [ ] Verify Grafana is running: `docker ps | grep grafana`
- [ ] Verify database has MLO data: `make pipeline-status` or direct query
- [ ] Check Grafana version compatibility
- [ ] Review existing dashboard: `wp6-throughput-compare.json`

### Dashboard Creation
- [ ] Create `mlo-attack-scenarios.json` file
- [ ] Add dashboard metadata (uid, title, tags, time range)
- [ ] Add template variables (experiment_filter)
- [ ] Create Panel 1: Backoff Slots (attack indicator)
- [ ] Create Panel 2: Throughput (primary impact)
- [ ] Create Panel 3: Packet Loss
- [ ] Create Panel 4: Average Delay
- [ ] Create Panel 5: Average Jitter
- [ ] Create Panel 6: Retransmissions
- [ ] Create Panel 7: Channel Busy Ratio
- [ ] Create Panel 8: MAC Tx/Rx Rates
- [ ] Create Panel 9: Statistical Summary Table
- [ ] Validate JSON syntax: `python3 -m json.tool dashboard.json`
- [ ] Add color overrides (green/red/orange) to all panels
- [ ] Configure legend settings (show mean/max/min)
- [ ] Set panel descriptions

### Testing
- [ ] Test 1: Data presence verification
- [ ] Test 2: Time alignment check
- [ ] Test 3: Color coding verification
- [ ] Test 4: Attack pattern identification
- [ ] Test 5: Template variable functionality
- [ ] Test 6: Time range adjustment
- [ ] Test 7: Statistical accuracy validation

### Documentation
- [ ] Update `docs/WP7-ONE-COMMAND-PIPELINE.md` with dashboard section
- [ ] Update `docs/QUICK-REFERENCE.md` with dashboard URL
- [ ] Update `.claude/docs/context/current-session.md`
- [ ] Create ADR-WP7.5-01 (metric focus)
- [ ] Create ADR-WP7.5-02 (absolute time range)
- [ ] Create ADR-WP7.5-03 (color coding)

### Post-Implementation
- [ ] Take screenshot of dashboard for documentation
- [ ] Run full test suite (all 7 tests)
- [ ] Verify dashboard appears in Grafana "NDT" folder
- [ ] Test with fresh Grafana session (clear browser cache)
- [ ] Update `docs/ALL-ADRS.md` with new ADRs

---

## Time Estimates

| Phase | Task | Estimated Time |
|-------|------|----------------|
| **Phase 1** | Dashboard structure and metadata | 30 minutes |
| **Phase 2** | Create 9 panels (JSON) | 2-3 hours |
| **Phase 3** | Color overrides and formatting | 1 hour |
| **Phase 4** | Testing (all 7 scenarios) | 1-2 hours |
| **Phase 5** | Documentation updates | 1 hour |
| **Phase 6** | ADR creation | 30 minutes |
| **Total** | **5.5-7.5 hours** |

**Recommended Approach:**
- Day 1 (2-3 hours): Create dashboard structure + first 3 panels
- Day 1 (1-2 hours): Complete remaining 6 panels
- Day 2 (1 hour): Testing and bug fixes
- Day 2 (1.5 hours): Documentation and ADRs

---

## Success Criteria

### Functional Requirements
- [ ] Dashboard loads without errors in Grafana
- [ ] All 9 panels display data for 3 scenarios
- [ ] Time-aligned data across all panels
- [ ] Color coding: Green (normal), Red (positive), Orange (negative)
- [ ] Template variable allows scenario filtering
- [ ] Statistical table shows accurate aggregations

### Research Questions Answered
- [ ] How does backoff manipulation affect throughput? → Panel 1 vs Panel 2 correlation visible
- [ ] What's the impact on packet loss? → Panel 3 shows degradation
- [ ] Which metrics are most sensitive? → Panel 9 statistical variance analysis
- [ ] Can we visually distinguish attacks? → Color-coded patterns obvious

### Documentation Requirements
- [ ] Dashboard usage documented in WP7 docs
- [ ] Quick reference includes dashboard URL
- [ ] ADRs created for key decisions
- [ ] Troubleshooting guide available

### User Experience
- [ ] Researchers can load dashboard without assistance
- [ ] Visual distinction between scenarios is obvious
- [ ] Attack indicator (backoff) clearly highlighted
- [ ] Impact metrics (throughput, loss) easy to interpret

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

3. **Dashboard Won't Load:**
   - Remove dashboard file temporarily
   - Restart Grafana: `docker restart clab-ndt-wifi7-mlo-security-grafana`
   - Check provisioning logs

4. **Complete Rollback:**
   - Delete `mlo-attack-scenarios.json`
   - Revert documentation changes
   - Keep plan for future attempt

---

## Next Steps After Implementation

1. **User Feedback:**
   - Share dashboard with researchers
   - Gather feedback on panel selection
   - Identify missing metrics or views

2. **Dashboard Enhancements:**
   - Add annotations for experiment boundaries
   - Create "detailed" version with all 13 metrics
   - Add impact percentage calculations (vs baseline)
   - Consider adding statistical significance tests

3. **Future Dashboards (WP8+):**
   - Multi-scenario comparison (beyond 3 experiments)
   - Real-time attack detection dashboard
   - GNN prediction vs actual comparison
   - Temporal attack pattern analysis

4. **Automation:**
   - Query-based template variable for auto experiment discovery
   - Dynamic time range based on latest experiment
   - Alert rules for anomalous patterns

---

## References

- WP6 Dashboard Documentation: `docs/WP6-GRAFANA-DASHBOARDS.md`
- WP7 MLO Scenarios: `docs/WP7-ONE-COMMAND-PIPELINE.md` (WP7.5 section)
- Existing Dashboard Pattern: `clab/configs/grafana/dashboards/wp6-throughput-compare.json`
- Grafana Provisioning: `clab/configs/grafana/provisioning/dashboards/provider.yml`
- Database Schema: `docs/CURRENT-STATE.md` (Database Schema section)
- Architecture Decisions: `docs/ALL-ADRS.md` (ADR-WP6-01)

---

## Appendix A: Complete SQL Queries

### Query 1: Backoff Slots Time Series
```sql
SELECT
  ts AS "time",
  value,
  experiment_id
FROM metrics
WHERE
  $__timeFilter(ts)
  AND metric_name = 'avg_backoff_slots'
  AND experiment_id IN (
    '20260103-1400-mlo-normal-42',
    '20260103-1400-mlo-attack-pos-42',
    '20260103-1400-mlo-attack-neg-42'
  )
  AND entity_id = 'network'
ORDER BY ts, experiment_id;
```

### Query 2: Statistical Summary (All Metrics)
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
  AND experiment_id IN (
    '20260103-1400-mlo-normal-42',
    '20260103-1400-mlo-attack-pos-42',
    '20260103-1400-mlo-attack-neg-42'
  )
  AND entity_id = 'network'
GROUP BY experiment_id, metric_name
ORDER BY metric_name, experiment_id;
```

### Query 3: Impact Percentage vs Baseline
```sql
WITH baseline AS (
  SELECT
    metric_name,
    AVG(value) as baseline_value
  FROM metrics
  WHERE experiment_id = '20260103-1400-mlo-normal-42'
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
  WHERE experiment_id IN (
    '20260103-1400-mlo-attack-pos-42',
    '20260103-1400-mlo-attack-neg-42'
  )
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

**Accessibility Note:**
- Green/Red/Orange palette is distinguishable for most colorblind types
- For deuteranopia (red-green colorblind), use additional visual cues (line style, markers)
- Future enhancement: Add line style overrides (solid, dashed, dotted)

---

## Plan Summary

**Created:** 2026-01-04
**WP:** WP7.5 (MLO Attack Scenarios)
**Estimated Effort:** 5.5-7.5 hours
**Prerequisites Met:** Yes (all data in DB, pipeline working)
**Complexity:** Medium (9 panels, consistent JSON patterns, thorough testing)

**Key Decisions:**
1. Focus on 8 key metrics (not all 13)
2. Use absolute time range (not relative)
3. Color coding: Green/Red/Orange for visual distinction
4. Metric-focused layout (not scenario-focused)
5. Statistical table for numerical comparison

**Deliverables:**
1. `mlo-attack-scenarios.json` dashboard
2. Documentation updates (WP7, QUICK-REFERENCE)
3. 3 new ADRs (metric focus, time range, color coding)
4. 7-test validation suite

**Next Session Should:**
1. Implement dashboard JSON (Steps 1-5)
2. Run testing suite (Step 7)
3. Update documentation (Step 8)
4. Create ADRs
5. Verify in Grafana UI

---

**End of Implementation Plan**
