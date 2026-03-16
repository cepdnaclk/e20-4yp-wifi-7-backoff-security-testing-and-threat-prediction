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
	  -v "$(CURDIR)":/work \
	  $(NS3_IMAGE) \
	  bash -lc "./sim/ns3/scenario/run_baseline.sh $(EXP_ID) 42"


.PHONY: ns3-run-example

ns3-run-example:
	@test -n "$(EXP_ID)" || (echo "EXP_ID required" && exit 1)
	@docker run --rm -it \
	  --user "$$(id -u):$$(id -g)" \
	  -v "$(CURDIR)":/work \
	  $(NS3_IMAGE) \
	  bash -lc "./sim/ns3/scenario/run_wifi_example_and_export.sh $(EXP_ID) 42"

.PHONY: exporter-build harmonizer-build exporter-run harmonizer-run run-wifi-pipeline

EXPORTER_IMAGE=ndt/ns3-exporter:local
HARMONIZER_IMAGE=ndt/harmonizer:local

KAFKA_BROKERS ?= bus-redpanda:9092
KAFKA_TOPIC   ?= wifi7.telemetry.v0_1
EXPORTER_POLL_INTERVAL ?= 0.25
EXPORTER_FLUSH_TIMEOUT ?= 30.0
EXPORTER_MAX_MESSAGES_PER_CYCLE ?= 0
EXPORTER_RUN_CONTINUOUS ?= false

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
	@docker run --rm $(if $(INTERACTIVE),-it,) \
	  --network clab-mgmt \
	  --user "$$(id -u):$$(id -g)" \
	  -v "$(CURDIR)/sim/ns3/artifacts:/work/sim/ns3/artifacts:ro" \
	  -v "$(CURDIR)/.exporter_state:/state" \
	  -e TELEMETRY_FILE="/work/sim/ns3/artifacts/$(EXP_ID)/telemetry.jsonl" \
	  -e KAFKA_BROKERS="$(KAFKA_BROKERS)" \
	  -e KAFKA_TOPIC="$(KAFKA_TOPIC)" \
	  -e POLL_INTERVAL="$(EXPORTER_POLL_INTERVAL)" \
	  -e FLUSH_TIMEOUT="$(EXPORTER_FLUSH_TIMEOUT)" \
	  -e MAX_MESSAGES_PER_CYCLE="$(EXPORTER_MAX_MESSAGES_PER_CYCLE)" \
	  -e RUN_CONTINUOUS="$(EXPORTER_RUN_CONTINUOUS)" \
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
	@docker compose -f docker-compose.pipeline.yml up -d
	@echo ""
	@echo "Pipeline services started. Check status with: make pipeline-status"

# Stop pipeline services
pipeline-down:
	@echo "Stopping pipeline services..."
	@docker compose -f docker-compose.pipeline.yml down
	@echo "Pipeline services stopped."

# Check pipeline services status
pipeline-status:
	@docker compose -f docker-compose.pipeline.yml ps
	@echo ""
	@echo "Harmonizer logs (last 10 lines):"
	@docker compose -f docker-compose.pipeline.yml logs --tail=10 harmonizer

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

# =============================================================================
# WP7.5: MLO Attack Scenario Targets
# =============================================================================
# Usage:
#   make run-mlo-normal EXP_ID=20260103-1400-mlo-normal-42
#   make run-mlo-positive EXP_ID=20260103-1400-mlo-attack-pos-42
#   make run-mlo-negative EXP_ID=20260103-1400-mlo-attack-neg-42
#   make run-mlo-exp EXP_ID=... SCENARIO=normal|positive|negative
# =============================================================================

.PHONY: run-mlo-normal run-mlo-positive run-mlo-negative run-mlo-exp run-mlo-exp-stream run-mlo-dynamic

SEED       ?= 42
SIM_TIME   ?= 50.0
NAP        ?= 1
NSTA       ?= 2
NCPU       ?= $(shell nproc)
V3_COLLECT ?=
V3_DATA_DIR ?= twin/gnn/training_data/v3

