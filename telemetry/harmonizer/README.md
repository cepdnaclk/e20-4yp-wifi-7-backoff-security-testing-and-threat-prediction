# Harmonizer (WP5)

Consumes telemetry from Redpanda and writes normalized metrics to UDR (Postgres/Timescale).

# Build the harmonizer image correctly
    Option A (recommended)
docker build -t ndt/harmonizer:local telemetry/harmonizer

# Then verify:
docker images | grep harmonizer

#  Run the harmonizer (after build succeeds)
docker run --rm -it \
  --network clab-mgmt \
  -e KAFKA_BROKERS="bus-redpanda:9092" \
  -e KAFKA_TOPIC="wifi7.telemetry.v0_1" \
  -e PG_HOST="udr-db" \
  -e PG_DB="udr" \
  -e PG_USER="udr" \
  -e PG_PASS="udr_pass" \
  ndt/harmonizer:local

# Quick sanity checks if it still fails
    4.1 Confirm Redpanda hostname resolves on clab network
docker run --rm -it --network clab-mgmt alpine:3.20 sh -lc "apk add --no-cache bind-tools >/dev/null && nslookup bus-redpanda"

    4.2 Confirm Postgres hostname resolves and port open
docker run --rm -it --network clab-mgmt alpine:3.20 sh -lc "apk add --no-cache netcat-openbsd >/dev/null && nc -vz udr-db 5432"

# -------------------------------------------------------------------------------------------------->

# Below is a detailed “runbook” you can follow any day to (a) start everything, (b) generate new ns-3 telemetry, (c) publish it to Kafka/Redpanda, (d) ingest into Postgres (UDR), and (e) verify it.

# 1) “Is it already done?” (Exporter non-root + state permissions)
# What is done

In your last exporter run you used:
--user "$(id -u):$(id -g)"
So the exporter state is now created with your user, not root. That’s correct.

# What is NOT automatically done

If you run the exporter without --user ..., Docker will run it as root inside the container, and your host folder .exporter_state/ can become root-owned again.

# How to verify quickly
ls -la .exporter_state


# If you see root root on files inside it, you must fix it once:

sudo chown -R "$USER:$USER" .exporter_state

# 2) Start/stop the lab (Redpanda + UDR DB + Grafana)
# Start
From repo root:

make up
make status

# Check key containers are running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "bus-redpanda|udr-db|grafana"

# Stop and clean
make down

# 3) One full end-to-end run (New ns-3 telemetry → Kafka → UDR DB)
Step A: Create a new experiment ID

Use your standard format:
EXP_ID=20251223-1430-wifi-example-42

Step B: Run ns-3 and generate telemetry.jsonl
make ns3-run-example EXP_ID=$EXP_ID


Confirm file exists:

ls -la sim/ns3/artifacts/$EXP_ID/telemetry.jsonl
cat sim/ns3/artifacts/$EXP_ID/telemetry.jsonl

Step C: Export telemetry.jsonl into Redpanda topic
Recommended: keep state per EXP_ID so offsets never conflict:

mkdir -p ".exporter_state/${EXP_ID}"
docker run --rm -it \
  --network clab-mgmt \
  --user "$(id -u):$(id -g)" \
  -v "$(pwd)/sim/ns3/artifacts:/work/sim/ns3/artifacts:ro" \
  -v "$(pwd)/.exporter_state/${EXP_ID}:/state" \
  -e TELEMETRY_FILE="/work/sim/ns3/artifacts/${EXP_ID}/telemetry.jsonl" \
  -e KAFKA_BROKERS="bus-redpanda:9092" \
  -e KAFKA_TOPIC="wifi7.telemetry.v0_1" \
  ndt/ns3-exporter:local


Expected:
resume_offset=0 for a fresh EXP_ID

It publishes at least 1 message.

Step D: Confirm message is in Kafka/Redpanda (no Docker Hub pulls needed)
Use the Redpanda container:

docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic consume wifi7.telemetry.v0_1 --brokers localhost:9092 -n 5

You should see your new experiment_id.

Step E: Run harmonizer to write into Postgres (UDR)

For normal operation (stable group):

docker run --rm -it \
  --network clab-mgmt \
  -e KAFKA_BROKERS="bus-redpanda:9092" \
  -e KAFKA_TOPIC="wifi7.telemetry.v0_1" \
  -e KAFKA_GROUP="harmonizer-udm-v0" \
  -e PG_HOST="udr-db" \
  -e PG_DB="udr" \
  -e PG_USER="udr" \
  -e PG_PASS="udr_pass" \
  -e BATCH_SIZE=1 \
  ndt/harmonizer:local


For debugging or replay, use a test group:
-e KAFKA_GROUP="harmonizer-udm-v0-test2" -e AUTO_OFFSET_RESET="earliest"


Expected:
inserted/updated 1 rows (or more).

Step F: Verify UDR DB has the new row
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "SELECT experiment_id, ts, entity_id, metric_name, value, unit, source, ingest_time FROM metrics ORDER BY ts DESC LIMIT 20;"


You should see your EXP_ID.

# 4) The two most common failure cases and the fixes
# Case 1: Exporter runs but nothing new appears

Cause: offset state reused or wrong.
Fix:

Use per-exp state mount (recommended above), or reset state:

sudo rm -rf .exporter_state
mkdir -p .exporter_state

# Case 2: Harmonizer shows no inserts

Cause: consumer group already consumed offsets and no new messages exist.
Fix:

Use a new group for replay:

-e KAFKA_GROUP="harmonizer-udm-v0-testX" -e AUTO_OFFSET_RESET="earliest"

# 5) Make it “one command” next time (recommended Makefile targets)

If you want this to be repeatable without copy-pasting long commands, add two Make targets:

make exporter-run EXP_ID=...

make harmonizer-run

I can give you the exact Makefile snippet that matches your repo’s current Makefile (to avoid conflicts). Paste your current Makefile section around the existing ns3/exporter targets and I will write a clean drop-in patch.