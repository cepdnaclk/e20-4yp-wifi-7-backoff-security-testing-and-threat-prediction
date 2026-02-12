# Implementation Plan: Exporter Reliability Fix (CORRECTED)

## Date
2026-01-04 (CORRECTED VERSION)

## Critical Corrections Made

**PREVIOUS PLAN HAD FATAL FLAWS:**

1. **`min(confirmed_offsets)` causes infinite replays** - If first line is offset 100, min() stays 100 forever
2. **Conflicting advice in MLO plan** - Suggested saving in callback (async, unsafe)
3. **`max(confirmed_offsets)` skips gaps** - Out-of-order callbacks cause data loss
4. **Duplicate key tracking** - Using Kafka key as dict key breaks with duplicates

**THIS CORRECTED PLAN USES SIMPLE COUNTER APPROACH - THE ONLY WAY THAT ACTUALLY WORKS**

---

## Objective

Fix critical exporter bug that saves file offset state BEFORE Kafka confirms delivery, leading to silent data loss when Kafka is unavailable or topics don't exist.

**The bug:** Line 123 in `exporter.py` calls `save_offset()` immediately after `producer.produce()`, but `produce()` only enqueues the message. Actual delivery happens asynchronously via callback.

**The fix:** Use simple counter-based approach - save final file position only after ALL messages confirmed.

---

## Background

**Critical Bug Identified:** During WP7.5 MLO experiments, 1 of 3 experiments lost data. Root cause: exporter saves state before Kafka delivery confirmation.

**Current broken flow:**
```python
line 114: producer.produce(...)  # Enqueues message (async)
line 120: producer.poll(0)       # Processes 0+ callbacks
line 123: save_offset(...)       # BUG! Saves before delivery confirmed
```

**Result:** If Kafka is down, message fails but offset saved → permanent data loss.

---

## Prerequisites

- [x] Read existing exporter code (`telemetry/exporters/ns3_file_exporter/exporter.py`)
- [x] Understand that `producer.produce()` is async (only enqueues)
- [x] Understand that callbacks may arrive out-of-order
- [x] Review database unique index for duplicate handling

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `telemetry/exporters/ns3_file_exporter/exporter.py` | Modify | Implement counter-based delivery confirmation |
| `Makefile` | Modify | Add `kafka-init`, `exporter-state`, `exporter-reset*` targets |
| `docs/WP4-TELEMETRY-EXPORTER.md` | Update | Document delivery confirmation semantics |
| `docs/ALL-ADRS.md` | Append | Add ADR-WP7.5-01 (delivery confirmation) |
| `docs/ALL-ADRS.md` | Append | Add ADR-WP7.5-02 (topic pre-creation) |
| `docs/QUICK-REFERENCE.md` | Update | Add Kafka management commands |

---

## Implementation Steps

### Phase 1: Understand Why Simple Counter Approach Works

#### The CORRECT Solution

**Key insight:** We don't need complex offset tracking. Just:
1. Read entire file from start position to end
2. Count messages sent vs. confirmed
3. Save final file position ONLY if all confirmed
4. At-least-once semantics: replay whole file on failure (database handles duplicates)

**Why this works:**
- File is small (260 lines, processes in <1 second)
- Database unique index prevents duplicate rows
- Simple count comparison: `confirmed_count == total_sent`
- No offset tracking complexity
- Handles out-of-order callbacks naturally (just increment counter)

**Why complex approaches FAIL:**
- `min(confirmed_offsets)` → stays at first offset forever
- `max(confirmed_offsets)` → skips failed messages in middle
- Per-message state saving → async file I/O, race conditions
- Keying by Kafka key → duplicate keys break tracking

---

### Phase 2: Implement Counter-Based Approach

#### 2.1 Modify exporter.py - Complete Replacement of main()

**Action:** Replace `main()` function (lines 74-130) with corrected implementation

**New implementation:**

