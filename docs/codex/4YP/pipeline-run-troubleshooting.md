# Pipeline Run Troubleshooting Notes

## What Happened
- Containerlab services started correctly (Redpanda, TimescaleDB, Grafana).
- The pipeline harmonizer service started via `make pipeline-up`.
- `make run-exp EXP_ID=...` ran the ns-3 scenario and created:
  - sim/ns3/artifacts/<EXP_ID>/telemetry.jsonl
- The exporter published the telemetry message to Kafka successfully.
- The database initially showed 0 rows in the `metrics` table.

## Evidence Collected
- telemetry.jsonl existed and had one JSONL record:
  - experiment_id=20260103-115316-test
  - metric=throughput_mbps
- Kafka topic `wifi7.telemetry.v0_1` contained the message (confirmed via `rpk topic consume`).
- TimescaleDB table `metrics` existed but had no rows.
- Harmonizer logs showed no output in the background container.

## Root Cause
The background harmonizer uses a Kafka consumer group (`harmonizer-udm-v0`) with
`AUTO_OFFSET_RESET=latest` by default. If the consumer group already has an
offset recorded or starts after the message is produced, it will not read older
messages. This makes it look like the pipeline is "stuck" even though Kafka has
data.

## Fix That Worked
Running a one-shot harmonizer with a new consumer group and `AUTO_OFFSET_RESET=earliest`
successfully ingested the existing Kafka message into the database:

```
docker run --rm --network clab-mgmt \
  -e KAFKA_GROUP=harmonizer-replay-$(date +%s) \
  -e AUTO_OFFSET_RESET=earliest \
  ndt/harmonizer:local
```

After this, the row appeared in `metrics`:
- experiment_id=20260103-115316-test
- metric_name=throughput_mbps
- value=117.5

## Why It Happens
Kafka remembers consumer offsets per group. The background harmonizer is
configured for steady-state ingestion (new data only), so it will skip older
messages unless:
- the group has no previous offsets, or
- `AUTO_OFFSET_RESET=earliest` is used for a new group.

## How To Avoid It Next Time
Pick one of these approaches:

1) Start the harmonizer before running experiments
- `make pipeline-up`
- `make run-exp EXP_ID=...`

2) Use a fresh consumer group when starting the pipeline
- `KAFKA_GROUP=harmonizer-$(date +%s) AUTO_OFFSET_RESET=earliest make pipeline-up`

## Quick Verification Commands
- Check Kafka:
  - `docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda rpk topic consume wifi7.telemetry.v0_1 -o oldest -n 5`
- Check DB:
  - `docker exec -it clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "SELECT * FROM metrics ORDER BY ts DESC LIMIT 5;"`
