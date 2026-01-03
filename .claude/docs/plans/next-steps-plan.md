# Implementation Plan: WP7 - One-Command Pipeline

## Date
2026-01-03

## Objective
Transform the current manual multi-step pipeline into a one-command automated workflow. Users should be able to run a complete experiment (ns-3 simulation → Kafka → DB → Grafana) with a single command, with long-running services (harmonizer) managed as background services rather than manual terminal sessions.

## Background
WP1-WP6 have established a complete working pipeline, but it requires manual execution of multiple steps:
1. `make ns3-run-example EXP_ID=...`
2. `make exporter-run EXP_ID=...`
3. `make harmonizer-run` (in separate terminal, must be kept running)

This is cumbersome for iterative experimentation and doesn't scale well. WP7 aims to automate this into a single command while maintaining the same component architecture established in previous WPs.

## Prerequisites
- [x] WP1-WP6 complete and working
- [x] Containerlab topology running (`make up`)
- [x] All images built (ns3, exporter, harmonizer)
- [x] Understanding of current Makefile targets
- [x] Familiarity with Docker Compose patterns

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `docker-compose.pipeline.yml` | Create | Define long-running pipeline services (harmonizer) |
| `Makefile` | Modify | Add `pipeline-up`, `pipeline-down`, `run-exp` targets |
| `docs/WP7-ONE-COMMAND-PIPELINE.md` | Create | Documentation for WP7 |
| `docs/CURRENT-STATE.md` | Modify | Update to reflect WP7 completion |
| `docs/QUICK-REFERENCE.md` | Modify | Add new pipeline commands |
| `.gitignore` | Verify | Ensure docker-compose override files ignored |
| `docs/adr/ADR-WP7-01-*.md` | Create (optional) | Document key decisions if needed |

## Implementation Steps

### Step 1: Create Docker Compose for Pipeline Services
**File:** `docker-compose.pipeline.yml`

**What to implement:**
- Service definition for harmonizer (long-running)
- Network configuration to connect to `clab-mgmt` network
- Environment variables matching current Makefile
- Health checks for harmonizer
- Logging configuration

**Key design decisions:**
- Use `external: true` for `clab-mgmt` network (already created by containerlab)
- Harmonizer runs continuously with restart policy
- Exporter runs on-demand via docker run (not compose)
- All environment variables should have defaults matching current setup

**Example structure:**
```yaml
version: '3.8'

networks:
  clab-mgmt:
    external: true  # Created by containerlab

services:
  harmonizer:
    image: ndt/harmonizer:local
    container_name: ndt-pipeline-harmonizer
    restart: unless-stopped
    networks:
      - clab-mgmt
    environment:
      KAFKA_BROKERS: "bus-redpanda:9092"
      KAFKA_TOPIC: "wifi7.telemetry.v0_1"
      KAFKA_GROUP: "harmonizer-udm-v0"
      AUTO_OFFSET_RESET: "latest"
      PG_HOST: "udr-db"
      PG_DB: "udr"
      PG_USER: "udr"
      PG_PASS: "udr_pass"
      BATCH_SIZE: "100"
    healthcheck:
      test: ["CMD", "pgrep", "-f", "harmonizer.py"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**How to verify:**
```bash
docker-compose -f docker-compose.pipeline.yml config  # Validate syntax
docker-compose -f docker-compose.pipeline.yml up -d harmonizer
docker-compose -f docker-compose.pipeline.yml ps
docker-compose -f docker-compose.pipeline.yml logs harmonizer
```

---

### Step 2: Add Makefile Targets for Pipeline Management

**File:** `Makefile`

**What to add:**
Four new phony targets:
1. `pipeline-up` - Start long-running pipeline services
2. `pipeline-down` - Stop pipeline services
3. `pipeline-status` - Check pipeline status
4. `run-exp` - Run complete experiment end-to-end

**Implementation details:**

```makefile
.PHONY: pipeline-up pipeline-down pipeline-status run-exp

# Start long-running pipeline services (harmonizer)
pipeline-up:
	@echo "Starting pipeline services..."
	@docker-compose -f docker-compose.pipeline.yml up -d
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

# Run complete experiment: ns-3 → exporter → (harmonizer already running)
run-exp:
	@test -n "$(EXP_ID)" || (echo "EXP_ID required. Example: make run-exp EXP_ID=20260103-1200-test-01" && exit 1)
	@echo "Running experiment: EXP_ID=$(EXP_ID)"
	@echo ""
	@echo "Step 1/3: Running ns-3 simulation..."
	@$(MAKE) ns3-run-example EXP_ID=$(EXP_ID) || exit 1
	@echo ""
	@echo "Step 2/3: Publishing telemetry to Kafka..."
	@$(MAKE) exporter-run EXP_ID=$(EXP_ID) || exit 1
	@echo ""
	@echo "Step 3/3: Waiting for harmonizer ingestion (5s)..."
	@sleep 5
	@echo ""
	@echo "Experiment complete! Verify in Grafana: http://localhost:3000"
