# Implementation Plan: MLO Data Recovery and Pipeline Hardening

## Date
2026-01-04

## Objective
Recover missing MLO normal experiment data from the database, verify Grafana can display MLO metrics, and implement safeguards to prevent future pipeline failures due to missing Kafka topics or exporter state issues.

## Background
WP7.5 successfully implemented MLO attack scenarios. The pipeline executed without error messages, but only 2 of 3 experiments made it to the database:
- `20260103-1400-mlo-attack-pos-42`: 260 rows (COMPLETE)
- `20260103-1400-mlo-attack-neg-42`: 240 rows (COMPLETE)
- `20260103-1400-mlo-normal-42`: 0 rows (MISSING)

**Root cause:** Kafka topic `wifi7.telemetry.v0_1` did not exist when experiments first ran. The exporter marked files as processed even though Kafka publish failed. The topic was created later (manually or by Redpanda auto-creation), allowing subsequent experiments to succeed.

**Secondary issue:** Current exporter design has a critical flaw - it saves file offset state even when Kafka delivery fails (line 123 in exporter.py), leading to data loss.

## Prerequisites
- [x] Containerlab services running (`make up`)
- [x] Pipeline harmonizer running (`make pipeline-up`)
- [x] Kafka topic `wifi7.telemetry.v0_1` exists (verify first)
- [x] Understanding of exporter state mechanism

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------||
| `.exporter_state/exporter_state.json` | Modify | Remove offset for missing experiment to allow re-export |
| `telemetry/exporters/ns3_file_exporter/exporter.py` | Modify | Fix: only save offset after confirmed Kafka delivery |
| `Makefile` | Modify | Add `kafka-init` target for topic pre-creation |
| `Makefile` | Modify | Add `exporter-reset` target for state management |
| `clab/configs/redpanda/init-topics.sh` | Create | Script to create required Kafka topics |
| `clab/topo.yml` | Modify | Add bind-mount for Redpanda init script |
| `docs/TROUBLESHOOTING.md` | Create | Centralized troubleshooting guide |
| `docs/WP7-ONE-COMMAND-PIPELINE.md` | Modify | Add MLO data recovery section and updated troubleshooting |
| `clab/configs/grafana/dashboards/wp75-mlo-attack-comparison.json` | Create | Dashboard for MLO metrics visualization |

## Implementation Steps

### Phase 1: Immediate Data Recovery

#### 1.1 Verify Kafka Topic Exists
**Action:**
```bash
docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic list --brokers localhost:9092
```

**Expected outcome:** `wifi7.telemetry.v0_1` appears in list

**How to verify:** Command output shows topic name

**If missing:** Create it:
```bash
docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic create wifi7.telemetry.v0_1 --brokers localhost:9092 --partitions 3
```

#### 1.2 Check Database Current State
**Action:**
```bash
docker exec -it clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "
  SELECT experiment_id, COUNT(*) as row_count,
         MIN(ts) as earliest_ts, MAX(ts) as latest_ts
  FROM metrics
  WHERE experiment_id LIKE '20260103-1400-mlo%'
  GROUP BY experiment_id
  ORDER BY experiment_id;
"
```

**Expected outcome:** Shows current row counts (pos: 260, neg: 240, normal: 0)

**How to verify:** Confirms which experiments need recovery

#### 1.3 Verify Telemetry File Still Exists
**Action:**
```bash
ls -lh sim/ns3/artifacts/20260103-1400-mlo-normal-42/telemetry.jsonl
wc -l sim/ns3/artifacts/20260103-1400-mlo-normal-42/telemetry.jsonl
```

**Expected outcome:** File exists with 260 lines (20 windows × 13 metrics)

**How to verify:** File shows ~50KB size and 260 lines

#### 1.4 Reset Exporter State for Missing Experiment
**Action:**
Edit `.exporter_state/exporter_state.json` and remove the entry for normal experiment:

Before:
```json
{
  "files": {
    "/work/sim/ns3/artifacts/20260103-1400-mlo-normal-42/telemetry.jsonl": 50738,
    ...
  }
}
```

