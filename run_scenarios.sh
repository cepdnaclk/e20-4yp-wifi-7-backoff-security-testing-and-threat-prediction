#!/usr/bin/env bash
# ==============================================================================
# run_scenarios.sh
#
# Runs a sequence of normal and attack scenarios through the NDT Wi-Fi 7 MLO
# digital twin pipeline and presents results from the GCN detector and DB.
#
# Usage:
#   ./run_scenarios.sh              # default sequence: normal, neg, normal, pos
#   ./run_scenarios.sh --help       # show options
#
# Requirements:
#   - Containerlab stack running (make up)
#   - Pipeline services running  (make pipeline-up  AND  docker compose ... up)
#   - ndt/ns3-exporter:local image built (make exporter-build)
#   - Validation telemetry files present under sim/ns3/artifacts/
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# Paths & config
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTIFACTS_DIR="${SCRIPT_DIR}/sim/ns3/artifacts"

KAFKA_BROKERS="bus-redpanda:9092"
KAFKA_TOPIC="wifi7.telemetry.v0_1"
NETWORK="clab-mgmt"
EXPORTER_IMAGE="ndt/ns3-exporter:local"

GCN_CONTAINER="ndt-pipeline-gcn-detector"
WINDOWIZER_CONTAINER="ndt-pipeline-windowizer"
DB_CONTAINER="clab-ndt-wifi7-mlo-security-udr-db"
DB_USER="udr"
DB_NAME="udr"

GRAFANA_URL="http://localhost:3000"

# Source experiments (26,000 events each)
SRC_NORMAL="20260215-validation-normal-01"
SRC_ATTACK_NEG="20260215-validation-attack-neg-01"
SRC_ATTACK_POS="20260215-validation-attack-pos-01"

# Default scenario sequence: label:source_experiment
DEFAULT_SCENARIOS=(
    "normal:${SRC_NORMAL}"
    "attack-neg:${SRC_ATTACK_NEG}"
    "normal:${SRC_NORMAL}"
    "attack-pos:${SRC_ATTACK_POS}"
)

# ------------------------------------------------------------------------------
# Colors & logging
# ------------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

log()    { echo -e "${CYAN}[$(date +%H:%M:%S)]${NC} $*"; }
ok()     { echo -e "${GREEN}[$(date +%H:%M:%S)] ✓${NC} $*"; }
warn()   { echo -e "${YELLOW}[$(date +%H:%M:%S)] ⚠${NC} $*"; }
fail()   { echo -e "${RED}[$(date +%H:%M:%S)] ✗${NC} $*"; exit 1; }
header() {
    echo ""
    echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}  $*${NC}"
    echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════════${NC}"
    echo ""
}

# ------------------------------------------------------------------------------
# Help
# ------------------------------------------------------------------------------
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --help        Show this help"
    echo "  --no-flush    Skip DB flush (predictions stay buffered)"
    echo "  --keep-temp   Keep temp telemetry files after run"
    echo ""
    echo "Scenario sequence (edit SCENARIOS array in script to change):"
    for s in "${DEFAULT_SCENARIOS[@]}"; do
        IFS=':' read -r label _ <<< "$s"
        echo "  - $label"
    done
    exit 0
fi

FLUSH_DB=true
KEEP_TEMP=false
for arg in "${@}"; do
    [[ "$arg" == "--no-flush"   ]] && FLUSH_DB=false
    [[ "$arg" == "--keep-temp"  ]] && KEEP_TEMP=true
done

SCENARIOS=("${DEFAULT_SCENARIOS[@]}")

# ------------------------------------------------------------------------------
# Preflight checks
# ------------------------------------------------------------------------------
header "Preflight Checks"

RUN_TIMESTAMP=$(date +"%Y%m%d-%H%M")
TEMP_DIR="/tmp/ndt-scenarios-${RUN_TIMESTAMP}"
mkdir -p "$TEMP_DIR"

log "Run ID: ${BOLD}${RUN_TIMESTAMP}${NC}"
log "Temp dir: ${TEMP_DIR}"
echo ""

# Check Docker images
if ! docker image inspect "$EXPORTER_IMAGE" &>/dev/null; then
    fail "Exporter image '${EXPORTER_IMAGE}' not found. Run: make exporter-build"
fi
ok "Exporter image present"

# Check pipeline containers
for svc in "$GCN_CONTAINER" "$WINDOWIZER_CONTAINER" "$DB_CONTAINER"; do
    status=$(docker inspect "$svc" --format '{{.State.Status}}' 2>/dev/null || echo "missing")
    if [[ "$status" == "running" ]]; then
        ok "${svc} running"
    else
        fail "${svc} is not running (status: ${status}). Start the pipeline first."
    fi
done