# Run MLO normal baseline scenario (no attack)
run-mlo-normal:
	@test -n "$(EXP_ID)" || (echo "EXP_ID required. Example: make run-mlo-normal EXP_ID=20260103-1400-mlo-normal-42" && exit 1)
	@docker run --rm $(if $(INTERACTIVE),-it,) \
	  --user "$$(id -u):$$(id -g)" \
	  -v "$(CURDIR)":/work \
	  -e NAP="$(NAP)" \
	  -e NSTA="$(NSTA)" \
	  -e SEED="$(SEED)" \
	  -e SIM_TIME="$(SIM_TIME)" \
	  -e V3_COLLECT="$(V3_COLLECT)" \
	  -e V3_DATA_DIR="/work/$(V3_DATA_DIR)" \
	  -e V4_COLLECT="$(V4_COLLECT)" \
	  -e V4_DATA_DIR="/work/$(V4_DATA_DIR)" \
	  -e V4_TAG="$(V4_TAG)" \
	  $(NS3_IMAGE) \
	  bash -lc "/work/sim/ns3/scenario/run_mlo_scenario.sh $(EXP_ID) normal"

# Run MLO positive bias attack scenario
run-mlo-positive:
	@test -n "$(EXP_ID)" || (echo "EXP_ID required. Example: make run-mlo-positive EXP_ID=20260103-1400-mlo-attack-pos-42" && exit 1)
	@docker run --rm $(if $(INTERACTIVE),-it,) \
	  --user "$$(id -u):$$(id -g)" \
	  -v "$(CURDIR)":/work \
	  -e NAP="$(NAP)" \
	  -e NSTA="$(NSTA)" \
	  -e SEED="$(SEED)" \
	  -e SIM_TIME="$(SIM_TIME)" \
	  -e BIAS="$(BIAS)" \
	  -e V3_COLLECT="$(V3_COLLECT)" \
	  -e V3_DATA_DIR="/work/$(V3_DATA_DIR)" \
	  -e V4_COLLECT="$(V4_COLLECT)" \
	  -e V4_DATA_DIR="/work/$(V4_DATA_DIR)" \
	  -e V4_TAG="$(V4_TAG)" \
	  $(NS3_IMAGE) \
	  bash -lc "/work/sim/ns3/scenario/run_mlo_scenario.sh $(EXP_ID) positive"

# Run MLO negative bias attack scenario
run-mlo-negative:
	@test -n "$(EXP_ID)" || (echo "EXP_ID required. Example: make run-mlo-negative EXP_ID=20260103-1400-mlo-attack-neg-42" && exit 1)
	@docker run --rm $(if $(INTERACTIVE),-it,) \
	  --user "$$(id -u):$$(id -g)" \
	  -v "$(CURDIR)":/work \
	  -e NAP="$(NAP)" \
	  -e NSTA="$(NSTA)" \
	  -e SEED="$(SEED)" \
	  -e SIM_TIME="$(SIM_TIME)" \
	  -e BIAS="$(BIAS)" \
	  -e V3_COLLECT="$(V3_COLLECT)" \
	  -e V3_DATA_DIR="/work/$(V3_DATA_DIR)" \
	  -e V4_COLLECT="$(V4_COLLECT)" \
	  -e V4_DATA_DIR="/work/$(V4_DATA_DIR)" \
	  -e V4_TAG="$(V4_TAG)" \
	  $(NS3_IMAGE) \
	  bash -lc "/work/sim/ns3/scenario/run_mlo_scenario.sh $(EXP_ID) negative"

# Full MLO pipeline: simulation + exporter (requires pipeline-up first)
run-mlo-exp:
	@test -n "$(EXP_ID)" || (echo "EXP_ID required" && exit 1)
	@test -n "$(SCENARIO)" || (echo "SCENARIO required (normal|positive|negative)" && exit 1)
	@echo "=============================================="
	@echo "Running MLO experiment: $(EXP_ID)"
	@echo "Scenario: $(SCENARIO)"
	@echo "Sim time: $(SIM_TIME)s"
	@echo "Exporter max messages/cycle: $(EXPORTER_MAX_MESSAGES_PER_CYCLE)"
	@echo "=============================================="
	@echo ""
	@echo "[1/3] Running ns-3 MLO simulation..."
	@$(MAKE) run-mlo-$(SCENARIO) EXP_ID=$(EXP_ID) SEED=$(SEED) SIM_TIME=$(SIM_TIME)
	@echo ""
	@echo "[2/3] Publishing telemetry to Kafka..."
	@$(MAKE) exporter-run EXP_ID=$(EXP_ID) \
	  EXPORTER_POLL_INTERVAL=$(EXPORTER_POLL_INTERVAL) \
	  EXPORTER_FLUSH_TIMEOUT=$(EXPORTER_FLUSH_TIMEOUT) \
	  EXPORTER_MAX_MESSAGES_PER_CYCLE=$(EXPORTER_MAX_MESSAGES_PER_CYCLE)
	@echo ""
	@echo "[3/3] Waiting for harmonizer ingestion (5s)..."
	@sleep 5
	@echo ""
	@echo "=============================================="
	@echo "MLO experiment complete!"
	@echo "=============================================="
	@echo "View results:"
	@echo "  - Grafana: http://localhost:3000"
	@echo "  - DB check: docker exec -it clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c \"SELECT COUNT(*) FROM metrics WHERE experiment_id='$(EXP_ID)';\""