After:
```json
{
  "files": {
    ...other experiments...
  }
}
```

Or simpler - delete entire state file:
```bash
rm .exporter_state/exporter_state.json
```

**Expected outcome:** Exporter will re-process the normal experiment file

**How to verify:** File is modified or deleted

#### 1.5 Re-export Missing Experiment
**Action:**
```bash
make exporter-run EXP_ID=20260103-1400-mlo-normal-42
```

**Expected outcome:**
- Exporter reads 260 lines
- Publishes to Kafka
- Updates state file with new offset

**How to verify:** Check exporter output for "Published" messages

#### 1.6 Verify Kafka Messages
**Action:**
```bash
docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic consume wifi7.telemetry.v0_1 -o oldest -n 5 \
  --brokers localhost:9092 | grep "20260103-1400-mlo-normal-42"
```

**Expected outcome:** Messages for normal experiment appear in Kafka

**How to verify:** JSON payloads contain correct experiment_id

#### 1.7 Wait for Harmonizer Ingestion
**Action:**
```bash
sleep 10
make pipeline-status
```

**Expected outcome:** Harmonizer logs show ingestion activity

**How to verify:** Recent logs show batch inserts

#### 1.8 Verify Database Recovery
**Action:**
```bash
docker exec -it clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "
  SELECT experiment_id, COUNT(*) as row_count
  FROM metrics
  WHERE experiment_id = '20260103-1400-mlo-normal-42';
"
```

**Expected outcome:** Shows 260 rows for normal experiment

**How to verify:** Row count matches telemetry.jsonl line count

---

### Phase 2: Fix Exporter Reliability

#### 2.1 Analyze Current Exporter Flaw
**Action:** Review `telemetry/exporters/ns3_file_exporter/exporter.py` lines 114-123

**Problem identified:**
```python
producer.produce(
    TOPIC,
    key=key.encode("utf-8"),
    value=json.dumps(rec.model_dump()).encode("utf-8"),
    callback=delivery_report,
)
producer.poll(0)

# persist state after successful enqueue  ← WRONG! Only enqueued, not delivered
save_offset(state, TELEMETRY_FILE, offset)
```

**Issue:** Saves offset immediately after `produce()` call, not after delivery confirmation

#### 2.2 Implement Confirmed Delivery Tracking
**Action:** Modify exporter to track delivery status

**Strategy:**
1. Track pending deliveries in memory
2. Only save offset after delivery_report confirms success
3. Handle failures by NOT advancing offset

**Code change pattern:**
```python
# Track delivery status
pending_deliveries = {}
last_confirmed_offset = offset

def delivery_report(err, msg):
    msg_offset = pending_deliveries.get(msg.key().decode('utf-8'))
    if err is not None:
        print(f"[exporter] delivery failed: {err}")
        # Don't update offset - will retry on next run
    else:
        # Success - safe to advance offset
        if msg_offset:
            save_offset(state, TELEMETRY_FILE, msg_offset)
            print(f"[exporter] confirmed delivery, offset={msg_offset}")

# In main loop:
pending_deliveries[key] = f.tell()  # Track offset for this message
producer.produce(...)
```

**Expected outcome:** Exporter only advances state after Kafka confirms delivery

**How to verify:**
- Test with Kafka down - state should not advance
- Test with Kafka up - state advances normally

#### 2.3 Add Exporter Health Checks
**Action:** Add broker connectivity check before processing

**Implementation:**
```python
def check_broker_health():
    """Verify broker is reachable and topic exists"""
    admin_client = AdminClient({"bootstrap.servers": BROKERS})
    metadata = admin_client.list_topics(timeout=5)

    if TOPIC not in metadata.topics:
        raise SystemExit(f"Topic '{TOPIC}' does not exist. Create it first.")

    print(f"[exporter] broker health check passed, topic '{TOPIC}' exists")

# Call before main loop:
check_broker_health()
```

**Expected outcome:** Exporter fails fast if topic missing

**How to verify:** Run with missing topic - should exit with clear error

---

### Phase 3: Kafka Topic Pre-Creation

#### 3.1 Create Topic Initialization Script
**Action:** Create `clab/configs/redpanda/init-topics.sh`

