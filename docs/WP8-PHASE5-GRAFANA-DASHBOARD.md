# WP8 Phase 5: Grafana Dashboard for GCN Attack Detection

**Date**: 2026-02-10
**Status**: ✅ Complete
**Dashboard**: `gcn-attack-detection`

---

## Overview

Phase 5 delivers a comprehensive Grafana dashboard for real-time visualization and monitoring of GCN-based WiFi 7 attack detection. The dashboard provides security analysts with actionable insights into attack patterns, model performance, and prediction confidence.

---

## Dashboard Features

### 1. Executive Summary Panel (Top Row)

**Six Key Metrics:**

| Metric | Description | Thresholds |
|--------|-------------|------------|
| **Total Predictions** | Count of all predictions made | Blue < 10 < Green < 100 < Yellow |
| **Attacks Detected** | Number of attack classifications | Green < 1 < Yellow < 10 < Red |
| **Attack Rate** | Percentage of segments classified as attacks | Green < 20% < Yellow < 50% < Orange < 80% < Red |
| **Avg Confidence** | Mean confidence score (0-1) | Red < 0.6 < Yellow < 0.8 < Green |
| **Avg Inference Time** | Mean prediction latency | Green < 100ms < Yellow < 500ms < Red |
| **Active Model** | Currently deployed model version | Blue background |

### 2. Attack Detection Timeline

**Panel ID**: 10
**Type**: Time Series (Bar Chart)
**Purpose**: Real-time visualization of attack vs normal classifications

**Features:**
- Bar chart showing 0 (Normal) and 1 (Attack) predictions over time
- Color-coded by experiment and entity
- Annotations show attack detections with confidence scores
- 10-second auto-refresh for live monitoring

**Use Cases:**
- Identify attack burst patterns
- Correlate attacks with experiment phases
- Monitor attack frequency over time

### 3. Confidence Analysis

**Panel ID**: 11 & 12
**Type**: Time Series + Histogram
**Purpose**: Analyze model certainty

**Confidence Over Time (Panel 11):**
- Line chart with points showing confidence per prediction
- Grouped by experiment and entity
- Shows mean, min, max in legend
- Helps identify low-confidence predictions that need review

**Confidence Distribution (Panel 12):**
- Histogram with 0.05 bucket size
- Shows concentration of confidence scores
- Ideal: bimodal distribution (high confidence for both classes)
- Red flag: concentration around threshold (0.5)

### 4. Prediction Distribution

**Panel ID**: 20, 21, 22
**Type**: Pie Chart, Bar Gauge, Stats
**Purpose**: Aggregate view of detection results

**Prediction Distribution (Panel 20):**
- Donut chart: Normal (green) vs Attack (red)
- Shows percentage and count
- Quick sanity check on overall detection balance

**Attack Rate by Experiment (Panel 21):**
- Horizontal bar gauge per experiment
- Color gradient based on attack rate thresholds
- Identifies which experiments have highest attack activity

**Model Performance Summary (Panel 22):**
- Multi-stat panel with 5 KPIs
- Total segments, avg confidence, avg inference time
- Unique experiments processed
- Active model version

### 5. Recent Predictions Table

**Panel ID**: 30
**Type**: Table
**Purpose**: Detailed inspection of individual predictions

**Columns:**
1. **Experiment** - Experiment ID
2. **Entity** - Station/network identifier
3. **Segment** - Segment ID
4. **Start Time** - Segment timestamp
5. **Prediction** - Normal (green) or Attack (red background)
6. **Confidence** - 0-1 score with gradient gauge
7. **Probabilities** - [P(Normal), P(Attack)] array
8. **Inference Time** - Model latency in ms
9. **Model** - Model version used
10. **Detected At** - Database insertion timestamp

**Features:**
- Last 100 predictions
- Color-coded prediction column
- Gradient gauge for confidence (red < 0.7 < yellow < 0.9 < green)
- Sortable columns
- Clickable rows for drill-down

### 6. Performance Metrics

**Panel ID**: 40 & 41
**Type**: Time Series
**Purpose**: Monitor model operational performance

