# Why the Counter-Based Approach Works (and Offset Tracking Fails)

## Date
2026-01-04

## Purpose
This document explains why the simple counter-based approach is the ONLY correct solution for the exporter reliability bug, and why all offset-tracking approaches FAIL.

---

## The Bug (Line 123 in exporter.py)

```python
producer.produce(...)  # Line 114 - async enqueue
producer.poll(0)       # Line 120 - process callbacks (maybe 0, maybe some)
save_offset(...)       # Line 123 - BUG! Saves before delivery confirmed
```

**Problem:** `producer.produce()` is async. It only enqueues the message. Delivery happens later via callback. If Kafka is down, message fails but offset already saved → permanent data loss.

---

## Previous Plan's Fatal Flaws

### Flaw 1: `min(confirmed_offsets)` Causes Infinite Replays

**Original plan said (line 472 of old plan):**
```python
safe_offset = min(confirmed_offsets) if confirmed_offsets else 0
save_offset(state, TELEMETRY_FILE, safe_offset)
```

**Why this FAILS:**

Example run:
```
Line 1 (offset 0-100): "message 1"
Line 2 (offset 100-200): "message 2"
Line 3 (offset 200-300): "message 3"
```

First run:
1. Read line 1 → offset moves to 100
2. Read line 2 → offset moves to 200
3. Read line 3 → offset moves to 300
4. Confirm all deliveries: `confirmed_offsets = [100, 200, 300]`
5. Save `min([100, 200, 300])` = **100**

Second run:
1. Seek to offset 100
2. Read line 2 → offset moves to 200
3. Read line 3 → offset moves to 300
4. Confirm all: `confirmed_offsets = [200, 300]`
5. Save `min([200, 300])` = **200**

Third run:
1. Seek to offset 200
2. Read line 3 → offset moves to 300
4. Confirm: `confirmed_offsets = [300]`
5. Save `min([300])` = **300**

**PROBLEM:** Offset advances by one line per run. For a 260-line file, you need 260 runs to process it once! This is effectively an infinite replay bug.

**Even worse:**
- If offset starts at 100 (already processed first line), min() never goes below 100
- File never fully processes
- Infinite loop of replays

---

### Flaw 2: `max(confirmed_offsets)` Skips Gaps

**Alternative approach:**
```python
safe_offset = max(confirmed_offsets)
```

**Why this FAILS:**

Example with out-of-order callbacks:
```
Send messages 1, 2, 3 (offsets 100, 200, 300)
Callbacks arrive: 1 (offset 100), 3 (offset 300), 2 (offset 200)

After 1st callback: confirmed_offsets = [100]
After 2nd callback: confirmed_offsets = [100, 300]  ← 2 not confirmed yet!
After 3rd callback: confirmed_offsets = [100, 300, 200]
```

If you save `max([100, 300])` = 300 after 2nd callback (before 3rd arrives):
- Offset 200 not yet confirmed
- If process crashes, message 2 is LOST
- Next run starts at offset 300, skips message 2

**DATA LOSS!**

---

### Flaw 3: Duplicate Keys Break Offset Tracking

**Original plan used (line 361 of old plan):**
```python
pending_offsets = {}  # Keyed by message key

def delivery_report(err, msg):
    key = msg.key().decode('utf-8')
    if key in pending_offsets:
        offset = pending_offsets[key]
```

**Why this FAILS:**

Example:
```
Line 1: key="exp1|sta1|throughput|2026-01-04T12:00:00Z", offset=100
Line 2: key="exp1|sta2|throughput|2026-01-04T12:00:00Z", offset=200
Line 3: key="exp1|sta1|throughput|2026-01-04T12:00:00Z", offset=300  ← SAME KEY!
```

With dict keyed by message key:
```python
pending_offsets = {
    "exp1|sta1|throughput|...": 100,  # Line 1
    "exp1|sta2|throughput|...": 200,  # Line 2
    "exp1|sta1|throughput|...": 300,  # Line 3 - OVERWRITES offset 100!
}
```

