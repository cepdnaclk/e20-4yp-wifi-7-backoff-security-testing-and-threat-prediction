# MLO Runs: telemetry.jsonl Created but Grafana Empty (Report)

## Summary

Your MLO runs created `telemetry.jsonl` correctly and the exporter read the
files, but the Kafka topic the pipeline depends on did not exist. The harmonizer
log confirms it could not subscribe to `wifi7.telemetry.v0_1` because the topic
was missing. As a result, no messages were ingested into TimescaleDB, so Grafana
shows no data.

## Evidence Collected

1. **Exporter advanced offsets**
   - `.exporter_state/exporter_state.json` contains offsets for all three new
     EXP_IDs, which means the exporter read each file and advanced to EOF.
   - Example entries:
     - `/work/sim/ns3/artifacts/20260103-1400-mlo-normal-42/telemetry.jsonl`
     - `/work/sim/ns3/artifacts/20260103-1400-mlo-attack-pos-42/telemetry.jsonl`
     - `/work/sim/ns3/artifacts/20260103-1400-mlo-attack-neg-42/telemetry.jsonl`

2. **Harmonizer error**
   - `docker-compose -f docker-compose.pipeline.yml logs --tail=50 harmonizer`
     shows:
     ```
     offset reset ... failed to query logical offset: Broker: Unknown topic or partition
     ```
   - This indicates `wifi7.telemetry.v0_1` does **not** exist in Redpanda.

3. **Resulting pipeline behavior**
   - Exporter attempted to publish, but the broker had no topic.
   - Harmonizer never received messages.
   - DB has no new rows, so Grafana shows no data.

## Is the Exporter Supposed to Always Run?

**No.** The current flow (run the simulation first, then run the exporter) is
correct.

Why:
- The exporter reads from disk and uses a persisted file offset.
- It does not need to be running while ns-3 writes the file.
- Running it afterward is a normal, supported mode.

**Important caveat:** the exporter updates its offset state even if Kafka is not
ready. If the topic is missing, the exporter can mark the file as "done" without
the data being delivered.

## Root Cause

**Kafka topic missing.**  
The Redpanda topic `wifi7.telemetry.v0_1` was not created, so the harmonizer
could not subscribe and the exporter could not publish successfully.

This matches the troubleshooting note in `docs/codex/pipeline-run-troubleshooting.md`
and the setup requirement in `telemetry/exporters/ns3_file_exporter/README.md`.

## What To Do Now (Recovery)

1. **Create the topic (one-time)**
   ```bash
   docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
     rpk topic create wifi7.telemetry.v0_1 --brokers localhost:9092
   ```

2. **Confirm the topic exists**
   ```bash
   docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
     rpk topic list --brokers localhost:9092
   ```

3. **Re-publish telemetry**
   - Option A: delete or reset the exporter state for those files:
     - Edit `.exporter_state/exporter_state.json` and remove those entries,
       or delete the file entirely (it will be recreated).
   - Option B: rerun with new `EXP_ID`s to generate new telemetry files.

4. **Verify ingestion**
   ```bash
   docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
     rpk topic consume wifi7.telemetry.v0_1 -o oldest -n 5

   docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
     psql -U udr -d udr -c "SELECT COUNT(*) FROM metrics;"
   ```

5. **Grafana time range check**
   - Your telemetry timestamps are in **2026** (`2026-01-04T...Z`).
   - In Grafana, make sure the time picker covers those dates.

## Preventive Steps

1. **Create the Kafka topic once as part of setup**
   - Add a note or a Makefile target to run `rpk topic create ...` after `make up`.

2. **Optional: make harmonizer start with a fresh consumer group**
   - If you need to replay existing messages:
     ```
     KAFKA_GROUP=harmonizer-$(date +%s) AUTO_OFFSET_RESET=earliest make pipeline-up
     ```

3. **Optional: improve exporter safety**
   - It currently saves offsets even when Kafka publish fails.
   - A future improvement is to only update offsets after delivery success.

## Bottom Line

The exporter does **not** need to run before simulation, but the Kafka topic
must exist before the exporter runs. In your case, missing topic creation
prevented end-to-end ingestion, so Grafana stayed empty even though the
telemetry files were generated.