**Inference Performance (Panel 40):**
- Line chart of inference time per prediction
- Shows mean and max in legend
- Identifies performance degradation
- Useful for capacity planning

**Attack Probability Over Time (Panel 41):**
- Shows P(Attack) probability (class 1) for each prediction
- Useful for threshold tuning
- Identifies borderline cases
- Shows probability trends across experiments

---

## Annotations

### 1. Attack Detections (Red)

```sql
SELECT
  ts_start as time,
  CONCAT('Attack: ', segment_id, ' (conf: ', ROUND(confidence::numeric, 2), ')') as text,
  'attack' as tags
FROM gcn_predictions
WHERE prediction = 1
ORDER BY ts_start
```

**Appearance**: Red vertical line with attack details in tooltip

### 2. Model Version Changes (Blue)

```sql
WITH version_changes AS (
  SELECT model_version, MIN(created_at) as time
  FROM gcn_predictions
  GROUP BY model_version
)
SELECT
  time,
  CONCAT('Model: ', model_version) as text,
  'model' as tags
FROM version_changes
ORDER BY time
```

**Appearance**: Blue vertical line marking model deployments

---

## Template Variables

### 1. `experiment_filter`

**Type**: Multi-select query variable
**Query**: `SELECT DISTINCT experiment_id FROM gcn_predictions ORDER BY experiment_id DESC`
**Default**: All experiments
**Usage**: Filter all panels by experiment ID(s)
**Refresh**: On dashboard load

### 2. `model_version`

**Type**: Single-select query variable
**Query**: `SELECT DISTINCT model_version FROM gcn_predictions ORDER BY model_version DESC`
**Default**: All versions
**Usage**: Compare performance across model versions
**Refresh**: On dashboard load

---

## Usage Guide

### Accessing the Dashboard

1. **Navigate to Grafana**: http://localhost:3000
2. **Login**: admin / admin (default credentials)
3. **Find Dashboard**:
   - Home → Dashboards → Browse
   - Search: "GCN Attack Detection"
   - Or direct URL: http://localhost:3000/d/gcn-attack-detection

### Basic Workflow

#### 1. Live Monitoring

```bash
# Ensure pipeline is running
docker compose -f docker-compose.pipeline.yml ps

# Check services
make status

# Dashboard should auto-refresh every 10 seconds
```

**What to Watch:**
- Attack Detection Timeline for new attacks
- Recent Predictions table for latest results
- Attack Rate metric for overall activity

#### 2. Investigate Specific Experiment

1. **Select Experiment**: Use `experiment_filter` dropdown
2. **Review Timeline**: Check when attacks occurred
3. **Inspect Table**: Look at individual predictions
4. **Check Confidence**: Verify model certainty
5. **Analyze Performance**: Review inference times

#### 3. Model Performance Analysis

1. **Select Time Range**: Last 1 hour, 6 hours, or custom
2. **Review KPIs**: Check avg confidence and inference time
3. **Check Distribution**: Look at confidence histogram
4. **Identify Issues**:
   - Low confidence → Model uncertainty
   - High inference time → Performance problem
   - 100% attack rate → Model bias issue
   - Unbalanced distribution → Dataset imbalance

#### 4. Compare Model Versions

1. **Use `model_version` filter**: Select specific version
2. **Compare metrics** across time periods
3. **Check regression**: Ensure new models improve performance
4. **Validate deployment**: Confirm version change annotations

### Advanced Analysis

#### Detecting False Positives

**Scenario**: High attack rate on known-normal experiments

**Steps:**
1. Filter by normal experiment (e.g., `20260210-phase4-normal-full`)
2. Check Attack Rate metric (should be 0% or very low)
3. Review Recent Predictions table for false positives
4. Examine confidence scores (low confidence = uncertain)
5. Check Attack Probability chart (borderline cases near 0.5)

**Actions:**
- If attack rate > 20% on normal: **Model needs retraining**
- If confidence < 0.7: **Review threshold setting**
- If probabilities near 0.5: **Borderline cases, need expert review**

#### Performance Degradation Detection

**Scenario**: Model inference time increasing