**Content:**
```bash
#!/usr/bin/env bash
# init-topics.sh - Create required Kafka topics for NDT pipeline

set -euo pipefail

BROKER="localhost:9092"
TOPICS=(
    "wifi7.telemetry.v0_1:3:1"  # format: topic:partitions:replicas
)

echo "Initializing Kafka topics..."

for topic_spec in "${TOPICS[@]}"; do
    IFS=':' read -r topic partitions replicas <<< "$topic_spec"

    if rpk topic list --brokers "$BROKER" | grep -q "^${topic}$"; then
        echo "  ✓ ${topic} (already exists)"
    else
        echo "  Creating ${topic} (partitions=${partitions}, replicas=${replicas})"
        rpk topic create "$topic" \
            --brokers "$BROKER" \
            --partitions "$partitions" \
            --replicas "$replicas"
    fi
done

echo "Topic initialization complete."
```

**Expected outcome:** Reusable script for topic creation

**How to verify:** Script runs without errors, topics exist after execution

#### 3.2 Add Makefile Target for Kafka Initialization
**Action:** Add to `Makefile`:

```makefile
# =============================================================================
# Kafka Topic Management
# =============================================================================

.PHONY: kafka-init kafka-list kafka-reset

# Create required Kafka topics (run once after 'make up')
kafka-init:
	@echo "Creating required Kafka topics..."
	@docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
	  rpk topic create wifi7.telemetry.v0_1 \
	  --brokers localhost:9092 \
	  --partitions 3 \
	  || echo "Topic may already exist (safe to ignore)"
	@echo "✓ Kafka topics initialized"

# List all Kafka topics
kafka-list:
	@docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
	  rpk topic list --brokers localhost:9092

# DANGER: Delete all topics (use for testing only)
kafka-reset:
	@echo "WARNING: This will delete ALL Kafka topics!"
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
	  rpk topic delete wifi7.telemetry.v0_1 --brokers localhost:9092 || true
	@echo "Kafka topics deleted. Run 'make kafka-init' to recreate."
```

**Expected outcome:** Easy topic management via Makefile

**How to verify:** Run `make kafka-init`, then `make kafka-list`

#### 3.3 Add Exporter State Management Targets
**Action:** Add to `Makefile`:

```makefile
# =============================================================================
# Exporter State Management
# =============================================================================

.PHONY: exporter-reset exporter-state exporter-reset-exp

# Show current exporter state
exporter-state:
	@if [ -f .exporter_state/exporter_state.json ]; then \
	  echo "Current exporter state:"; \
	  cat .exporter_state/exporter_state.json | python3 -m json.tool; \
	else \
	  echo "No exporter state file found"; \
	fi

# Reset all exporter state (forces full re-export)
exporter-reset:
	@echo "Deleting exporter state..."
	@rm -f .exporter_state/exporter_state.json
	@echo "✓ Exporter state reset (all files will be re-exported)"

# Reset exporter state for specific experiment
exporter-reset-exp:
	@test -n "$(EXP_ID)" || (echo "EXP_ID required. Example: make exporter-reset-exp EXP_ID=20260103-1400-mlo-normal-42" && exit 1)
	@python3 -c "import json; \
	  state = json.load(open('.exporter_state/exporter_state.json')); \
	  key = '/work/sim/ns3/artifacts/$(EXP_ID)/telemetry.jsonl'; \
	  state['files'].pop(key, None); \
	  json.dump(state, open('.exporter_state/exporter_state.json', 'w'))"
	@echo "✓ Reset exporter state for $(EXP_ID)"
```

**Expected outcome:** Easy state management for debugging and recovery

**How to verify:** Run `make exporter-state` to view state

---

### Phase 4: Grafana Dashboard for MLO Metrics

#### 4.1 Create MLO Attack Comparison Dashboard
**Action:** Create `clab/configs/grafana/dashboards/wp75-mlo-attack-comparison.json`

