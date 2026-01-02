# WP6: Grafana Provisioning and Dashboards

## Status: ✅ COMPLETED

## Overview
WP6 configured Grafana to query the UDR database and display telemetry metrics with experiment comparison capabilities.

---

## What Was Implemented

### 1. Grafana Provisioning as Code
**Paths:**
```
clab/configs/grafana/
├── provisioning/
│   ├── datasources/
│   │   └── udr-postgres.yml
│   └── dashboards/
│       └── dashboards.yml
└── dashboards/
    └── *.json
```

### 2. Datasource Configuration
**File:** `clab/configs/grafana/provisioning/datasources/udr-postgres.yml`

```yaml
apiVersion: 1
datasources:
  - name: UDR-Timescale
    type: postgres
    access: proxy
    url: udr-db:5432
    database: udr
    user: udr
    secureJsonData:
      password: udr_pass
    jsonData:
      sslmode: "disable"
      postgresVersion: 1600
      timescaledb: true
    isDefault: true
```

### 3. Dashboard Provisioning
**File:** `clab/configs/grafana/provisioning/dashboards/dashboards.yml`

```yaml
apiVersion: 1
providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /var/lib/grafana/dashboards
```

### 4. Containerlab Mounts
```yaml
grafana:
  binds:
    - configs/grafana/provisioning:/etc/grafana/provisioning:ro
    - configs/grafana/dashboards:/var/lib/grafana/dashboards:ro
```

---

## Acceptance Criteria (All Met)

| Criteria | Status |
|----------|--------|
| Grafana starts without errors | ✅ |
| Datasource connects to DB | ✅ |
| Can query metrics table | ✅ |
| Dashboard shows data | ✅ |
| Multiple experiments visible | ✅ |

---

## Key URLs

| Service | URL |
|---------|-----|
| Grafana | http://localhost:3000 |
| Default login | admin / admin |

---

## Problems Solved

### Problem 1: Grafana Keeps Restarting
**Error:**
```
Only one datasource per organization can be marked as default
```

**Cause:** Multiple datasource YAMLs had `isDefault: true`

**Solution:** Ensure only ONE datasource has `isDefault: true`

### Problem 2: Datasource Can't Connect
**Error:** Connection refused to database

**Cause:** 
- Wrong hostname (should be container name: `udr-db`)
- Not on same Docker network

**Solution:**
- Use container name as hostname
- Verify both containers on `clab-mgmt` network

### Problem 3: Dashboard Shows No Data
**Cause:** Time range doesn't include data timestamps

**Solution:**
- Check when data was inserted
- Adjust Grafana time range
- Ensure experiment timestamps are recent

---

## Dashboard Queries

### Throughput Over Time
```sql
SELECT
  ts AS time,
  value,
  experiment_id
FROM metrics
WHERE metric_name = 'throughput_mbps'
  AND $__timeFilter(ts)
ORDER BY ts
```

### Last N Experiments Comparison
```sql
SELECT
  experiment_id,
  AVG(value) as avg_throughput
FROM metrics
WHERE metric_name = 'throughput_mbps'
  AND experiment_id IN (
    SELECT DISTINCT experiment_id 
    FROM metrics 
    ORDER BY ts DESC 
    LIMIT 10
  )
GROUP BY experiment_id
ORDER BY experiment_id DESC
```

### Metrics by Entity
```sql
SELECT
  ts AS time,
  entity_id,
  value
FROM metrics
WHERE metric_name = $metric
  AND experiment_id = $experiment
  AND $__timeFilter(ts)
ORDER BY ts
```

---

## Data Flow (Complete Pipeline)

```
┌─────────────────────────────────────────────────────────────────┐
│                     COMPLETE PIPELINE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐                                           │
│  │    ns-3 Run      │                                           │
│  │                  │                                           │
│  │  make ns3-run    │                                           │
│  └────────┬─────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────┐                                           │
│  │ telemetry.jsonl  │  sim/ns3/artifacts/<EXP_ID>/              │
│  └────────┬─────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────┐                                           │
│  │    Exporter      │  File → Kafka                             │
│  └────────┬─────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────┐                                           │
│  │    Redpanda      │  wifi7.telemetry.v0_1                     │
│  └────────┬─────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────┐                                           │
│  │   Harmonizer     │  Kafka → DB                               │
│  └────────┬─────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────┐                                           │
│  │  TimescaleDB     │  public.metrics                           │
│  └────────┬─────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────┐                                           │
│  │    Grafana       │  http://localhost:3000                    │
│  │                  │                                           │
│  │  ┌────────────┐  │                                           │
│  │  │ Dashboard  │  │  Visualizes metrics                       │
│  │  └────────────┘  │                                           │
│  └──────────────────┘                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Grafana Configuration Structure

```
/etc/grafana/provisioning/           (read-only mount)
├── datasources/
│   └── udr-postgres.yml             Datasource definition
└── dashboards/
    └── dashboards.yml               Dashboard provider config

/var/lib/grafana/dashboards/         (read-only mount)
└── *.json                           Dashboard JSON files
```

---

## Verification Steps

```bash
# 1. Check Grafana is running
docker ps | grep grafana

# 2. Check logs for errors
docker logs clab-ndt-wifi7-mlo-security-grafana

# 3. Verify datasource in UI
# Go to: Settings → Data Sources → UDR-Timescale → Test

# 4. Query metrics directly
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "SELECT COUNT(*) FROM metrics;"

# 5. Verify data appears in Grafana
# Create a panel with: SELECT ts, value FROM metrics LIMIT 10
```

---

## Operational Notes

### Grafana Only Shows DB Data
- Grafana queries the database directly
- It does NOT read from Kafka
- Data must flow: Kafka → Harmonizer → DB → Grafana

### Time Range Matters
- Default Grafana time range is "Last 6 hours"
- If experiments are older, data won't show
- Adjust time range or use "Last 7 days"

### Dashboard Updates
- Dashboards are read from JSON files
- Changes in files are picked up automatically (updateIntervalSeconds: 10)
- Can also edit in UI and export JSON

---

## Current Operational Workflow

```bash
# 1. Start lab (if not running)
make up

# 2. Run experiment
EXP_ID=20251223-test-01
make ns3-run-example EXP_ID=$EXP_ID

# 3. Publish to Kafka
make exporter-run EXP_ID=$EXP_ID

# 4. Ingest to DB (run in separate terminal or background)
make harmonizer-run

# 5. View in Grafana
# Open http://localhost:3000
# Check dashboard for new experiment
```

---

## Related ADRs
- ADR-WP6-01: Grafana provisioning as code

---

## Next Steps (→ WP7)
- Make pipeline one-command
- Run harmonizer as long-running service
- Add `make pipeline-up` and `make run-exp`