**Steps:**
1. Check "Avg Inference Time" stat (should be < 100ms)
2. Review "Inference Performance Over Time" chart
3. Look for trends: gradual increase or sudden spikes
4. Correlate with "Total Predictions" (throughput)

**Possible Causes:**
- Resource contention (CPU/memory)
- Model complexity (after update)
- Database bottleneck (writes)
- Network latency (Kafka)

**Actions:**
- Scale horizontally (more detector instances)
- Optimize batch size
- Profile inference code
- Check resource utilization

#### Model Drift Detection

**Scenario**: Changing attack patterns over time

**Steps:**
1. Set time range to last 7 days
2. Compare Attack Rate across days
3. Check Confidence Distribution stability
4. Review probability trends

**Indicators of Drift:**
- Increasing attack rate on normal data
- Decreasing average confidence
- Shifting probability distributions
- New unknown patterns

**Actions:**
- Collect new training data
- Retrain model with recent samples
- Implement online learning
- Add monitoring alerts

---

## Alert Rules (Future Enhancement)

### Recommended Grafana Alerts

#### 1. High Attack Rate

```yaml
Condition: Attack Rate > 80% for 5 minutes
Severity: Warning
Action: Notify security team
Reason: Possible attack wave or model misconfiguration
```

#### 2. Low Model Confidence

```yaml
Condition: Avg Confidence < 0.6 for 10 minutes
Severity: Warning
Action: Flag for manual review
Reason: Model uncertainty indicates edge cases
```

#### 3. Inference Performance Degradation

```yaml
Condition: Avg Inference Time > 500ms for 5 minutes
Severity: Critical
Action: Page on-call engineer
Reason: Service degradation affecting real-time detection
```

#### 4. No Predictions Received

```yaml
Condition: Total Predictions unchanged for 15 minutes
Severity: Critical
Action: Check pipeline health
Reason: Pipeline may be broken
```

---

## Troubleshooting

### Dashboard Shows No Data

**Symptoms**: All panels empty, no metrics

**Checks:**
1. **Verify GCN detector is running**:
   ```bash
   docker compose -f docker-compose.pipeline.yml ps | grep gcn-detector
   ```

2. **Check predictions in database**:
   ```bash
   docker exec clab-ndt-wifi7-mlo-security-udr-db psql -d udr -c \
     "SELECT COUNT(*) FROM gcn_predictions;"
   ```

3. **Verify datasource connection**:
   - Grafana → Configuration → Data Sources → udr_postgres
   - Click "Test" button

4. **Check time range**: Adjust to cover period when experiments ran

### Predictions Not Updating

**Symptoms**: Dashboard frozen, no new data

**Checks:**
1. **Check GCN detector logs**:
   ```bash
   docker logs ndt-pipeline-gcn-detector --tail 50
   ```

2. **Verify Kafka topics have data**:
   ```bash
   docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
     rpk topic consume wifi7.ml.windowed_features.v1 -n 1
   ```

3. **Check windowizer is processing**:
   ```bash
   docker logs ndt-pipeline-windowizer --tail 20
   ```

4. **Verify auto-refresh**: Dashboard should refresh every 10s

### Annotations Not Showing

**Symptoms**: No attack markers on timeline

**Checks:**
1. **Enable annotations**: Dashboard Settings → Annotations → Enable all
2. **Check annotation queries**: Review SQL in annotation configuration
3. **Verify predictions exist**: Check Recent Predictions table
4. **Adjust time range**: Annotations only show in visible time window

### Performance Issues

**Symptoms**: Dashboard slow to load, queries timing out

**Causes:**
- Too many predictions in database (millions)
- Complex queries without indexes
- Long time range selected

**Solutions:**
1. **Limit time range**: Use shorter periods (1 hour vs 7 days)
2. **Filter by experiment**: Use experiment_filter variable
3. **Add database indexes**: Already included in schema
4. **Enable query caching**: Configure in Grafana settings

---

## Database Schema Reference

### `gcn_predictions` Table

