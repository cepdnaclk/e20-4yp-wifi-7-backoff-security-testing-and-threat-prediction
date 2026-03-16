# Implementation Plan: WP13 — Closed-Loop Policy Actuation

## Date
2026-03-13

## Objective
Close the detection loop by adding a Policy Engine service that consumes GCN detection
events from the `wifi7.security.gcn_predictions.v1` Kafka topic, applies configurable
severity and cooldown rules, and triggers simulated mitigation responses including
Kafka alerts, TimescaleDB logging, and dashboard notifications. No hardware or live
RF actuation is required; all actuation is logged as "would execute" with a simulated
channel-steering or backoff-reset command recorded alongside a real alert.

## Background
WP8–WP12 delivered a working detection pipeline: NS-3 scenarios produce telemetry,
the GCN detector classifies each 256-window segment as Normal (0) or Attack (1) with
99.73% accuracy, and writes results to `gcn_predictions`. The `security/` directory
already has stub subdirectories `actuation/`, `detector/`, and `policy/` waiting to
be populated. WP13 populates `security/policy/` and `security/actuation/` and wires
them into the existing compose stack.

---

## Architecture Diagram

```
                 Kafka: wifi7.security.gcn_predictions.v1
                                │
                                ▼
                   ┌─────────────────────────┐
                   │      Policy Engine       │
                   │  (security/policy/)      │
                   │                          │
                   │  ┌───────────────────┐   │
                   │  │  Severity Scorer  │   │
                   │  │  (conf, run rate) │   │
                   │  └────────┬──────────┘   │
                   │           │              │
                   │  ┌────────▼──────────┐   │
                   │  │  Policy Evaluator │   │
                   │  │  (thresholds,     │   │
                   │  │   cooldown, TTL)  │   │
                   │  └────────┬──────────┘   │
                   │           │              │
                   │  ┌────────▼──────────┐   │
                   │  │ Actuation Planner │   │
                   │  │ (decide action)   │   │
                   │  └────────┬──────────┘   │
                   └───────────┼──────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                 ▼
  Kafka:               TimescaleDB          Health API
  wifi7.security.      mitigations          (port 8082)
  mitigations.v1       table
              │                │
              ▼                ▼
  Dashboard WebSocket    Dashboard API
  (live alert panel)     /api/mitigations
```

---

## `gcn.detections` Message Format (Confirmed from Source)

The GCN detector publishes to topic `wifi7.security.gcn_predictions.v1` with this
JSON envelope (produced by `inference_engine.py`, lines 128–143):

```json
{
  "experiment_id": "20260313-1400-mlo-positive-42",
  "entity_id":     "network",
  "segment_id":    "20260313-1400-mlo-positive-42_network_seg0001",
  "window_start_idx": 0,
  "window_end_idx":   255,
  "ts_start":     "2026-03-13T14:00:00.000000+00:00",
  "ts_end":       "2026-03-13T14:00:25.600000+00:00",
  "prediction":   1,
  "confidence":   0.9973,
  "probabilities": [0.0027, 0.9973],
  "model_version": "v2.1.0",
  "model_path":   "/app/registry/current",
  "inference_time_ms": 12.4
}
```

Key fields the Policy Engine will use:
- `prediction` — 1 = attack, 0 = normal
- `confidence` — p_attack (float 0–1)
- `experiment_id` — carries scenario context (positive/negative/normal in name)
- `ts_start` / `ts_end` — segment time window
- `entity_id` — affected network entity

---

## Prerequisites

- [ ] WP8–WP12 pipeline is running and healthy (`docker ps | grep ndt`)
- [ ] `wifi7.security.gcn_predictions.v1` topic exists (`make kafka-status`)
- [ ] `udr-db` TimescaleDB container is healthy (port 5432 accessible)
- [ ] `clab-mgmt` Docker network exists (created by containerlab)
- [ ] Python 3.11 available for container builds
- [ ] `docker-compose.pipeline.yml` is the live compose file