```python
def main():
    if not TELEMETRY_FILE:
        raise SystemExit("TELEMETRY_FILE env is required (path to telemetry.jsonl)")

    producer = Producer({"bootstrap.servers": BROKERS})
    state = load_state()
    offset = get_offset(state, TELEMETRY_FILE)

    print(f"[exporter] brokers={BROKERS} topic={TOPIC}")
    print(f"[exporter] file={TELEMETRY_FILE} resume_offset={offset}")

    # Health check before processing
    check_broker_health(producer)

    while True:
        if not os.path.exists(TELEMETRY_FILE):
            time.sleep(1.0)
            continue

        # Counters for delivery tracking
        confirmed_count = 0
        total_sent = 0
        delivery_errors = []

        # Define callback as closure capturing counters
        def delivery_report(err, msg):
            nonlocal confirmed_count
            if err is not None:
                error_msg = f"{err}"
                delivery_errors.append(error_msg)
                print(f"[exporter] ERROR: Message delivery failed: {error_msg}")
            else:
                confirmed_count += 1
                # Log every 50th confirmation to show progress
                if confirmed_count % 50 == 0:
                    print(f"[exporter] delivered {confirmed_count} messages")

        with open(TELEMETRY_FILE, "r", encoding="utf-8") as f:
            # Seek to last confirmed position
            f.seek(offset)

            print(f"[exporter] reading from offset {offset}")

            # Read ENTIRE file from offset to end
            while True:
                line = f.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    raw = json.loads(line)
                    raw["source"] = raw.get("source", SOURCE)
                    raw["schema_version"] = raw.get("schema_version", SCHEMA_VERSION)
                    raw["ts"] = normalize_ts(raw.get("ts"))

                    rec = TelemetryRecord(**raw)

                    # Deterministic key helps idempotency downstream
                    key = f"{rec.experiment_id}|{rec.entity_id}|{rec.metric}|{rec.ts}"

                    # Enqueue message (async, non-blocking)
                    producer.produce(
                        TOPIC,
                        key=key.encode("utf-8"),
                        value=json.dumps(rec.model_dump()).encode("utf-8"),
                        callback=delivery_report,
                    )
                    total_sent += 1

                    # Process callbacks (non-blocking)
                    producer.poll(0)

                except (json.JSONDecodeError, ValidationError) as e:
                    print(f"[exporter] invalid line skipped: {e}")

            # Capture final file position BEFORE flush
            # This is where we stopped reading (end of file or last processed line)
            final_offset = f.tell()

        # Now we've read the entire file
        # Wait for ALL messages to be delivered
        print(f"[exporter] flushing {total_sent} messages (confirmed so far: {confirmed_count})...")
        outstanding = producer.flush(timeout=30.0)

        # Check for errors
        if outstanding > 0:
            error_msg = f"{outstanding} messages did not flush within timeout"
            print(f"[exporter] FATAL: {error_msg}")
            raise SystemExit(f"Exporter failed: {error_msg}")

        if delivery_errors:
            print(f"[exporter] FATAL: {len(delivery_errors)} delivery error(s):")
            for error in delivery_errors[:10]:  # Show first 10
                print(f"  - {error}")
            raise SystemExit(f"Exporter failed: {len(delivery_errors)} messages not delivered")

        if confirmed_count != total_sent:
            print(f"[exporter] FATAL: Sent {total_sent} but only confirmed {confirmed_count}")
            raise SystemExit(f"Exporter failed: delivery count mismatch")

        # ALL messages successfully delivered!
        # NOW it's safe to save state
        if total_sent > 0:
            print(f"[exporter] SUCCESS: All {confirmed_count} messages delivered")
            print(f"[exporter] saving offset={final_offset}")
            save_offset(state, TELEMETRY_FILE, final_offset)
            offset = final_offset  # Update for next iteration
        else:
            print(f"[exporter] no new messages in file")

        time.sleep(POLL_INTERVAL)
```

**Expected outcome:** Exporter only saves offset after ALL messages confirmed

**How to verify:**
1. Run with Kafka down → state file NOT updated
2. Run with Kafka up → state file updated after flush
3. Kill exporter mid-run → next run replays from last confirmed offset

---

#### 2.2 Add Health Check Function

**Action:** Add BEFORE `main()` function (around line 68)

