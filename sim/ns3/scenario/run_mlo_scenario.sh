#!/usr/bin/env bash
# run_mlo_scenario.sh
# Runs Wi-Fi 7 MLO backoff manipulation scenarios and converts output to pipeline format
#
# Usage: ./run_mlo_scenario.sh <EXP_ID> <SCENARIO> [SEED] [BIAS] [SIM_TIME]
#
# Arguments:
#   EXP_ID    - Experiment identifier (e.g., 20260103-1400-mlo-normal-42)
#   SCENARIO  - Scenario type: normal, positive, or negative
#   SEED      - Random seed (default: 42)
#   BIAS      - Attack bias override (default: scenario-specific)
#   SIM_TIME  - Simulation time in seconds (default: 50.0)
#
# Examples:
#   ./run_mlo_scenario.sh 20260103-1400-mlo-normal-42 normal
#   ./run_mlo_scenario.sh 20260103-1400-mlo-attack-pos-42 positive 42 5000
#   ./run_mlo_scenario.sh 20260103-1400-mlo-attack-neg-42 negative 42 -5000 60.0

set -euo pipefail

# --- Input Validation ---
EXP_ID="${1:-}"
SCENARIO="${2:-}"
SEED="${3:-42}"
BIAS_OVERRIDE="${4:-}"
SIM_TIME="${5:-50.0}"
if [ -z "${EXP_ID}" ] || [ -z "${SCENARIO}" ]; then
    echo "Usage: $0 <EXP_ID> <SCENARIO> [SEED] [BIAS] [SIM_TIME]"
    echo ""
    echo "SCENARIO options:"
    echo "  normal   - Baseline Wi-Fi 7 MLO (bias=0)"
    echo "  positive - Positive backoff bias attack (default bias=5000)"
    echo "  negative - Negative backoff bias attack (default bias=-5000)"
    echo ""
    echo "Examples:"
    echo "  $0 20260103-1400-mlo-normal-42 normal"
    echo "  $0 20260103-1400-mlo-attack-pos-42 positive 42 5000"
    exit 1
fi

# --- Scenario Configuration ---
case "${SCENARIO}" in
    normal)
        CC_FILE="wifi7-mlo-Normal.cc"
        DEFAULT_BIAS=0
        SCENARIO_LABEL="mlo-normal"
        ;;
    positive)
        CC_FILE="wifi7-mlo-Positive.cc"
        DEFAULT_BIAS=5000
        SCENARIO_LABEL="mlo-attack-positive"
        ;;
    negative)
        CC_FILE="wifi7-mlo-Negative.cc"
        DEFAULT_BIAS=-5000
        SCENARIO_LABEL="mlo-attack-negative"
        ;;
    *)
        echo "ERROR: Invalid scenario '${SCENARIO}'"
        echo "Valid options: normal, positive, negative"
        exit 1
        ;;
esac

# Use override bias if provided, otherwise use default
BIAS="${BIAS_OVERRIDE:-${DEFAULT_BIAS}}"

echo "=============================================="
echo "Wi-Fi 7 MLO Scenario Runner"
echo "=============================================="
echo "Experiment ID: ${EXP_ID}"
echo "Scenario:      ${SCENARIO_LABEL}"
echo "Source file:   ${CC_FILE}"
echo "Bias:          ${BIAS}"
echo "Seed:          ${SEED}"
echo "Sim time:      ${SIM_TIME}s"
echo "=============================================="

# --- Directory Setup ---
OUT_DIR="/work/sim/ns3/artifacts/${EXP_ID}"
mkdir -p "${OUT_DIR}"
STATUS_FILE="${OUT_DIR}/pipeline_status.json"
ACTIVE_STATUS_FILE="/work/sim/ns3/artifacts/.pipeline_active.json"

# --- Live Pipeline Status ---
CURRENT_STAGE="ns3"
CURRENT_STATE="idle"
LAST_WINDOWS=0
LAST_METRICS=0