**Dashboard structure:**
- Panel 1: Time series - `avg_backoff_slots` by experiment (key attack indicator)
- Panel 2: Time series - `net_throughput_mbps` by experiment
- Panel 3: Time series - `channel_busy_ratio` by experiment
- Panel 4: Table - Summary statistics (avg throughput, backoff, loss ratio)
- Panel 5: Time series - `net_packet_loss_ratio` by experiment
- Panel 6: Time series - `mac_total_retrans` by experiment

**Key query pattern:**
```sql
SELECT
  ts AS "time",
  value,
  experiment_id AS "metric"
FROM metrics
WHERE $__timeFilter(ts)
  AND metric_name = 'avg_backoff_slots'
  AND experiment_id LIKE '%mlo%'
ORDER BY 1;
```

**Template variables:**
- `scenario_filter`: Custom query with options: `all`, `normal`, `positive`, `negative`
- `last_n`: Number of recent experiments to show

**Expected outcome:** Dashboard shows all 13 MLO metrics with experiment comparison

**How to verify:**
1. Dashboard loads without errors
2. Queries return data for all 3 scenarios
3. Time range picker covers 2026 dates

#### 4.2 Verify Dashboard Queries with Current Data
**Action:** Test each query manually first

**Test queries:**
```sql
-- Verify MLO metrics exist
SELECT DISTINCT metric_name
FROM metrics
WHERE experiment_id LIKE '%mlo%'
ORDER BY metric_name;

-- Should show all 13 metrics:
-- avg_backoff_slots, channel_busy_ratio,
-- mac_drop_count, mac_total_ack, mac_total_retrans, mac_total_rx, mac_total_tx,
-- net_active_flows, net_avg_delay_ms, net_avg_jitter_ms,
-- net_packet_loss_ratio, net_throughput_mbps, phy_drop_count

-- Verify time range
SELECT MIN(ts) as earliest, MAX(ts) as latest
FROM metrics
WHERE experiment_id LIKE '%mlo%';

-- Should show times in 2026
```

**Expected outcome:** All 13 metrics present, timestamps in 2026

**How to verify:** Query results match expected metric count and time range

#### 4.3 Configure Grafana Time Range Defaults
**Action:** Update dashboard JSON time range to cover simulation times

**Change in dashboard JSON:**
```json
"time": {
  "from": "2026-01-04T11:51:00Z",
  "to": "2026-01-04T11:53:00Z"
}
```

**Alternative:** Use relative time with note:
```json
"time": {
  "from": "now-1h",
  "to": "now"
},
"annotations": {
  "list": [{
    "name": "Time Range Note",
    "datasource": "-- Grafana --",
    "enable": true,
    "hide": false,
    "type": "dashboard",
    "builtIn": 1,
    "iconColor": "rgba(255, 96, 96, 1)",
    "tags": ["mlo"],
    "text": "⚠️ Simulation uses 2026 timestamps - adjust time picker if no data appears"
  }]
}
```

**Expected outcome:** Dashboard shows data by default or has clear instructions

**How to verify:** Open dashboard - data visible or annotation guides user

---

### Phase 5: Automated Setup Workflow

#### 5.1 Update Pipeline Startup Documentation
**Action:** Modify `docs/WP7-ONE-COMMAND-PIPELINE.md` to include topic initialization

**Add to "Complete Workflow" section:**

**Before:**
```bash
# Start everything
make up              # Containerlab services
make pipeline-up     # Pipeline services
```

**After:**
```bash
# Start everything (one-time setup)
make up              # Containerlab services
make kafka-init      # Create required Kafka topics
make pipeline-up     # Pipeline services
```

**Expected outcome:** Clear setup instructions prevent topic issues

**How to verify:** Documentation reads smoothly

#### 5.2 Create Initialization Checklist
**Action:** Add to `docs/QUICK-REFERENCE.md`:

```markdown
## First-Time Setup Checklist

After cloning the repository:

- [ ] Deploy containerlab: `make up`
- [ ] Wait 30s for services to be ready
- [ ] Create Kafka topics: `make kafka-init`
- [ ] Verify topic exists: `make kafka-list`
- [ ] Start pipeline: `make pipeline-up`
- [ ] Check pipeline status: `make pipeline-status`
- [ ] Run test experiment: `make run-exp EXP_ID=20260104-test-01`
- [ ] Verify in Grafana: http://localhost:3000

Troubleshooting: See `docs/TROUBLESHOOTING.md`
```