# Run MLO dynamic scenario — bias changes mid-simulation according to PHASES schedule.
# Usage:
#   make run-mlo-dynamic EXP_ID=20260315-2200-mlo-dynamic-42 PHASES="0:0,20:5000,40:-5000,60:0"
#   make run-mlo-dynamic EXP_ID=... PHASES="0:5000,40:0" SEED=99 SIM_TIME=80 NAP=2 NSTA=4
run-mlo-dynamic:
	@test -n "$(EXP_ID)" || (echo "EXP_ID required" && exit 1)
	@test -n "$(PHASES)" || (echo "PHASES required. Example: PHASES='0:0,20:5000,40:-5000,60:0'" && exit 1)
	@docker run --rm $(if $(INTERACTIVE),-it,) \
	  --user "$$(id -u):$$(id -g)" \
	  -v "$(CURDIR)":/work \
	  -e NAP="$(NAP)" \
	  -e NSTA="$(NSTA)" \
	  -e SEED="$(SEED)" \
	  -e SIM_TIME="$(SIM_TIME)" \
	  -e V4_COLLECT="$(V4_COLLECT)" \
	  -e V4_DATA_DIR="/work/$(V4_DATA_DIR)" \
	  -e V4_TAG="$(V4_TAG)" \
	  $(NS3_IMAGE) \
	  bash -lc "/work/sim/ns3/scenario/run_mlo_dynamic.sh $(EXP_ID) '$(PHASES)'"

# Stream-friendly MLO run: publish telemetry in segment-sized chunks to mimic live flow.
run-mlo-exp-stream:
	@$(MAKE) run-mlo-exp \
	  EXP_ID=$(EXP_ID) \
	  SCENARIO=$(SCENARIO) \
	  SEED=$(SEED) \
	  SIM_TIME=$(SIM_TIME) \
	  EXPORTER_MAX_MESSAGES_PER_CYCLE=3328 \
	  EXPORTER_POLL_INTERVAL=0.5

# =============================================================================
# Kafka Topic Management (WP7.5 Pipeline Hardening)
# =============================================================================
# Run 'make kafka-init' once after 'make up' to create required topics.
# This prevents silent data loss when topics don't exist.
# See ADR-WP7.5-02 for rationale.
# =============================================================================

.PHONY: kafka-init kafka-list kafka-reset

# Create required Kafka topics (run once after 'make up')
kafka-init:
	@echo "Creating required Kafka topics..."
	@docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
	  rpk topic create $(KAFKA_TOPIC) \
	  --brokers localhost:9092 \
	  --partitions 3 \
	  2>/dev/null || echo "Topic may already exist (safe to ignore)"
	@echo ""
	@echo "Verifying topics..."
	@docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
	  rpk topic list --brokers localhost:9092
	@echo ""
	@echo "Kafka topics initialized."

# List all Kafka topics
kafka-list:
	@docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
	  rpk topic list --brokers localhost:9092

# DANGER: Delete all topics (use for testing only)
kafka-reset:
	@echo "WARNING: This will delete ALL Kafka topics!"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read confirm
	@docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
	  rpk topic delete $(KAFKA_TOPIC) --brokers localhost:9092 || true
	@echo "Kafka topics deleted. Run 'make kafka-init' to recreate."

# =============================================================================
# Exporter State Management (WP7.5 Pipeline Hardening)
# =============================================================================
# Use these targets to view or reset exporter state for debugging/recovery.
# See ADR-WP7.5-01 for delivery confirmation design.
# =============================================================================

.PHONY: exporter-state exporter-reset exporter-reset-exp

# Show current exporter state
exporter-state:
	@if [ -f .exporter_state/exporter_state.json ]; then \
	  echo "Current exporter state:"; \
	  cat .exporter_state/exporter_state.json | python3 -m json.tool; \
	else \
	  echo "No exporter state file found"; \
	fi