---

## Files to Create or Modify

| File | Action | Purpose |
|------|--------|---------|
| `security/policy/policy_engine.py` | Create | Main consumer/dispatcher service |
| `security/policy/severity_scorer.py` | Create | Converts confidence + run-rate to severity level |
| `security/policy/policy_evaluator.py` | Create | Applies thresholds, cooldown, TTL rules |
| `security/policy/actuation_planner.py` | Create | Maps severity + experiment context to action list |
| `security/policy/config.yaml` | Create | Policy thresholds, cooldown, Kafka, DB settings |
| `security/policy/requirements.txt` | Create | confluent-kafka, psycopg2-binary, pyyaml, pydantic |
| `security/policy/Dockerfile` | Create | python:3.11-slim image, non-root user |
| `security/actuation/actuator.py` | Create | Executes simulated actuation commands |
| `security/actuation/channel_steer.py` | Create | Simulated channel-steering logic |
| `security/actuation/backoff_reset.py` | Create | Simulated CW reset logic |
| `clab/configs/udr-db/initdb/004_mitigations_schema.sql` | Create | `mitigations` DB table + hypertable |
| `docker-compose.pipeline.yml` | Modify | Add `policy-engine` service |
| `Makefile` | Modify | Add `policy-*` and `kafka-init-policy` targets |
| `dashboard/app/backend/api/mitigations.py` | Create | FastAPI router for `/api/mitigations` |
| `dashboard/app/backend/db/queries.py` | Modify | Add mitigation query functions |
| `dashboard/app/backend/main.py` | Modify | Register `/api/mitigations` router |
| `dashboard/app/frontend/src/sections/MitigationSection.tsx` | Create | React section for active mitigations panel |
| `dashboard/app/frontend/src/hooks/useMitigations.ts` | Create | React hooks for mitigation endpoints |
| `dashboard/app/frontend/src/components/layout/Sidebar.tsx` | Modify | Add "Mitigations" nav item |
| `dashboard/app/frontend/src/App.tsx` | Modify | Wire MitigationSection with `'mitigations'` section ID |

---

## Implementation Steps

### Phase 1: DB Schema (Day 1)

**Step 1.1 — Create `mitigations` table schema**

Create `clab/configs/udr-db/initdb/004_mitigations_schema.sql`.

Schema design:
```sql
CREATE TABLE IF NOT EXISTS public.mitigations (
    id BIGSERIAL PRIMARY KEY,

    -- Source detection
    experiment_id   TEXT NOT NULL,
    entity_id       TEXT NOT NULL,
    segment_id      TEXT NOT NULL,
    detection_ts    TIMESTAMPTZ NOT NULL,   -- ts_start of triggering segment
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    -- Severity
    severity        TEXT NOT NULL,          -- 'low', 'medium', 'high', 'critical'
    severity_score  DOUBLE PRECISION NOT NULL,

    -- Policy decision
    action_taken    TEXT NOT NULL,          -- 'channel_steer', 'backoff_reset', 'alert_only', 'suppressed'
    policy_rule     TEXT NOT NULL,          -- which rule triggered (e.g. 'sustained_high')
    cooldown_active BOOLEAN DEFAULT FALSE,  -- suppressed due to cooldown?

    -- Actuation detail
    action_payload  JSONB,                  -- simulated command details
    action_result   TEXT,                   -- 'simulated', 'skipped', 'error'

    -- GCN source data
    gcn_confidence  DOUBLE PRECISION,
    gcn_prediction  INTEGER,
    model_version   TEXT,

    -- Constraints
    CONSTRAINT severity_valid CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT prediction_valid CHECK (gcn_prediction IN (0, 1))
);

-- Indexes
CREATE INDEX IF NOT EXISTS mit_exp_ts_idx ON public.mitigations (experiment_id, created_at DESC);
CREATE INDEX IF NOT EXISTS mit_severity_idx ON public.mitigations (severity, created_at DESC);
CREATE INDEX IF NOT EXISTS mit_action_idx ON public.mitigations (action_taken, created_at DESC);

-- TimescaleDB hypertable
SELECT create_hypertable('mitigations', 'created_at',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day');

-- Grants
GRANT SELECT, INSERT ON public.mitigations TO udr;
GRANT USAGE, SELECT ON SEQUENCE mitigations_id_seq TO udr;
```

