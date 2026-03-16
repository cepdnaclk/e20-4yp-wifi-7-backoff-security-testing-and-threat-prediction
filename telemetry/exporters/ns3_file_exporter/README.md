# ns3_file_exporter

Publishes `telemetry.jsonl` lines to Redpanda (Kafka API).

# WP4 acceptance checks (you must run these before you commit)
# 4.1 Ensure lab is up and Redpanda is running
make up
make status

# Sanity check:
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | grep -E "redpanda|timescale|grafana|clab-ndt"

# 4.2 Create the topic once (if not created already)
docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic create wifi7.telemetry.v0_1 --brokers localhost:9092

# 4.2.1 Verify topic exists:
docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic list --brokers localhost:9092

# 4.3 Build exporter image
docker build -t ndt/ns3-exporter:local telemetry/exporters/ns3_file_exporter

# 4.4 Run ns-3 to generate telemetry.jsonl

(Use your existing command)

make ns3-run-example EXP_ID=20251222-2340-wifi-example-42

# 4.5 Run exporter
EXP_ID=20251222-2340-wifi-example-42

docker run --rm -it \
  --network clab-mgmt \
  -v "$(pwd)/sim/ns3/artifacts:/work/sim/ns3/artifacts" \
  -v "$(pwd)/.exporter_state:/state" \
  -e TELEMETRY_FILE="/work/sim/ns3/artifacts/${EXP_ID}/telemetry.jsonl" \
  -e KAFKA_BROKERS="bus-redpanda:9092" \
  -e KAFKA_TOPIC="wifi7.telemetry.v0_1" \
  ndt/ns3-exporter:local

# 4.6 Confirm messages are in Redpanda - Open a second terminal and run:
docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic consume wifi7.telemetry.v0_1 --brokers localhost:9092 -n 5

# You must see your JSON records.