```python
def check_broker_health(producer: Producer) -> None:
    """Verify broker is reachable and topic exists before processing"""
    from confluent_kafka.admin import AdminClient

    print(f"[exporter] checking broker health: {BROKERS}")

    try:
        admin_client = AdminClient({"bootstrap.servers": BROKERS})

        # List topics with timeout
        metadata = admin_client.list_topics(timeout=10)

        # Check if our topic exists
        if TOPIC not in metadata.topics:
            raise SystemExit(
                f"\n{'='*70}\n"
                f"FATAL ERROR: Kafka topic '{TOPIC}' does not exist\n"
                f"{'='*70}\n"
                f"The exporter cannot publish messages to a non-existent topic.\n\n"
                f"Fix: Create the topic first:\n"
                f"  make kafka-init\n\n"
                f"Or manually:\n"
                f"  docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \\\n"
                f"    rpk topic create {TOPIC} --brokers localhost:9092 --partitions 3\n"
                f"{'='*70}\n"
            )

        print(f"[exporter] health check passed: topic '{TOPIC}' exists")

    except Exception as e:
        if "does not exist" in str(e):
            raise  # Re-raise the topic missing error
        raise SystemExit(
            f"\n{'='*70}\n"
            f"FATAL ERROR: Cannot connect to Kafka broker\n"
            f"{'='*70}\n"
            f"Error: {e}\n\n"
            f"Possible causes:\n"
            f"  1. Containerlab services not running (run 'make up')\n"
            f"  2. Redpanda container not ready (wait 30s after 'make up')\n"
            f"  3. Network configuration issue (check --network clab-mgmt)\n\n"
            f"Diagnostics:\n"
            f"  make status    # Check containerlab services\n"
            f"  make logs      # Check container logs\n"
            f"{'='*70}\n"
        )
```

**Expected outcome:** Clear, actionable errors when infrastructure not ready

**How to verify:** Run with topic missing → clear error with fix instructions

---

### Phase 3: Add Makefile Kafka Management Targets

#### 3.1 Create Kafka Topic Management Section

**Action:** Add to `Makefile` after harmonizer targets

```makefile
# =============================================================================
# Kafka Topic Management
# =============================================================================

.PHONY: kafka-init kafka-list kafka-describe kafka-reset

# Create required Kafka topics (run once after 'make up')
kafka-init:
	@echo "Creating Kafka topics for NDT Wi-Fi 7 pipeline..."
	@docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
	  rpk topic create wifi7.telemetry.v0_1 \
	    --brokers localhost:9092 \
	    --partitions 3 \
	    --replicas 1 \
	  2>&1 | grep -v "TOPIC_ALREADY_EXISTS" || true
	@echo "✓ Kafka topics initialized"
	@echo ""
	@echo "Verify with: make kafka-list"

# List all Kafka topics
kafka-list:
	@echo "Kafka topics:"
	@docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
	  rpk topic list --brokers localhost:9092

# Show detailed topic information
kafka-describe:
	@docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
	  rpk topic describe wifi7.telemetry.v0_1 --brokers localhost:9092

# DANGER: Delete all topics (for testing/debugging only)
kafka-reset:
	@echo "⚠️  WARNING: This will DELETE all Kafka topics and data!"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read confirm
	@docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
	  rpk topic delete wifi7.telemetry.v0_1 --brokers localhost:9092 || true
	@echo "Topics deleted. Run 'make kafka-init' to recreate."
```

**Expected outcome:** Easy topic management via Makefile

**How to verify:** Run `make kafka-init` then `make kafka-list`

---

#### 3.2 Create Exporter State Management Section

**Action:** Add to `Makefile` after Kafka section

```makefile
# =============================================================================
# Exporter State Management
# =============================================================================

.PHONY: exporter-state exporter-reset exporter-reset-exp

# Show current exporter state (what's been processed)
exporter-state:
	@echo "Exporter state:"
	@if [ -f .exporter_state/exporter_state.json ]; then \
	  cat .exporter_state/exporter_state.json | python3 -m json.tool; \
	else \
	  echo "  (no state file - all files will be processed from start)"; \
	fi

# Reset ALL exporter state (forces full re-export of all files)
exporter-reset:
	@echo "⚠️  This will reset exporter state for ALL files."
	@echo "All telemetry files will be re-exported on next run."
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read confirm
	@rm -f .exporter_state/exporter_state.json
	@echo "✓ Exporter state reset"

# Reset exporter state for specific experiment (allows re-export)
exporter-reset-exp:
	@test -n "$(EXP_ID)" || (echo "ERROR: EXP_ID required" && \
	  echo "Example: make exporter-reset-exp EXP_ID=20260103-1400-mlo-normal-42" && exit 1)
	@echo "Resetting exporter state for: $(EXP_ID)"
	@if [ ! -f .exporter_state/exporter_state.json ]; then \
	  echo "No state file exists - nothing to reset"; \
	  exit 0; \
	fi
	@python3 -c "import json, sys; \
	  state = json.load(open('.exporter_state/exporter_state.json')); \
	  key = '/work/sim/ns3/artifacts/$(EXP_ID)/telemetry.jsonl'; \
	  if key in state.get('files', {}): \
	    del state['files'][key]; \
	    json.dump(state, open('.exporter_state/exporter_state.json', 'w'), indent=2); \
	    print(f'✓ Reset state for {key}'); \
	  else: \
	    print(f'No state found for {key} (already at start)');"
	@echo ""
	@echo "Re-export with: make exporter-run EXP_ID=$(EXP_ID)"
```