**Expected outcome:** New users follow correct setup sequence

**How to verify:** Follow checklist from scratch

---

### Phase 6: Comprehensive Troubleshooting Guide

#### 6.1 Create Centralized Troubleshooting Document
**Action:** Create `docs/TROUBLESHOOTING.md`

**Sections:**
1. **Pipeline Issues**
   - No data in Grafana
   - Exporter stuck at offset
   - Harmonizer not ingesting
   - Kafka topic missing

2. **Data Issues**
   - Missing experiment data
   - Duplicate rows
   - Wrong timestamps
   - Partial data

3. **Service Issues**
   - Containerlab won't start
   - Grafana connection errors
   - Database connection refused
   - Permission denied errors

4. **Recovery Procedures**
   - Re-export specific experiment
   - Reset consumer group
   - Clear exporter state
   - Replay Kafka messages

**Format per issue:**
```markdown
### Issue: No Data in Grafana

**Symptoms:**
- Dashboard loads but shows "No Data"
- Time series panels are empty
- Table queries return 0 rows

**Diagnostic Steps:**
1. Check time range in Grafana (simulations use 2026 timestamps)
2. Verify data in database: [query]
3. Check harmonizer logs: [command]
4. Verify Kafka has messages: [command]

**Root Causes:**
1. Wrong time range selected
2. Harmonizer not running
3. Kafka topic missing
4. Exporter state marked files as done but delivery failed

**Solutions:**
[Step-by-step fix for each root cause]

**Prevention:**
- Always run `make kafka-init` after `make up`
- Verify `make pipeline-status` shows harmonizer running
- Use `make exporter-state` to check what's been processed
```

**Expected outcome:** Complete troubleshooting reference

**How to verify:** Document covers all known issues from codex reports

#### 6.2 Add Troubleshooting Links to All Docs
**Action:** Add troubleshooting links to key documentation files:

- `README.md` - link at top
- `docs/CURRENT-STATE.md` - in "Known Issues" section
- `docs/WP7-ONE-COMMAND-PIPELINE.md` - in "Troubleshooting" section
- `docs/QUICK-REFERENCE.md` - in header

**Expected outcome:** Easy access to troubleshooting from anywhere

**How to verify:** Links work, navigate correctly

---

### Phase 7: Verification and Testing

#### 7.1 Test Complete Recovery Workflow
**Action:** Simulate the original problem and verify fix

**Test steps:**
1. Delete Kafka topic: `make kafka-reset`
2. Run experiment: `make run-mlo-exp EXP_ID=20260104-test-recovery-42 SCENARIO=normal`
3. Verify exporter shows error (improved version with health check)
4. Create topic: `make kafka-init`
5. Re-export: `make exporter-reset-exp EXP_ID=20260104-test-recovery-42 && make exporter-run EXP_ID=20260104-test-recovery-42`
6. Verify data in DB
7. Verify data in Grafana

**Expected outcome:** Clear error message, easy recovery, data appears

**How to verify:** All 260 rows appear in database

#### 7.2 Test MLO Dashboard with All Scenarios
**Action:** Run all three scenarios and verify dashboard displays correctly

**Test commands:**
```bash
make run-mlo-exp EXP_ID=20260104-verify-normal-42 SCENARIO=normal
make run-mlo-exp EXP_ID=20260104-verify-pos-42 SCENARIO=positive
make run-mlo-exp EXP_ID=20260104-verify-neg-42 SCENARIO=negative
```

**Expected outcome:**
- All 3 experiments show in Grafana
- Attack scenarios show different `avg_backoff_slots` values
- Throughput differences are visible
- No missing metrics

**How to verify:**
- Dashboard shows 3 distinct lines per metric
- Normal: backoff ~15-20 slots
- Positive: backoff >5000 slots
- Negative: backoff <-4990 slots

#### 7.3 Test State Management Targets
**Action:** Verify all new Makefile targets work

