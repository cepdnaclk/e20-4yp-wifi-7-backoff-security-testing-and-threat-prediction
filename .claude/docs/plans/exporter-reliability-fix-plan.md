# Implementation Plan: Exporter Reliability Fix and Pipeline Hardening

## Date
2026-01-04

## Objective
Fix the critical exporter state management bug that caused data loss in WP7.5. The exporter currently saves file offsets BEFORE Kafka confirms delivery, leading to silent data loss when Kafka is unavailable or topics don't exist. Implement at-least-once delivery semantics and fail-fast health checks to prevent future data loss.

## Background
**Critical Bug Identified:** During WP7.5 MLO experiments, 1 of 3 experiments lost data despite exporter showing no errors. Root cause analysis revealed:

1. **Exporter saves state too early** - Line 123 in `exporter.py` calls `save_offset()` immediately after `producer.produce()`, but `produce()` only enqueues the message in an internal buffer. Actual delivery happens asynchronously via callback.

2. **No topic existence check** - Exporter runs even when Kafka topic doesn't exist. Messages are "sent" but silently fail. State advances anyway.

3. **Silent failures** - Current `delivery_report()` callback only prints errors, doesn't prevent state advancement.

4. **Wrong flow:**
   ```
   Current (BROKEN):
   produce() → save_offset() → callback (too late!)

   Correct:
   produce() → callback confirms → save_offset()
   ```

**Impact:** Lost 260 rows of data from `20260103-1400-mlo-normal-42` experiment. Only recovered 180/260 rows due to duplicate key constraints on re-export.

## Prerequisites
- [x] Read existing exporter code (`telemetry/exporters/ns3_file_exporter/exporter.py`)
- [x] Understand confluent_kafka Producer async behavior
- [x] Review database unique index for duplicate handling
- [x] Check ADRs for existing delivery semantics decisions
- [x] Review WP4 documentation for original design intent

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------||
| `telemetry/exporters/ns3_file_exporter/exporter.py` | Modify | Implement delivery confirmation tracking before saving state |
| `telemetry/exporters/ns3_file_exporter/requirements.txt` | Check | Verify confluent_kafka version supports AdminClient |
| `Makefile` | Modify | Add `kafka-init`, `kafka-list`, `exporter-state`, `exporter-reset*` targets |
| `docs/WP4-TELEMETRY-EXPORTER.md` | Update | Document new delivery confirmation semantics |
| `docs/ALL-ADRS.md` | Append | Add ADR-WP7.5-01 (delivery confirmation requirement) |
| `docs/ALL-ADRS.md` | Append | Add ADR-WP7.5-02 (topic pre-creation requirement) |
| `docs/TROUBLESHOOTING.md` | Create | Centralized troubleshooting guide |
| `docs/QUICK-REFERENCE.md` | Update | Add Kafka and exporter management commands |

## Implementation Steps

---

### Phase 1: Analyze Callback Timing and Thread Safety

#### 1.1 Document Current Broken Flow
**Action:** Create detailed code analysis of the bug

**Current code flow (lines 93-123 in exporter.py):**
```python
while True:  # File reading loop
    line = f.readline()
    if not line:
        break

    offset = f.tell()  # Get current file position

    # Parse and validate line...
    rec = TelemetryRecord(**raw)

    # Generate key
    key = f"{rec.experiment_id}|{rec.entity_id}|{rec.metric}|{rec.ts}"

    # STEP 1: Enqueue message (async, non-blocking)
    producer.produce(
        TOPIC,
        key=key.encode("utf-8"),
        value=json.dumps(rec.model_dump()).encode("utf-8"),
        callback=delivery_report,  # Called later on background thread
    )

    # STEP 2: Poll to trigger callbacks (processes 0+ callbacks)
    producer.poll(0)

    # STEP 3: Save offset - BUG! Message may not be delivered yet!
    save_offset(state, TELEMETRY_FILE, offset)
```

**Problem:**
- `producer.produce()` returns immediately after enqueuing to internal buffer
- `delivery_report()` callback executes asynchronously on producer's background thread
- `save_offset()` runs BEFORE callback confirms delivery
- If Kafka is down, message fails but offset is already saved → data loss

**Expected outcome:** Clear documentation of why current code is wrong

**How to verify:** Code comments accurately describe the bug

---

#### 1.2 Research confluent_kafka Delivery Guarantees
**Action:** Document how confluent_kafka Producer callbacks work