**Expected outcome:** Easy state management for recovery

**How to verify:** Run `make exporter-state` to view current state

---

### Phase 4: Update Documentation

#### 4.1 Update WP4 Documentation

**Action:** Add to `docs/WP4-TELEMETRY-EXPORTER.md` after "Implementation Details"

```markdown
## Delivery Semantics (Updated WP7.5)

### At-Least-Once Delivery

The exporter guarantees **at-least-once delivery** semantics:
- Messages may be delivered more than once (on retry/recovery)
- Messages will NEVER be lost due to exporter state management
- Database handles duplicates via unique index

### State Management Flow (Counter-Based)

```
1. Read entire file from last saved offset to end
2. Track: confirmed_count, total_sent, delivery_errors
3. Enqueue all messages to Kafka (async)
4. Capture final_offset = f.tell() at end of file
5. Flush producer (wait for ALL deliveries)
6. Check: confirmed_count == total_sent?
7. Check: delivery_errors empty?
8. If BOTH true → save final_offset
9. If ANY false → exit with error, DON'T save state
10. Next run resumes from saved offset
```

### Why Simple Counter Approach?

**Previous approaches that FAIL:**
- `min(confirmed_offsets)` → stays at first offset forever (infinite replays)
- `max(confirmed_offsets)` → skips failed messages in gaps
- Save in callback → async file I/O, race conditions

**Why counters work:**
- Simple comparison: `confirmed_count == total_sent`
- Handles out-of-order callbacks naturally (just increment)
- No duplicate key issues
- File is small (processes in <1 second)
- At-least-once: replay whole file on failure (database deduplicates)

### Health Checks

Exporter performs health check on startup:
1. Verify Kafka broker is reachable
2. Verify topic exists
3. Exit with clear error if checks fail

**Fail-fast** prevents silent data loss.

### Error Handling

| Scenario | Behavior |
|----------|----------|
| Topic doesn't exist | Exit with error, show `make kafka-init` |
| Broker unreachable | Exit with error, show diagnostics |
| Delivery fails | Exit with error, state NOT saved, retry on next run |
| Flush timeout | Exit with error, show outstanding count |
| Count mismatch | Exit with error, don't save state |

### Recovery Workflow

If data is missing from database:

```bash
# 1. Check exporter state
make exporter-state

# 2. Reset state for specific experiment
make exporter-reset-exp EXP_ID=20260103-1400-mlo-normal-42

# 3. Re-export
make exporter-run EXP_ID=20260103-1400-mlo-normal-42

# 4. Verify in database
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "SELECT COUNT(*) FROM metrics WHERE experiment_id='20260103-1400-mlo-normal-42';"
```
```

**Expected outcome:** Clear documentation of correct behavior

**How to verify:** Documentation matches implementation

---

#### 4.2 Create ADR-WP7.5-01

**Action:** Append to `docs/ALL-ADRS.md`