Verification: After `make down && make up`, run:
```bash
docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "\d mitigations"
```

**Note:** The `004_mitigations_schema.sql` file is only auto-applied when the DB
container is created fresh. If the DB already exists, apply manually:
```bash
docker exec -i clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr < clab/configs/udr-db/initdb/004_mitigations_schema.sql
```

---

### Phase 2: Policy Engine Service (Days 1–2)

**Step 2.1 — Severity Scorer (`security/policy/severity_scorer.py`)**

This module converts a detection event into a severity level. It maintains a
short sliding window of recent predictions per `(experiment_id, entity_id)` to
compute a sustained attack rate.

Design:
- Input: a GCN prediction dict (as received from Kafka)
- State: in-memory deque of the last N predictions per entity key, with timestamps
- Outputs: `severity` string and `severity_score` float

Severity mapping (configurable via `config.yaml`):
```
severity_score = 0.4 * confidence + 0.6 * recent_attack_rate

score >= 0.85  → 'critical'
score >= 0.70  → 'high'
score >= 0.50  → 'medium'
score >= 0.30  → 'low'
score <  0.30  → None (below action threshold, no mitigation)
```

Where `recent_attack_rate` = fraction of last 10 predictions that were attacks
for the same `(experiment_id, entity_id)` pair. This prevents single-segment
false positives from triggering high-severity actions.

**Step 2.2 — Policy Evaluator (`security/policy/policy_evaluator.py`)**

Enforces cooldown and deduplication rules:
- Maintains per-entity cooldown state: `{entity_key: last_action_ts}`
- Cooldown period is configurable per severity level in `config.yaml`
- If `time.time() - last_action_ts < cooldown_seconds[severity]`, sets
  `cooldown_active = True` and returns action `'suppressed'`
- Otherwise returns the evaluated action and updates cooldown state

Cooldown defaults (configurable):
```
critical: 30 seconds
high:     60 seconds
medium:   120 seconds
low:      300 seconds
```

The evaluator also applies a global rate limit: no more than N mitigations per
minute system-wide (prevents runaway logging if every segment triggers).

**Step 2.3 — Actuation Planner (`security/policy/actuation_planner.py`)**

Maps `(severity, experiment_context)` to an ordered list of actuation steps.

Experiment context is derived from `experiment_id` string (same logic as the
dashboard `get_attack_by_type` query):
```
experiment_id contains 'positive' → attack_type = 'backoff_positive'
experiment_id contains 'negative' → attack_type = 'backoff_negative'
otherwise                         → attack_type = 'unknown'
```

Action matrix:
| Severity | Actions |
|----------|---------|
| critical | channel_steer + backoff_reset + alert |
| high     | backoff_reset + alert |
| medium   | alert |
| low      | alert |

Each action generates a payload dict that describes the simulated command. No
real network commands are issued; payloads are logged and stored.

**Step 2.4 — Actuator (`security/actuation/actuator.py`)**

Executes the action list from the planner. Each action type calls a dedicated
handler:

- `channel_steer` → calls `ChannelSteerer.steer(experiment_id, entity_id, payload)`
- `backoff_reset` → calls `BackoffResetter.reset(experiment_id, entity_id, payload)`
- `alert` → always fires (publishes to Kafka `wifi7.security.mitigations.v1` and writes to DB)

**Step 2.5 — Channel Steerer (`security/actuation/channel_steer.py`)**