**Tests:**
```bash
make kafka-list          # Should show topics
make exporter-state      # Should show JSON state
make exporter-reset-exp EXP_ID=20260104-verify-normal-42
make exporter-state      # Should not have that experiment
make exporter-reset      # Should delete state file
make exporter-state      # Should show "No state file"
```

**Expected outcome:** All commands work as documented

**How to verify:** Output matches expected behavior

#### 7.4 Validate Documentation Accuracy
**Action:** Have someone unfamiliar follow the docs from scratch

**Steps:**
1. Follow setup checklist in `docs/QUICK-REFERENCE.md`
2. Run first experiment using `docs/WP7-ONE-COMMAND-PIPELINE.md`
3. When issue occurs, use `docs/TROUBLESHOOTING.md`
4. Verify they can recover without external help

**Expected outcome:** Documentation is complete and accurate

**How to verify:** User successfully runs pipeline without asking questions

---

## Integration Points

### Exporter → Kafka
- Enhanced with health checks
- Delivery confirmation tracking
- State only advances after confirmed delivery

### Makefile → Kafka
- New targets for topic management
- Documented in QUICK-REFERENCE.md
- Part of standard setup workflow

### Grafana → Database
- New dashboard queries 13 MLO metrics
- Time range adjusted for simulation timestamps
- Template variables for scenario filtering

### Documentation → Codebase
- Troubleshooting guide references specific commands
- Recovery procedures tested and verified
- Setup checklist matches actual requirements

---

## Testing Strategy

### Manual Testing
- [ ] Recovery: Delete state, re-export, verify DB rows
- [ ] Exporter fix: Stop Kafka, run exporter, verify state doesn't advance
- [ ] Topic creation: Run `make kafka-init`, verify idempotent
- [ ] Dashboard: Load in Grafana, verify all panels show data
- [ ] Time range: Verify 2026 timestamps display correctly

### Verification Commands
```bash
# Verify recovery complete
docker exec -it clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "
  SELECT experiment_id, COUNT(*)
  FROM metrics
  WHERE experiment_id LIKE '20260103-1400-mlo%'
  GROUP BY experiment_id;
"
# Expected: All 3 experiments with 260, 260, 240 rows

# Verify Kafka topic exists
make kafka-list
# Expected: wifi7.telemetry.v0_1 appears

# Verify exporter state management
make exporter-state
# Expected: JSON shows processed files

# Verify Grafana dashboard
curl -s http://localhost:3000/api/dashboards/uid/wp75-mlo-attack | jq '.dashboard.title'
# Expected: Dashboard title returned
```

### End-to-End Test
```bash
# Full pipeline test with new workflow
make down
make up
sleep 30
make kafka-init
make pipeline-up
make run-mlo-exp EXP_ID=20260104-e2e-test-42 SCENARIO=positive
# Verify in Grafana - should see data immediately
```

---

## Potential Issues

### Issue 1: Consumer Group Offset
**Problem:** Harmonizer may have already committed offset past the normal experiment messages

**Impact:** Even after re-export, harmonizer won't consume old messages

**Solution:** Use new consumer group with `earliest` offset:
```bash
docker-compose -f docker-compose.pipeline.yml down
KAFKA_GROUP=harmonizer-recovery-$(date +%s) AUTO_OFFSET_RESET=earliest \
  docker-compose -f docker-compose.pipeline.yml up -d
```

**Prevention:** Document consumer group management in troubleshooting guide

### Issue 2: Exporter Callback Timing
**Problem:** Delivery callbacks may arrive out of order

**Impact:** Saving offset per callback could skip messages

**Solution:** Track pending deliveries as set, only save highest confirmed offset periodically:
```python
confirmed_offsets = []
def delivery_report(err, msg):
    if not err:
        confirmed_offsets.append(pending_deliveries[msg.key()])

# Periodically flush:
if len(confirmed_offsets) > 0:
    save_offset(state, TELEMETRY_FILE, max(confirmed_offsets))
    confirmed_offsets.clear()
```

**Prevention:** Thorough testing with concurrent publishes

### Issue 3: Grafana Time Picker Confusion
**Problem:** Users forget to adjust time range to 2026

