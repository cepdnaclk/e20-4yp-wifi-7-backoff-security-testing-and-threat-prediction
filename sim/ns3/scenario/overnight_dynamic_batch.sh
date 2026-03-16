#!/usr/bin/env bash
# overnight_dynamic_batch.sh — Comprehensive Dynamic Scenario Overnight Runner
#
# Launches 39 dynamic NS-3 experiments one-by-one via the dashboard API,
# covering every phase pattern type, all 4 segment lengths, nap=1 and nap=2.
#
# Usage:
#   bash overnight_dynamic_batch.sh            # run all scenarios
#   bash overnight_dynamic_batch.sh --dry-run  # print plan without launching
#
# Log: /tmp/overnight_run.log
# Estimated runtime: ~6-8 hours (39 scenarios)
#
# Phase notation:
#   norm=0 bias (normal traffic)
#   pos=+5000 (positive backoff attack)
#   neg=-5000 (negative backoff attack)
#   wkpos=+2000 (weak positive attack)
#   wkneg=-2000 (weak negative attack)
#
# Sim time selection ensures ≥ N segments at the most constraining window:
#   seg_len=256 stride=64: need (256 + (N-1)*64)/10 seconds minimum
#   2-phase → 60s, 3-phase → 75s, 4-phase → 80s, 5-phase → 85s

set -euo pipefail
IFS=$'\n\t'

API="http://localhost:8888"
LOG="/tmp/overnight_run.log"
POLL_SEC=20       # seconds between status polls
COOLDOWN_SEC=90   # wait after active=false before next launch
                  # allows windowizer drain (30s) + reconfiguration (~8s) + buffer
DRY_RUN="${1:-}"

PASS=0
FAIL=0
SKIP=0
START_TIME=$(date +%s)

# ── Logging ──────────────────────────────────────────────────────────────────

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

elapsed_total() {
    local now; now=$(date +%s)
    echo $(( (now - START_TIME) / 60 ))
}

# ── Launch + poll one scenario ────────────────────────────────────────────────