# Reset ALL exporter state (forces full re-export of all files)
exporter-reset:
	@echo "Deleting ALL exporter state..."
	@rm -f .exporter_state/exporter_state.json
	@echo "Exporter state reset. All files will be re-exported on next run."

# Reset exporter state for specific experiment only
exporter-reset-exp:
	@test -n "$(EXP_ID)" || (echo "EXP_ID required. Example: make exporter-reset-exp EXP_ID=20260103-1400-mlo-normal-42" && exit 1)
	@python3 -c "import json, sys; f='.exporter_state/exporter_state.json'; \
	import os; \
	key='/work/sim/ns3/artifacts/$(EXP_ID)/telemetry.jsonl'; \
	state=json.load(open(f)) if os.path.exists(f) else {'files':{}}; \
	removed=state.get('files',{}).pop(key,None); \
	json.dump(state,open(f,'w')) if removed else None; \
	print('Reset exporter state for $(EXP_ID)' if removed else 'No state found for $(EXP_ID)')"

# =============================================================================
# WP8: GCN Attack Detection Integration
# =============================================================================
# Kafka Topics Management
# =============================================================================

.PHONY: kafka-topics-create kafka-topics-list kafka-topics-delete

kafka-topics-create:
	@echo "Creating Kafka topics for GCN pipeline..."
	@docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
		rpk topic create wifi7.ml.windowed_features.v1 \
		--partitions 3 --retention 86400000ms || true
	@docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
		rpk topic create wifi7.security.gcn_predictions.v1 \
		--partitions 3 --retention 2592000000ms || true
	@docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
		rpk topic create wifi7.security.gcn_predictions.dlq \
		--partitions 1 --retention 604800000ms || true
	@echo "Kafka topics created."

kafka-topics-list:
	@docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
		rpk topic list

kafka-topics-delete:
	@echo "WARNING: This will delete GCN Kafka topics!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
		rpk topic delete wifi7.ml.windowed_features.v1 || true
	@docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
		rpk topic delete wifi7.security.gcn_predictions.v1 || true
	@docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
		rpk topic delete wifi7.security.gcn_predictions.dlq || true

# =============================================================================
# Windowizer Service
# =============================================================================

.PHONY: windowizer-build windowizer-run windowizer-stop windowizer-logs windowizer-health

WINDOWIZER_IMAGE=ndt/windowizer:local

windowizer-build:
	@echo "Building windowizer image..."
	@docker build -t $(WINDOWIZER_IMAGE) security/detector/windowizer/

windowizer-run:
	@echo "Starting windowizer service..."
	@docker compose -f docker-compose.pipeline.yml up -d windowizer

windowizer-stop:
	@docker compose -f docker-compose.pipeline.yml stop windowizer

windowizer-logs:
	@docker compose -f docker-compose.pipeline.yml logs -f windowizer

windowizer-health:
	@curl -s http://localhost:8081/health || echo "Windowizer not responding"

# =============================================================================
# GCN Detector Service
# =============================================================================

.PHONY: gcn-detector-build gcn-detector-run gcn-detector-stop gcn-detector-logs gcn-detector-health

GCN_DETECTOR_IMAGE=ndt/gcn-detector:local

gcn-detector-build:
	@echo "Building GCN detector image..."
	@docker build -t $(GCN_DETECTOR_IMAGE) twin/gnn/detector/

gcn-detector-run:
	@echo "Starting GCN detector service..."
	@docker compose -f docker-compose.pipeline.yml up -d gcn-detector

gcn-detector-stop:
	@docker compose -f docker-compose.pipeline.yml stop gcn-detector

gcn-detector-logs:
	@docker compose -f docker-compose.pipeline.yml logs -f gcn-detector

gcn-detector-health:
	@curl -s http://localhost:8080/health | jq . || echo "GCN detector not responding"

# =============================================================================
# GCN Training Pipeline
# =============================================================================

.PHONY: gcn-trainer-build gcn-train gcn-train-v3 gcn-train-v4 gcn-collect-v4-static gcn-collect-v4-dynamic gcn-collect-v4 gcn-evaluate gcn-deploy

V4_DATA_DIR ?= twin/gnn/training_data/v4

GCN_TRAINER_IMAGE=ndt/gcn-trainer:local

gcn-trainer-build:
	@echo "Building GCN trainer image (CUDA)..."
	@docker build -t $(GCN_TRAINER_IMAGE) \
		-f twin/gnn/trainer/Dockerfile \
		twin/gnn/detector/