write_pipeline_status() {
    local stage="${1:-ns3}"
    local state="${2:-idle}"
    local windows="${3:-0}"
    local metrics="${4:-0}"
    local updated_at
    updated_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

    CURRENT_STAGE="${stage}"
    CURRENT_STATE="${state}"
    LAST_WINDOWS="${windows}"
    LAST_METRICS="${metrics}"

    cat > "${STATUS_FILE}.tmp" <<EOF
{
  "experiment_id": "${EXP_ID}",
  "stage": "${stage}",
  "state": "${state}",
  "ns3_windows": ${windows},
  "metrics_count": ${metrics},
  "updated_at": "${updated_at}"
}
EOF
    mv -f "${STATUS_FILE}.tmp" "${STATUS_FILE}"
    cp -f "${STATUS_FILE}" "${ACTIVE_STATUS_FILE}" 2>/dev/null || true
}

clear_active_status() {
    if [ -f "${ACTIVE_STATUS_FILE}" ] && grep -Eq "\"experiment_id\"[[:space:]]*:[[:space:]]*\"${EXP_ID}\"" "${ACTIVE_STATUS_FILE}" 2>/dev/null; then
        rm -f "${ACTIVE_STATUS_FILE}"
    fi
}

cleanup_pipeline_status() {
    local rc=$?
    if [ "${rc}" -ne 0 ] && [ "${CURRENT_STATE}" = "active" ]; then
        write_pipeline_status "${CURRENT_STAGE}" "error" "${LAST_WINDOWS}" "${LAST_METRICS}"
    fi
    if [ "${CURRENT_STATE}" = "idle" ]; then
        clear_active_status
    fi
}
trap cleanup_pipeline_status EXIT

# --- Write Metadata ---
TS_NOW="$(date -Iseconds)"
{
    echo "exp_id=${EXP_ID}"
    echo "scenario=${SCENARIO_LABEL}"
    echo "bias=${BIAS}"
    echo "seed=${SEED}"
    echo "sim_time=${SIM_TIME}"
    echo "cc_file=${CC_FILE}"
    echo "ns3_version=$(cat /opt/ns-3-dev/VERSION 2>/dev/null || echo unknown)"
    echo "git_sha=$(cd /work && git rev-parse --short HEAD 2>/dev/null || echo unknown)"
    echo "start_time=${TS_NOW}"
} > "${OUT_DIR}/meta.txt"

echo "Metadata written to ${OUT_DIR}/meta.txt"

# --- Source File Check ---
SRC_FILE="/work/sim/ns3/scratch/${CC_FILE}"
DST_FILE="/opt/ns-3-dev/scratch/${CC_FILE}"

if [ ! -f "${SRC_FILE}" ]; then
    echo "ERROR: Source file not found: ${SRC_FILE}"
    exit 1
fi

# Copy to ns-3 scratch directory
cp -f "${SRC_FILE}" "${DST_FILE}"
echo "Copied ${CC_FILE} to ns-3 scratch"

# --- Run ns-3 Simulation ---
JSON_OUTPUT="${OUT_DIR}/mlo_output.json"

echo "Running ns-3 simulation..."
echo "  Output: ${JSON_OUTPUT}"

set +e
cd /opt/ns-3-dev
write_pipeline_status "ns3" "active" 0 0
./ns3 run "scratch/${CC_FILE%.cc}" -- \
    --bias="${BIAS}" \
    --time="${SIM_TIME}" \
    --jsonPath="${JSON_OUTPUT}" \
    > "${OUT_DIR}/ns3_stdout.log" \
    2> "${OUT_DIR}/ns3_stderr.log" &
ns3_pid=$!

