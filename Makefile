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
	  ndt/ns3:local \
	  bash -lc "./sim/ns3/scenario/run_wifi_example_and_export.sh $(EXP_ID) 42"

