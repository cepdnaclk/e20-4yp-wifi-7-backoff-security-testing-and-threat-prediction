.PHONY: up down status run-baseline

up:
	@echo "TODO: bring up containerlab + services"

down:
	@echo "TODO: tear down containerlab + services"

status:
	@echo "TODO: show running services and ports"

run-baseline:
	@test -n "$(EXP_ID)" || (echo "EXP_ID required. Example: make run-baseline EXP_ID=20251222-2100-baseline-42" && exit 1)
	@echo "TODO: run ns-3 baseline with EXP_ID=$(EXP_ID)"
