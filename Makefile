# Makefile

.PHONY: up down status logs

CLAB_TOPO=clab/topo.yml

up:
	@containerlab deploy -t $(CLAB_TOPO)

down:
	@containerlab destroy -t $(CLAB_TOPO) --cleanup

status:
	@containerlab inspect -t $(CLAB_TOPO)

logs:
	@echo "Use: docker logs -f <container_name>"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

run-baseline:
	@test -n "$(EXP_ID)" || (echo "EXP_ID required. Example: make run-baseline EXP_ID=20251222-2100-baseline-42" && exit 1)
	@echo "TODO: run ns-3 baseline with EXP_ID=$(EXP_ID)"


.PHONY: ns3-build ns3-run

NS3_IMAGE=ndt/ns3:local

ns3-build:
	@docker build -t $(NS3_IMAGE) -f docker/ns3/Dockerfile docker/ns3

ns3-run:
	@test -n "$(EXP_ID)" || (echo "EXP_ID required. Example: make ns3-run EXP_ID=20251222-1835-baseline-42" && exit 1)
	@docker run --rm -it \
	  --user "$$(id -u):$$(id -g)" \
	  -v "$(PWD)":/work \
	  $(NS3_IMAGE) \
	  bash -lc "./sim/ns3/scenario/run_baseline.sh $(EXP_ID) 42"


.PHONY: ns3-run-example

ns3-run-example:
	@test -n "$(EXP_ID)" || (echo "EXP_ID required" && exit 1)
	@docker run --rm -it \
	  --user "$$(id -u):$$(id -g)" \
	  -v "$(PWD)":/work \
	  $(NS3_IMAGE) \
	  bash -lc "./sim/ns3/scenario/run_wifi_example_and_export.sh $(EXP_ID) 42"

.PHONY: exporter-build harmonizer-build exporter-run harmonizer-run run-wifi-pipeline

EXPORTER_IMAGE=ndt/ns3-exporter:local
HARMONIZER_IMAGE=ndt/harmonizer:local

KAFKA_BROKERS ?= bus-redpanda:9092
KAFKA_TOPIC   ?= wifi7.telemetry.v0_1

PG_HOST ?= udr-db
PG_DB   ?= udr
PG_USER ?= udr
PG_PASS ?= udr_pass

exporter-build:
	@docker build -t $(EXPORTER_IMAGE) telemetry/exporters/ns3_file_exporter

harmonizer-build:
	@docker build -t $(HARMONIZER_IMAGE) telemetry/harmonizer

exporter-run:
	@test -n "$(EXP_ID)" || (echo "EXP_ID required" && exit 1)
	@docker run --rm -it \
	  --network clab-mgmt \
	  --user "$$(id -u):$$(id -g)" \
	  -v "$(PWD)/sim/ns3/artifacts:/work/sim/ns3/artifacts:ro" \
	  -v "$(PWD)/.exporter_state:/state" \
	  -e TELEMETRY_FILE="/work/sim/ns3/artifacts/$(EXP_ID)/telemetry.jsonl" \
	  -e KAFKA_BROKERS="$(KAFKA_BROKERS)" \
	  -e KAFKA_TOPIC="$(KAFKA_TOPIC)" \
	  $(EXPORTER_IMAGE)

harmonizer-run:
	@docker run --rm -it \
	  --network clab-mgmt \
	  -e KAFKA_BROKERS="$(KAFKA_BROKERS)" \
	  -e KAFKA_TOPIC="$(KAFKA_TOPIC)" \
	  -e PG_HOST="$(PG_HOST)" \
	  -e PG_DB="$(PG_DB)" \
	  -e PG_USER="$(PG_USER)" \
	  -e PG_PASS="$(PG_PASS)" \
	  -e BATCH_SIZE=1 \
	  $(HARMONIZER_IMAGE)

run-wifi-pipeline:
	@echo "DEPRECATED: Use 'make run-exp EXP_ID=...' instead (requires 'make pipeline-up' first)"
	@test -n "$(EXP_ID)" || (echo "EXP_ID required" && exit 1)
	@$(MAKE) ns3-run-example EXP_ID=$(EXP_ID)
	@$(MAKE) exporter-run EXP_ID=$(EXP_ID)

# =============================================================================
# WP7: One-Command Pipeline
# =============================================================================
# Usage:
#   make pipeline-up   # Start harmonizer as background service
#   make run-exp EXP_ID=20260103-1200-test-01  # Run full experiment
#   make pipeline-down # Stop harmonizer
# =============================================================================

.PHONY: pipeline-up pipeline-down pipeline-status run-exp

# Start long-running pipeline services (harmonizer)
pipeline-up:
	@echo "Starting pipeline services..."
	@docker-compose -f docker-compose.pipeline.yml up -d
	@echo ""
	@echo "Pipeline services started. Check status with: make pipeline-status"

# Stop pipeline services
pipeline-down:
	@echo "Stopping pipeline services..."
	@docker-compose -f docker-compose.pipeline.yml down
	@echo "Pipeline services stopped."

# Check pipeline services status
pipeline-status:
	@docker-compose -f docker-compose.pipeline.yml ps
	@echo ""
	@echo "Harmonizer logs (last 10 lines):"
	@docker-compose -f docker-compose.pipeline.yml logs --tail=10 harmonizer

# Run complete experiment: ns-3 -> exporter -> (harmonizer already running)
run-exp:
	@test -n "$(EXP_ID)" || (echo "EXP_ID required. Example: make run-exp EXP_ID=20260103-1200-test-01" && exit 1)
	@echo "=============================================="
	@echo "Running experiment: $(EXP_ID)"
	@echo "=============================================="
	@echo ""
	@echo "[1/3] Running ns-3 simulation..."
	@$(MAKE) ns3-run-example EXP_ID=$(EXP_ID)
	@echo ""
	@echo "[2/3] Publishing telemetry to Kafka..."
	@$(MAKE) exporter-run EXP_ID=$(EXP_ID)
	@echo ""
	@echo "[3/3] Waiting for harmonizer ingestion (5s)..."
	@sleep 5
	@echo ""
	@echo "=============================================="
	@echo "Experiment complete!"
	@echo "=============================================="
	@echo "View results:"
	@echo "  - Grafana: http://localhost:3000"
	@echo "  - DB check: docker exec -it clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c \"SELECT COUNT(*) FROM metrics WHERE experiment_id='$(EXP_ID)';\""