run_scenario() {
    local label="$1"    # short name used in experiment_id
    local phases="$2"   # e.g. "0:0,30:5000"
    local sim_time="$3" # simulation duration in seconds
    local num_ap="$4"
    local num_sta="$5"
    local seg_len="$6"
    local seed="$7"

    local ts; ts=$(date -u '+%Y%m%d-%H%M')
    local exp_id="${ts}-${label}-nap${num_ap}-${seg_len}w-seed${seed}"

    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "LAUNCH  $exp_id"
    log "  phases='$phases'  sim=${sim_time}s  nap=${num_ap} nsta=${num_sta}  seg=${seg_len}  seed=${seed}"
    log "  elapsed=$(elapsed_total) min since batch start"

    if [[ "$DRY_RUN" == "--dry-run" ]]; then
        log "  [DRY-RUN] Skipping"
        ((SKIP++)) || true
        log ""
        return 0
    fi

    # Build JSON payload
    local payload
    payload=$(printf '{
        "scenario": "dynamic",
        "phases": "%s",
        "sim_time": %s,
        "num_ap": %d,
        "num_sta": %d,
        "segment_length": %d,
        "seed": %d,
        "experiment_id": "%s"
    }' "$phases" "$sim_time" "$num_ap" "$num_sta" "$seg_len" "$seed" "$exp_id")

    # Launch — retry once on 409 conflict
    local http_code resp
    for attempt in 1 2; do
        http_code=$(curl -sf \
            -o /tmp/.overnight_resp.json \
            -w "%{http_code}" \
            -X POST "$API/api/run/launch" \
            -H "Content-Type: application/json" \
            -d "$payload" 2>&1) || http_code="000"

        if [[ "$http_code" == "200" ]]; then
            break
        elif [[ "$http_code" == "409" ]] && [[ $attempt -eq 1 ]]; then
            log "  WARN: 409 conflict — waiting 120s for prior run to finish, then retrying..."
            sleep 120
        else
            log "  ERROR: Launch returned HTTP $http_code (attempt $attempt)"
            cat /tmp/.overnight_resp.json >> "$LOG" 2>/dev/null || true
            if [[ $attempt -eq 2 ]]; then
                log "  SKIP: $exp_id (failed to launch)"
                ((FAIL++)) || true
                log ""
                return 0
            fi
        fi
    done

    log "  Launched OK"

    # Poll until active=false
    local elapsed=0
    while true; do
        sleep $POLL_SEC
        elapsed=$((elapsed + POLL_SEC))

        local status_json
        status_json=$(curl -sf "$API/api/run/status" 2>/dev/null || echo '{}')

        local active stage state
        active=$(python3 -c "
import sys, json
d = json.load(sys.stdin)
print(str(d.get('active', False)).lower())
" <<< "$status_json" 2>/dev/null || echo "false")

        stage=$(python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('stage') or '?')
" <<< "$status_json" 2>/dev/null || echo "?")

        state=$(python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('state') or '?')
" <<< "$status_json" 2>/dev/null || echo "?")

        log "  [${elapsed}s] active=${active} stage=${stage} state=${state}"

        if [[ "$active" == "false" ]]; then
            log "  DONE: $exp_id (${elapsed}s run time)"
            ((PASS++)) || true
            break
        fi

        # Hard timeout: 40 minutes per scenario
        if [[ $elapsed -gt 2400 ]]; then
            log "  TIMEOUT: $exp_id after 40 min — moving on"
            ((FAIL++)) || true
            break
        fi
    done

    log "  Cooldown ${COOLDOWN_SEC}s (windowizer drain + reconfigure)..."
    sleep $COOLDOWN_SEC
    log ""
}

# ─────────────────────────────────────────────────────────────────────────────
# BATCH START
# ─────────────────────────────────────────────────────────────────────────────

# Ensure log directory exists and API is reachable
mkdir -p "$(dirname "$LOG")"
log "════════════════════════════════════════════════════════════════"
log "OVERNIGHT DYNAMIC BATCH — $(date)"
log "  API: $API"
log "  Planned: 39 scenarios | Poll: ${POLL_SEC}s | Cooldown: ${COOLDOWN_SEC}s"
log "  Dry-run: ${DRY_RUN:-no}"
log "════════════════════════════════════════════════════════════════"
log ""

if [[ "$DRY_RUN" != "--dry-run" ]]; then
    if ! curl -sf "$API/api/health" > /dev/null 2>&1; then
        log "ERROR: Dashboard API not reachable at $API — aborting"
        exit 1
    fi
    log "API health check OK"
    log ""
fi

# ═══════════════════════════════════════════════════════════════════════════
# GROUP A: 2-phase scenarios — nap=1, all 4 segment lengths (16 runs)
# sim_time=60s → 600 windows → seg=256,stride=64: 6 segments ≥ 2 phases ✓
# ═══════════════════════════════════════════════════════════════════════════
log "▶ GROUP A: 2-phase nap=1 (16 runs) ─────────────────────────────"
log ""

# norm→pos (+5000): normal traffic transitions to positive backoff attack
run_scenario "dyn2p-norm-pos"  "0:0,30:5000"   60  1 2  32  42
run_scenario "dyn2p-norm-pos"  "0:0,30:5000"   60  1 2  64  42
run_scenario "dyn2p-norm-pos"  "0:0,30:5000"   60  1 2 128  42
run_scenario "dyn2p-norm-pos"  "0:0,30:5000"   60  1 2 256  42

# norm→neg (-5000): normal traffic transitions to negative backoff attack
run_scenario "dyn2p-norm-neg"  "0:0,30:-5000"  60  1 2  32 111
run_scenario "dyn2p-norm-neg"  "0:0,30:-5000"  60  1 2  64 111
run_scenario "dyn2p-norm-neg"  "0:0,30:-5000"  60  1 2 128 111
run_scenario "dyn2p-norm-neg"  "0:0,30:-5000"  60  1 2 256 111

# pos→norm (+5000→0): attack clears mid-stream
run_scenario "dyn2p-pos-norm"  "0:5000,30:0"   60  1 2  32 222
run_scenario "dyn2p-pos-norm"  "0:5000,30:0"   60  1 2  64 222
run_scenario "dyn2p-pos-norm"  "0:5000,30:0"   60  1 2 128 222
run_scenario "dyn2p-pos-norm"  "0:5000,30:0"   60  1 2 256 222

# neg→norm (-5000→0): negative attack clears mid-stream
run_scenario "dyn2p-neg-norm"  "0:-5000,30:0"  60  1 2  32 333
run_scenario "dyn2p-neg-norm"  "0:-5000,30:0"  60  1 2  64 333
run_scenario "dyn2p-neg-norm"  "0:-5000,30:0"  60  1 2 128 333
run_scenario "dyn2p-neg-norm"  "0:-5000,30:0"  60  1 2 256 333

# ═══════════════════════════════════════════════════════════════════════════
# GROUP B: 3-phase scenarios — nap=1 (11 runs)
# sim_time=75s → 750 windows → seg=256,stride=64: 8 segments ≥ 3 phases ✓
# ═══════════════════════════════════════════════════════════════════════════
log "▶ GROUP B: 3-phase nap=1 (11 runs) ─────────────────────────────"
log ""

# norm→pos→norm: attack window in the middle
run_scenario "dyn3p-norm-pos-norm"  "0:0,25:5000,50:0"    75  1 2  64  42
run_scenario "dyn3p-norm-pos-norm"  "0:0,25:5000,50:0"    75  1 2 128  42
run_scenario "dyn3p-norm-pos-norm"  "0:0,25:5000,50:0"    75  1 2 256  42

# norm→neg→norm: negative attack window in the middle
run_scenario "dyn3p-norm-neg-norm"  "0:0,25:-5000,50:0"   75  1 2  64 111
run_scenario "dyn3p-norm-neg-norm"  "0:0,25:-5000,50:0"   75  1 2 128 111
run_scenario "dyn3p-norm-neg-norm"  "0:0,25:-5000,50:0"   75  1 2 256 111

# pos→norm→pos: attack, brief recovery, attack resumes
run_scenario "dyn3p-pos-norm-pos"   "0:5000,25:0,50:5000"  75  1 2 128 222
run_scenario "dyn3p-pos-norm-pos"   "0:5000,25:0,50:5000"  75  1 2 256 222

# pos→norm→neg: positive attack flips to negative (polarity reversal)
run_scenario "dyn3p-pos-norm-neg"   "0:5000,25:0,50:-5000" 75  1 2 128 333
run_scenario "dyn3p-pos-norm-neg"   "0:5000,25:0,50:-5000" 75  1 2 256 333

# neg→norm→pos: negative attack flips to positive (reverse reversal)
run_scenario "dyn3p-neg-norm-pos"   "0:-5000,25:0,50:5000" 75  1 2 256 456

# ═══════════════════════════════════════════════════════════════════════════
# GROUP C: 4-phase scenarios — nap=1 (4 runs)
# sim_time=80s → 800 windows → seg=256,stride=64: 9 segments ≥ 4 phases ✓
# ═══════════════════════════════════════════════════════════════════════════
log "▶ GROUP C: 4-phase nap=1 (4 runs) ──────────────────────────────"
log ""

# norm→pos→neg→norm: alternating polarity attack
run_scenario "dyn4p-norm-pos-neg-norm"  "0:0,20:5000,40:-5000,60:0"  80  1 2 128  42
run_scenario "dyn4p-norm-pos-neg-norm"  "0:0,20:5000,40:-5000,60:0"  80  1 2 256  42

# norm→neg→pos→norm: reverse alternating polarity
run_scenario "dyn4p-norm-neg-pos-norm"  "0:0,20:-5000,40:5000,60:0"  80  1 2 128 111
run_scenario "dyn4p-norm-neg-pos-norm"  "0:0,20:-5000,40:5000,60:0"  80  1 2 256 111

# ═══════════════════════════════════════════════════════════════════════════
# GROUP D: 5-phase scenarios — nap=1 (2 runs)
# sim_time=85s → 850 windows → seg=256,stride=64: 10 segments ≥ 5 phases ✓
# ═══════════════════════════════════════════════════════════════════════════
log "▶ GROUP D: 5-phase nap=1 (2 runs) ──────────────────────────────"
log ""

# norm→pos→norm→neg→norm: full dual-polarity cycle
# Phases: 0-16s normal, 16-32s pos attack, 32-48s normal, 48-64s neg attack, 64-85s normal
run_scenario "dyn5p-norm-pos-norm-neg-norm"  "0:0,16:5000,32:0,48:-5000,64:0"  85  1 2 128 222
run_scenario "dyn5p-norm-pos-norm-neg-norm"  "0:0,16:5000,32:0,48:-5000,64:0"  85  1 2 256 222

# ═══════════════════════════════════════════════════════════════════════════
# GROUP E: Weak-bias variants — nap=1 (2 runs)
# Tests GCN sensitivity to lower-intensity attacks (bias=±2000 vs ±5000)
# ═══════════════════════════════════════════════════════════════════════════
log "▶ GROUP E: Weak-bias (±2000) nap=1 (2 runs) ────────────────────"
log ""

run_scenario "dyn2p-norm-wkpos"  "0:0,30:2000"   60  1 2 256 456
run_scenario "dyn2p-norm-wkneg"  "0:0,30:-2000"  60  1 2 256 789

# ═══════════════════════════════════════════════════════════════════════════
# GROUP F: nap=2, nsta=4 — key scenarios at seg=256 only (4 runs)
# Note: nap=2 NS-3 runs are slower (~15-25 min per scenario)
# ═══════════════════════════════════════════════════════════════════════════
log "▶ GROUP F: nap=2 nsta=4 key scenarios, seg=256 (4 runs) ─────────"
log ""

run_scenario "dyn2p-norm-pos"               "0:0,30:5000"                      60  2 4 256  42
run_scenario "dyn2p-norm-neg"               "0:0,30:-5000"                     60  2 4 256 111
run_scenario "dyn3p-norm-pos-norm"          "0:0,25:5000,50:0"                 75  2 4 256 222
run_scenario "dyn5p-norm-pos-norm-neg-norm" "0:0,16:5000,32:0,48:-5000,64:0"  85  2 4 256 333

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
log ""
log "════════════════════════════════════════════════════════════════"
log "BATCH COMPLETE — $(date)"
log "  Total elapsed : $(elapsed_total) minutes"
log "  Passed  : $PASS"
log "  Failed  : $FAIL"
log "  Skipped : $SKIP (dry-run)"
log "  Total   : $((PASS + FAIL + SKIP)) / 39"
log "════════════════════════════════════════════════════════════════"