```markdown
## ADR-WP7.5-01: Exporter Must Confirm Delivery Before Advancing State (Counter-Based)

### Status
Accepted

### Context

WP7.5 discovered critical data loss bug. Exporter saved file offset immediately after `producer.produce()`, but this only enqueues (async). Actual delivery happens via callback. If Kafka unavailable, messages fail but state advances → permanent data loss.

**Bug:**
```python
producer.produce(...)  # Line 114 - async enqueue
producer.poll(0)       # Line 120 - process 0+ callbacks
save_offset(...)       # Line 123 - BUG! Saves before delivery confirmed
```

**Impact:** Lost 260 rows from experiment `20260103-1400-mlo-normal-42`.

### Decision

Use **simple counter-based approach** to track delivery:
1. Count messages sent: `total_sent`
2. Count messages confirmed: `confirmed_count` (callback increments)
3. Track errors: `delivery_errors` list
4. After flush: verify `confirmed_count == total_sent AND no errors`
5. Only then save `final_offset = f.tell()`

**Why counters, not offset tracking?**
- `min(confirmed_offsets)` → infinite replays (stays at first offset)
- `max(confirmed_offsets)` → skips gaps (data loss)
- Per-message save → async I/O, race conditions
- Simple counters → handles out-of-order callbacks, no complexity

### Implementation

```python
confirmed_count = 0
total_sent = 0
delivery_errors = []

def delivery_report(err, msg):
    nonlocal confirmed_count
    if err is None:
        confirmed_count += 1
    else:
        delivery_errors.append(str(err))

# Read entire file
while line:
    producer.produce(..., callback=delivery_report)
    total_sent += 1

final_offset = f.tell()  # Capture BEFORE flush

producer.flush()

if delivery_errors or confirmed_count != total_sent:
    exit(1)  # Don't save state!

save_offset(state, file, final_offset)  # Safe!
```

### Rationale

**At-least-once delivery:**
- File small (260 lines, <1 sec processing)
- Replay whole file on failure (safe)
- Database unique index handles duplicates

**Fail-fast:**
- Clear errors better than silent failures
- Automatic retry on next run

**Simplicity:**
- No complex offset tracking
- No async file I/O
- Easy to understand and debug

### Consequences

**Positive:**
- No data loss from Kafka failures
- Clear error messages
- Automatic retry
- Simple implementation

**Negative:**
- May replay entire file on recovery
- Exporter exits on any delivery failure

**Mitigation:**
- Database unique index prevents duplicate rows
- File processing is fast (<1 sec)
- Clear error messages guide to fix

### Alternatives Considered

**Option 1:** Track `min(confirmed_offsets)`
- **Rejected:** Stays at first offset forever (infinite replays)

**Option 2:** Track `max(confirmed_offsets)`
- **Rejected:** Skips failed messages in gaps (data loss)

**Option 3:** Save after each callback
- **Rejected:** Async file I/O, race conditions, poor performance

### Related
- ADR-WP4-04: Exporter persisted offsets (original design)
- ADR-WP5-03: DB unique index (enables safe replay)
```

**Expected outcome:** Decision documented

**How to verify:** ADR explains why counters work, why offsets don't

---

#### 4.3 Create ADR-WP7.5-02

**Action:** Append to `docs/ALL-ADRS.md`

```markdown
## ADR-WP7.5-02: Kafka Topics Must Pre-Exist (Explicit Creation)

### Status
Accepted

### Context

WP7.5 data loss occurred partly because topic didn't exist when exporter first ran. Relying on auto-creation is implicit and error-prone.

### Decision

Require explicit topic creation via `make kafka-init` before experiments.

**Setup workflow:**
```bash
make up          # Deploy containerlab
make kafka-init  # Create topics (ONE TIME)
make pipeline-up # Start pipeline
make run-exp ... # Run experiments
```

### Rationale

**Explicit > Implicit:**
- Clear separation: setup vs. use
- Predictable behavior
- No auto-create surprises

**Fail-fast:**
- Exporter health check catches missing topic
- Clear error shows fix: `make kafka-init`

**Control:**
- Set partition count, replication
- Configure retention policies
- Easier debugging

### Consequences

**Positive:**
- Clear setup workflow
- Predictable behavior
- Easy troubleshooting

**Negative:**
- Extra manual step
- Could forget

**Mitigation:**
- Exporter health check reminds if forgotten
- Error shows exact command
- Documented in setup checklist

### Implementation

```makefile
kafka-init:
    docker exec ... rpk topic create wifi7.telemetry.v0_1 --partitions 3
```

```python
def check_broker_health():
    if TOPIC not in metadata.topics:
        raise SystemExit("Topic missing. Run: make kafka-init")
```

### Related
- ADR-WP7.5-01: Delivery confirmation
```

**Expected outcome:** Topic strategy documented

**How to verify:** ADR clear and concise

---

#### 4.4 Update QUICK-REFERENCE.md

