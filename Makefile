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
	@test -n "$(EXP_ID)" || (echo "EXP_ID required" && exit 1)
	@$(MAKE) ns3-run-example EXP_ID=$(EXP_ID)
	@$(MAKE) exporter-run EXP_ID=$(EXP_ID)