**Impact:** Dashboard shows "No Data" even when DB has rows

**Solution:**
1. Add dashboard annotation with warning
2. Set default time range to cover simulation times
3. Add note in dashboard description

**Prevention:** Document clearly in WP7 docs

### Issue 4: Duplicate Data After Recovery
**Problem:** Re-exporting may create duplicate messages in Kafka

**Impact:** Database may have duplicate rows (conflicts with unique index)

**Solution:** Database unique index handles this:
```sql
CREATE UNIQUE INDEX uq_metrics_idem
  ON metrics (experiment_id, entity_id, metric_name, ts);
```

Harmonizer uses INSERT ... ON CONFLICT DO UPDATE, so duplicates are safe.

**Prevention:** Verify harmonizer upsert logic handles duplicates correctly

---

## ADR Candidates

### ADR-WP7.5-01: Exporter Must Confirm Delivery Before Advancing State
**Decision:** Modify exporter to only save file offset after Kafka delivery confirmation

**Rationale:**
- Prevents data loss when Kafka is unavailable
- Makes pipeline resilient to transient failures
- Aligns with at-least-once delivery semantics

**Consequences:**
- Exporter may re-publish same messages after crashes
- Database must handle duplicates via unique index
- State file updates less frequently (batched)

### ADR-WP7.5-02: Kafka Topics Must Pre-Exist Before Pipeline Use
**Decision:** Require manual topic creation via `make kafka-init` before running experiments

**Rationale:**
- Explicit is better than implicit (no auto-create surprises)
- Allows setting partition count and replication
- Clear failure mode if topic missing
- Documents required infrastructure

**Consequences:**
- One-time manual step after `make up`
- Exporter should fail fast if topic missing
- Documentation must include this step

**Alternative considered:** Auto-create topics via Redpanda config
**Rejected because:** Less control over partition count, harder to debug

### ADR-WP7.5-03: Grafana Dashboards Use Absolute Time Ranges for Simulations
**Decision:** MLO attack dashboard uses absolute time range (2026 dates) as default

**Rationale:**
- Simulation timestamps are not "now"
- Relative time ranges ("Last 6 hours") mislead users
- Absolute range makes data immediately visible

**Consequences:**
- Dashboard only shows current batch of experiments by default
- Users must adjust range to see historical runs
- Need to update dashboard when running new experiments

**Alternative:** Add template variable for "most recent N experiments" (already implemented in WP6 dashboard)

---

## Related Documentation

### Existing Docs to Reference
- `docs/WP7-ONE-COMMAND-PIPELINE.md` - Pipeline workflow (update with recovery section)
- `docs/WP6-GRAFANA-DASHBOARDS.md` - Dashboard creation patterns
- `docs/WP4-TELEMETRY-EXPORTER.md` - Exporter design (update with delivery confirmation)
- `docs/ALL-ADRS.md` - Add new ADRs after implementation

### New Docs to Create
- `docs/TROUBLESHOOTING.md` - Centralized troubleshooting guide
- `clab/configs/redpanda/README.md` - Kafka topic management

### Docs to Update After Implementation
- `docs/CURRENT-STATE.md` - Update "Known Issues" section with resolutions
- `docs/QUICK-REFERENCE.md` - Add Kafka and exporter state management commands
- `README.md` - Add link to troubleshooting guide
- `docs/WP7-ONE-COMMAND-PIPELINE.md` - Add WP7.5 data recovery section

---

## Summary Checklist

### Data Recovery (Phase 1)
- [ ] Verify Kafka topic exists
- [ ] Check current DB state
- [ ] Reset exporter state for normal experiment
- [ ] Re-export missing experiment
- [ ] Verify 260 rows in database
- [ ] Verify data visible in Grafana

### Exporter Fix (Phase 2)
- [ ] Implement delivery confirmation tracking
- [ ] Add broker health check on startup
- [ ] Test with Kafka down (should not advance state)
- [ ] Test with Kafka up (should advance normally)

### Infrastructure (Phase 3)
- [ ] Create `make kafka-init` target
- [ ] Create `make exporter-reset` and `exporter-state` targets
- [ ] Test all new Makefile targets
- [ ] Document in QUICK-REFERENCE.md