**Action:** Add after "Pipeline Components" section

```markdown
### Kafka Topic Management
```bash
make kafka-init                # Create required topics (run once)
make kafka-list                # List all topics
make kafka-describe            # Show topic details
make kafka-reset               # Delete all topics (WARNING)
```

### Exporter State Management
```bash
make exporter-state                        # Show current state
make exporter-reset                        # Reset all state
make exporter-reset-exp EXP_ID=...         # Reset specific experiment
```

### First-Time Setup Checklist
```bash
# 1. Deploy infrastructure
make up
sleep 30  # Wait for services

# 2. Create Kafka topics (ONE TIME)
make kafka-init

# 3. Verify topics
make kafka-list

# 4. Start pipeline
make pipeline-up

# 5. Run experiment
make run-exp EXP_ID=20260104-test-01

# 6. Verify in Grafana
open http://localhost:3000
```
```

**Expected outcome:** Quick reference updated

**How to verify:** Commands match Makefile

---

### Phase 5: Testing and Validation

#### 5.1 Test Health Check - Topic Missing

**Test:**
```bash
make kafka-reset  # Delete topic
make exporter-run EXP_ID=20260103-1400-mlo-positive-42
```

**Expected:**
- Clear error: "Topic 'wifi7.telemetry.v0_1' does not exist"
- Shows fix: "make kafka-init"
- Exits immediately

**How to verify:** Error message contains "make kafka-init"

---

#### 5.2 Test Counter Logic - Normal Flow

**Test:**
```bash
make up
sleep 30
make kafka-init
make exporter-reset
make exporter-run EXP_ID=20260103-1400-mlo-positive-42
```

**Expected output:**
```
[exporter] checking broker health...
[exporter] health check passed
[exporter] reading from offset 0
[exporter] delivered 50 messages
[exporter] delivered 100 messages
...
[exporter] flushing 260 messages (confirmed so far: 260)...
[exporter] SUCCESS: All 260 messages delivered
[exporter] saving offset=50738
```

**How to verify:**
1. Health check runs first
2. "SUCCESS" printed before saving
3. State file updated after flush

---

#### 5.3 Test Offset Advances Correctly (NO INFINITE REPLAY)

**Test:**
```bash
# First run
make exporter-reset
make exporter-run EXP_ID=20260103-1400-mlo-positive-42
make exporter-state  # Check offset saved

# Second run (should be no-op)
make exporter-run EXP_ID=20260103-1400-mlo-positive-42
```

**Expected:**
- First run: "SUCCESS: All 260 messages delivered, saving offset=50738"
- Second run: "no new messages in file" (resume_offset=50738)
- Offset ADVANCES (not stuck at 0 or 100)

**How to verify:** Second run shows "no new messages", not re-processing

---

#### 5.4 Test State Management

**Test:**
```bash
make exporter-state  # View state
make exporter-reset-exp EXP_ID=20260103-1400-mlo-positive-42
make exporter-state  # Verify removed
make exporter-run EXP_ID=20260103-1400-mlo-positive-42  # Re-export
```

**Expected:**
- State reset removes specific experiment
- Re-export processes from offset 0
- Database handles duplicates gracefully

**How to verify:** State changes, re-export succeeds

---

#### 5.5 Test End-to-End Pipeline

**Test:**
```bash
make down
make exporter-reset
make up
sleep 30
make kafka-init
make pipeline-up
make run-exp EXP_ID=20260104-e2e-test-42

# Verify
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "SELECT COUNT(*) FROM metrics WHERE experiment_id='20260104-e2e-test-42';"
```

**Expected:**
- Pipeline works end-to-end
- Row count matches telemetry.jsonl lines
- No data loss

**How to verify:** Database has all rows

---

## Integration Points

### Exporter ↔ Kafka
- **Enhanced:** Health check verifies topic exists
- **Enhanced:** Counters track delivery confirmation
- **Enhanced:** State saved only after ALL confirmations
- **New:** AdminClient for health checks

### Makefile ↔ Kafka
- **New:** `kafka-init` for topic creation
- **New:** `kafka-list` for inspection
- **New:** `kafka-reset` for testing

### Makefile ↔ Exporter State
- **New:** `exporter-state` to view
- **New:** `exporter-reset` to clear all
- **New:** `exporter-reset-exp` to reset one

