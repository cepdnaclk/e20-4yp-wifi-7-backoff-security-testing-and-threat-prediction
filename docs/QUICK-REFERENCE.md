# NDT Wi-Fi 7 MLO Security — Quick Reference

## Pipeline Overview

```
NS-3 → telemetry.jsonl → Exporter → Redpanda → Harmonizer → TimescaleDB
                                          │
                                     Windowizer → GCN Detector → gcn_predictions
                                                                        │
                                              ┌─────────────────────────┤
                                              ▼                         ▼
                                       Grafana :3000       Dashboard :8888
```

---

## Full Startup Sequence

```bash
# 1. Start infrastructure (once per session)
make up                  # Containerlab: DB, Redpanda, Grafana

# 2. Start pipeline services (once per session)
make pipeline-up         # Harmonizer (Kafka → DB)
make gcn-up              # Windowizer + GCN Detector

# 3. Start custom dashboard (optional)
make dashboard-up        # React + FastAPI → http://localhost:8888

# 4. Run experiments
bash run_scenarios.sh    # Normal + positive attack + negative attack
# or individually:
make run-mlo-exp EXP_ID="$(date +%Y%m%d-%H%M)-mlo-normal-42"   SCENARIO=normal
make run-mlo-exp EXP_ID="$(date +%Y%m%d-%H%M)-mlo-attack-pos"  SCENARIO=positive
make run-mlo-exp EXP_ID="$(date +%Y%m%d-%H%M)-mlo-attack-neg"  SCENARIO=negative

# 5. Open dashboards
# http://localhost:8888      ← Custom dashboard (real-time)
# http://localhost:3000      ← Grafana (analytics)

# 6. Stop everything
make gcn-down            # Stop GCN pipeline
make dashboard-down      # Stop custom dashboard
make pipeline-down       # Stop harmonizer
make down                # Destroy Containerlab
```

---

## Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Custom Dashboard | http://localhost:8888 | — |
| Grafana | http://localhost:3000 | admin / admin |
| Unified Grafana dashboard | http://localhost:3000/d/ndt-unified | — |

---

## Infrastructure Commands

```bash
make up                  # Deploy Containerlab
make down                # Destroy Containerlab
make status              # Container status
make logs                # Tail all logs
```

---

## Pipeline Commands

```bash
# Harmonizer (raw telemetry → DB)
make pipeline-up         # Start harmonizer (background)
make pipeline-down       # Stop
make pipeline-status     # Logs + status

# GCN pipeline (segments → predictions)
make gcn-up              # Start windowizer + GCN detector
make gcn-down            # Stop
make gcn-status          # Logs + status
```

---

## Experiment Commands

```bash
# Generic
make run-exp EXP_ID=20260228-1400-test-42

# MLO attack scenarios
make run-mlo-exp EXP_ID=20260228-1400-mlo-normal-42   SCENARIO=normal
make run-mlo-exp EXP_ID=20260228-1400-mlo-attack-pos  SCENARIO=positive
make run-mlo-exp EXP_ID=20260228-1400-mlo-attack-neg  SCENARIO=negative

# Batch (all three)
bash run_scenarios.sh
```

### Experiment ID format
```
YYYYMMDD-HHMM-<scenario>-<seed>
```

---

## Custom Dashboard Commands

```bash
make dashboard-build     # Build Docker image
make dashboard-up        # Start http://localhost:8888
make dashboard-down      # Stop
make dashboard-logs      # Follow logs
make dashboard-status    # Status + last 20 log lines
```

---

## Build Commands

```bash
make ns3-build           # ns-3.46.1 image
make exporter-build      # File → Kafka exporter
make harmonizer-build    # Kafka → DB
make windowizer-build    # 256-window segmentation
make gcn-detector-build  # GCN inference
make dashboard-build     # React + FastAPI dashboard
```

---

## GCN Model Commands

```bash
make gcn-train           # Train new model
make gcn-evaluate        # Evaluate model
make gcn-deploy VERSION=v2.0.0   # Deploy version (updates current symlink)
```

Active model: `twin/registry/gcn/current` → `v2.0.0`

---

## Database

```bash
# Connect
docker exec -it clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr

# Row counts
SELECT COUNT(*) FROM metrics;
SELECT COUNT(*) FROM gcn_predictions;

# Experiment list with attack rates
SELECT experiment_id, COUNT(*) AS segs,
       ROUND(AVG(confidence)::numeric,3) AS avg_conf
  FROM gcn_predictions GROUP BY 1 ORDER BY 1;

# Fresh start (preserves filesystem training data)
TRUNCATE metrics; TRUNCATE gcn_predictions;
```