Simulated only. Generates a payload dict:
```json
{
  "action": "channel_steer",
  "simulated": true,
  "target_entity": "network",
  "reason": "sustained_high_confidence_attack",
  "suggested_link": "link_2",
  "ns3_param_would_be": "--channelOverride=2",
  "note": "In a real deployment this would send a Management Frame to the AP"
}
```
Returns `action_result = 'simulated'`.

**Step 2.6 — Backoff Resetter (`security/actuation/backoff_reset.py`)**

Simulated only. Generates:
```json
{
  "action": "backoff_reset",
  "simulated": true,
  "target_entity": "network",
  "reason": "backoff_manipulation_detected",
  "cw_min_reset_to": 15,
  "cw_max_reset_to": 1023,
  "ns3_param_would_be": "--cwMin=15 --cwMax=1023",
  "note": "In a real deployment this would trigger a STA disassociation + re-association"
}
```
Returns `action_result = 'simulated'`.

**Step 2.7 — Main Policy Engine (`security/policy/policy_engine.py`)**

Structure mirrors `detector.py` exactly — same class pattern, same signal
handling, same Kafka consumer/producer pattern.

Service loop:
1. `consumer.poll(1.0)` on topic `wifi7.security.gcn_predictions.v1`
2. Filter: skip if `prediction == 0` (only process attacks)
3. `SeverityScorer.score(prediction_dict)` → `(severity, score)` or None
4. If severity is None, skip (below threshold)
5. `PolicyEvaluator.evaluate(entity_key, severity)` → `(action, cooldown_active)`
6. If `cooldown_active`, write suppressed record to DB only (no Kafka publish)
7. `ActuationPlanner.plan(severity, experiment_id)` → action list
8. `Actuator.execute(action_list, prediction_dict)` → mitigation record dict
9. Publish mitigation record to `wifi7.security.mitigations.v1`
10. Write mitigation record to `mitigations` table via `psycopg2`
11. Commit Kafka offset

**Step 2.8 — Config file (`security/policy/config.yaml`)**

```yaml
kafka:
  input_topic: wifi7.security.gcn_predictions.v1
  output_topic: wifi7.security.mitigations.v1
  brokers: bus-redpanda:9092
  consumer_group: policy-engine-v1
  auto_offset_reset: latest  # Only react to new events, not replay history

severity:
  window_size: 10            # Number of recent predictions to track per entity
  weights:
    confidence: 0.4
    attack_rate: 0.6
  thresholds:
    critical: 0.85
    high: 0.70
    medium: 0.50
    low: 0.30

cooldown_seconds:
  critical: 30
  high: 60
  medium: 120
  low: 300

rate_limits:
  max_mitigations_per_minute: 30

database:
  host: udr-db
  port: 5432
  dbname: udr
  user: udr
  table: mitigations
  batch_insert_size: 1

health:
  port: 8082
```

**Important:** `auto_offset_reset: latest` (NOT `earliest`). The policy engine
must only act on live detections. Replaying historical predictions from training
runs would create a flood of spurious mitigations and pollute the `mitigations`
table with stale data.

---

### Phase 3: Kafka Topic Creation (Day 2)

Create new Makefile target `kafka-init-policy`:
```makefile
kafka-init-policy:
    docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
      rpk topic create wifi7.security.mitigations.v1 -p 1 -r 1
```

Verification:
```bash
make kafka-init-policy
docker exec clab-ndt-wifi7-mlo-security-bus-redpanda rpk topic list
```

---

### Phase 4: Docker Service (Day 2)

**Step 4.1 — Dockerfile (`security/policy/Dockerfile`)**

Same pattern as `twin/gnn/detector/Dockerfile`:
- Base: `python:3.11-slim`
- Non-root user `policy` (uid 1001)
- WORKDIR `/app`
- Copy `requirements.txt`, install, then copy source
- `CMD ["python", "-u", "policy_engine.py", "/app/config.yaml"]`
- HEALTHCHECK against port 8082