---

## Potential Issues

### Issue 1: Thread Safety of Counter

**Problem:** Callback on background thread, counter on main thread

**Mitigation:**
- Python `int +=` is atomic (GIL protected)
- Only main thread reads counters (after flush, no concurrent access)
- Callbacks only increment (no complex operations)

**Verification:** Python GIL guarantees atomic int operations

---

### Issue 2: Empty File

**Problem:** `total_sent == 0`, what to save?

**Mitigation:**
```python
if total_sent > 0:
    save_offset(state, file, final_offset)
else:
    print("no new messages")
```

**Verification:** Test with already-processed file

---

### Issue 3: Flush Timeout

**Problem:** `producer.flush(30)` returns `outstanding > 0`

**Mitigation:**
- Treat as error
- Exit without saving state
- Next run retries

**Verification:** Test with network delays

---

## ADR Candidates

1. **ADR-WP7.5-01:** Counter-based delivery confirmation (documented in Phase 4.2)
2. **ADR-WP7.5-02:** Explicit topic creation (documented in Phase 4.3)

---

## Related Documentation

### Update After Implementation
- `docs/WP4-TELEMETRY-EXPORTER.md` - Delivery semantics
- `docs/ALL-ADRS.md` - Add ADRs
- `docs/QUICK-REFERENCE.md` - Add commands
- `docs/CURRENT-STATE.md` - Remove from "Known Issues"

---

## Success Criteria

1. **No Infinite Replays:**
   - Run exporter twice on same file
   - Second run shows "no new messages"
   - Offset advances correctly

2. **No Data Loss:**
   - Stop Kafka mid-run
   - Verify state NOT saved
   - Restart, verify messages retried

3. **Clear Errors:**
   - Run without topic → clear error with fix
   - Run with Kafka down → clear diagnostic

4. **State Management:**
   - `make exporter-state` works
   - `make exporter-reset-exp` works
   - Recovery workflow documented

5. **End-to-End:**
   - Fresh deployment works
   - No silent failures
   - All data in database

---

## Implementation Checklist

### Code Changes
- [ ] Replace `main()` with counter-based implementation
- [ ] Add `check_broker_health()` function
- [ ] Remove line 123 premature `save_offset()`
- [ ] Add counters: `confirmed_count`, `total_sent`, `delivery_errors`
- [ ] Define `delivery_report` as closure (captures counters)
- [ ] Capture `final_offset = f.tell()` BEFORE flush
- [ ] Verify counts after flush
- [ ] Save offset only if all confirmed
- [ ] Test thoroughly

### Makefile Targets
- [ ] Add `kafka-init`
- [ ] Add `kafka-list`
- [ ] Add `kafka-describe`
- [ ] Add `kafka-reset`
- [ ] Add `exporter-state`
- [ ] Add `exporter-reset`
- [ ] Add `exporter-reset-exp`

### Documentation
- [ ] Update WP4 with counter approach
- [ ] Create ADR-WP7.5-01
- [ ] Create ADR-WP7.5-02
- [ ] Update QUICK-REFERENCE
- [ ] Update CURRENT-STATE after tests pass

### Testing
- [ ] Test: topic missing → clear error
- [ ] Test: normal flow → all messages delivered
- [ ] Test: offset advances (no infinite replay)
- [ ] Test: state reset works
- [ ] Test: end-to-end pipeline
- [ ] Test: recovery workflow

---

## Summary

**The bug:** Line 123 saves offset before Kafka confirms delivery.

**Why previous plans failed:**
- `min(confirmed_offsets)` → infinite replays
- `max(confirmed_offsets)` → skips gaps
- Complex offset tracking → race conditions

**The correct fix:**
1. Simple counters: `confirmed_count`, `total_sent`
2. Read entire file, enqueue all messages
3. Capture `final_offset` at end
4. Flush and wait
5. Verify: `confirmed_count == total_sent AND no errors`
6. Only then save `final_offset`

**Why this works:**
- File small (processes in <1 sec)
- At-least-once delivery (replay safe)
- Database deduplicates
- Simple, no complexity
- **NO INFINITE REPLAYS** - offset advances to final position

**Time estimate:** ~6-8 hours total
- Code changes: 2 hours
- Makefile: 1 hour
- Documentation: 2 hours
- Testing: 2-3 hours