Now you only have 2 entries (lost line 1's offset). Callback for line 1 arrives:
```python
key = "exp1|sta1|throughput|..."
offset = pending_offsets[key]  # Returns 300, not 100!
```

**Offset tracking is corrupted.**

---

### Flaw 4: Saving in Callback is Async Unsafe

**MLO plan suggested (line 203 of mlo-data-recovery plan):**
```python
def delivery_report(err, msg):
    if err is None:
        offset = pending_offsets[msg.key()]
        save_offset(state, TELEMETRY_FILE, offset)  # WRONG!
```

**Why this FAILS:**

1. **Callback runs on librdkafka background thread**
2. **Main thread also writes to state file**
3. **Race condition:**
   - Callback thread writes state file
   - Main thread writes state file
   - File corruption or lost updates

4. **Out-of-order callbacks:**
   - Message 3 confirms before message 2
   - Callback saves offset 300
   - Then callback for message 2 saves offset 200
   - **Offset goes backwards!**
   - Next run skips messages 201-300

**DATA LOSS and FILE CORRUPTION!**

---

## The CORRECT Solution: Simple Counters

### Code

```python
confirmed_count = 0
total_sent = 0
delivery_errors = []

def delivery_report(err, msg):
    nonlocal confirmed_count
    if err is not None:
        delivery_errors.append(str(err))
    else:
        confirmed_count += 1

# Read ENTIRE file
while line:
    producer.produce(..., callback=delivery_report)
    total_sent += 1
    producer.poll(0)

# Capture final file position BEFORE flush
final_offset = f.tell()

# Wait for ALL deliveries
producer.flush(timeout=30.0)

# Verify complete success
if delivery_errors or confirmed_count != total_sent:
    exit(1)  # Don't save state!

# All messages delivered successfully
save_offset(state, TELEMETRY_FILE, final_offset)
```

---

### Why This Works

#### 1. No Infinite Replays

**First run:**
- Read 260 lines (offsets 0 → 50738)
- `total_sent = 260`
- `final_offset = 50738` (end of file)
- All confirm: `confirmed_count = 260`
- Save `final_offset = 50738`

**Second run:**
- Seek to offset 50738 (end of file)
- No new lines to read
- `total_sent = 0`
- Print "no new messages"
- **Offset doesn't replay!**

#### 2. No Gaps (Handles Out-of-Order)

Out-of-order callbacks just increment counter:
```
Callback 1: confirmed_count = 1
Callback 3: confirmed_count = 2  (order doesn't matter!)
Callback 2: confirmed_count = 3
```

Only save if `confirmed_count == total_sent` (all confirmed).

**Can't skip messages** because:
- We wait for ALL to confirm before saving
- If any fail, we exit without saving
- Next run replays entire file from last saved position

#### 3. No Duplicate Key Issues

Don't use keys for tracking, just count:
```python
total_sent += 1  # Simple increment, no dict
```

Doesn't matter if same key appears twice - we're just counting total messages.

#### 4. Thread-Safe

- Callback only increments `confirmed_count` (atomic in Python)
- Main thread only reads counters (after flush, no concurrent access)
- Only main thread writes state file
- **No race conditions**

#### 5. At-Least-Once Semantics

File is small (260 lines, processes in <1 second):
- If any delivery fails → exit, don't save state
- Next run: replay entire file from last saved position
- Database unique index handles duplicates
- **Safe to replay, no data loss**

---

## Comparison Table

| Approach | Replays? | Gaps? | Duplicates? | Async Safe? | Verdict |
|----------|----------|-------|-------------|-------------|---------|
| `min(confirmed_offsets)` | ✗ INFINITE | ✓ | ✗ | ✓ | **FAILS** |
| `max(confirmed_offsets)` | ✓ | ✗ DATA LOSS | ✗ | ✓ | **FAILS** |
| Save in callback | ✓ | ✗ | ✗ | ✗ RACE | **FAILS** |
| Sequential offset tracking | ✓ | ✓ | ✗ | ✓ | Complex |
| **Counter-based** | ✓ | ✓ | ✓ | ✓ | **WORKS** |

---

## Why Previous Plans Made This Mistake

### Mistake 1: Overthinking the Problem

Original plan tried to be "clever":
- Track every offset
- Handle out-of-order delivery
- Resume from exact position

**But:** File is small (260 lines). Processing entire file takes <1 second. No need for complex incremental processing.

### Mistake 2: Not Testing the Logic

The `min(confirmed_offsets)` approach SOUNDS reasonable:
- "Save the minimum to be conservative"
- "Ensures no gaps"

**But:** Didn't trace through what happens:
- First line is offset 100
- min([100, 200, 300]) = 100
- Next run: seek(100)
- Read from offset 100 again
- min([200, 300]) = 200
- **Offset advances by 100 each run, not to end of file**

### Mistake 3: Conflicting Advice Across Plans

- Main plan: Save after flush (correct)
- MLO plan: Save in callback (wrong)
- No one noticed the conflict

### Mistake 4: Not Considering "Final Offset"

Key insight: `f.tell()` after reading entire file gives you the END position.
- First run: read 260 lines → `f.tell()` = 50738
- Save 50738
- Second run: seek(50738) → at end, no new lines
- **This is the natural file position to save!**

Using `min(confirmed_offsets)` throws away this information.

---

## The Right Mental Model

**Wrong:** "Save the offset of each confirmed message"
- Leads to complex tracking
- Prone to min/max errors
- Duplicate key issues

**Right:** "Did ALL messages deliver successfully?"
- Yes → save final file position (f.tell())
- No → exit, don't save, retry next run
- Simple binary check: `confirmed_count == total_sent`

**File offset is not about messages, it's about file position:**
- Before: file pointer at position X
- After reading: file pointer at position Y
- Save Y if all messages from X to Y delivered
- Next run: seek to Y, continue reading

---

## Summary

**The bug:** Line 123 saves offset before Kafka confirms delivery.

**Why offset tracking fails:**
- `min()` causes infinite replays (advances one line per run)
- `max()` skips gaps (data loss on out-of-order)
- Duplicate keys corrupt tracking dict
- Saving in callback is async unsafe

**Why counters work:**
- Simple count: `confirmed_count == total_sent`
- Save `final_offset = f.tell()` (end of file)
- Next run: seek(final_offset) → resumes correctly
- No infinite replays (offset advances to end)
- No gaps (all-or-nothing)
- No duplicate issues (just counting)
- Thread-safe (atomic increment)

**The fix is simple because the problem is simple:**
- Read file
- Send all messages
- Wait for all confirmations
- Save final position
- Done

Don't overthink it.