**Step 4.2 — Add service to `docker-compose.pipeline.yml`**

Add `policy-engine` service after `gcn-detector`:

```yaml
  policy-engine:
    image: ndt/policy-engine:local
    container_name: ndt-pipeline-policy-engine
    restart: unless-stopped
    networks:
      - clab-mgmt
    environment:
      KAFKA_BROKERS: ${KAFKA_BROKERS:-bus-redpanda:9092}
      KAFKA_INPUT_TOPIC: ${KAFKA_PREDICTIONS_TOPIC:-wifi7.security.gcn_predictions.v1}
      KAFKA_OUTPUT_TOPIC: ${KAFKA_MITIGATIONS_TOPIC:-wifi7.security.mitigations.v1}
      KAFKA_GROUP: policy-engine-v1
      PG_HOST: ${PG_HOST:-udr-db}
      PG_DB: ${PG_DB:-udr}
      PG_USER: ${PG_USER:-udr}
      PG_PASS: ${PG_PASS:-udr_pass}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    volumes:
      - ./security/policy/config.yaml:/app/config.yaml:ro
    ports:
      - "8082:8082"   # Health endpoint (8080=gcn-detector, 8081=windowizer)
    depends_on:
      - gcn-detector
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

**Step 4.3 — Add Makefile targets**

```makefile
# WP13: Closed-Loop Policy Actuation
POLICY_ENGINE_IMAGE=ndt/policy-engine:local

policy-engine-build:
    @docker build -t $(POLICY_ENGINE_IMAGE) security/policy/

policy-engine-run:
    @docker compose -f docker-compose.pipeline.yml up -d policy-engine

policy-engine-stop:
    @docker compose -f docker-compose.pipeline.yml stop policy-engine

policy-engine-logs:
    @docker compose -f docker-compose.pipeline.yml logs -f policy-engine

policy-engine-health:
    @curl -s http://localhost:8082/health | python3 -m json.tool

kafka-init-policy:
    @docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
      rpk topic create wifi7.security.mitigations.v1 -p 1 -r 1

policy-up: policy-engine-build kafka-init-policy policy-engine-run
    @echo "Policy engine started. Check: make policy-engine-health"

policy-down:
    @docker compose -f docker-compose.pipeline.yml stop policy-engine