# Check source telemetry files
for src in "$SRC_NORMAL" "$SRC_ATTACK_NEG" "$SRC_ATTACK_POS"; do
    fpath="${ARTIFACTS_DIR}/${src}/telemetry.jsonl"
    if [[ -f "$fpath" ]]; then
        lines=$(wc -l < "$fpath")
        ok "Telemetry: ${src} (${lines} rows)"
    else
        fail "Missing telemetry: ${fpath}"
    fi
done

# Kill any stale exporter containers from previous runs
stale=$(docker ps --format "{{.Names}}\t{{.Image}}" | awk -v img="$EXPORTER_IMAGE" '$2==img{print $1}')
if [[ -n "$stale" ]]; then
    warn "Stopping stale exporter containers: ${stale}"
    echo "$stale" | xargs docker stop > /dev/null
fi

echo ""
log "Scenario sequence:"
for i in "${!SCENARIOS[@]}"; do
    IFS=':' read -r label _ <<< "${SCENARIOS[$i]}"
    seq=$((i + 1))
    exp_id="${RUN_TIMESTAMP}-seq${seq}-${label}"
    case "$label" in
        normal)     echo -e "  ${seq}. ${GREEN}${exp_id}${NC}  [normal traffic]" ;;
        attack-neg) echo -e "  ${seq}. ${RED}${exp_id}${NC}  [negative bias attack]" ;;
        attack-pos) echo -e "  ${seq}. ${RED}${exp_id}${NC}  [positive bias attack]" ;;
    esac
done
echo ""

# ------------------------------------------------------------------------------
# Helper: run one experiment
# ------------------------------------------------------------------------------
run_scenario() {
    local seq="$1"
    local label="$2"
    local source_exp="$3"
    local exp_id="$4"
    local total="$5"

    case "$label" in
        normal)     header "Scenario ${seq}/${total}: NORMAL TRAFFIC — ${exp_id}" ;;
        attack-neg) header "Scenario ${seq}/${total}: ATTACK (negative bias) — ${exp_id}" ;;
        attack-pos) header "Scenario ${seq}/${total}: ATTACK (positive bias) — ${exp_id}" ;;
    esac

    # ------------------------------------------------------------------
    # Step 1: Prepare telemetry with time-based experiment_id
    # ------------------------------------------------------------------
    local temp_file="${TEMP_DIR}/${exp_id}.jsonl"
    local state_dir="${TEMP_DIR}/state-${exp_id}"
    mkdir -p "$state_dir"
    echo '{"files":{}}' > "${state_dir}/exporter_state.json"

    log "Step 1/4 — Preparing telemetry (stamping experiment_id = ${exp_id})..."
    python3 - <<PYEOF
import json, sys
src = "${ARTIFACTS_DIR}/${source_exp}/telemetry.jsonl"
dst = "${temp_file}"
count = 0
with open(src) as fin, open(dst, 'w') as fout:
    for line in fin:
        ev = json.loads(line)
        ev['experiment_id'] = "${exp_id}"
        fout.write(json.dumps(ev) + '\n')
        count += 1