### Grafana (Phase 4)
- [ ] Create MLO attack comparison dashboard
- [ ] Test all dashboard queries
- [ ] Verify time range settings
- [ ] Add annotations/notes for user guidance

### Documentation (Phases 5-6)
- [ ] Create TROUBLESHOOTING.md
- [ ] Update WP7 docs with recovery section
- [ ] Update QUICK-REFERENCE.md with setup checklist
- [ ] Add ADRs for key decisions

### Testing (Phase 7)
- [ ] End-to-end test: topic creation → experiment → Grafana
- [ ] Recovery test: simulate failure → recover → verify
- [ ] Dashboard test: all 3 scenarios → all metrics visible
- [ ] State management test: all Makefile targets work

---

## Success Criteria

1. **Data Recovery Complete:**
   - All 3 MLO experiments (`20260103-1400-mlo-*`) have data in DB
   - Normal experiment: 260 rows
   - Positive attack: 260 rows
   - Negative attack: 240 rows

2. **Pipeline Hardened:**
   - Exporter fails fast if topic missing (clear error message)
   - Exporter only advances state after delivery confirmation
   - No data loss on Kafka failures

3. **User Experience Improved:**
   - Clear setup checklist in docs
   - One command to create topics: `make kafka-init`
   - Easy state management: `make exporter-state`, `make exporter-reset`
   - Comprehensive troubleshooting guide

4. **Grafana Working:**
   - MLO dashboard shows all 13 metrics
   - All 3 scenarios distinguishable
   - Time range configured correctly (2026 dates)
   - Attack patterns visible (backoff manipulation)

5. **Documentation Complete:**
   - Setup workflow includes topic creation
   - Troubleshooting guide covers this failure mode
   - ADRs document design decisions
   - Recovery procedures tested and documented

---

## Next Steps After Implementation

### Immediate (WP7.5+)
1. Run complete end-to-end test with new workflow
2. Verify all documentation is accurate
3. Create ADRs for key decisions

### Short-term (WP8)
1. Consider Redpanda init script that runs on container start
2. Add monitoring for exporter delivery failures
3. Implement consumer group management tools
4. Add Grafana alerts for missing data

### Long-term (WP9+)
1. Add metrics for pipeline health (Prometheus exporter)
2. Implement automatic retry logic in exporter
3. Add pipeline smoke tests to CI
4. Create dashboard for pipeline observability

---

## Time Estimate

| Phase | Estimated Time | Priority |
|-------|---------------|----------|
| Phase 1: Data Recovery | 30 minutes | P0 (Immediate) |
| Phase 2: Exporter Fix | 2 hours | P0 (Critical) |
| Phase 3: Kafka Init | 1 hour | P1 (High) |
| Phase 4: Grafana Dashboard | 2 hours | P1 (High) |
| Phase 5: Setup Docs | 1 hour | P1 (High) |
| Phase 6: Troubleshooting | 2 hours | P2 (Medium) |
| Phase 7: Testing | 2 hours | P2 (Medium) |

**Total:** ~10-12 hours

**Recommended approach:**
- Phase 1 first (30 min) - gets data visible immediately
- Phases 2-3 together (3 hours) - fixes root cause
- Phase 4 (2 hours) - enables analysis
- Phases 5-6 (3 hours) - prevents future issues
- Phase 7 (2 hours) - validates everything works

---

## Questions to Resolve

1. **Consumer Group Management:** Should we automate consumer group creation with `earliest` offset for recovery scenarios?

2. **Exporter Design:** Should exporter exit after processing file once, or continue polling for new data? Current behavior polls indefinitely.

3. **Topic Auto-Creation:** Should we enable Redpanda auto-topic-creation for development ease, or keep manual creation for production discipline?

4. **Grafana Time Range:** Fixed absolute range vs. template variable for "last N experiments"? Current WP6 dashboard uses template variable approach.

5. **State File Location:** Should exporter state be per-experiment instead of global file? Would prevent cross-contamination but complicate management.

**Recommendation:** Document current decisions, defer major design changes to WP8 refactoring.
