# Architecture Decision Records (ADRs)

This document contains all architectural decisions made during the implementation of the NDT Wi-Fi 7 MLO Security project.

---

## Index

### WP1-WP3 (Foundation)
- [ADR-0001](#adr-0001-use-github-ssh-ed25519-for-repo-access): Use GitHub SSH (ed25519) for repo access
- [ADR-0002](#adr-0002-use-gh-cli-for-repo-creation): Use gh CLI for repo creation
- [ADR-0003](#adr-0003-use-containerlab-for-lab-environment): Use Containerlab for lab environment
- [ADR-0004](#adr-0004-keep-config-as-code): Keep config as code
- [ADR-0005](#adr-0005-use-postgres-as-udr-datastore): Use Postgres as UDR datastore
- [ADR-0006](#adr-0006-keep-ns-3-as-separate-container): Keep ns-3 as separate container
- [ADR-0007](#adr-0007-standardize-experiment-outputs-as-artifacts): Standardize experiment outputs as artifacts
- [ADR-0008](#adr-0008-use-stable-jsonl-telemetry-contract): Use stable JSONL telemetry contract
- [ADR-0009](#adr-0009-use-ns-3461-for-wifi-7): Use ns-3.46.1 for Wi-Fi 7
- [ADR-0010](#adr-0010-prefer-scratch-programs-over-copying-examples): Prefer scratch programs over copying examples
- [ADR-0011](#adr-0011-avoid-ns3-list-for-runnable-discovery): Avoid ./ns3 list for runnable discovery
- [ADR-0012](#adr-0012-fix-permissions-by-design): Fix permissions by design

### WP4-WP6 (Pipeline)
- [ADR-WP4-01](#adr-wp4-01-telemetry-contract-is-jsonl-v01): Telemetry contract is JSONL (v0.1)
- [ADR-WP4-02](#adr-wp4-02-exporter-reads-file-and-publishes-to-kafka): Exporter reads file and publishes to Kafka
- [ADR-WP4-03](#adr-wp4-03-deterministic-kafka-message-key): Deterministic Kafka message key
- [ADR-WP4-04](#adr-wp4-04-exporter-uses-persisted-offsets): Exporter uses persisted offsets
- [ADR-WP5-01](#adr-wp5-01-kafka-is-ingestion-bus-db-is-query-source): Kafka is ingestion bus, DB is query source
- [ADR-WP5-02](#adr-wp5-02-harmonizer-responsible-for-validation-and-mapping): Harmonizer responsible for validation and mapping
- [ADR-WP5-03](#adr-wp5-03-db-idempotency-enforced-with-unique-index): DB idempotency enforced with unique index
- [ADR-WP6-01](#adr-wp6-01-grafana-provisioning-as-code): Grafana provisioning as code

### WP7.5 (Exporter Reliability)
- [ADR-WP7.5-01](#adr-wp75-01-counter-based-delivery-confirmation): Counter-based delivery confirmation
- [ADR-WP7.5-02](#adr-wp75-02-topic-pre-creation-and-health-checks): Topic pre-creation and health checks
- [ADR-WP7.5-03](#adr-wp75-03-at-least-once-delivery-semantics): At-least-once delivery semantics

---

## ADR-0001: Use GitHub SSH (ed25519) for Repo Access

### Status
Accepted

### Context
Need to decide authentication method for GitHub repository access in development workflow.

### Decision
Use SSH authentication with an ed25519 key instead of HTTPS tokens.

### Rationale
- Cleaner for CLI workflows (git + gh)
- Works well in Kali/Linux and CI later
- Avoids token leakage risk in shells/scripts
- No need to manage token expiration

### Implementation
- Key lives at `~/.ssh/id_ed25519`
- SSH trust established via `ssh -T git@github.com`
- Verified with verbose auth test

### Consequences
- Every teammate must add their own SSH key to GitHub
- Repository clone URLs should be SSH (`git@github.com:...`)
- Need to document SSH setup process

---

## ADR-0002: Use gh CLI for Repo Creation

### Status
Accepted

### Context
Need a repeatable way to create and manage GitHub repositories.

### Decision
Use GitHub CLI (gh) for repo bootstrapping, auth, and push.

### Rationale
- Repeatable and faster than manual UI steps
- Standardizes onboarding instructions
- Can be scripted for automation

### Implementation
- On Kali, `apt install gh` was not available, so `snap install gh` was used
- Login via device-code browser flow

### Consequences
- On systems without snap, teammates may need alternate install method
- Docs must mention Kali-specific install caveat

---

## ADR-0003: Use Containerlab for Lab Environment

### Status
Accepted

### Context
Need an orchestration method for the services environment (UDR DB, Grafana, Kafka, etc.).

### Decision
Use Containerlab as the main orchestrator for the lab environment.

### Rationale
- Reproducible lab topology defined in YAML
- Services can be connected via controlled network
- Easier to extend without ad-hoc docker compose sprawl
- CI-ready lifecycle management

### Implementation
- Topology declared in `clab/topo.yml`
- Service configs mounted from `clab/configs/...`
- Makefile targets: `make up`, `make down`, `make status`

### Consequences
- All bind-mount paths referenced in topo.yml must exist
- Path mistakes break deploy early (containerlab validates mounts)
- Team must learn containerlab basics

---

## ADR-0004: Keep Config as Code

### Status
Accepted

### Context
Need to decide how to manage service configurations (Grafana datasources, dashboards, etc.).

### Decision
Store Grafana provisioning and service configs in the repo under `clab/configs/...`.

### Rationale
- Reproducibility: dashboards/datasources can be recreated
- No manual clicking in Grafana UI required for baseline setup
- Version controlled alongside code
- Easy to review changes in PRs

### Implementation
- Grafana provisioning at `clab/configs/grafana/provisioning/`
- Dashboards at `clab/configs/grafana/dashboards/`
- Bind-mounted into containers as read-only

### Consequences
- Empty config folders must still exist in git (use `.gitkeep`)
- Topology must mount correct paths relative to `clab/topo.yml`

---

## ADR-0005: Use Postgres as UDR Datastore

### Status
Accepted

### Context
Need to choose a database for the Unified Data Repository (UDR).

### Decision
Use Postgres with TimescaleDB extension for UDR (metrics + snapshots tables).

### Rationale
- Strong relational querying for metrics (Grafana-friendly)
- Simple and reliable in containers
- TimescaleDB provides time-series optimizations
- Avoids MongoDB complexity and schema drift for this use case

### Implementation
- Container: `timescale/timescaledb:latest-pg14`
- Tables: `metrics` (hypertable), `snapshots`
- Accessible via standard psql

### Consequences
- WP4/WP5 pipeline inserts telemetry rows into Postgres
- Schema migrations must be tracked and versioned
- Need to manage connection pooling for scale

---

## ADR-0006: Keep ns-3 as Separate Container

### Status
Accepted

### Context
Need to decide how to integrate ns-3 simulation with the lab environment.

### Decision
Run ns-3 in a separate Docker image (`ndt/ns3:local`) with repo bind-mounted, rather than embedding ns-3 directly inside containerlab.

### Rationale
- Much easier debugging
- ns-3 toolchain is heavy and has different lifecycle than "services"
- Avoids coupling ns-3 build/runtime problems to lab network problems
- Can iterate on ns-3 without restarting services

### Implementation
- Dockerfile at `docker/ns3/Dockerfile`
- Repo mounted at `/work` in container
- Artifacts written to `sim/ns3/artifacts/`

### Consequences
- Two execution planes exist: containerlab services and ns-3 runner
- Integration (ns-3 → Kafka) happens via file-based exporter
- Need separate build/run commands for ns-3

---

## ADR-0007: Standardize Experiment Outputs as Artifacts

### Status
Accepted

### Context
Need a consistent way to store and reference experiment outputs.

### Decision
All runs must output into `sim/ns3/artifacts/<EXP_ID>/...`

### Rationale
- Reproducibility and traceability
- Easy to commit sample artifacts or compare runs
- Future CI can archive artifacts per run
- Clear naming convention

### Implementation
- Experiment ID format: `YYYYMMDD-HHMM-<scenario>-<seed>`
- Standard artifacts: `meta.txt`, `telemetry.jsonl`, logs
- Directory created by run scripts

### Consequences
- Scripts must always create artifact directories
- Permissions must be controlled so host user owns artifacts
- Need to gitignore artifacts directory

---

## ADR-0008: Use Stable JSONL Telemetry Contract

### Status
Accepted

### Context
Need a stable interface format between ns-3 outputs and downstream pipeline stages.

### Decision
Use JSON Lines (`telemetry.jsonl`) as the interface between ns-3 and later pipeline stages.

### Rationale
- Easy streaming format (Kafka-friendly)
- Append-only and log-based
- Simple to parse with Python/Go/etc.
- Human-readable for debugging

### Current Schema (v0.1)
```json
{
  "experiment_id": "string",
  "ts": "ISO timestamp",
  "source": "ns3",
  "schema_version": "v0.1",
  "entity_id": "string",
  "metric": "string",
  "value": "float",
  "unit": "string"
}
```

### Consequences
- WP4 exporter must assume this schema
- Any schema change must be versioned (`schema_version` field exists)
- All scenarios must produce consistent output

---

## ADR-0009: Use ns-3.46.1 for Wi-Fi 7

### Status
Accepted

### Context
Need to choose ns-3 version that supports Wi-Fi 7 / 802.11be features.

### Decision
Use ns-3 version 3.46.1 (from ns-3-dev repo checkout).

### Rationale
- Wi-Fi 7 / MLO related features are in later ns-3 versions
- Establishes a consistent baseline for research work
- Reproducible across team members

### Implementation
- Version verified via `cat /opt/ns-3-dev/VERSION`
- Wrapper does not support `./ns3 --version`
- Dockerfile pins specific checkout

### Consequences
- Examples/tutorial code from other versions may not compile without adaptation
- Helper APIs can differ across versions
- Must test compile on this version

---

## ADR-0010: Prefer Scratch Programs Over Copying Examples

### Status
Accepted

### Context
Need to decide how to create ns-3 simulation scenarios.

### Decision
Use custom scratch programs for Wi-Fi experiments, rather than copying examples that depend on extra headers.

### Rationale
- Copying examples broke because headers like `wifi-example-apps.h` were missing
- Scratch program gives full control and stable compilation
- Self-contained code is easier to maintain

### Implementation
- Scenarios in `sim/ns3/scratch/`
- Each scenario is self-contained
- No external header dependencies

### Consequences
- Must maintain own simulation scenarios
- Should version scenario code carefully
- More initial effort but more reliable

---

## ADR-0011: Avoid ./ns3 list for Runnable Discovery

### Status
Accepted

### Context
Need a reliable way to discover available ns-3 programs.

### Decision
Do not use `./ns3 list` output filtering as a reliable discovery method for Wi-Fi programs.

### Rationale
- `./ns3 list | grep wifi` returned nothing even though Wi-Fi module was built
- The list output depends on how programs are registered
- Not reliable across versions

### Alternatives
- Use `./ns3 show targets` inside container
- Or compile known scratch files directly

### Consequences
- Docs should explain correct ways to discover runnable targets
- Don't rely on list output in scripts

---

## ADR-0012: Fix Permissions by Design

### Status
Accepted

### Context
Container runs were creating root-owned files in the repo.

### Decision
Ensure container runs do not create root-owned files in the repo.

### Rationale
- Root-owned artifacts caused "permission denied" when reading logs and deleting folders
- Team workflow breaks if artifacts require sudo cleanup
- Security best practice

### Implementation
- ns-3 container uses non-root user (`ns3`)
- Makefile runs containers with `--user "$(id -u):$(id -g)"`
- Key directories made writable in Dockerfile

### Consequences
- Always verify artifact ownership after runs
- Makefile targets must consistently enforce user mapping

---

## ADR-WP4-01: Telemetry Contract is JSONL (v0.1)

### Status
Accepted

### Context
Need to formalize the telemetry format for the pipeline.

### Decision
JSON Lines file per experiment run with v0.1 schema.

### Rationale
- Easy to generate from simulation
- Easy to stream and replay
- Easy to validate with Pydantic

### Consequences
- All ns-3 scenarios must output telemetry in this contract
- Schema changes require version bump

---

## ADR-WP4-02: Exporter Reads File and Publishes to Kafka

### Status
Accepted

### Context
Need to get telemetry from ns-3 artifacts into Kafka.

### Decision
File→Kafka exporter as separate container.

### Rationale
- Keeps ns-3 simple (no Kafka client needed)
- Simplifies debugging
- Supports multiple producers later
- Decouples simulation from transport

### Implementation
- Python service with kafka-python
- Reads JSONL file line by line
- Publishes to Redpanda topic

### Consequences
- Pipeline becomes modular and testable
- Need to manage exporter state (offsets)

---

## ADR-WP4-03: Deterministic Kafka Message Key

### Status
Accepted

### Context
Need to ensure idempotent message handling.

### Decision
Key = `experiment_id|entity_id|metric|ts`

### Rationale
- Enables downstream idempotency
- Kafka can dedupe by key
- Harmonizer can safely upsert

### Consequences
- Same measurement always has same key
- Re-publishing is safe

---

## ADR-WP4-04: Exporter Uses Persisted Offsets

### Status
Accepted

### Context
Exporter needs to track what it has already published.

### Decision
Store file read position (offset) in persistent state file.

### Rationale
- Prevents re-publishing same lines
- Survives container restarts
- Can resume after failures

### Implementation
- State file: `/state/exporter_state.json`
- Stores offset per file path
- Mounted from host `.exporter_state/`

### Consequences
- Offset must be per file (not global)
- Permissions must be handled correctly

---

## ADR-WP5-01: Kafka is Ingestion Bus, DB is Query Source

### Status
Accepted

### Context
Need to clarify the roles of Kafka and database.

### Decision
Kafka for transport, Postgres/Timescale for storage/query.

### Rationale
- Grafana works best with DB querying
- Kafka is not suitable as a dashboard store
- Clear separation of concerns

### Consequences
- Grafana depends on DB ingestion correctness
- Kafka is transient, DB is persistent

---

## ADR-WP5-02: Harmonizer Responsible for Validation and Mapping

### Status
Accepted

### Context
Need to decide where to enforce data quality.

### Decision
Enforce schema validation at harmonizer boundary.

### Rationale
- DB remains clean and queryable
- Single point of validation
- Can reject bad messages early

### Implementation
- Validates required fields
- Maps field names (metric → metric_name)
- Logs rejected messages

### Consequences
- Harmonizer must reject bad messages and log clearly
- Need monitoring for rejected messages

---

## ADR-WP5-03: DB Idempotency Enforced with Unique Index

### Status
Accepted

### Context
Need to prevent duplicate rows from replay scenarios.

### Decision
Prevent duplicates using unique constraint and upsert strategy.

### Rationale
- Experiments are often re-run
- Replay should be safe
- Consistent with Kafka key strategy

### Implementation
- Unique index: `(experiment_id, entity_id, metric_name, ts)`
- INSERT ... ON CONFLICT DO UPDATE

### Consequences
- Re-running pipeline is safe
- Need to use upsert, not plain insert

---

## ADR-WP6-01: Grafana Provisioning as Code

### Status
Accepted

### Context
Need to manage Grafana configuration reproducibly.

### Decision
Datasource and dashboards are versioned in repo via provisioning mounts.

### Rationale
- Reproducible labs
- Easy onboarding
- Version controlled changes
- No manual UI configuration needed

### Implementation
- Provisioning at `clab/configs/grafana/provisioning/`
- Dashboards at `clab/configs/grafana/dashboards/`
- Read-only bind mounts

### Consequences
- Provisioning YAML must be valid
- Only one default datasource per organization
- Dashboard JSON changes tracked in git

---

## ADR-WP7.5-01: Counter-Based Delivery Confirmation

### Status
Accepted

### Context
During WP7.5 MLO experiments, 1 of 3 experiments lost data. Root cause analysis revealed line 123 in `exporter.py` saves file offset state BEFORE Kafka confirms delivery.

**The bug:**
```python
producer.produce(...)  # Line 114 - async enqueue
producer.poll(0)       # Line 120 - process 0+ callbacks
save_offset(...)       # Line 123 - BUG! Saves before delivery confirmed
```

**Result:** If Kafka is down or topic missing, message fails but offset already saved → permanent data loss.

**Previous approaches that FAILED:**
- `min(confirmed_offsets)` → causes infinite replays (stays at first offset)
- `max(confirmed_offsets)` → skips gaps (data loss on out-of-order callbacks)
- Saving in callback → async unsafe, race conditions
- Keying by Kafka message key → duplicate keys corrupt tracking

### Decision
Use simple counter-based approach: count messages sent vs. confirmed, save final file position only after ALL messages confirmed.

### Rationale
**Why counters work:**
1. **Simple verification:** `confirmed_count == total_sent` (all-or-nothing)
2. **No infinite replays:** Save `f.tell()` (end of file position), next run resumes correctly
3. **No gaps:** All messages must confirm before saving state
4. **No duplicate tracking issues:** Just counting totals, not tracking individual offsets
5. **Thread-safe:** Counter increment is atomic, only main thread writes state file
6. **File is small:** 260 lines process in <1 second, no need for complex incremental processing

**The fix is simple because the problem is simple:**
- Read entire file from saved position to end
- Send all messages with delivery callback
- Callback increments `confirmed_count` on success, logs errors
- Wait for all deliveries: `producer.flush(timeout=30.0)`
- Verify: `confirmed_count == total_sent` and no errors
- Save `f.tell()` (final file position) only if all succeeded
- Next run: seek to saved position, continue reading

### Implementation
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
    print(f"Delivery failed: {confirmed_count}/{total_sent} confirmed")
    sys.exit(1)  # Don't save state!

# All messages delivered successfully
save_offset(state, TELEMETRY_FILE, final_offset)
```

**File modified:** `telemetry/exporters/ns3_file_exporter/exporter.py` (lines 74-130)

### Consequences
- **At-least-once semantics:** On failure, entire file replays from last saved position
- **Database handles duplicates:** Unique index `(experiment_id, entity_id, metric_name, ts)` prevents duplicate rows
- **Zero data loss:** State only saved after confirmed delivery of ALL messages
- **Simple to reason about:** Binary success/failure (all or nothing)
- **Fast enough:** 260-line file processes in <1 second, full replay is acceptable
- **No complex offset tracking:** File position is single number, not per-message state

---

## ADR-WP7.5-02: Topic Pre-Creation and Health Checks

### Status
Accepted

### Context
Exporter silently fails when Kafka topic doesn't exist. Messages enqueue successfully (no error from `producer.produce()`), but delivery callbacks never arrive because topic is missing. Exporter waits in `flush()` until timeout, then exits with "0/260 confirmed" error message.

**Problem:** Silent failure wastes time (30+ seconds timeout), provides unclear error, and requires manual debugging to discover missing topic.

### Decision
Check topic existence on startup using AdminClient. Fail fast with clear error message if topic missing.

### Rationale
**Benefits of pre-flight check:**
1. **Clear error messages:** "Topic 'wifi7.telemetry.v0_1' does not exist" vs "0/260 confirmed"
2. **Faster debugging:** Fail in <1 second vs 30+ second timeout
3. **Prevents wasted CPU:** Don't read file or enqueue messages if topic missing
4. **Explicit dependencies:** Makes Kafka topic requirement visible
5. **Better UX:** Clear actionable error for operator

**Why not auto-create topics:**
- Wrong partition count or replication factor could be set
- Topic configuration should be intentional (managed by `make kafka-init`)
- Explicit is better than implicit for infrastructure dependencies

### Implementation
```python
from confluent_kafka.admin import AdminClient

def check_topic_exists(bootstrap_servers, topic_name, timeout=10.0):
    admin = AdminClient({'bootstrap.servers': bootstrap_servers})
    metadata = admin.list_topics(timeout=timeout)

    if topic_name not in metadata.topics:
        print(f"ERROR: Topic '{topic_name}' does not exist")
        print(f"Create it with: make kafka-init")
        sys.exit(1)

    print(f"Topic '{topic_name}' exists ✓")

# Call at start of main()
check_topic_exists(KAFKA_BROKERS, KAFKA_TOPIC)
```

**Makefile target added:**
```makefile
kafka-init:
	docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
	  rpk topic create wifi7.telemetry.v0_1 -p 1 -r 1
```

### Consequences
- **Requires manual topic creation:** Operator must run `make kafka-init` before first exporter run
- **Faster failure:** 1 second vs 30+ second timeout
- **Better error messages:** Clear indication of missing topic
- **Additional dependency:** AdminClient for health checks (already in confluent-kafka library)
- **Documented in QUICK-REFERENCE.md:** Common issues section updated

---

## ADR-WP7.5-03: At-Least-Once Delivery Semantics

### Status
Accepted

### Context
Need to choose delivery semantics for exporter-to-database pipeline. Options:
1. **At-most-once:** Send message, don't wait for confirmation (risk: data loss)
2. **At-least-once:** Wait for confirmation, replay on failure (risk: duplicates)
3. **Exactly-once:** Distributed transaction across Kafka and DB (complex, overhead)

**Current state:** Database has unique index `(experiment_id, entity_id, metric_name, ts)` preventing duplicate rows.

**File characteristics:**
- Small (260 lines, 50 KB)
- Processes in <1 second
- Re-runs are cheap

### Decision
Use at-least-once delivery semantics with database deduplication via unique index.

### Rationale
**Why at-least-once:**
1. **Zero data loss:** Better to replay than to lose data
2. **Simple implementation:** Just wait for all confirmations
3. **Database already handles duplicates:** Unique index rejects duplicates automatically
4. **Fast enough to replay:** 260-line file processes in <1 second
5. **No distributed transactions:** Avoid complexity of exactly-once semantics

**Why not exactly-once:**
- Requires Kafka transactions + database coordination
- Significant complexity for minimal benefit
- Database unique index already provides deduplication
- File replay is fast (<1 second), overhead is negligible

**Why not at-most-once:**
- Data loss is unacceptable for research data
- Lost samples corrupt analysis results
- Cannot tolerate missing metrics

### Implementation
**Exporter behavior:**
```python
# Send all messages
for line in file:
    producer.produce(..., callback=delivery_report)
    total_sent += 1

# Wait for ALL confirmations
producer.flush(timeout=30.0)

# Verify all succeeded
if confirmed_count != total_sent:
    sys.exit(1)  # Don't save state → next run replays

# All confirmed → save state
save_offset(state, TELEMETRY_FILE, final_offset)
```

**Database deduplication:**
```sql
CREATE UNIQUE INDEX idx_metrics_unique
ON metrics (experiment_id, entity_id, metric_name, ts);

INSERT INTO metrics (...) VALUES (...)
ON CONFLICT (experiment_id, entity_id, metric_name, ts)
DO UPDATE SET value = EXCLUDED.value;  -- Idempotent upsert
```

**Result:** If exporter crashes after Kafka delivery but before saving state:
1. Next run replays entire file
2. Kafka receives duplicate messages
3. Harmonizer inserts duplicate rows
4. Database rejects duplicates via unique constraint
5. Final state: All messages delivered, no data loss, no duplicates

### Consequences
- **Possible replays:** On failure, entire file replays from last saved position
- **Database receives duplicates:** Harmonizer inserts all messages (including replays)
- **Unique constraint handles it:** Database automatically deduplicates
- **Log noise:** Duplicate key violations appear in harmonizer logs (expected, not errors)
- **No data loss:** Guaranteed delivery of all messages
- **Simple to reason about:** Binary success/failure (all or nothing)
- **Performance acceptable:** 260-message replay takes <1 second