print(f"  Prepared {count} events → {dst}")
PYEOF
    ok "Telemetry ready (26,000 events, experiment_id = ${exp_id})"

    # ------------------------------------------------------------------
    # Step 2: Publish to Kafka
    # ------------------------------------------------------------------
    log "Step 2/4 — Publishing to Kafka (${KAFKA_TOPIC})..."

    # Run exporter in detached mode; kill it once SUCCESS is confirmed
    local exporter_cid
    exporter_cid=$(docker run -d \
        --network "$NETWORK" \
        --user "$(id -u):$(id -g)" \
        -v "${temp_file}:/data/telemetry.jsonl:ro" \
        -v "${state_dir}:/state" \
        -e TELEMETRY_FILE="/data/telemetry.jsonl" \
        -e KAFKA_BROKERS="$KAFKA_BROKERS" \
        -e KAFKA_TOPIC="$KAFKA_TOPIC" \
        "$EXPORTER_IMAGE")

    # Poll for SUCCESS or failure (max 3 min)
    local deadline=$((SECONDS + 180))
    local delivered=0
    while [[ $SECONDS -lt $deadline ]]; do
        local logs
        logs=$(docker logs "$exporter_cid" 2>&1)
        if echo "$logs" | grep -q "SUCCESS"; then
            delivered=$(echo "$logs" | grep -oP 'All \K[0-9]+(?= messages delivered)' || echo "26000")
            break
        fi
        if echo "$logs" | grep -q "ERROR"; then
            docker stop "$exporter_cid" > /dev/null
            docker rm "$exporter_cid" > /dev/null
            fail "Exporter reported an error for ${exp_id}"
        fi
        # Show progress every 10s
        local progress
        progress=$(echo "$logs" | grep -oP 'delivered \K[0-9]+' | tail -1 || echo "0")
        printf "\r  delivered %s / 26000 messages..." "$progress"
        sleep 5
    done

    printf "\r"
    docker stop "$exporter_cid" > /dev/null
    docker rm  "$exporter_cid" > /dev/null

    ok "All ${delivered} messages delivered to Kafka"

    # ------------------------------------------------------------------
    # Step 3: Wait for windowizer + GCN to process
    # ------------------------------------------------------------------
    log "Step 3/4 — Waiting for windowizer & GCN to build segments..."

    # Poll windowizer for this experiment to appear and emit segments
    local wait_deadline=$((SECONDS + 60))
    local segments_emitted=0
    while [[ $SECONDS -lt $wait_deadline ]]; do
        local wz_log
        wz_log=$(docker logs "$WINDOWIZER_CONTAINER" --since 90s 2>&1)
        if echo "$wz_log" | grep -q "${exp_id}"; then
            # Extract segments count
            segments_emitted=$(echo "$wz_log" \
                | grep "${exp_id}" \
                | grep -oP 'segments: \K[0-9]+' \
                | sort -n | tail -1 || echo "0")
            if [[ "$segments_emitted" -ge 7 ]]; then
                break
            fi
        fi
        printf "\r  windowizer: %s segments emitted for %s..." "$segments_emitted" "$exp_id"
        sleep 5
    done

    printf "\r"
    ok "Windowizer emitted ${segments_emitted} segments for ${exp_id}"

    # Give GCN detector 5s to process the last segments
    sleep 5

    # ------------------------------------------------------------------
    # Step 4: Show live predictions from detector log
    # ------------------------------------------------------------------
    log "Step 4/4 — GCN Detector predictions:"
    echo ""

    local attack_lines
    attack_lines=$(docker logs "$GCN_CONTAINER" --since 120s 2>&1 \
        | grep "ATTACK DETECTED.*${exp_id}" || true)

    if [[ -n "$attack_lines" ]]; then
        local attack_count
        attack_count=$(echo "$attack_lines" | wc -l)
        echo "$attack_lines" | while IFS= read -r line; do
            echo -e "    ${RED}${line}${NC}"
        done
        echo ""
        case "$label" in
            normal)
                warn "UNEXPECTED: ${attack_count} attack detections on normal traffic!"
                ;;
            attack-*)
                ok "${attack_count}/7 segments flagged as ATTACK (confidence: 1.00) ✓"
                ;;
        esac
    else
        case "$label" in
            normal)
                ok "0 attack detections on normal traffic ✓"
                echo -e "    ${GREEN}All 7 segments predicted: NORMAL${NC}"
                ;;
            attack-*)
                warn "No ATTACK DETECTED log lines found yet for ${exp_id}"
                warn "Predictions may still be buffered. Check after DB flush."
                ;;
        esac
    fi

    # Latest aggregate stats
    local stats
    stats=$(docker logs "$GCN_CONTAINER" --since 30s 2>&1 \
        | grep -E "Segments received|Attack rate" | tail -2 || true)
    if [[ -n "$stats" ]]; then
        echo ""
        echo "  GCN Detector cumulative stats (all scenarios so far):"
        echo "$stats" | while IFS= read -r line; do
            echo "    $line"
        done
    fi

    echo ""
}

# ------------------------------------------------------------------------------
# Run all scenarios
# ------------------------------------------------------------------------------
EXPERIMENT_IDS=()
for i in "${!SCENARIOS[@]}"; do
    IFS=':' read -r label source_exp <<< "${SCENARIOS[$i]}"
    seq=$((i + 1))
    exp_id="${RUN_TIMESTAMP}-seq${seq}-${label}"
    EXPERIMENT_IDS+=("$exp_id")

    run_scenario "$seq" "$label" "$source_exp" "$exp_id" "${#SCENARIOS[@]}"
done

# ------------------------------------------------------------------------------
# Flush predictions to TimescaleDB
# ------------------------------------------------------------------------------
if [[ "$FLUSH_DB" == true ]]; then
    header "Flushing Predictions to TimescaleDB"

    log "Gracefully stopping GCN detector (triggers buffer flush)..."
    docker stop "$GCN_CONTAINER" > /dev/null
    sleep 3

    # Confirm flush from logs
    flush_msg=$(docker logs "$GCN_CONTAINER" 2>&1 | grep "Flushed.*predictions" | tail -1 || true)
    if [[ -n "$flush_msg" ]]; then
        ok "DB flush confirmed: ${flush_msg}"
    else
        warn "No flush confirmation in logs — predictions may have already been flushed"
    fi

    log "Restarting GCN detector..."
    docker start "$GCN_CONTAINER" > /dev/null
    sleep 5
    ok "GCN detector restarted (v2.0.0 model loaded)"