```

---

### Phase 5: Dashboard Integration (Day 3)

**Step 5.1 — Backend: Mitigation queries (`dashboard/app/backend/db/queries.py`)**

Add the following query functions to the existing file:

- `get_mitigations(pool, limit, offset, experiment_id, severity)` — paginated list
- `get_mitigation_summary(pool)` — counts by severity, action, last 24h
- `get_active_mitigations(pool, since_minutes=5)` — mitigations in last N minutes
- `get_mitigation_series(pool, experiment_id)` — time-series for timeline chart

**Step 5.2 — Backend: Mitigations router (`dashboard/app/backend/api/mitigations.py`)**

New FastAPI router following the same pattern as `analysis.py` and `experiments.py`:

```
GET /api/mitigations/summary        → counts by severity + action_taken
GET /api/mitigations/recent         → last N mitigations (default limit=50)
GET /api/mitigations/active         → mitigations in last 5 minutes
GET /api/mitigations/history        → paginated full history
GET /api/mitigations/{id}           → single mitigation record detail
```

**Step 5.3 — Register router in `main.py`**

Add `from .api import mitigations` and `app.include_router(mitigations.router, prefix="/api")`.

**Step 5.4 — Frontend: React hook (`dashboard/app/frontend/src/hooks/useMitigations.ts`)**

Same pattern as `useRun.ts`. Hook `useMitigations` polls `GET /api/mitigations/active`
every 3 seconds. Returns `{ mitigations, summary, isLoading }`.

**Step 5.5 — Frontend: Mitigations section (`dashboard/app/frontend/src/sections/MitigationSection.tsx`)**

New React section with:
- Summary row: total mitigations today, by severity (critical/high/medium/low counts)
- "Active Mitigations" banner (if any in last 5 minutes): highlighted red/orange
- Scrollable table: timestamp, experiment_id, severity, action_taken, confidence,
  action_payload summary, cooldown_active badge
- Auto-refreshes every 3 seconds using `useMitigations`

**Step 5.6 — Wire into navigation**

In `Sidebar.tsx`: add "Mitigations" nav item with a shield or alert icon.
In `App.tsx`: add `MitigationSection` with `sectionId='mitigations'`.

---

### Phase 6: Testing (Day 4)

**Step 6.1 — Manual smoke test**

1. Run a positive-attack experiment:
   ```bash
   make run-mlo-positive EXP_ID=20260313-1400-mlo-positive-42 NAP=2 NSTA=4 SEED=42 SIM_TIME=80
   ```
2. Run exporter:
   ```bash
   make exporter-run EXP_ID=20260313-1400-mlo-positive-42
   ```
3. Check policy engine is receiving events:
   ```bash
   make policy-engine-logs
   ```
4. Query mitigations DB:
   ```bash
   docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr \
     -c "SELECT severity, action_taken, created_at FROM mitigations ORDER BY created_at DESC LIMIT 10;"
   ```
5. Check Kafka output topic:
   ```bash
   docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
     rpk topic consume wifi7.security.mitigations.v1 --num 5
   ```

**Step 6.2 — Normal experiment (no false positives)**

Run a normal experiment and verify no `critical` or `high` mitigations are created.
Check that mitigation count stays 0 or only `low` alerts appear if any.

**Step 6.3 — Dashboard verification**

Open `http://localhost:8888`, navigate to "Mitigations". Verify:
- Summary counts match DB query
- Active banner appears during an attack experiment
- Table populates with correct severity, action, confidence

**Step 6.4 — Cooldown verification**

Run a rapid-fire test: ensure second mitigation for same entity within cooldown window
is suppressed (`action_taken = 'suppressed'`, `cooldown_active = true` in DB).

---

## Integration Points

| Component | Role | How Connected |
|-----------|------|---------------|
| `gcn-detector` container | Source of detection events | Kafka topic `wifi7.security.gcn_predictions.v1` |
| `udr-db` | Persistent storage | psycopg2 connection, same credentials as other services |
| `bus-redpanda` | Message bus | Kafka consumer (predictions) + producer (mitigations) |
| `docker-compose.pipeline.yml` | Orchestration | New `policy-engine` service appended |
| `clab-mgmt` network | Container networking | All services share this external network |
| Dashboard backend | API queries | New `mitigations.py` router, existing `queries.py` |
| Dashboard frontend | User interface | New `MitigationSection.tsx` and `useMitigations.ts` |

---

## New Kafka Topics

| Topic | Direction | Description |
|-------|-----------|-------------|
| `wifi7.security.mitigations.v1` | Output (new) | Mitigation events published by policy engine |

The input topic `wifi7.security.gcn_predictions.v1` already exists and is pre-created
by `make kafka-init` (WP8). Only the mitigations output topic is new.

---

## Mitigation Kafka Message Schema

Published to `wifi7.security.mitigations.v1`:
```json
{
  "mitigation_id":   "20260313-1400-mlo-positive-42_network_seg0001_mit",
  "experiment_id":   "20260313-1400-mlo-positive-42",
  "entity_id":       "network",
  "segment_id":      "20260313-1400-mlo-positive-42_network_seg0001",
  "detection_ts":    "2026-03-13T14:00:00.000000+00:00",
  "created_at":      "2026-03-13T14:00:01.234567+00:00",
  "severity":        "high",
  "severity_score":  0.82,
  "action_taken":    "backoff_reset",
  "policy_rule":     "sustained_high",
  "cooldown_active": false,
  "action_payload":  {
    "action": "backoff_reset",
    "simulated": true,
    "cw_min_reset_to": 15,
    "cw_max_reset_to": 1023
  },
  "action_result":   "simulated",
  "gcn_confidence":  0.9973,
  "gcn_prediction":  1,
  "model_version":   "v2.1.0"
}
```