**Key facts about confluent_kafka:**
1. `producer.produce()` is asynchronous - only enqueues message
2. Returns `None` (doesn't indicate success/failure)
3. Callback signature: `callback(err, msg)` where:
   - `err` is `KafkaError` if delivery failed
   - `msg` is `Message` object with metadata if successful
4. Callbacks execute on librdkafka background thread (NOT main thread)
5. Callbacks may arrive out-of-order (message 100 before message 99)
6. `producer.poll(timeout)` processes queued callbacks
7. `producer.flush(timeout)` waits for all pending messages to deliver

**Thread safety considerations:**
- Cannot safely write to state file from callback (concurrent access)
- Need coordination between main loop and callback thread
- Python GIL provides some protection but not sufficient for file I/O

**Expected outcome:** Understanding of callback mechanics guides design

**How to verify:** Design choices align with Producer guarantees

---

### Phase 2: Design Delivery Confirmation Tracking System

#### 2.1 Choose State Saving Strategy

**Decision Point:** When to save offset?

**Option A: Save after EACH confirmed delivery (eager)**
```python
def delivery_report(err, msg):
    if err is None:
        offset = pending_offsets[msg.key()]
        save_offset(state, TELEMETRY_FILE, offset)
```
- Pros: Minimal data loss window (1 message)
- Cons: Many file writes (slow), concurrent access to state file

**Option B: Batch saves every N confirmations (batched)**
```python
confirmed_offsets = []
def delivery_report(err, msg):
    if err is None:
        confirmed_offsets.append(pending_offsets[msg.key()])

# In main loop every N messages:
if len(confirmed_offsets) >= 10:
    save_offset(state, TELEMETRY_FILE, min(confirmed_offsets))
    confirmed_offsets.clear()
```
- Pros: Fewer file writes, better performance
- Cons: Larger data loss window (N messages), complexity

**Option C: Save only on graceful shutdown (deferred)**
```python
def flush_and_save():
    producer.flush(timeout=30.0)  # Wait for all deliveries
    save_offset(state, TELEMETRY_FILE, final_offset)
```
- Pros: Minimal file I/O, simplest implementation
- Cons: Crash loses all progress, unsuitable for long-running processes

**RECOMMENDED: Option C with periodic saves**
- Save offset after `producer.flush()` every 100 messages
- Save on SIGTERM (graceful shutdown)
- Balances performance and data loss risk

**Rationale:**
- Exporter processes entire file quickly (< 1 second for 260 lines)
- Flush ensures all messages confirmed before saving
- No concurrent access issues
- Simpler code, easier to understand

**Expected outcome:** Clear strategy documented

**How to verify:** Design handles all edge cases

---

#### 2.2 Handle Out-of-Order Delivery Callbacks

**Problem:** Callbacks may arrive out of order
- Message at offset 1000 confirms before message at offset 500
- If we save offset 1000, messages 501-999 will be skipped on restart

**Solution: Track highest sequential confirmed offset**

**Approach:**
1. Track all pending offsets: `pending = {key: offset, ...}`
2. Track all confirmed offsets: `confirmed = set()`
3. Find highest offset where ALL previous messages confirmed
4. Only save that sequential offset

**Algorithm:**
```python
pending_offsets = {}  # {msg_key: file_offset}
confirmed_offsets = set()

def delivery_report(err, msg):
    if err is None:
        key = msg.key().decode('utf-8')
        offset = pending_offsets.get(key)
        if offset:
            confirmed_offsets.add(offset)

def get_safe_offset(all_pending_offsets):
    """Return highest offset where all previous offsets are confirmed"""
    if not confirmed_offsets:
        return 0

    sorted_pending = sorted(all_pending_offsets.values())
    safe_offset = 0

    for offset in sorted_pending:
        if offset in confirmed_offsets:
            safe_offset = offset
        else:
            break  # Gap found, stop here

    return safe_offset
```

**Alternative (simpler): Save minimum confirmed offset**
```python
# Always safe but may replay more messages
safe_offset = min(confirmed_offsets) if confirmed_offsets else 0
```

**RECOMMENDED: Simpler approach**
- Use `min(confirmed_offsets)` for safety
- Slight over-replay is acceptable (database deduplicates)
- Avoids complex sequential tracking logic

**Expected outcome:** Design handles out-of-order delivery

**How to verify:** Test with concurrent message production

---

#### 2.3 Handle Delivery Failures

**Decision Point:** What to do on delivery failure?

**Option A: Exit immediately**
```python
def delivery_report(err, msg):
    if err is not None:
        print(f"FATAL: Delivery failed: {err}")
        sys.exit(1)
```
- Pros: Fail-fast, clear error
- Cons: Exits on transient errors, no retry

**Option B: Retry failed messages**
```python
failed_messages = []
def delivery_report(err, msg):
    if err is not None:
        failed_messages.append(msg)

# Later: retry failed_messages
```
- Pros: Resilient to transient failures
- Cons: Complex retry logic, message ordering issues

**Option C: Log failure, continue (best-effort)**
```python
def delivery_report(err, msg):
    if err is not None:
        print(f"WARNING: Delivery failed: {err}")
        # Don't save offset for failed messages
```
- Pros: Simple, messages retried on next run
- Cons: Silent data loss if persistent failure

**RECOMMENDED: Exit on first failure (Option A with enhancement)**
```python
delivery_errors = []

def delivery_report(err, msg):
    if err is not None:
        delivery_errors.append(f"{err} (key={msg.key()})")
        print(f"ERROR: Message delivery failed: {err}")

# In main loop after flush:
if delivery_errors:
    print(f"FATAL: {len(delivery_errors)} message(s) failed delivery")
    for error in delivery_errors[:10]:  # Show first 10
        print(f"  - {error}")
    sys.exit(1)
```

**Rationale:**
- Fail-fast prevents silent data loss
- Shows clear error to user
- Next run will retry from last saved offset
- Persistent failures caught immediately

**Expected outcome:** Clear failure handling strategy

**How to verify:** Test with Kafka down scenario

---

### Phase 3: Implement Exporter Code Changes

#### 3.1 Add Delivery Tracking Data Structures
**Action:** Add at top of `main()` function (after line 79)

```python
def main():
    if not TELEMETRY_FILE:
        raise SystemExit("TELEMETRY_FILE env is required (path to telemetry.jsonl)")

    producer = Producer({"bootstrap.servers": BROKERS})
    state = load_state()
    offset = get_offset(state, TELEMETRY_FILE)

    print(f"[exporter] brokers={BROKERS} topic={TOPIC}")
    print(f"[exporter] file={TELEMETRY_FILE} resume_offset={offset}")

    # NEW: Delivery tracking
    pending_offsets = {}      # {msg_key: file_offset}
    confirmed_offsets = []    # List of confirmed offsets
    delivery_errors = []      # List of error messages

    # ... rest of function
```

**Expected outcome:** Data structures ready for tracking

**How to verify:** Code compiles without errors

---

#### 3.2 Modify delivery_report Callback
**Action:** Replace lines 69-71 with enhanced callback

**Current code:**
```python
def delivery_report(err, msg):
    if err is not None:
        print(f"[exporter] delivery failed: {err}")
```

**New code:**
```python
def delivery_report(err, msg):
    """Callback invoked when message delivery completes (success or failure)"""
    if err is not None:
        # Delivery failed - record error
        key = msg.key().decode('utf-8') if msg.key() else 'unknown'
        error_msg = f"Key={key}, Error={err}"
        delivery_errors.append(error_msg)
        print(f"[exporter] delivery FAILED: {error_msg}")
    else:
        # Delivery succeeded - track confirmed offset
        key = msg.key().decode('utf-8')
        if key in pending_offsets:
            offset = pending_offsets[key]
            confirmed_offsets.append(offset)
            print(f"[exporter] delivery confirmed: offset={offset}")
```

**Problem:** Callback can't access `pending_offsets`, `confirmed_offsets`, `delivery_errors` (wrong scope)

**Solution:** Use nonlocal or move callback inside main()

**Revised approach - Define callback inside main():**
```python
def main():
    # ... setup ...

    pending_offsets = {}
    confirmed_offsets = []
    delivery_errors = []

    def delivery_report(err, msg):
        """Closure capturing delivery tracking variables"""
        if err is not None:
            key = msg.key().decode('utf-8') if msg.key() else 'unknown'
            error_msg = f"Key={key}, Error={err}"
            delivery_errors.append(error_msg)
            print(f"[exporter] delivery FAILED: {error_msg}")
        else:
            key = msg.key().decode('utf-8')
            if key in pending_offsets:
                offset = pending_offsets[key]
                confirmed_offsets.append(offset)
                # Optional: print only every 10th confirmation to reduce noise
                if len(confirmed_offsets) % 10 == 0:
                    print(f"[exporter] delivered {len(confirmed_offsets)} messages")

    # ... rest of main loop ...
```

**Expected outcome:** Callback tracks delivery status

**How to verify:** Callback can access tracking variables

---

#### 3.3 Modify Main Loop to Track Pending Deliveries
**Action:** Modify lines 114-123

**Current code:**
```python
producer.produce(
    TOPIC,
    key=key.encode("utf-8"),
    value=json.dumps(rec.model_dump()).encode("utf-8"),
    callback=delivery_report,
)
producer.poll(0)

# persist state after successful enqueue
save_offset(state, TELEMETRY_FILE, offset)
```

**New code:**
```python
key_str = f"{rec.experiment_id}|{rec.entity_id}|{rec.metric}|{rec.ts}"
pending_offsets[key_str] = offset  # Track this message's offset

producer.produce(
    TOPIC,
    key=key_str.encode("utf-8"),
    value=json.dumps(rec.model_dump()).encode("utf-8"),
    callback=delivery_report,
)
producer.poll(0)  # Process callbacks

# DO NOT save offset here - wait for delivery confirmation!
```

**Expected outcome:** Messages tracked, offset NOT saved prematurely

**How to verify:** State file not modified during publishing

---

#### 3.4 Add Flush and Save Logic After File Processing
**Action:** Replace lines 128-129 with comprehensive flush logic

**Current code:**
```python
producer.flush(1.0)
time.sleep(POLL_INTERVAL)
```

**New code:**
```python
    # End of file reading loop

    # Wait for all pending deliveries to complete
    print(f"[exporter] flushing {len(pending_offsets)} pending messages...")
    outstanding = producer.flush(timeout=30.0)

    if outstanding > 0:
        print(f"[exporter] WARNING: {outstanding} messages did not flush in time")
        delivery_errors.append(f"{outstanding} messages timed out")

    # Check for delivery errors
    if delivery_errors:
        print(f"[exporter] FATAL: {len(delivery_errors)} delivery error(s) occurred:")
        for error in delivery_errors[:10]:  # Show first 10
            print(f"  - {error}")
        raise SystemExit(f"Exporter failed: {len(delivery_errors)} messages not delivered")

    # All messages delivered successfully - safe to save offset
    if confirmed_offsets:
        # Save the minimum confirmed offset (conservative, ensures no gaps)
        safe_offset = min(confirmed_offsets)
        print(f"[exporter] all messages delivered, saving offset={safe_offset}")
        save_offset(state, TELEMETRY_FILE, safe_offset)
    else:
        print(f"[exporter] no messages confirmed (empty file?)")

    # Reset tracking for next iteration
    pending_offsets.clear()
    confirmed_offsets.clear()
    delivery_errors.clear()

    time.sleep(POLL_INTERVAL)
```

**Expected outcome:** Offset only saved after ALL messages confirmed

**How to verify:** State file updated only after successful flush

---

### Phase 4: Add Health Check on Startup

#### 4.1 Implement Broker and Topic Health Check
**Action:** Add function before `main()`

```python
from confluent_kafka.admin import AdminClient

def check_broker_health():
    """Verify broker is reachable and topic exists before processing"""
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

**Expected outcome:** Clear, actionable error messages on failure

**How to verify:** Test with topic missing and broker down

---

#### 4.2 Call Health Check in main()
**Action:** Add call after initial setup (after line 83)

```python
def main():
    if not TELEMETRY_FILE:
        raise SystemExit("TELEMETRY_FILE env is required (path to telemetry.jsonl)")

    producer = Producer({"bootstrap.servers": BROKERS})
    state = load_state()
    offset = get_offset(state, TELEMETRY_FILE)

    print(f"[exporter] brokers={BROKERS} topic={TOPIC}")
    print(f"[exporter] file={TELEMETRY_FILE} resume_offset={offset}")

    # NEW: Health check before processing
    check_broker_health()

    # Delivery tracking
    pending_offsets = {}
    confirmed_offsets = []
    delivery_errors = []

    # ... rest of main
```

**Expected outcome:** Exporter fails fast if infrastructure not ready

**How to verify:** Run without topic - should exit with clear error

---

### Phase 5: Add Makefile Kafka Management Targets

#### 5.1 Create Kafka Topic Management Section
**Action:** Add to `Makefile` after harmonizer targets (around line 95)

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

#### 5.2 Create Exporter State Management Section
**Action:** Add to `Makefile` after Kafka section

```makefile
# =============================================================================
# Exporter State Management
# =============================================================================

.PHONY: exporter-state exporter-reset exporter-reset-exp exporter-reset-file

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

# Reset exporter state for specific file path (advanced usage)
exporter-reset-file:
	@test -n "$(FILE)" || (echo "ERROR: FILE required (full container path)" && \
	  echo "Example: make exporter-reset-file FILE=/work/sim/ns3/artifacts/.../telemetry.jsonl" && exit 1)
	@python3 -c "import json; \
	  state = json.load(open('.exporter_state/exporter_state.json')); \
	  state['files'].pop('$(FILE)', None); \
	  json.dump(state, open('.exporter_state/exporter_state.json', 'w'), indent=2)"
	@echo "✓ Reset state for $(FILE)"
```

**Expected outcome:** Easy state management for recovery scenarios

**How to verify:** Run `make exporter-state` to view current state

---

### Phase 6: Update Documentation

#### 6.1 Update WP4 Documentation
**Action:** Modify `docs/WP4-TELEMETRY-EXPORTER.md`

**Add new section after "Implementation Details":**

```markdown
## Delivery Semantics (Updated WP7.5)

### At-Least-Once Delivery
The exporter guarantees **at-least-once delivery** semantics:
- Messages may be delivered more than once (on retry/recovery)
- Messages will NEVER be lost due to exporter state management
- Database handles duplicates via unique index

### State Management Flow
```
1. Read line from telemetry.jsonl
2. Enqueue message to Kafka (producer.produce())
3. Track pending offset
4. Continue reading file
5. Flush producer (wait for all deliveries)
6. Check delivery_report callbacks
7. If ANY failures → exit with error (do NOT save state)
8. If ALL successful → save minimum confirmed offset
9. Next run resumes from saved offset
```

### Why Minimum Confirmed Offset?
Kafka delivery callbacks may arrive **out of order**:
- Message at offset 1000 may confirm before offset 500
- Saving offset 1000 would skip messages 501-999
- Saving `min(confirmed_offsets)` ensures no gaps
- May replay some messages, but database deduplicates

### Health Checks
Exporter performs health check on startup:
1. Verify Kafka broker is reachable
2. Verify topic exists
3. Exit with clear error if checks fail

**Fail-fast** prevents silent data loss.

### Error Handling
| Scenario | Behavior |
|----------|----------|
| Topic doesn't exist | Exit with error, show `make kafka-init` command |
| Broker unreachable | Exit with error, show diagnostics |
| Delivery fails | Exit with error, state NOT saved, retry on next run |
| Flush timeout | Exit with error, show number of outstanding messages |

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

### See Also
- ADR-WP7.5-01: Exporter delivery confirmation requirement
- ADR-WP7.5-02: Kafka topic pre-creation requirement
```

**Expected outcome:** Clear documentation of new behavior

**How to verify:** Documentation is accurate and complete

---

#### 6.2 Create ADR-WP7.5-01
**Action:** Append to `docs/ALL-ADRS.md`

```markdown
## ADR-WP7.5-01: Exporter Must Confirm Delivery Before Advancing State

### Status
Accepted

### Context
WP7.5 discovered critical data loss bug in exporter. The exporter was saving file offset state immediately after calling `producer.produce()`, but this call only enqueues the message in an internal buffer. Actual delivery happens asynchronously via callback. If Kafka is unreachable, messages fail but state advances anyway, causing permanent data loss.

**Bug example:**
```python
# WRONG (original code):
producer.produce(topic, value=msg, callback=delivery_report)
save_offset(state, file, offset)  # TOO EARLY!

# Callback runs later (maybe fails, maybe succeeds)
# But offset already saved → data loss if failed
```

**Impact:** Lost 260 rows from `20260103-1400-mlo-normal-42` experiment.

### Decision
Exporter must wait for Kafka delivery confirmation before advancing file offset state.

**Implementation:**
1. Track pending message offsets
2. Wait for delivery callbacks to confirm success
3. Only save offset after `producer.flush()` completes
4. Exit with error if any delivery fails (fail-fast)
5. Use minimum confirmed offset to handle out-of-order callbacks

**Code pattern:**
```python
pending_offsets = {}
confirmed_offsets = []

def delivery_report(err, msg):
    if err is None:
        confirmed_offsets.append(pending_offsets[msg.key()])
    else:
        # Error - will exit after flush

# Main loop:
pending_offsets[key] = offset
producer.produce(...)

# After reading file:
producer.flush()
if delivery_errors:
    exit(1)  # Don't save state
else:
    save_offset(state, file, min(confirmed_offsets))
```

### Rationale
- **At-least-once delivery:** Prevents data loss, accepts potential duplicates
- **Fail-fast:** Clear errors better than silent failures
- **Database deduplication:** Unique index handles replayed messages
- **Simple retry:** Next run automatically retries from last confirmed offset

### Consequences
**Positive:**
- No data loss from Kafka failures
- Clear error messages when infrastructure unavailable
- Automatic retry on next run
- Aligns with industry best practices

**Negative:**
- May replay messages on recovery (database handles duplicates)
- Exporter exits on any delivery failure (no graceful degradation)
- Slightly more complex code

**Mitigation:**
- Database unique index ensures duplicates are safe
- Clear error messages guide users to resolution
- Makefile targets simplify state management

### Alternatives Considered
**Option 1:** Save after each callback
- Rejected: Concurrent file writes, poor performance

**Option 2:** Best-effort delivery, log failures
- Rejected: Silent data loss unacceptable

**Option 3:** Implement retry logic in exporter
- Deferred: Added complexity, may revisit in WP8

### Related
- ADR-WP4-04: Exporter uses persisted offsets (original design)
- ADR-WP5-03: DB idempotency enforced with unique index (enables safe replay)
```

**Expected outcome:** Decision documented for future reference

**How to verify:** ADR accurately captures reasoning

---

#### 6.3 Create ADR-WP7.5-02
**Action:** Append to `docs/ALL-ADRS.md`

```markdown
## ADR-WP7.5-02: Kafka Topics Must Pre-Exist Before Pipeline Use

### Status
Accepted

### Context
WP7.5 data loss occurred partly because Kafka topic didn't exist when exporter first ran. Redpanda's default behavior varies:
- May auto-create topic (if configured)
- May silently fail message delivery
- May return error

Relying on auto-creation is implicit and error-prone.

### Decision
Require explicit topic creation via `make kafka-init` before running experiments.

**Implementation:**
1. Add `make kafka-init` Makefile target
2. Exporter checks topic existence on startup
3. Exit with clear error if topic missing
4. Update documentation to include topic creation step

**Setup workflow:**
```bash
make up          # Deploy containerlab
make kafka-init  # Create topics (ONE TIME)
make pipeline-up # Start pipeline
make run-exp ... # Run experiments
```

### Rationale
**Explicit is better than implicit:**
- Topic creation is infrastructure setup, not runtime concern
- Clear separation between "setup" and "use"
- Avoids surprises from auto-creation behavior

**Fail-fast:**
- Exporter health check catches missing topic immediately
- Clear error message guides user to solution
- No silent failures or partial success

**Control:**
- Explicit creation allows setting partition count
- Can set replication factor
- Can configure retention policies
- Easier to debug "why doesn't my topic exist?"

### Consequences
**Positive:**
- Clear setup workflow in documentation
- Predictable behavior across environments
- Easy troubleshooting (topic exists or doesn't)
- One-time setup cost, not per-experiment

**Negative:**
- Extra manual step after `make up`
- Could forget to run `make kafka-init`
- Not "just works" out of the box

**Mitigation:**
- Exporter health check reminds users if forgotten
- Error message shows exact command to run
- Documented in setup checklist
- Make target is idempotent (safe to run multiple times)

### Alternatives Considered
**Option 1:** Enable Redpanda auto-topic-creation
- Rejected: Less control, implicit behavior, harder to debug

**Option 2:** Exporter creates topic if missing
- Rejected: Mixes concerns, exporter shouldn't manage infrastructure

**Option 3:** Init script in Redpanda container
- Deferred: May add in WP8 for true "one-command" setup

### Implementation
```makefile
kafka-init:
	docker exec clab-...-bus-redpanda \
	  rpk topic create wifi7.telemetry.v0_1 \
	    --brokers localhost:9092 \
	    --partitions 3 \
	    --replicas 1
```

```python
# Exporter health check
def check_broker_health():
    metadata = admin_client.list_topics(timeout=10)
    if TOPIC not in metadata.topics:
        raise SystemExit(f"Topic '{TOPIC}' missing. Run: make kafka-init")
```

### Related
- ADR-WP7.5-01: Exporter delivery confirmation (prevents data loss)
- ADR-WP4-02: Exporter publishes to Kafka (original design)
```

**Expected outcome:** Topic management strategy documented

**How to verify:** ADR explains rationale clearly

---

#### 6.4 Update QUICK-REFERENCE.md
**Action:** Add Kafka and exporter commands

**Insert after "Pipeline Components" section:**

```markdown
### Kafka Topic Management
```bash
make kafka-init                # Create required topics (run once after 'make up')
make kafka-list                # List all topics
make kafka-describe            # Show topic details
make kafka-reset               # Delete all topics (WARNING: destructive)
```

### Exporter State Management
```bash
make exporter-state                        # Show current state
make exporter-reset                        # Reset all state (re-export everything)
make exporter-reset-exp EXP_ID=...         # Reset specific experiment
```

### First-Time Setup Checklist
```bash
# 1. Deploy infrastructure
make up
sleep 30  # Wait for services to be ready

# 2. Create Kafka topics (ONE TIME)
make kafka-init

# 3. Verify topics exist
make kafka-list

# 4. Start pipeline
make pipeline-up

# 5. Check pipeline status
make pipeline-status

# 6. Run first experiment
make run-exp EXP_ID=20260104-test-01

# 7. Verify in Grafana
open http://localhost:3000
```
```

**Expected outcome:** Quick reference updated with new commands

**How to verify:** Commands listed match Makefile targets

---

### Phase 7: Testing and Validation

#### 7.1 Test Health Check - Topic Missing
**Action:** Verify exporter fails fast when topic doesn't exist

**Test steps:**
```bash
# 1. Ensure topic does NOT exist
make kafka-reset  # Delete if exists

# 2. Try to run exporter
make exporter-run EXP_ID=20260103-1400-mlo-positive-42

# Expected: Clear error message showing:
# - "Topic 'wifi7.telemetry.v0_1' does not exist"
# - "Fix: make kafka-init"
# - Exporter exits with non-zero status
```

**Expected outcome:**
- Exporter exits immediately with error
- Error message is clear and actionable
- Shows exact command to fix issue

**How to verify:** Error message contains "make kafka-init"

---

#### 7.2 Test Health Check - Broker Unreachable
**Action:** Verify exporter fails fast when Kafka is down

**Test steps:**
```bash
# 1. Stop containerlab services
make down

# 2. Try to run exporter (will fail network check)
make exporter-run EXP_ID=20260103-1400-mlo-positive-42

# Expected: Error about broker unreachable
```

**Expected outcome:**
- Exporter exits with clear error
- Suggests checking `make status`

**How to verify:** Error mentions broker connectivity

---

#### 7.3 Test Delivery Confirmation - Normal Flow
**Action:** Verify state only saved after successful delivery

**Test steps:**
```bash
# 1. Start services and create topic
make up
sleep 30
make kafka-init

# 2. Delete exporter state
make exporter-reset

# 3. Run exporter
make exporter-run EXP_ID=20260103-1400-mlo-positive-42

# Expected output sequence:
# [exporter] checking broker health...
# [exporter] health check passed
# [exporter] file=... resume_offset=0
# [exporter] delivered 10 messages
# [exporter] delivered 20 messages
# ...
# [exporter] flushing 260 pending messages...
# [exporter] all messages delivered, saving offset=50738
```

**Expected outcome:**
- Health check runs first
- Messages delivered before state saved
- Offset saved only after flush completes

**How to verify:** State file updated after "flushing" message

---

#### 7.4 Test Delivery Failure - Kafka Stops Mid-Export
**Action:** Verify exporter doesn't save state when delivery fails

**Test steps:**
```bash
# This test is difficult without modifying code
# Alternative: Check that state is NOT saved if flush times out

# 1. Run exporter with very short flush timeout (modify code temporarily)
# 2. Verify exporter exits with error
# 3. Verify state file NOT updated
```

**Expected outcome:**
- Exporter exits with error on delivery failure
- State file not modified
- Next run retries from previous offset

**How to verify:** Compare state file timestamp before/after failed run

---

#### 7.5 Test State Management - Reset Specific Experiment
**Action:** Verify `make exporter-reset-exp` works correctly

**Test steps:**
```bash
# 1. Run exporter for experiment
make exporter-run EXP_ID=20260103-1400-mlo-positive-42

# 2. Check state
make exporter-state
# Should show offset for positive-42

# 3. Reset that experiment
make exporter-reset-exp EXP_ID=20260103-1400-mlo-positive-42

# 4. Check state again
make exporter-state
# Should NOT show offset for positive-42

# 5. Re-run exporter
make exporter-run EXP_ID=20260103-1400-mlo-positive-42
# Should process from offset 0
```

**Expected outcome:**
- State reset for specific experiment
- Other experiments unaffected
- Re-export starts from beginning

**How to verify:** State file changes correctly

---

#### 7.6 Test End-to-End - Complete Pipeline with New Workflow
**Action:** Verify complete workflow from scratch

**Test steps:**
```bash
# 1. Clean slate
make down
make exporter-reset

# 2. Setup
make up
sleep 30
make kafka-init
make kafka-list  # Verify topic exists
make pipeline-up

# 3. Run experiment
make run-exp EXP_ID=20260104-e2e-test-42

# 4. Verify in database
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "SELECT COUNT(*) FROM metrics WHERE experiment_id='20260104-e2e-test-42';"

# Expected: Row count matches telemetry.jsonl lines
```

**Expected outcome:**
- Pipeline works end-to-end
- No data loss
- All rows in database

**How to verify:** Database row count matches telemetry file

---

#### 7.7 Test Recovery Workflow - Simulate Original Bug
**Action:** Verify we can recover from missing data

**Test steps:**
```bash
# 1. Simulate the original problem:
#    - Exporter runs but messages don't deliver
#    - State is saved (OLD BUG BEHAVIOR - can't fully test with new code)
#    - Data missing from DB

# Instead, test recovery workflow:

# 1. Run experiment
make run-exp EXP_ID=20260104-recovery-test-42

# 2. Verify data in DB (260 rows)

# 3. Simulate "missing data" by resetting state
make exporter-reset-exp EXP_ID=20260104-recovery-test-42

# 4. Re-export
make exporter-run EXP_ID=20260104-recovery-test-42

# 5. Verify data STILL in DB (duplicates handled by unique index)
```

**Expected outcome:**
- Recovery workflow works
- Duplicate messages handled gracefully
- Final row count correct (not doubled)

**How to verify:** Database has expected row count, no errors

---

## Integration Points

### Exporter ↔ Kafka
- **Enhanced:** Health check verifies topic exists before processing
- **Enhanced:** Delivery confirmation tracked via callbacks
- **Enhanced:** State only saved after flush confirms all deliveries
- **New:** AdminClient used for health checks

### Makefile ↔ Kafka
- **New:** `kafka-init` target for topic creation
- **New:** `kafka-list` target for topic inspection
- **New:** `kafka-describe` for topic details
- **New:** `kafka-reset` for testing/debugging

### Makefile ↔ Exporter State
- **New:** `exporter-state` to view current state
- **New:** `exporter-reset` to clear all state
- **New:** `exporter-reset-exp` to reset specific experiment
- **Existing:** `exporter-run` target unchanged (same interface)

### Database ↔ Exporter
- **Unchanged:** Database unique index handles duplicates
- **Benefit:** At-least-once delivery + deduplication = no data loss

---

## Testing Strategy

### Unit Testing (Manual Code Review)
- [ ] Verify callback has access to tracking variables (closure)
- [ ] Verify offset saved only after flush
- [ ] Verify min() logic handles out-of-order callbacks
- [ ] Verify health check exits on missing topic
- [ ] Verify health check exits on unreachable broker

### Integration Testing (System Tests)
- [ ] Health check: topic missing → clear error
- [ ] Health check: broker down → clear error
- [ ] Normal flow: messages deliver, state saved
- [ ] Delivery failure: state NOT saved (hard to test)
- [ ] State reset: specific experiment cleared
- [ ] State reset: all experiments cleared
- [ ] End-to-end: experiment → database (no data loss)

### Recovery Testing
- [ ] Reset state → re-export → verify rows
- [ ] Duplicates handled by unique index
- [ ] Consumer group offset independent of exporter state

### Verification Commands
```bash
# Check exporter state
make exporter-state

# Check Kafka topics
make kafka-list

# Check database rows
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "SELECT experiment_id, COUNT(*) FROM metrics GROUP BY experiment_id ORDER BY experiment_id;"

# Check harmonizer logs
make pipeline-status
```

---

## Potential Issues

### Issue 1: Callback Thread Safety
**Problem:** `delivery_report()` runs on librdkafka background thread

**Risk:** Concurrent access to `confirmed_offsets` list

**Mitigation:**
- Python list.append() is atomic (GIL protection)
- We only append, never modify existing elements
- Main thread only reads after flush (no concurrent access)

**Verification:** Review Python GIL guarantees for list operations

---

### Issue 2: Out-of-Order Callbacks
**Problem:** Message 100 confirms before message 99

**Risk:** Saving wrong offset, skipping messages

**Mitigation:**
- Use `min(confirmed_offsets)` to get conservative offset
- Slight over-replay acceptable (database deduplicates)

**Verification:** Test with large file, verify no messages skipped

---

### Issue 3: Flush Timeout
**Problem:** `producer.flush(30.0)` times out with pending messages

**Risk:** Unclear whether messages delivered or lost

**Mitigation:**
- Treat timeout as error (exit without saving state)
- Next run retries from last confirmed offset
- Log number of outstanding messages for debugging

**Verification:** Test with network delays

---

### Issue 4: Empty File or No New Data
**Problem:** `confirmed_offsets` is empty after processing

**Risk:** Trying to call `min([])` raises exception

**Mitigation:**
```python
if confirmed_offsets:
    save_offset(state, file, min(confirmed_offsets))
else:
    print("[exporter] no new messages (file already processed or empty)")
```

**Verification:** Test with already-processed file

---

### Issue 5: Multiple Exporters Running Concurrently
**Problem:** Two exporters processing same file with shared state file

**Risk:** Race condition on state file, corrupted state

**Mitigation:**
- Document: Don't run multiple exporters for same file
- Use per-file locking (future enhancement)
- Current workflow doesn't require concurrent exporters

**Verification:** Add warning to documentation

---

### Issue 6: Consumer Group Already Consumed Messages
**Problem:** Re-exported messages already committed by harmonizer consumer group

**Risk:** Harmonizer won't re-consume, data missing from DB

**Mitigation:**
- Use new consumer group with `AUTO_OFFSET_RESET=earliest`
- Or reset existing consumer group offset
- Document in troubleshooting guide

**Verification:** Test recovery with existing consumer group

---

## ADR Candidates

### ADR-WP7.5-01: Exporter Must Confirm Delivery Before Advancing State
**Status:** Documented in Phase 6.2

**Summary:** Exporter tracks delivery callbacks and only saves file offset after flush confirms all messages delivered successfully.

---

### ADR-WP7.5-02: Kafka Topics Must Pre-Exist Before Pipeline Use
**Status:** Documented in Phase 6.3

**Summary:** Require explicit `make kafka-init` before experiments, exporter health check verifies topic exists.

---

### ADR-WP7.5-03: Use Minimum Confirmed Offset for State (NEW)
**Status:** Should be created

**Decision:** When callbacks arrive out-of-order, save `min(confirmed_offsets)` rather than last confirmed

**Rationale:**
- Guarantees no message skipped
- Simple algorithm (no complex sequential tracking)
- Slight over-replay acceptable (database deduplicates)

**Consequence:** May replay 10-50 messages on restart (vs 0-1 with perfect tracking)

---

## Related Documentation

### Documents to Update
- [x] `docs/WP4-TELEMETRY-EXPORTER.md` - Add delivery semantics section
- [x] `docs/ALL-ADRS.md` - Add ADR-WP7.5-01 and ADR-WP7.5-02
- [x] `docs/QUICK-REFERENCE.md` - Add Kafka and exporter commands
- [ ] `docs/CURRENT-STATE.md` - Remove from "Known Issues" after implementation
- [ ] `docs/TROUBLESHOOTING.md` - Add exporter troubleshooting section (future)

### Documents to Reference
- `docs/WP4-TELEMETRY-EXPORTER.md` - Original exporter design
- `docs/WP5-HARMONIZER.md` - Database deduplication strategy
- `.claude/docs/plans/mlo-data-recovery-and-pipeline-hardening-plan.md` - Original recovery plan (Phase 2-3)

---

## Success Criteria

1. **Exporter Reliability:**
   - [x] Exporter NEVER advances state unless Kafka confirms delivery
   - [x] Exporter fails fast with clear error if topic missing
   - [x] Exporter fails fast with clear error if broker unreachable
   - [x] Delivery failures prevent state advancement (next run retries)

2. **State Management:**
   - [x] `make exporter-state` shows current state
   - [x] `make exporter-reset` clears all state
   - [x] `make exporter-reset-exp EXP_ID=...` clears specific experiment
   - [x] State file only modified after successful flush

3. **Kafka Management:**
   - [x] `make kafka-init` creates required topics
   - [x] `make kafka-list` shows existing topics
   - [x] `make kafka-init` is idempotent (safe to run multiple times)

4. **Documentation:**
   - [x] WP4 doc updated with delivery semantics
   - [x] ADRs created for key decisions
   - [x] QUICK-REFERENCE updated with new commands
   - [x] Setup workflow includes `make kafka-init`

5. **End-to-End:**
   - [ ] Fresh deployment: `make up` → `kafka-init` → `run-exp` works
   - [ ] No data loss on Kafka failures
   - [ ] Recovery workflow documented and tested
   - [ ] All tests pass (Phase 7)

---

## Rollback Plan

If implementation breaks existing workflows:

### Symptoms of Broken Deployment
- Exporter exits when it used to work
- State file not updating
- Messages not reaching database

### Rollback Steps

1. **Revert code changes:**
   ```bash
   git checkout HEAD~1 -- telemetry/exporters/ns3_file_exporter/exporter.py
   ```

2. **Rebuild exporter:**
   ```bash
   make exporter-build
   ```

3. **Clear state if corrupted:**
   ```bash
   make exporter-reset
   ```

4. **Document issues:**
   - What broke?
   - Error messages seen?
   - Steps to reproduce?

### Prevent Rollback Scenarios

- Test thoroughly in Phase 7 before committing
- Keep old exporter as `exporter-v1.py` during transition
- Tag commit before changes: `git tag exporter-pre-fix`
- Test with multiple experiments before declaring success

---

## Time Estimate

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Analyze callback timing | 30 min | P0 |
| 2 | Design tracking system | 1 hour | P0 |
| 3 | Implement exporter changes | 2 hours | P0 |
| 4 | Add health checks | 1 hour | P0 |
| 5 | Add Makefile targets | 1 hour | P1 |
| 6 | Update documentation | 2 hours | P1 |
| 7 | Testing and validation | 2 hours | P0 |

**Total: ~9-10 hours**

**Critical path:** Phases 1-4 (core fix) must be done first, ~4-5 hours

**Can be deferred:** Phase 6 (documentation) can happen after code works

---

## Next Steps After Implementation

### Immediate
1. Run Phase 7 tests to validate fixes
2. Recover missing MLO data using new recovery workflow
3. Create ADRs for decisions made

### Short-term (WP8)
1. Consider adding metrics/monitoring for exporter
2. Add consumer group management tools
3. Add pipeline health dashboard
4. Consider init script in Redpanda container for auto-topic-creation

### Long-term (WP9+)
1. Add Prometheus metrics for exporter (messages sent, delivery errors)
2. Implement automatic retry with exponential backoff
3. Add pipeline smoke tests to CI
4. Consider distributed tracing for end-to-end visibility

---

## Questions to Resolve

### Q1: Should exporter run once or poll continuously?
**Current:** Polls indefinitely waiting for new data
**Alternative:** Process file once and exit
**Decision:** Keep polling for now (matches current behavior), revisit in WP8

### Q2: Flush timeout value?
**Current:** 30 seconds
**Consideration:** Too long delays error detection, too short causes false failures
**Decision:** 30s is reasonable (1000+ messages should deliver in <5s)

### Q3: Should we log every delivery confirmation?
**Current plan:** Log every 10th confirmation to reduce noise
**Alternative:** Log nothing, only log errors
**Decision:** Log every 10th for visibility without spam

### Q4: Should `make kafka-init` be part of `make up`?
**Current:** Separate command
**Alternative:** Auto-run on `make up`
**Decision:** Keep separate (explicit setup), may combine in WP8 "one-command" enhancement

### Q5: What about consumer group management?
**Current:** Manual (documented in troubleshooting)
**Alternative:** Add `make harmonizer-reset` to reset consumer group
**Decision:** Defer to WP8 (focus on exporter fix first)

---

## Implementation Checklist

### Code Changes
- [ ] Move `delivery_report` inside `main()` (closure)
- [ ] Add tracking variables: `pending_offsets`, `confirmed_offsets`, `delivery_errors`
- [ ] Modify callback to track confirmations and errors
- [ ] Track pending offsets in main loop
- [ ] Remove premature `save_offset()` call
- [ ] Add flush and confirmation logic after file processing
- [ ] Add `check_broker_health()` function with AdminClient
- [ ] Call health check in `main()` before processing
- [ ] Test and validate all changes

### Makefile Targets
- [ ] Add `kafka-init` target
- [ ] Add `kafka-list` target
- [ ] Add `kafka-describe` target
- [ ] Add `kafka-reset` target (with warning)
- [ ] Add `exporter-state` target
- [ ] Add `exporter-reset` target (with warning)
- [ ] Add `exporter-reset-exp` target
- [ ] Test all new targets

### Documentation
- [ ] Update WP4 with delivery semantics section
- [ ] Create ADR-WP7.5-01 (delivery confirmation)
- [ ] Create ADR-WP7.5-02 (topic pre-creation)
- [ ] Update QUICK-REFERENCE with new commands
- [ ] Update CURRENT-STATE after implementation
- [ ] Consider TROUBLESHOOTING.md (future)

### Testing
- [ ] Test health check: topic missing
- [ ] Test health check: broker down
- [ ] Test normal delivery flow
- [ ] Test state reset (all)
- [ ] Test state reset (specific experiment)
- [ ] Test end-to-end pipeline
- [ ] Test recovery workflow
- [ ] Validate no data loss in all scenarios

---

## Summary

This plan addresses the critical exporter reliability bug discovered in WP7.5. The core issue is simple but has significant impact: the exporter was saving its offset state before Kafka confirmed message delivery, leading to silent data loss when Kafka was unavailable.

**The fix is conceptual straightforward:**
1. Track which messages are pending delivery
2. Wait for Kafka to confirm via callbacks
3. Only save offset after ALL messages confirmed

**The implementation requires care:**
- Callback runs on background thread (use closure, not global state)
- Callbacks may arrive out-of-order (use min() of confirmed offsets)
- Delivery failures must prevent state advancement (fail-fast)
- Health checks prevent running when infrastructure incomplete

**The result will be:**
- Guaranteed at-least-once delivery (no data loss)
- Clear fail-fast errors (no silent failures)
- Easy recovery via state management (replay from last confirmed offset)
- Robust pipeline that survives Kafka failures

This is critical infrastructure - the plan emphasizes testing, validation, and clear documentation to prevent future issues.