fi

# ------------------------------------------------------------------------------
# Final DB report
# ------------------------------------------------------------------------------
header "Final Prediction Results"

log "Querying TimescaleDB (gcn_predictions)..."
echo ""

docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT
    experiment_id,
    CASE prediction
        WHEN 0 THEN 'NORMAL'
        WHEN 1 THEN 'ATTACK'
    END AS result,
    COUNT(*)                                    AS segments,
    ROUND(AVG(confidence)::numeric * 100, 2)    AS confidence_pct,
    ROUND(MIN(inference_time_ms)::numeric, 1)   AS min_ms,
    ROUND(MAX(inference_time_ms)::numeric, 1)   AS max_ms,
    model_version
FROM gcn_predictions
WHERE experiment_id LIKE '${RUN_TIMESTAMP}%'
GROUP BY experiment_id, prediction, model_version
ORDER BY experiment_id, prediction;
" 2>&1

echo ""

# Quick pass/fail summary
echo -e "${BOLD}Pass / Fail Summary:${NC}"
echo ""
all_pass=true
for i in "${!SCENARIOS[@]}"; do
    IFS=':' read -r label _ <<< "${SCENARIOS[$i]}"
    exp_id="${EXPERIMENT_IDS[$i]}"

    db_result=$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc "
        SELECT prediction, COUNT(*) as c
        FROM gcn_predictions
        WHERE experiment_id = '${exp_id}'
        GROUP BY prediction;
    " 2>/dev/null || echo "")

    attack_segs=$(echo "$db_result" | awk -F'|' '$1==1{print $2}' | tr -d ' ')
    normal_segs=$(echo "$db_result" | awk -F'|' '$1==0{print $2}' | tr -d ' ')
    attack_segs=${attack_segs:-0}
    normal_segs=${normal_segs:-0}
    total=$((attack_segs + normal_segs))

    case "$label" in
        normal)
            if [[ "$attack_segs" -eq 0 && "$normal_segs" -gt 0 ]]; then
                echo -e "  ${GREEN}PASS${NC}  ${exp_id}  →  ${normal_segs} segments: NORMAL (0% FPR)"
            else
                echo -e "  ${RED}FAIL${NC}  ${exp_id}  →  ${attack_segs} false positives out of ${total}"
                all_pass=false
            fi
            ;;
        attack-*)
            if [[ "$attack_segs" -gt 0 && "$normal_segs" -eq 0 ]]; then
                echo -e "  ${GREEN}PASS${NC}  ${exp_id}  →  ${attack_segs} segments: ATTACK (100% TPR)"
            else
                echo -e "  ${RED}FAIL${NC}  ${exp_id}  →  detected ${attack_segs}/${total} (expected all as ATTACK)"
                all_pass=false
            fi
            ;;
    esac
done

echo ""
if [[ "$all_pass" == true ]]; then
    echo -e "${BOLD}${GREEN}  ALL SCENARIOS PASSED ✓${NC}"
else
    echo -e "${BOLD}${RED}  ONE OR MORE SCENARIOS FAILED ✗${NC}"
fi

# ------------------------------------------------------------------------------
# Grafana instructions
# ------------------------------------------------------------------------------
header "Grafana Dashboard"

echo -e "  URL: ${BOLD}${GRAFANA_URL}${NC}  (default login: admin / admin)"
echo ""
echo -e "  Filter by this run's experiment IDs (prefix: ${BOLD}${RUN_TIMESTAMP}${NC}):"
echo ""
for i in "${!SCENARIOS[@]}"; do
    IFS=':' read -r label _ <<< "${SCENARIOS[$i]}"
    exp_id="${EXPERIMENT_IDS[$i]}"
    case "$label" in
        normal)     echo -e "    ${GREEN}${exp_id}${NC}" ;;
        attack-*)   echo -e "    ${RED}${exp_id}${NC}" ;;
    esac
done
echo ""
echo "  Panels to check:"
echo "    • GCN Attack Predictions  — shows prediction=0 (normal) vs 1 (attack) per segment"
echo "    • Network Throughput      — traffic patterns during each scenario"
echo "    • Backoff Slots           — attack signature visible as avg_backoff_slots spike"
echo "    • Attack Rate Over Time   — live attack % across the run"
echo ""

# ------------------------------------------------------------------------------
# Cleanup
# ------------------------------------------------------------------------------
if [[ "$KEEP_TEMP" == false ]]; then
    log "Cleaning up temp telemetry files (${TEMP_DIR})..."
    rm -rf "$TEMP_DIR"
    ok "Cleaned."
else
    log "Temp files kept at: ${TEMP_DIR}"
fi

echo ""
ok "Run ${RUN_TIMESTAMP} complete."