---

## DB Schema Additions Summary

New table: `public.mitigations` (see Step 1.1 above for full DDL).

Existing tables are unchanged. The policy engine reads from `gcn_predictions` indirectly
(via Kafka) and writes only to `mitigations`.

---

## Docker Service Additions Summary

| Service | Image | Port | Depends On |
|---------|-------|------|------------|
| `ndt-pipeline-policy-engine` | `ndt/policy-engine:local` | 8082 (health) | `gcn-detector` |

Existing port assignments:
- 8080: `gcn-detector` health
- 8081: `windowizer` health (per windowizer config.yaml)
- 8082: `policy-engine` health (new)
- 8888: `ndt-dashboard`

---

## Potential Issues and Mitigations

**Issue 1: Historical prediction replay floods mitigations table**
- Root cause: If `auto_offset_reset: earliest`, policy engine replays all historical
  detections from past experiments and creates thousands of spurious mitigations.
- Mitigation: Use `auto_offset_reset: latest` so only new live detections are processed.
  Document this clearly in `config.yaml` with a comment.

**Issue 2: Cooldown state lost on container restart**
- Root cause: Cooldown timers are in-memory, not persisted. A restart clears them.
- Mitigation: This is acceptable for v1. Post-restart the engine may re-fire a
  mitigation that was in cooldown. Add a note in comments. A future v2 could persist
  cooldown state to a Redis or DB table.

**Issue 3: Attack rate window contaminated by Normal experiment segments**
- Root cause: The sliding-window scorer tracks last 10 predictions per entity key.
  If a Normal experiment runs after an Attack experiment using the same entity_id,
  the window gradually clears — this is correct behavior.
- Mitigation: Scope the window by `(experiment_id, entity_id)` not just `entity_id`
  so each experiment gets a fresh scoring window.

**Issue 4: DB initdb SQL not auto-applied to existing DB**
- Root cause: TimescaleDB `initdb` scripts only run when the data volume is brand new.
  If the lab is already running (WP8–WP12 data present), the `004` script will not run.
- Mitigation: Document manual apply command in the plan. Add a `make db-migrate-wp13`
  target that applies the script to a running container.

**Issue 5: Port 8082 conflict**
- Root cause: Another service may already use 8082 on the host.
- Mitigation: The `ports:` mapping in compose can be changed. Alternatively, make
  the health port configurable via an env var `HEALTH_PORT`.

**Issue 6: GCN predictions from Normal experiments triggering low-severity alerts**
- Root cause: The GCN model has 0.27% false-positive rate. With many normal windows
  processed, some will score `prediction=1`.
- Mitigation: The `recent_attack_rate` component of severity scoring naturally suppresses
  this. A single false positive in a run of 10 normal predictions gives `attack_rate=0.1`,
  `severity_score ≈ 0.4 * 0.9 + 0.6 * 0.1 = 0.42` which is `medium` at most, and
  the cooldown will suppress repeat alerts. This is acceptable behavior for a digital
  twin research context.

---

## ADR Candidates

These decisions should be documented as ADRs after implementation:

1. **ADR-WP13-01: `auto_offset_reset: latest` for policy engine**
   - Why latest (not earliest) prevents spurious mitigation replay
   - Contrasts with harmonizer (earliest) and windowizer (earliest)

2. **ADR-WP13-02: Simulated actuation only**
   - Decision to log "would execute" rather than attempt real AP management
   - Rationale: no live hardware, NS-3 is not a real-time controllable sim
   - Future path: ns-3 could be extended with a control channel for real-time parameter changes