```sql
CREATE TABLE public.gcn_predictions (
    id BIGSERIAL PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    segment_id TEXT NOT NULL,
    ts_start TIMESTAMPTZ NOT NULL,
    ts_end TIMESTAMPTZ NOT NULL,
    window_start_idx INTEGER NOT NULL,
    window_end_idx INTEGER NOT NULL,
    prediction INTEGER NOT NULL,           -- 0=Normal, 1=Attack
    confidence DOUBLE PRECISION NOT NULL,  -- 0.0 to 1.0
    probabilities JSONB NOT NULL,          -- [P(Normal), P(Attack)]
    model_version TEXT NOT NULL,
    model_path TEXT NOT NULL,
    inference_time_ms DOUBLE PRECISION,
    source TEXT NOT NULL DEFAULT 'gcn-detector',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for dashboard queries
CREATE INDEX idx_predictions_experiment ON gcn_predictions(experiment_id);
CREATE INDEX idx_predictions_created_at ON gcn_predictions(created_at DESC);
CREATE INDEX idx_predictions_ts_start ON gcn_predictions(ts_start DESC);
CREATE INDEX idx_predictions_model ON gcn_predictions(model_version);
CREATE INDEX idx_predictions_prediction ON gcn_predictions(prediction);
```

### Sample Query

```sql
-- Get recent attacks with high confidence
SELECT
  experiment_id,
  entity_id,
  segment_id,
  ts_start,
  confidence,
  probabilities->>1 as attack_probability,
  inference_time_ms,
  model_version
FROM gcn_predictions
WHERE
  prediction = 1
  AND confidence > 0.8
  AND ts_start > NOW() - INTERVAL '1 hour'
ORDER BY ts_start DESC
LIMIT 20;
```

---

## Configuration Files

### Dashboard JSON Location

```
clab/configs/grafana/dashboards/gcn-attack-detection.json
```

### Provisioning Configuration

Grafana automatically provisions dashboards from this directory via:

```yaml
# clab/configs/grafana/provisioning/dashboards/dashboard.yml
apiVersion: 1
providers:
  - name: 'default'
    folder: ''
    type: file
    options:
      path: /etc/grafana/provisioning/dashboards
```

### Datasource Configuration

```yaml
# clab/configs/grafana/provisioning/datasources/udr-postgres.yml
apiVersion: 1
datasources:
  - name: udr_postgres
    type: postgres
    uid: udr_postgres
    url: clab-ndt-wifi7-mlo-security-udr-db:5432
    database: udr
    user: ${DB_USER}
    jsonData:
      sslmode: disable
      postgresVersion: 1600
      timescaledb: true
```

---

## Customization Guide

### Adding New Panels

1. **Open Dashboard**: Grafana UI → Edit mode
2. **Add Panel**: Click "Add" → "Visualization"
3. **Configure Query**:
   ```sql
   SELECT
     ts_start AS "time",
     <your_metric> as value,
     <your_label> as metric
   FROM gcn_predictions
   WHERE $__timeFilter(ts_start)
     AND experiment_id ~ '${experiment_filter:regex}'
   ORDER BY ts_start
   ```
4. **Set Visualization**: Choose chart type
5. **Configure Display**: Colors, legend, axes
6. **Save Dashboard**: Export JSON and save to repo

### Modifying Thresholds

Edit `fieldConfig.defaults.thresholds` in JSON:

```json
{
  "thresholds": {
    "mode": "absolute",
    "steps": [
      {"value": null, "color": "green"},
      {"value": 50, "color": "yellow"},
      {"value": 80, "color": "red"}
    ]
  }
}
```

### Adding New Variables

1. **Dashboard Settings** → Variables → New
2. **Configure**:
   - Name: `your_variable`
   - Type: Query
   - Data source: udr_postgres
   - Query: `SELECT DISTINCT column FROM table`
3. **Use in panels**: `${your_variable:regex}`

---

## Best Practices

### 1. Time Range Selection

- **Real-time monitoring**: Last 15 minutes with 10s refresh
- **Investigation**: Last 1 hour
- **Performance analysis**: Last 6-24 hours
- **Historical review**: Custom range

### 2. Variable Usage

