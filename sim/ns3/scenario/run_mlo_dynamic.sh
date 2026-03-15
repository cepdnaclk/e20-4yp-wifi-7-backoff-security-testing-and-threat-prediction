#!/usr/bin/env bash
# run_mlo_dynamic.sh
# Runs the Wi-Fi 7 MLO dynamic-phase backoff scenario.
# Bias changes mid-simulation according to a phase schedule, letting us test
# how the GCN model handles windows that span phase transitions.
#
# Usage:
#   ./run_mlo_dynamic.sh <EXP_ID> <PHASES>
#
# Arguments:
#   EXP_ID  - Experiment identifier (e.g., 20260315-2200-mlo-dynamic-42)
#   PHASES  - Phase schedule: "t0:b0,t1:b1,..." (time in seconds, bias integer)
#             First phase must start at t=0.
#             Example: "0:0,20:5000,40:-5000,60:0"
#
# Environment variables (all optional):
#   SEED      - Random seed (default: 42)
#   SIM_TIME  - Total simulation time in seconds (default: 80)
#   NAP       - Number of access points (default: 1)
#   NSTA      - Stations per AP (default: 2)
#
# Examples:
#   ./run_mlo_dynamic.sh 20260315-2200-mlo-dynamic-42 "0:0,20:5000,40:-5000,60:0"
#   SEED=99 SIM_TIME=120 ./run_mlo_dynamic.sh 20260315-2230-mlo-dynamic-99 "0:5000,30:0,60:5000"
#   NAP=2 NSTA=4 ./run_mlo_dynamic.sh 20260315-2300-mlo-dynamic-2ap "0:0,20:5000,40:0"

set -euo pipefail

# --- Inputs ---
EXP_ID="${1:-}"
PHASES="${2:-}"
SEED="${SEED:-42}"
SIM_TIME="${SIM_TIME:-80}"
NAP="${NAP:-1}"
NSTA="${NSTA:-2}"

if [ -z "${EXP_ID}" ] || [ -z "${PHASES}" ]; then
    echo "Usage: $0 <EXP_ID> <PHASES>"
    echo ""
    echo "PHASES format: 't0:b0,t1:b1,...'"
    echo "  t0 must be 0 (sets initial bias)"
    echo "  b0 is the bias at t0 (0=normal, 5000=positive attack, -5000=negative attack)"
    echo ""
    echo "Examples:"
    echo "  $0 20260315-2200-mlo-dyn-42 '0:0,20:5000,40:-5000,60:0'"
    echo "  $0 20260315-2200-mlo-dyn-42 '0:5000,40:0'"
    exit 1
fi

CC_FILE="wifi7-mlo-Dynamic.cc"

echo "=============================================="
echo "Wi-Fi 7 MLO Dynamic Phase Runner"
echo "=============================================="
echo "Experiment ID: ${EXP_ID}"
echo "Phase schedule: ${PHASES}"
echo "Seed:          ${SEED}"
echo "Sim time:      ${SIM_TIME}s"
echo "nAP:           ${NAP}"
echo "nSTA (per AP): ${NSTA}"
echo "=============================================="

# --- Directory Setup ---
OUT_DIR="/work/sim/ns3/artifacts/${EXP_ID}"
mkdir -p "${OUT_DIR}"
STATUS_FILE="${OUT_DIR}/pipeline_status.json"
ACTIVE_STATUS_FILE="/work/sim/ns3/artifacts/.pipeline_active.json"

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
    if [ -f "${ACTIVE_STATUS_FILE}" ] && \
       grep -Eq "\"experiment_id\"[[:space:]]*:[[:space:]]*\"${EXP_ID}\"" "${ACTIVE_STATUS_FILE}" 2>/dev/null; then
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
    echo "scenario=dynamic"
    echo "phases=${PHASES}"
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

cp -f "${SRC_FILE}" "${DST_FILE}"
echo "Copied ${CC_FILE} to ns-3 scratch"