gcn-train:
	@test -n "$(OUTPUT_DIR)" || (echo "OUTPUT_DIR required. Example: make gcn-train OUTPUT_DIR=twin/registry/gcn/v1.1.0" && exit 1)
	@echo "Training new GCN model..."
	@echo "Output: $(OUTPUT_DIR)"
	@docker run --rm \
		-v $(CURDIR)/twin/registry/gcn:/output \
		-v $(CURDIR)/data:/data \
		-v $(CURDIR)/twin/gnn/trainer/training.yaml:/config/training.yaml:ro \
		$(GCN_TRAINER_IMAGE)

gcn-train-v3:
	@test -n "$(OUTPUT_DIR)" || (echo "OUTPUT_DIR required. Example: make gcn-train-v3 OUTPUT_DIR=twin/registry/gcn/v3.0.0" && exit 1)
	@echo "Training GCN v3 (multi-AP, multi-segment-length)..."
	@echo "Data:   twin/gnn/training_data/v3"
	@echo "Output: $(OUTPUT_DIR)"
	@mkdir -p $(CURDIR)/$(OUTPUT_DIR)
	@docker run --rm --gpus all \
		--user "$(shell id -u):$(shell id -g)" \
		-v $(CURDIR)/twin/gnn/training_data/v3:/data:ro \
		-v $(CURDIR)/$(OUTPUT_DIR):/output \
		-v $(CURDIR)/twin/gnn/trainer/training_v3.yaml:/config/training_v3.yaml:ro \
		$(GCN_TRAINER_IMAGE) \
		--config /config/training_v3.yaml \
		--data-root /data \
		--output-dir /output

gcn-train-v4:
	@test -n "$(OUTPUT_DIR)" || (echo "OUTPUT_DIR required. Example: make gcn-train-v4 OUTPUT_DIR=twin/registry/gcn/v4.0.0" && exit 1)
	@echo "Training GCN v4 (dynamic generalization, multi-AP, multi-segment-length)..."
	@echo "Data:   $(V4_DATA_DIR)"
	@echo "Output: $(OUTPUT_DIR)"
	@mkdir -p $(CURDIR)/$(OUTPUT_DIR)
	@docker run --rm --gpus all \
		--user "$(shell id -u):$(shell id -g)" \
		--entrypoint python \
		-v $(CURDIR)/$(V4_DATA_DIR):/data:ro \
		-v $(CURDIR)/$(OUTPUT_DIR):/output \
		-v $(CURDIR)/twin/gnn/trainer/training_v4.yaml:/config/training_v4.yaml:ro \
		$(GCN_TRAINER_IMAGE) \
		-u run_training_v4.py \
		--config /config/training_v4.yaml \
		--data-root /data \
		--output-dir /output

SPLIT ?= train
NCPU  ?= $(shell nproc)

gcn-collect-v4-static:
	@echo "Collecting GCN v4 static data (split=$(SPLIT), ncpu=$(NCPU))..."
	@mkdir -p $(CURDIR)/$(V4_DATA_DIR)
	@NCPU=$(NCPU) V4_DATA_DIR=$(CURDIR)/$(V4_DATA_DIR) \
		bash sim/ns3/scenario/collect_v4_static_data.sh --split $(SPLIT)

gcn-collect-v4-dynamic:
	@echo "Collecting GCN v4 dynamic data (split=$(SPLIT), ncpu=$(NCPU))..."
	@mkdir -p $(CURDIR)/$(V4_DATA_DIR)
	@NCPU=$(NCPU) V4_DATA_DIR=$(CURDIR)/$(V4_DATA_DIR) \
		bash sim/ns3/scenario/collect_v4_dynamic_data.sh --split $(SPLIT)

gcn-collect-v4:
	@echo "Collecting ALL GCN v4 data (split=$(SPLIT), ncpu=$(NCPU))..."
	$(MAKE) gcn-collect-v4-static SPLIT=$(SPLIT) NCPU=$(NCPU)
	$(MAKE) gcn-collect-v4-dynamic SPLIT=$(SPLIT) NCPU=$(NCPU)

gcn-evaluate:
	@test -n "$(MODEL)" || (echo "MODEL required. Example: make gcn-evaluate MODEL=v1.0.0" && exit 1)
	@echo "Evaluating model $(MODEL)..."
	@docker run --rm \
		-v $(CURDIR)/twin/registry/gcn:/models \
		$(GCN_TRAINER_IMAGE) evaluate --model $(MODEL)