while true; do
    if [ ! -r "/proc/${ns3_pid}/stat" ]; then
        break
    fi
    NS3_STATE=$(awk '{print $3}' "/proc/${ns3_pid}/stat" 2>/dev/null || echo "?")
    if [ "${NS3_STATE}" = "Z" ]; then
        break
    fi

    if [ -f "${JSON_OUTPUT}" ]; then
        LAST_WINDOWS=$(grep -c '"window":' "${JSON_OUTPUT}" 2>/dev/null || true)
    else
        LAST_WINDOWS=0
    fi
    if ! [[ "${LAST_WINDOWS}" =~ ^[0-9]+$ ]]; then
        LAST_WINDOWS=0
    fi
    LAST_METRICS=$((LAST_WINDOWS * 13))
    write_pipeline_status "ns3" "active" "${LAST_WINDOWS}" "${LAST_METRICS}"
    sleep 1
done

wait "${ns3_pid}"
rc=$?
set -e

if [ $rc -ne 0 ]; then
    write_pipeline_status "ns3" "error" "${LAST_WINDOWS}" "${LAST_METRICS}"
    echo "ERROR: ns-3 simulation failed with exit code $rc"
    echo "Check logs:"
    echo "  ${OUT_DIR}/ns3_stdout.log"
    echo "  ${OUT_DIR}/ns3_stderr.log"
    exit 1
fi

echo "Simulation completed successfully"

# --- Verify JSON Output ---
if [ ! -f "${JSON_OUTPUT}" ]; then
    echo "ERROR: JSON output not created: ${JSON_OUTPUT}"
    exit 1
fi

# Check if JSON file has content (without jq - may not be installed in container)
FILE_SIZE=$(stat -c%s "${JSON_OUTPUT}" 2>/dev/null || stat -f%z "${JSON_OUTPUT}" 2>/dev/null || echo 0)
if [ "${FILE_SIZE}" -lt 10 ]; then
    echo "ERROR: JSON output is empty or too small"
    exit 1
fi

# Count windows by counting opening braces for window objects (simple check)
WINDOW_COUNT=$(grep -c '"window":' "${JSON_OUTPUT}" 2>/dev/null || true)
if ! [[ "${WINDOW_COUNT}" =~ ^[0-9]+$ ]]; then
    WINDOW_COUNT=0
fi
echo "JSON output created: ${WINDOW_COUNT} windows (${FILE_SIZE} bytes)"
write_pipeline_status "ns3" "active" "${WINDOW_COUNT}" "$((WINDOW_COUNT * 13))"

# --- Convert to JSONL ---
echo "Converting JSON to JSONL format..."
/work/sim/ns3/scenario/convert_mlo_json_to_jsonl.sh \
    "${JSON_OUTPUT}" \
    "${EXP_ID}" \
    "${TS_NOW}"

# --- Verify JSONL Output ---
JSONL_FILE="${OUT_DIR}/telemetry.jsonl"
if [ ! -f "${JSONL_FILE}" ]; then
    echo "ERROR: JSONL output not created"
    exit 1
fi

JSONL_LINES=$(wc -l < "${JSONL_FILE}")
echo "JSONL output created: ${JSONL_LINES} metrics"
write_pipeline_status "ns3" "idle" "${WINDOW_COUNT}" "${JSONL_LINES}"

# --- Summary ---
echo ""
echo "=============================================="
echo "Scenario Complete!"
echo "=============================================="
echo "Artifacts directory: ${OUT_DIR}"
echo ""
echo "Files created:"
echo "  meta.txt          - Run metadata"
echo "  mlo_output.json   - Original JSON (for GNN training)"
echo "  telemetry.jsonl   - Pipeline-compatible JSONL"
echo "  pipeline_status.json - Live stage status (for dashboard)"
echo "  ns3_stdout.log    - Simulation stdout"
echo "  ns3_stderr.log    - Simulation stderr"
echo ""
echo "Next steps:"
echo "  1. Run exporter: make exporter-run EXP_ID=${EXP_ID}"
echo "  2. Or full pipeline: make run-mlo-exp EXP_ID=${EXP_ID} SCENARIO=${SCENARIO}"
echo "=============================================="