- Always use `experiment_filter` when analyzing specific tests
- Use `model_version` to compare before/after deployments
- Don't filter too narrowly (may miss patterns)

### 3. Performance Optimization

- Use relative time ranges (last 1h) instead of absolute
- Filter by experiment when possible
- Limit table rows (100 default is good)
- Disable unused panels
- Cache frequently used queries

### 4. Alerting

- Set alerts on actionable metrics only
- Use appropriate severity levels
- Include context in alert messages
- Test alerts with synthetic data

### 5. Documentation

- Screenshot important findings
- Export dashboard JSON after changes
- Document custom queries
- Version control dashboard configs

---

## Integration with Other Tools

### 1. Prometheus (Future)

Export GCN detector metrics to Prometheus:

```python
# In detector.py
from prometheus_client import Counter, Histogram

predictions_total = Counter('gcn_predictions_total', 'Total predictions')
attacks_detected = Counter('gcn_attacks_detected', 'Attacks detected')
inference_duration = Histogram('gcn_inference_seconds', 'Inference time')
```

### 2. Alertmanager (Future)

Route Grafana alerts to Alertmanager:

```yaml
# alertmanager.yml
receivers:
  - name: 'security-team'
    webhook_configs:
      - url: 'https://slack.com/api/webhooks/...'
```

### 3. Jupyter Notebooks

Export data for analysis:

```python
import psycopg2
import pandas as pd

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='udr',
    user='postgres'
)

df = pd.read_sql("""
    SELECT * FROM gcn_predictions
    WHERE experiment_id = '20260210-phase4-positive-full'
""", conn)

# Analyze with pandas/scikit-learn
```

---

## Maintenance

### Regular Tasks

**Daily:**
- Check dashboard for anomalies
- Review attack detections
- Verify auto-refresh working

**Weekly:**
- Analyze attack rate trends
- Review model performance metrics
- Check for data quality issues
- Update time range bookmarks

**Monthly:**
- Archive old predictions (> 30 days)
- Review dashboard performance
- Update thresholds based on drift
- Document notable incidents

### Dashboard Updates

**When to Update:**
- New model version deployed
- Schema changes in database
- New metrics added to predictions
- User feedback on usability
- Performance optimization needed

**Update Process:**
1. Edit in Grafana UI
2. Test changes thoroughly
3. Export JSON: Dashboard → Share → Export
4. Save to `clab/configs/grafana/dashboards/`
5. Commit to git with descriptive message
6. Update this documentation

---

## Related Documentation

- `WP8-GCN-INTEGRATION-PLAN.md` - Overall WP8 plan
- `WP8-PHASE4-E2E-TEST-ANALYSIS.md` - Testing results
- `CURRENT-STATE.md` - Project status
- `QUICK-REFERENCE.md` - Command reference

---

## Appendix: Panel Reference

| ID | Panel Name | Type | Purpose |
|----|------------|------|---------|
| 1 | Total Predictions | Stat | Count all predictions |
| 2 | Attacks Detected | Stat | Count attack classifications |
| 3 | Attack Rate | Stat | Percentage attacks |
| 4 | Avg Confidence | Stat | Mean confidence score |
| 5 | Avg Inference Time | Stat | Mean latency |
| 6 | Active Model | Stat | Current model version |
| 10 | Attack Detection Timeline | Time Series | Real-time attack visualization |
| 11 | Prediction Confidence Over Time | Time Series | Confidence trends |
| 12 | Confidence Score Distribution | Histogram | Confidence distribution |
| 20 | Prediction Distribution | Pie Chart | Normal vs Attack split |
| 21 | Attack Rate by Experiment | Bar Gauge | Per-experiment rates |
| 22 | Model Performance Summary | Stat | KPI summary |
| 30 | Recent Predictions | Table | Detailed prediction list |
| 40 | Inference Performance Over Time | Time Series | Latency trends |
| 41 | Probability Distributions Over Time | Time Series | Attack probability |

---

**Document Version**: 1.0
**Last Updated**: 2026-02-10
**Grafana Version**: 10.x+
**Dashboard UID**: `gcn-attack-detection`