gcn-deploy:
	@test -n "$(VERSION)" || (echo "VERSION required. Example: make gcn-deploy VERSION=v1.0.0" && exit 1)
	@echo "Deploying model version $(VERSION)..."
	@cd twin/registry/gcn && rm -f current && ln -s $(VERSION) current
	@echo "Model $(VERSION) is now active."
	@echo "GCN detector will reload the model automatically."

# =============================================================================
# Complete GCN Pipeline
# =============================================================================

.PHONY: gcn-up gcn-down gcn-status gcn-build

gcn-build: windowizer-build gcn-detector-build
	@echo "GCN pipeline images built."

gcn-up: gcn-build
	@echo "Starting complete GCN pipeline..."
	@docker compose -f docker-compose.pipeline.yml up -d windowizer gcn-detector
	@echo ""
	@echo "GCN pipeline started. Check status with: make gcn-status"

gcn-down:
	@echo "Stopping GCN pipeline..."
	@docker compose -f docker-compose.pipeline.yml stop windowizer gcn-detector

gcn-status:
	@echo "GCN Pipeline Status:"
	@echo "===================="
	@docker compose -f docker-compose.pipeline.yml ps windowizer gcn-detector
	@echo ""
	@echo "Windowizer logs (last 10 lines):"
	@docker compose -f docker-compose.pipeline.yml logs --tail=10 windowizer
	@echo ""
	@echo "GCN Detector logs (last 10 lines):"
	@docker compose -f docker-compose.pipeline.yml logs --tail=10 gcn-detector

# =============================================================================
# End-to-End GCN Test
# =============================================================================

.PHONY: test-gcn-e2e

test-gcn-e2e:
	@echo "Running end-to-end GCN test..."
	@echo "This will:"
	@echo "  1. Run ns-3 attack scenario"
	@echo "  2. Export to Kafka"
	@echo "  3. Windowize features"
	@echo "  4. Run GCN inference"
	@echo "  5. Validate predictions in DB"
	@echo ""
	@bash tests/gcn_e2e_test.sh || echo "Test script not yet implemented"

# =============================================================================
# WP9: Custom Web Dashboard
# =============================================================================

.PHONY: dashboard-build dashboard-up dashboard-down dashboard-logs dashboard-status dashboard-dev

dashboard-build:
	@echo "Building NDT Dashboard image..."
	@docker build -t ndt/dashboard:local ./dashboard/app
	@echo "Dashboard image built: ndt/dashboard:local"

dashboard-up: dashboard-build
	@echo "Starting NDT Dashboard on http://localhost:8888 ..."
	@docker compose -f docker-compose.dashboard.yml up -d
	@echo "Dashboard started. Open: http://localhost:8888"

dashboard-down:
	@echo "Stopping NDT Dashboard..."
	@docker compose -f docker-compose.dashboard.yml down

dashboard-logs:
	@docker compose -f docker-compose.dashboard.yml logs -f dashboard

dashboard-status:
	@echo "Dashboard Status:"
	@echo "================="
	@docker compose -f docker-compose.dashboard.yml ps
	@echo ""
	@echo "Last 20 log lines:"
	@docker compose -f docker-compose.dashboard.yml logs --tail=20 dashboard

## ── DB Utilities ──────────────────────────────────────────────────────────────

DB_CONTAINER ?= clab-ndt-wifi7-mlo-security-udr-db

db-reset-experiments:
	@echo "Clearing experiment data (metrics + gcn_predictions)..."
	@echo "Model registry and model files are preserved."
	@docker exec $(DB_CONTAINER) psql -U $(PG_USER) -d $(PG_DB) -c \
		"TRUNCATE TABLE gcn_predictions; TRUNCATE TABLE metrics;"
	@echo "Done. DB is clean for fresh evaluation runs."

db-count:
	@docker exec $(DB_CONTAINER) psql -U $(PG_USER) -d $(PG_DB) -c \
		"SELECT 'metrics' AS tbl, COUNT(*) FROM metrics UNION ALL SELECT 'gcn_predictions', COUNT(*) FROM gcn_predictions;"

dashboard-dev:
	@echo "Starting dashboard in DEV mode (hot-reload)..."
	@echo "Backend: http://localhost:8888"
	@echo "Frontend dev server: http://localhost:5173"
	@echo ""
	@echo "In a second terminal run: cd dashboard/app/frontend && npm run dev"
	@cd dashboard/app/backend && uvicorn backend.main:app --host 0.0.0.0 --port 8888 --reload