# --- Run ns-3 Simulation ---
JSON_OUTPUT="${OUT_DIR}/mlo_output.json"

echo "Running ns-3 dynamic simulation..."
echo "  Output: ${JSON_OUTPUT}"

set +e
cd /opt/ns-3-dev
write_pipeline_status "ns3" "active" 0 0
./ns3 run "scratch/${CC_FILE%.cc}" -- \
    --nAp="${NAP}" \
    --nSta="${NSTA}" \
    --seed="${SEED}" \
    --time="${SIM_TIME}" \
    --phases="${PHASES}" \
    --jsonPath="${JSON_OUTPUT}" \
    > "${OUT_DIR}/ns3_stdout.log" \
    2> "${OUT_DIR}/ns3_stderr.log" &
ns3_pid=$!

while true; do
    if [ ! -r "/proc/${ns3_pid}/stat" ]; then break; fi
    NS3_STATE=$(awk '{print $3}' "/proc/${ns3_pid}/stat" 2>/dev/null || echo "?")
    if [ "${NS3_STATE}" = "Z" ]; then break; fi

    if [ -f "${JSON_OUTPUT}" ]; then
        LAST_WINDOWS=$(grep -c '"window":' "${JSON_OUTPUT}" 2>/dev/null || true)
    else
        LAST_WINDOWS=0
    fi
    if ! [[ "${LAST_WINDOWS}" =~ ^[0-9]+$ ]]; then LAST_WINDOWS=0; fi
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

FILE_SIZE=$(stat -c%s "${JSON_OUTPUT}" 2>/dev/null || stat -f%z "${JSON_OUTPUT}" 2>/dev/null || echo 0)
if [ "${FILE_SIZE}" -lt 10 ]; then
    echo "ERROR: JSON output is empty or too small"
    exit 1
fi

WINDOW_COUNT=$(grep -c '"window":' "${JSON_OUTPUT}" 2>/dev/null || true)
if ! [[ "${WINDOW_COUNT}" =~ ^[0-9]+$ ]]; then WINDOW_COUNT=0; fi
echo "JSON output created: ${WINDOW_COUNT} windows (${FILE_SIZE} bytes)"
write_pipeline_status "ns3" "active" "${WINDOW_COUNT}" "$((WINDOW_COUNT * 13))"

# --- Copy to v4 dynamic training data if requested ---
# V4_DATA_DIR = destination directory (e.g. twin/gnn/training_data/v4/Dynamic)
# V4_TAG = canonical filename tag (without .json)
if [ -n "${V4_COLLECT:-}" ]; then
    V4_DEST_DIR="${V4_DATA_DIR:-twin/gnn/training_data/v4/Dynamic}"
    V4_FILE_TAG="${V4_TAG:-${EXP_ID}_dynamic}"
    mkdir -p "${V4_DEST_DIR}"
    cp "${JSON_OUTPUT}" "${V4_DEST_DIR}/${V4_FILE_TAG}.json"
    echo "[v4collect] Saved ${V4_DEST_DIR}/${V4_FILE_TAG}.json"
fi

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
echo "Dynamic Scenario Complete!"
echo "=============================================="
echo "Experiment ID: ${EXP_ID}"
echo "Phase schedule: ${PHASES}"
echo "Artifacts:     ${OUT_DIR}"
echo ""
echo "Files created:"
echo "  meta.txt            - Run metadata (includes phase schedule)"
echo "  mlo_output.json     - Raw JSON (bias changes per window)"
echo "  telemetry.jsonl     - Pipeline-compatible JSONL"
echo "  pipeline_status.json"
echo "  ns3_stdout.log / ns3_stderr.log"
echo ""
echo "Next steps:"
echo "  make exporter-run EXP_ID=${EXP_ID}"
echo "  # Then check predictions in Grafana/Dashboard"
echo "=============================================="