---

## Verification Commands

```bash
# Check Kafka messages
docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic consume wifi7.telemetry.v0_1 -o oldest -n 5

# Check GCN windowed features topic
docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic consume wifi7.ml.windowed_features.v1 -o oldest -n 2

# Check all pipeline services
docker compose -f docker-compose.pipeline.yml ps

# Health endpoints
curl -s http://localhost:8080/status        # GCN detector
curl -s http://localhost:8888/api/health    # Custom dashboard
curl -s http://localhost:3000/api/health    # Grafana
```

---

## Attack Scenarios Reference

| Scenario | Backoff Bias | Observed Effect |
|----------|-------------|-----------------|
| `normal` | 0 | Baseline Wi-Fi 7 MLO |
| `positive` | +5000 | +285× backoff slots, −84% throughput |
| `negative` | −5000 | −56% backoff slots, −44% throughput |

---

## Container Names

```
clab-ndt-wifi7-mlo-security-udr-db        (TimescaleDB  :5432)
clab-ndt-wifi7-mlo-security-grafana       (Grafana      :3000)
clab-ndt-wifi7-mlo-security-bus-redpanda  (Redpanda     :9092)
ndt-pipeline-harmonizer
ndt-pipeline-windowizer
ndt-pipeline-gcn-detector
ndt-dashboard                             (Dashboard    :8888)
```

---

## Telemetry Schema (v0.1)

```json
{
  "experiment_id": "20260228-1400-mlo-normal-42",
  "ts": "2026-02-28T14:00:00.000Z",
  "source": "ns3",
  "schema_version": "v0.1",
  "entity_id": "network",
  "metric": "backoff_slots",
  "value": 4.95,
  "unit": "slots"
}
```

### 13 Tracked Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| backoff_slots | slots | CSMA/CA backoff window size |
| throughput_mbps | Mbps | Network throughput |
| packet_loss_rate | ratio | Fraction of lost packets |
| delay_ms | ms | End-to-end delay |
| channel_busy_ratio | ratio | Channel busy fraction |
| retry_count | count | Transmission retry count |
| link1_usage | ratio | MLO Link 1 utilisation |
| link2_usage | ratio | MLO Link 2 utilisation |
| mcs_index | index | Modulation and coding scheme |
| rssi_dbm | dBm | Received signal strength |
| snr_db | dB | Signal-to-noise ratio |
| queue_depth | packets | TX queue depth |
| jitter_ms | ms | Delay variation |

---

## Grafana Unified Dashboard Variables

| Variable | Purpose | All-value |
|----------|---------|-----------|
| `run_prefix` | Filter by experiment name prefix | `%` (show all) |
| `model_version` | Filter by GCN model version | `.*` |
| `experiment_selector` | Pick one experiment for drill-down | `%` |

---

## Common Issues

| Problem | Solution |
|---------|----------|
| Exporter publishes nothing | `rm -f .exporter_state/exporter_state.json` |
| Harmonizer: no DB changes | Use new consumer group with `AUTO_OFFSET_RESET=earliest` |
| GCN: no predictions | Verify windowizer is consuming telemetry from Kafka |
| Grafana: no data | Check time range — simulation timestamps are historical |
| Dashboard: DB unavailable | Run `make up` first (needs clab-mgmt Docker network) |
| Permission denied on artifacts | `--user "$(id -u):$(id -g)"` |
| Port conflict | Check 3000, 5432, 8888, 9092 are free before `make up` |

---

## File Locations

| What | Where |
|------|-------|
| Containerlab topology | `clab/topo.yml` |
| Unified Grafana dashboard | `clab/configs/grafana/dashboards/ndt-unified.json` |
| DB schema | `clab/configs/udr-db/initdb/` |
| ns-3 scenarios | `sim/ns3/scenario/` |
| ns-3 artifacts | `sim/ns3/artifacts/<EXP_ID>/` |
| Exporter | `telemetry/exporters/ns3_file_exporter/` |
| Harmonizer | `telemetry/harmonizer/` |
| Windowizer | `security/detector/windowizer/` |
| GCN detector | `twin/gnn/detector/` |
| GCN model registry | `twin/registry/gcn/` |
| Custom dashboard | `dashboard/app/` |
| ADRs | `docs/ALL-ADRS.md`, `docs/adr/` |
| Batch scenario runner | `run_scenarios.sh` |
