# NDT Wi-Fi 7 MLO Security - Quick Reference

## Pipeline Overview
```
ns-3 → telemetry.jsonl → Exporter → Kafka → Harmonizer → DB → Grafana
```

## Essential Commands (WP7)

```bash
# Start everything
make up              # Containerlab services
make pipeline-up     # Harmonizer (background)

# Run experiment (one command!)
make run-exp EXP_ID=20260103-1200-test-01

# Check status
make pipeline-status

# Stop everything
make pipeline-down   # Stop harmonizer
make down            # Stop containerlab
```

## MLO Attack Scenarios (WP7.5)

```bash
# Run MLO scenarios (requires pipeline-up first)
make run-mlo-normal EXP_ID=20260103-1400-mlo-normal-42
make run-mlo-positive EXP_ID=20260103-1400-mlo-attack-pos-42
make run-mlo-negative EXP_ID=20260103-1400-mlo-attack-neg-42

# Full pipeline with exporter
make run-mlo-exp EXP_ID=... SCENARIO=normal|positive|negative
```

| Scenario | Bias | Purpose |
|----------|------|---------|
| normal | 0 | Baseline (no attack) |
| positive | +5000 | Aggressive transmission |
| negative | -5000 | Extreme aggression |

## Manual Mode (Legacy)

```bash
# Run experiment components separately
EXP_ID=20260103-1500-test-01
make ns3-run-example EXP_ID=$EXP_ID
make exporter-run EXP_ID=$EXP_ID
make harmonizer-run  # In separate terminal
```

## Service URLs

| Service | URL/Port |
|---------|----------|
| Grafana | http://localhost:3000 |
| Redpanda | localhost:9092 |
| Database | localhost:5432 |

## Container Names
```
clab-ndt-wifi7-mlo-security-udr-db
clab-ndt-wifi7-mlo-security-grafana
clab-ndt-wifi7-mlo-security-bus-redpanda
```

## Verification Commands

```bash
# Check Kafka messages
docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic consume wifi7.telemetry.v0_1 -o oldest -n 5

# Check database
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "SELECT * FROM metrics ORDER BY ts DESC LIMIT 5;"

# Check container status
make status
```

## Experiment ID Format
```
YYYYMMDD-HHMM-<scenario>-<seed>
Example: 20251223-1500-wifi-example-42
```

## Telemetry Schema (v0.1)
```json
{
  "experiment_id": "string",
  "ts": "ISO timestamp",
  "source": "ns3",
  "schema_version": "v0.1",
  "entity_id": "string",
  "metric": "string",
  "value": float,
  "unit": "string"
}
```

## Common Issues

| Problem | Solution |
|---------|----------|
| Exporter publishes nothing | Delete `.exporter_state/exporter_state.json` |
| Harmonizer: no DB changes | Use new consumer group with `earliest` |
| Grafana: no data | Check time range, verify DB has rows |
| Permission denied | Run with `--user "$(id -u):$(id -g)"` |

## File Locations

| What | Where |
|------|-------|
| Containerlab topology | `clab/topo.yml` |
| ns-3 artifacts | `sim/ns3/artifacts/<EXP_ID>/` |
| Exporter code | `telemetry/exporters/ns3_file_exporter/` |
| Harmonizer code | `telemetry/harmonizer/` |
| Grafana dashboards | `clab/configs/grafana/dashboards/` |
| ADRs | `docs/adr/` |

## Build Commands

```bash
make ns3-build        # Build ns-3 image
make exporter-build   # Build exporter image
make harmonizer-build # Build harmonizer image
```

## Database Access

```bash
# Connect to database
docker exec -it clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr

# Quick queries
\dt                    # List tables
\d metrics             # Describe metrics table
SELECT COUNT(*) FROM metrics;
```