3. **ADR-WP13-03: Severity scoring uses composite score (confidence + run rate)**
   - Why confidence alone is insufficient for policy gating
   - Why sliding window scope is per `(experiment_id, entity_id)` not global

4. **ADR-WP13-04: Policy engine is a separate service, not embedded in GCN detector**
   - Single-responsibility principle: detection and policy are separate concerns
   - Allows policy to be updated/restarted without touching detector
   - Enables future multi-detector inputs (if a second detection method is added)

---

## Scope Boundaries (What NOT to Do in WP13)

The following are explicitly out of scope for WP13:

- **No real AP or STA control**: No NETCONF, RESTCONF, or management frame injection.
  All actuation is logged as `"simulated": true` in the action payload.

- **No NS-3 real-time parameter injection**: NS-3 runs as a batch simulation; there
  is no runtime control API. Channel steering and CW reset are recorded as what the
  command "would be" but not executed.

- **No Grafana panels for mitigations**: Grafana integration is out of scope. The
  existing Grafana dashboard (`ndt-unified.json`) is not to be modified. Mitigation
  visibility is provided solely through the React dashboard.

- **No email, webhook, or external alerting**: No PagerDuty, Slack, or email.
  Mitigation events are published to Kafka and stored in DB only.

- **No policy hot-reload**: The policy engine reads `config.yaml` at startup only.
  A `SIGHUP`-based reload mechanism would be a nice future enhancement.

- **No multi-tenant policy**: One policy set applied globally. Entity-specific
  policy overrides are not in scope.

- **No persistence of cooldown state**: Cooldown is in-memory only. Acceptable for
  a research digital twin.

- **No GCN detector modification**: `detector.py`, `inference_engine.py`, and related
  files must not be changed. The policy engine is purely a consumer of the existing
  Kafka output.

---

## Implementation Phases Summary

| Phase | Days | Deliverable |
|-------|------|-------------|
| 1: DB Schema | Day 1 | `004_mitigations_schema.sql` applied |
| 2: Policy Engine | Days 1–2 | All `security/policy/` and `security/actuation/` files |
| 3: Kafka Topic | Day 2 | `wifi7.security.mitigations.v1` topic created |
| 4: Docker Service | Day 2 | `policy-engine` in compose + Makefile targets |
| 5: Dashboard | Day 3 | API router + React section + nav item |
| 6: Testing | Day 4 | Manual smoke tests passing, normal experiment verified |

---

## Related Documentation

- `docs/CURRENT-STATE.md` — update WP13 status after completion
- `docs/ALL-ADRS.md` — add ADR-WP13-01 through ADR-WP13-04
- `docs/BLUEPRINT.md` — add WP13 section
- `twin/gnn/detector/detector.py` — reference pattern for service structure
- `telemetry/harmonizer/harmonizer.py` — reference pattern for Kafka consumer
- `clab/configs/udr-db/initdb/003_gcn_schema.sql` — reference pattern for DB schema
- `dashboard/app/backend/api/analysis.py` — reference pattern for FastAPI router
- `dashboard/app/backend/api/run.py` — reference pattern for complex router
- `docker-compose.pipeline.yml` — file to modify for new service
- `security/detector/windowizer/config.yaml` — reference for service config format

---

## Verification Commands (Quick Reference)

```bash
# Build and start policy engine
make policy-engine-build && make kafka-init-policy && make policy-engine-run

# Check health
make policy-engine-health

# View logs
make policy-engine-logs

# Check DB for mitigations
docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr \
  -c "SELECT severity, action_taken, count(*) FROM mitigations GROUP BY severity, action_taken;"

# Check Kafka output topic
docker exec clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic consume wifi7.security.mitigations.v1 --num 5

# Full pipeline status
docker compose -f docker-compose.pipeline.yml ps
```
