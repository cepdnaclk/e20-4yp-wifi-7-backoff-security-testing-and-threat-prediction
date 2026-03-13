#!/usr/bin/env bash
# Parallel NS-3 data collection for GCN v3 training dataset
# Usage: NCPU=8 SIM_TIME=80 bash sim/ns3/scenario/collect_v3_data.sh
# Runs all 72 simulations (6 AP configs × 3 scenarios × 4 seeds) in parallel

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "${REPO_ROOT}"

NCPU="${NCPU:-$(nproc)}"
SIM_TIME="${SIM_TIME:-80}"
V3_DATA_DIR="${V3_DATA_DIR:-twin/gnn/training_data/v3}"
SEEDS=(42 43 44 45)
# nAp:nSta pairs
AP_STA_PAIRS=("1:2" "2:4" "3:6" "4:8" "5:10" "6:12")
SCENARIOS=("normal" "positive" "negative")

mkdir -p "${V3_DATA_DIR}/Attack" "${V3_DATA_DIR}/Normal"

echo "========================================="
echo "GCN v3 Data Collection"
echo "  Cores:     ${NCPU}"
echo "  Sim time:  ${SIM_TIME}s"
echo "  Output:    ${V3_DATA_DIR}"
echo "========================================="

# Build job list
JOBS=()
for AP_STA in "${AP_STA_PAIRS[@]}"; do
    NAP="${AP_STA%%:*}"
    NSTA="${AP_STA##*:}"
    for SCENARIO in "${SCENARIOS[@]}"; do
        for SEED in "${SEEDS[@]}"; do
            TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
            TAG="nap${NAP}_nsta${NSTA}_seed${SEED}_${SCENARIO}_${SIM_TIME}s"
            EXP_ID="${TIMESTAMP}-${TAG}"
            JOBS+=("NAP=${NAP} NSTA=${NSTA} SEED=${SEED} SIM_TIME=${SIM_TIME} V3_COLLECT=1 V3_DATA_DIR=${V3_DATA_DIR} bash sim/ns3/scenario/run_mlo_scenario.sh ${EXP_ID} ${SCENARIO}")
        done
    done
done

TOTAL="${#JOBS[@]}"
echo "Total jobs: ${TOTAL}"
COMPLETED=0

run_job() {
    local job="$1"
    local idx="$2"
    echo "[${idx}/${TOTAL}] Starting: ${job}"
    if eval "${job}" >> "${V3_DATA_DIR}/collection.log" 2>&1; then
        echo "[${idx}/${TOTAL}] DONE"
    else
        echo "[${idx}/${TOTAL}] FAILED: ${job}" >&2
    fi
}
export -f run_job
export TOTAL

# GNU parallel if available, else bash semaphore
if command -v parallel &>/dev/null; then
    printf '%s\n' "${JOBS[@]}" | \
        parallel -j "${NCPU}" --progress \
        run_job {} {#}
else
    echo "GNU parallel not found — using bash semaphore"
    pids=()
    idx=0
    for job in "${JOBS[@]}"; do
        (( ++idx ))
        run_job "${job}" "${idx}" &
        pids+=($!)
        # Wait if at max concurrency
        while (( ${#pids[@]} >= NCPU )); do
            for i in "${!pids[@]}"; do
                if ! kill -0 "${pids[$i]}" 2>/dev/null; then
                    unset 'pids[$i]'
                fi
            done
            pids=("${pids[@]}")  # reindex
            sleep 0.5
        done
    done
    wait
fi

echo ""
echo "========================================="
echo "Data collection complete!"
echo "  Normal:  $(ls "${V3_DATA_DIR}/Normal/"*.json 2>/dev/null | wc -l) files"
echo "  Attack:  $(ls "${V3_DATA_DIR}/Attack/"*.json 2>/dev/null | wc -l) files"
echo "========================================="
