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

### WP12 (GCN v3 Multi-AP Training)
- [ADR-WP12-01](#adr-wp12-01-sim_time80s-for-v3-training-data): SIM_TIME=80s for v3 training data
- [ADR-WP12-02](#adr-wp12-02-nap1-4-only-for-v300-training): nap1-4 only for v3.0.0 training
- [ADR-WP12-03](#adr-wp12-03-17th-feature-for-segment-length-conditioning): 17th feature for segment-length conditioning

### WP13 (GCN v4 Dynamic Generalization)
- [ADR-WP13-01](#adr-wp13-01-30-threshold-for-dynamic-segment-labeling): 30% threshold for dynamic segment labeling
- [ADR-WP13-02](#adr-wp13-02-wider-deeper-gcn-architecture-for-v4): Wider/deeper GCN architecture for v4
- [ADR-WP13-03](#adr-wp13-03-strict-seed-pool-partitioning-for-no-leakage): Strict seed pool partitioning for no-leakage
- [ADR-WP13-04](#adr-wp13-04-nap5-6-held-out-as-topology-generalization-test): nap5-6 held out as topology generalization test
- [ADR-WP13-05](#adr-wp13-05-bias-diversity-in-training-set): Bias diversity in training set
- [ADR-WP13-06](#adr-wp13-06-static-dynamic-folder-separation): Static/Dynamic folder separation
- [ADR-WP13-07](#adr-wp13-07-synthetic-stitching-for-dynamic-training-data): Synthetic stitching for dynamic training data

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

---

## ADR-WP12-01: SIM_TIME=80s for v3 Training Data

### Status
Accepted

### Date
2026-03-13

### Context
WP12 required collecting training data across multiple AP counts (nap1-6). At 300s simulation time, a nap4 run takes over 2.5 hours. Running 72 simulations (nap1-6, 4 seeds, 3 scenarios) at 300s would require 7.5+ days of sequential compute, or over 22 hours even with 8 parallel cores.

### Decision
Use SIM_TIME=80s for all v3 training data collection.

### Rationale
- 80s produces ~800 windows per file (80s / 0.1s per window), which is sufficient for training
- Sliding window segmentation with stride=64 gives 9 segments per file at 256-window length — 3x more than non-overlapping, compensating for the shorter run
- At SIM_TIME=80s, nap4 runs take ~40 minutes; nap1 runs take ~4 minutes
- Total wall-clock time with 8 cores: ~36-38 minutes for 48 files (nap1-4)
- Sufficient segment diversity: 48 files × (9+6+12+25) segments = ~2,496 training segments

### Implementation
All v3 data collected at SIM_TIME=80s, stored in `twin/gnn/training_data/v3/`. The Makefile default is `SIM_TIME=80` for `gcn-collect-data`.

### Consequences

#### Positive
- Practical wall-clock time for data collection
- Sufficient window budget for all four segment lengths
- Allows iteration on training without waiting days for data

#### Negative
- 80s captures fewer unique traffic patterns than 300s
- Overlapping 256-window segments share some windows (not fully independent)

#### Mitigations
- Overlapping segments from the same file are kept in the same train/val/test split partition (split by file, not by segment) to prevent leakage
- 4 different seeds per config provides some diversity
- v3.1.0 can add nap5/6 with SIM_TIME=30s for even faster collection

### Related
- WP12: GCN v3 multi-AP training
- ADR-WP12-02: nap1-4 only for v3.0.0

---

## ADR-WP12-02: nap1-4 Only for v3.0.0 Training

### Status
Accepted

### Date
2026-03-13

### Context
The original WP12 plan targeted nap1-6 (1 to 6 access points) to cover a wide range of multi-AP topologies. During data collection, nap5 runs were measured at approximately 2.5 hours per simulation at SIM_TIME=80s. Collecting nap5/6 data (12 configs x 4 seeds x 3 scenarios = 144 runs) would require 15+ days of sequential compute, or approximately 45 hours with 8 parallel cores — not practical for a single session.

### Decision
Train v3.0.0 on nap1-4 only. Defer nap5/6 to v3.1.0.

### Rationale
- nap1-4 provides meaningful AP-count diversity (1, 2, 3, 4 access points)
- nap4 is already a demanding topology (32 stations, significant contention)
- v3.0.0 with nap1-4 significantly extends v2 (nap1 only) to cover the most common deployment sizes
- Adding nap5/6 later (v3.1.0) is straightforward: just add data and retrain
- nap5/6 strategy for v3.1.0: use SIM_TIME=30s to reduce per-run time from ~2.5h to ~45min; NCPU=6 parallelisation gives ~9h wall-clock for 12 runs

### Implementation
`collect_v3_data.sh` and the `NAP_NSTA` array cover nap1-4 for v3.0.0 collection. The nap5-6 entries are commented out with a note pointing to v3.1.0.

### Consequences

#### Positive
- v3.0.0 deliverable in one session rather than weeks
- Model covers the most common enterprise Wi-Fi AP counts
- Strong generalisation across nap1-4 verified by test results (F1=0.9978)

#### Negative
- Model may underperform on nap5/6 topologies (outside training distribution)
- Dashboard will show no warning when user selects nAp=5 or nAp=6 with v3.0.0

#### Mitigations
- Dashboard shows "trained on nap1-4" note for nAp selections above 4 (planned for v3.1.0 UI update)
- v3.1.0 adds nap5/6 with SIM_TIME=30s strategy

### Related
- WP12: GCN v3 multi-AP training
- ADR-WP12-01: SIM_TIME=80s for training data

---

## ADR-WP12-03: 17th Feature for Segment-Length Conditioning

### Status
Accepted

### Date
2026-03-13

### Context
GCN v3 needs to support multiple segment window lengths (32, 64, 128, 256) within a single model. The GCN architecture (global_mean_pool) is topology-agnostic — it can process graphs of any node count — but the StandardScaler fit on 256-window segments produces out-of-distribution z-scores for shorter segments because delta features accumulate over fewer windows (smaller absolute values).

Options considered:
1. Train four separate models (one per segment length): simple but quadruples inference infrastructure
2. Train a unified model on all segment lengths but add a conditioning feature: single model, minimal architectural change
3. Encode segment length in Kafka message headers and use a routing layer: complex, requires multi-head architecture

### Decision
Append `log2(segment_length) / 8.0` as a constant 17th feature to every node's feature vector. The GCN's input dimension changes from 16 to 17. All other architecture choices (2 GCN layers, hidden=64, global mean pool, MLP head) are unchanged.

### Rationale
- A single 17th scalar signal is sufficient for the GCN to learn scale-dependent patterns
- `log2(L)/8.0` maps [32,64,128,256] to [0.625, 0.75, 0.875, 1.0] — evenly spaced in log space
- The StandardScaler learns the correct normalisation for this feature from the training distribution
- Single model simplifies deployment: no routing, no separate inference endpoints
- Minimal impact on inference latency (one extra scalar per node)

### Implementation
`preprocessing.py` appends the feature during training: `np.hstack([features, seg_len_feature])`.

`feature_processor.py` appends the same feature at inference time after reading `segment_length` from the windowed feature message. The v2 backward compatibility path is triggered when `scaler.n_features_in_ == 16` (v2 scaler) — in that case the 17th feature and multi-AP normalisation are skipped.

`config.py` sets `in_channels=17`. v2 models remain in the registry with their original 16-channel config and are not affected.

### Consequences

#### Positive
- Single model handles all four window sizes
- Simple to reason about: one constant per graph
- v2 backward compatibility preserved in `feature_processor.py`
- No change to GCN graph structure or edge construction

#### Negative
- v2 and v3 model configs are incompatible (`in_channels` differs)
- The 17th feature is constant across all nodes in a segment — a graph-level signal masquerading as a node feature

#### Mitigations
- Registry version check ensures the correct `in_channels` is used for each model
- Scaler dimension check (`n_features_in_`) provides automatic v2/v3 routing at inference time

### Related
- WP12: GCN v3 multi-AP training
- ADR-WP12-01: SIM_TIME=80s choice
- ADR-WP12-02: nap1-4 scope

---

## ADR-WP13-01: 30% Threshold for Dynamic Segment Labeling

### Status
Accepted

### Date
2026-03-15

### Context
GCN v4 introduces per-segment labeling for dynamic files (files where `bias` changes mid-simulation). The original plan specified 50% majority vote: a segment is labeled Attack if more than half of its windows have `bias != 0`. However, a 50% threshold means that a segment with, say, 31% attack windows would be labeled Normal even though an attack is clearly underway in a meaningful fraction of the observation window.

### Decision
Use a 30% threshold: label a segment as Attack if more than 30% of its windows have `bias != 0`.

### Rationale
- A 30% threshold is more sensitive to early-onset attacks within a transition segment
- In practice, transition segments often have 1/3 to 2/3 attack windows; a 30% threshold reliably labels these as Attack
- Erring on the side of attack detection (lower false-negative rate) is preferable for a security system
- Pure normal segments (0% attack windows) are still labeled Normal; pure attack segments (100%) are still labeled Attack

### Implementation
`twin/gnn/detector/gcn_src/data/dataset_v4.py` implements `get_label_from_segment_dynamic(segment, threshold=0.30)`.

### Consequences

#### Positive
- More sensitive to early-phase attacks in transition segments
- Lower false-negative rate for transition segments
- Pure segments unaffected (0% or 100% is always below or above 30%)

#### Negative
- Segments with 30%-50% attack windows are labeled Attack; under 50% majority this would be Normal
- Slightly higher false-positive rate for segments that are mostly normal with a short attack burst

#### Mitigations
- Class weights in training (`use_class_weights: true`) correct for any class imbalance introduced
- Threshold can be adjusted as a hyperparameter if evaluation reveals FP-rate issues

### Related
- WP13: GCN v4 dynamic generalization
- ADR-WP13-06: Static/Dynamic folder separation

---

## ADR-WP13-02: Wider/Deeper GCN Architecture for v4

### Status
Accepted

### Date
2026-03-15

### Context
GCN v3.0.0 uses `hidden_channels=64` and `num_layers=2`. v4 is trained on dynamic data with higher variance (phase transitions create more complex temporal patterns than static uniform-bias files). The question is whether to increase model capacity or keep v3 architecture unchanged.

### Decision
Increase to `hidden_channels=128` and `num_layers=3` for v4.0.0. Keep `in_channels=17` (backward compatible feature set).

### Rationale
- Dynamic segments have more complex, non-uniform feature distributions than static segments
- A wider network (128 vs 64) can represent more diverse temporal patterns in one embedding
- A third GCN layer provides more message-passing rounds, giving the model wider graph context
- Residual connections in the architecture mitigate oversmoothing from the extra layer
- The 16x increase in training data (2,878 files vs 48 files) justifies more capacity

### Implementation
`twin/gnn/trainer/training_v4.yaml` sets `hidden_channels: 128`, `num_layers: 3`, `dropout: 0.4` (vs v3: 64, 2, 0.3).
`twin/gnn/detector/gcn_src/training/train_v4.py` uses these settings.

### Consequences

#### Positive
- More capacity for complex phase-transition patterns
- 3-layer message passing gives richer graph representations
- Higher dropout (0.4 vs 0.3) prevents overfitting on the larger dataset

#### Negative
- Larger model: inference latency increases marginally (hidden=128 vs 64)
- v4 checkpoint is not backward compatible with v3 registry entries (different architecture)

#### Mitigations
- Registry versioning (`current` symlink) ensures only one model serves at a time
- Inference latency increase is negligible for the batch sizes used in production

### Related
- WP13: GCN v4 dynamic generalization
- WP12: ADR-WP12-03 (17th feature; in_channels=17 unchanged in v4)

---

## ADR-WP13-03: Strict Seed Pool Partitioning for No-Leakage

### Status
Accepted

### Date
2026-03-15

### Context
GCN v3 used seeds 42/43/44/45 for training and a random 80/20 file split for validation. This approach risks leakage when the same seed appears in both train and val sets (different bias values, but correlated noise patterns from the simulation RNG). v4 requires stricter controls because dynamic stitching creates files that inherit seed-correlated patterns from their static sources.

### Decision
Use three strictly disjoint seed pools with no overlap:
- Train: 42, 111, 123, 222, 321, 333, 456, 654, 789, 987 (10 seeds)
- Val: 444, 777, 888 (3 seeds)
- Test: 555, 999, 1234 (3 seeds)

No file from one pool may appear in any other pool, including synthetically stitched files.

### Rationale
- Prevents simulation-RNG correlation leakage between splits
- Synthetic stitching inherits seed identity from source files; same seed pool guarantee means stitched dynamic files from train seeds only appear in the train split
- Enables genuine generalization measurement: test F1 measures performance on seeds the model has never seen
- Phase patterns (dynamic scenarios) are also split: T-group patterns only in test

### Implementation
`sim/ns3/scenario/collect_v4_static_data.sh` enforces seed assignments per split.
`twin/gnn/stitch_dynamic.py` only stitches files within the same split.
`twin/gnn/detector/gcn_src/data/dataset_v4.py`'s `load_v4_files()` reads from pre-partitioned folders.

### Consequences

#### Positive
- True generalization measurement at test time
- No seed-correlation leakage between train, val, and test
- Dynamic stitching is leakage-safe by construction

#### Negative
- Smaller train pool (10 seeds) than would be available without partitioning
- Cannot use random splits; must maintain folder structure discipline

#### Mitigations
- 10 train seeds provide sufficient diversity for the training set
- Folder structure makes the split explicit and auditable

### Related
- WP13: GCN v4 dynamic generalization
- ADR-WP13-07: Synthetic stitching

---

## ADR-WP13-04: nap5-6 Held Out as Topology Generalization Test

### Status
Accepted

### Date
2026-03-15

### Context
GCN v3 was trained on nap1-4 only (nap5-6 deferred due to simulation time; ADR-WP12-02). v4 continues using nap1-4 for training data because nap5+ run times remain impractical. However, v4 adds a topology generalization evaluation on nap5-6 using test-split data to measure zero-shot performance.

### Decision
Train v4 on nap1-4 only. Include nap5/6 runs in the test split (for topology generalization measurement) but never in train or val.

### Rationale
- nap5 runs take approximately 2.5 hours each at SIM_TIME=80s; adding nap5/6 to training is impractical
- Holding out nap5-6 from training creates a valuable zero-shot topology generalization evaluation
- Expected v4 performance on nap5-6: F1 >= 0.92 (since multi-AP normalisation is topology-agnostic)
- This directly answers the research question: "Does the model generalise to unseen network sizes?"

### Implementation
`sim/ns3/scenario/collect_v4_static_data.sh` limits AP/STA pairs to nap1-4 for train and val splits.
Test set includes nap5/6 runs (planned; not yet collected as of 2026-03-15).

### Consequences

#### Positive
- Topology generalization evaluated rigorously on held-out configurations
- Addresses the main limitation of v3.0.0 (no nap5/6 coverage)

#### Negative
- nap5/6 not in training; model may underperform on these topologies compared to nap1-4
- Test collection for nap5/6 not yet done (pending)

#### Mitigations
- Multi-AP normalisation (dividing by num_ap/num_sta) is the primary mechanism for topology generalization
- If topology generalization F1 is below target, nap5/6 can be added to v4.1.0 training data using SIM_TIME=30s (45min per run)

### Related
- WP12: ADR-WP12-02 (nap1-4 only for v3.0.0)
- WP13: GCN v4 dynamic generalization

---

## ADR-WP13-05: Bias Diversity in Training Set

### Status
Accepted

### Date
2026-03-15

### Context
GCN v3 was trained only on bias=±5000. The 54-experiment evaluation showed v3 detects attacks at bias=1000 (one-fifth of training bias), but it has not been trained to distinguish weak attacks from normal traffic. v4 must generalise across a wider range of attack strengths.

### Decision
Train v4 on three bias levels: ±1000, ±2000, ±5000 for the static training split. Validation uses ±5000. Test set additionally includes ±500, ±4000 to measure interpolation and boundary performance.

### Rationale
- Including ±1000 and ±2000 in training teaches the model to detect weak attacks, not just strong ones
- ±5000 as the common bias across all splits ensures train/val/test comparability
- Excluding ±500 from training creates a boundary-generalization test
- Excluding ±4000 from training tests interpolation between trained bias values

### Implementation
`sim/ns3/scenario/collect_v4_static_data.sh` hardcodes `TRAIN_BIASES=(1000 2000 5000)`, `VAL_BIASES=(5000)`, `TEST_BIASES=(500 1000 2000 4000 5000)`.

### Consequences

#### Positive
- Model trained to detect both weak and strong attacks
- Validation remains simple (single bias)
- Test set covers interpolation, boundary, and extrapolation points

#### Negative
- More static training files required (3 bias levels vs 1 for v3)
- Imbalanced attack-to-normal ratio in static training data (165 Attack vs 28 Normal files)

#### Mitigations
- `use_class_weights: true` in training config corrects for class imbalance
- Normal files come from bias=0 simulations (no need to vary bias for normal class)

### Related
- WP13: GCN v4 dynamic generalization
- ADR-WP13-03: Seed pool partitioning

---

## ADR-WP13-06: Static/Dynamic Folder Separation

### Status
Accepted

### Date
2026-03-15

### Context
v4 training data combines static files (uniform bias throughout) and dynamic files (bias changes mid-simulation). These require different labeling strategies: static files use file-level labels; dynamic files require per-segment majority-vote labeling. The question is how to distinguish them at load time.

Options:
1. Filename convention: embed `_dynamic_` in filename, parse at load time
2. Separate folders: `Static/` and `Dynamic/` subdirectories within each split
3. Metadata sidecar: JSON file per data file indicating labeling strategy

### Decision
Use separate `Static/{Normal,Attack}/` and `Dynamic/` subdirectories within each split folder. The dataset loader detects the parent folder name to select the labeling strategy.

### Rationale
- Folder structure is explicit and auditable without filename parsing
- Static Normal/Attack separation preserves existing v3 labeling convention
- Dynamic folder avoids needing a separate `Normal/Attack` distinction at the file level (label is per-segment)
- No additional metadata files needed
- Works cleanly with `load_v4_files()` which walks the pre-partitioned directory tree

### Implementation
```
twin/gnn/training_data/v4/
  train/
    Static/Normal/   ← file-level label=0
    Static/Attack/   ← file-level label=1
    Dynamic/         ← per-segment majority-vote label
  val/  (same structure)
  test/ (same structure)
```
`dataset_v4.py` checks `'Static/Normal' in filepath`, `'Static/Attack' in filepath`, or `'Dynamic' in filepath` to select labeling.

### Consequences

#### Positive
- Clear labeling strategy per file, determined by folder membership
- No filename parsing needed
- Folder structure is self-documenting

#### Negative
- Must maintain folder discipline when adding new files
- File accidentally placed in wrong folder gets wrong labeling strategy

#### Mitigations
- Collection scripts write directly to the correct subdirectory
- `stitch_dynamic.py` only writes to `Dynamic/` folders

### Related
- WP13: GCN v4 dynamic generalization
- ADR-WP13-01: 30% threshold for dynamic labeling
- ADR-WP13-07: Synthetic stitching

---

## ADR-WP13-07: Synthetic Stitching for Dynamic Training Data

### Status
Accepted

### Date
2026-03-15

### Context
The original v4 plan required running 528+ NS-3 dynamic simulations to generate dynamic training data (each with a unique phase pattern, AP count, seed, and duration). At ~30-60s per simulation, this would take approximately 85 minutes with 8 parallel cores but requires all combinations to be explicitly simulated.

An alternative approach: synthesize dynamic files by concatenating window slices from existing static source files. Each "phase" in a dynamic file is represented by a slice of 400 windows taken from the middle of a 800-window static source file with the matching bias value.

### Decision
Generate dynamic training data synthetically by stitching together static source files using `twin/gnn/stitch_dynamic.py`. Each phase is 400 windows from windows[200:600] of a matching static source file. Phases are offset [200, 0, 400] to avoid reusing the same source windows across phases when all phases share the same source seed.

### Rationale
- Produces far more dynamic training files than NS-3 simulation alone: 1,852 train files vs 528 planned
- No additional simulation time required beyond already-collected static data
- Phase transitions are reproduced faithfully: the `bias` field in each window reflects the source file's bias, creating realistic attack-onset and attack-offset patterns within a single stitched file
- No-leakage guarantee: source files are only stitched within the split they belong to (train seeds only stitched into train dynamic files)
- Skip-if-exists logic makes the stitching resumable

### Implementation
`twin/gnn/stitch_dynamic.py`:
- Phase slicing: `source_windows[offset + 200 : offset + 600]` (400 windows per phase)
- Phase offsets: [200, 0, 400] to differentiate source windows across phases of the same seed/bias
- 30 phase patterns (groups A/B/C/D/E/T) as defined in the phase pattern catalogue
- Per-split output to `twin/gnn/training_data/v4/{split}/Dynamic/`
- Bias variants for training patterns (_b1000, _b2000 suffixes)

### Consequences

#### Positive
- 3.5x more dynamic training files than originally planned (1,852 vs 528)
- Faster to generate (stitching is a file I/O operation, not a simulation)
- Dataset can be regenerated from existing static source files at any time
- Consistent with no-leakage requirements

#### Negative
- Stitched transitions are artificial: adjacent phases share no simulation state (no gradual backoff reset, no hidden Markov state across the phase boundary)
- The model trained on stitched data may not generalise perfectly to real NS-3 dynamic simulations where the underlying simulation state transitions gradually
- Requires existing static source files to be present before stitching can run

#### Mitigations
- Dynamic evaluation benchmark uses real NS-3 dynamic runs (not stitched files), so the model is evaluated on authentic transition data
- If stitching-trained model underperforms on authentic dynamic runs, NS-3 simulated dynamic data can be collected and added to the training set
- `stitch_dynamic.py --dry-run` verifies source file availability before generating

### Related
- WP13: GCN v4 dynamic generalization
- ADR-WP13-03: Strict seed pool partitioning
- ADR-WP13-06: Static/Dynamic folder separation
