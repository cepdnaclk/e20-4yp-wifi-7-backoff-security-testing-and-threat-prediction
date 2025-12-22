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