```

---

### Step 3: Update Existing Makefile Target (Optional Enhancement)

Add deprecation notice to `run-wifi-pipeline`:
```makefile
run-wifi-pipeline:
	@echo "DEPRECATED: Use 'make run-exp EXP_ID=...' instead"
	@echo "This target will be removed in WP8."
	@test -n "$(EXP_ID)" || (echo "EXP_ID required" && exit 1)
	@$(MAKE) ns3-run-example EXP_ID=$(EXP_ID)
	@$(MAKE) exporter-run EXP_ID=$(EXP_ID)
```

---

### Step 4: Create WP7 Documentation

**File:** `docs/WP7-ONE-COMMAND-PIPELINE.md`

**What to include:**
- Status: ✅ COMPLETED
- Overview of what was implemented
- Before/After workflow comparison
- New commands (`pipeline-up`, `pipeline-down`, `run-exp`)
- Acceptance criteria and verification
- Problems solved
- Related ADRs (if any created)

---

### Step 5: Update Project Documentation

**Files to update:**
1. `docs/CURRENT-STATE.md` - Update WP7 status to complete
2. `docs/QUICK-REFERENCE.md` - Add new pipeline commands

---

### Step 6: Testing and Validation

**Test scenarios:**

1. **Clean Start Test**
   ```bash
   make down && make pipeline-down
   make up && make pipeline-up
   make run-exp EXP_ID=20260103-clean-test-01
   ```

2. **Multiple Experiments Test**
   ```bash
   make run-exp EXP_ID=20260103-test-01
   make run-exp EXP_ID=20260103-test-02
   make run-exp EXP_ID=20260103-test-03
   ```

3. **Restart Resilience Test**
   ```bash
   make run-exp EXP_ID=20260103-test-before
   make pipeline-down && make pipeline-up
   make run-exp EXP_ID=20260103-test-after
   ```

4. **Error Handling Test**
   ```bash
   make run-exp  # Should show error message
   ```

---

### Step 7: Cleanup and Polish

- Remove any debug/test code
- Ensure `.gitignore` covers generated files
- Verify permissions on all files
- Check for hardcoded paths

---

## Integration Points

### With Existing Components

1. **Containerlab (WP2):** Docker Compose uses `external: true` for `clab-mgmt` network
2. **ns-3 (WP3):** `run-exp` calls existing `ns3-run-example` target
3. **Exporter (WP4):** `run-exp` calls existing `exporter-run` target
4. **Harmonizer (WP5):** Becomes a long-running service via Docker Compose
5. **Grafana (WP6):** No changes required

### Patterns to Follow

From previous WPs, maintain these patterns:
- **ADR-0004:** Config as code (docker-compose.yml in repo)
- **ADR-0006:** Keep ns-3 separate (don't add to compose)
- **ADR-0012:** Fix permissions (use --user where needed)
- **Makefile conventions:** Phony targets, `@test -n` for required params

---

## Success Criteria

WP7 is complete when:
- [ ] `docker-compose.pipeline.yml` exists and is valid
- [ ] `make pipeline-up` starts harmonizer successfully
- [ ] `make pipeline-down` stops cleanly
- [ ] `make pipeline-status` shows service status
- [ ] `make run-exp EXP_ID=...` runs full pipeline
- [ ] Multiple experiments can run sequentially
- [ ] Data appears in database correctly
- [ ] Data visible in Grafana dashboards
- [ ] Documentation is complete and accurate

---

## Potential Issues

### Issue 1: Docker Compose Network Timing
**Problem:** Harmonizer might start before containerlab services are ready.
**Mitigation:** Add `restart: unless-stopped` policy; harmonizer will retry connections.

### Issue 2: Conflicting Consumer Groups
**Problem:** If user previously ran `make harmonizer-run`, the consumer group offset might conflict.
**Mitigation:** Use the same consumer group name: `harmonizer-udm-v0`

### Issue 3: Exporter State Persistence
**Problem:** Exporter state might not persist correctly.
**Mitigation:** Keep exporter as docker run (current Makefile approach)

---

## ADR Candidates

Consider creating:
1. **ADR-WP7-01:** Use Docker Compose for Long-Running Pipeline Services

---

## Next Steps After WP7

Once WP7 is complete, the project will be ready for:
- **WP8:** Multi-scenario support (scenario registry, parameterized runs)
- **WP9:** Enhanced telemetry model (more metrics, better schemas)
- **WP10:** Production hygiene (health checks, monitoring, state management)

WP7 establishes the automation patterns that make WP8+ much easier to implement.
