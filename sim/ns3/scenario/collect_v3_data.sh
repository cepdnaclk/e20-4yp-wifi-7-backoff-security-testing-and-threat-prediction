#!/usr/bin/env bash
# Parallel NS-3 data collection for GCN v3 training dataset
# Usage: NCPU=8 SIM_TIME=80 bash sim/ns3/scenario/collect_v3_data.sh
# Runs all 72 simulations (6 AP configs × 3 scenarios × 4 seeds) in parallel
#
# Each job calls: make run-mlo-{scenario} EXP_ID=... NAP=N NSTA=M SEED=S SIM_TIME=80
#   V3_COLLECT=1 causes run_mlo_scenario.sh to copy mlo_output.json to
#   twin/gnn/training_data/v3/Normal/ or /Attack/ after each run.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "${REPO_ROOT}"

NCPU="${NCPU:-$(nproc)}"
SIM_TIME="${SIM_TIME:-80}"
V3_DATA_DIR="${V3_DATA_DIR:-twin/gnn/training_data/v3}"
SEEDS=(42 43 44 45)
AP_STA_PAIRS=("1:2" "2:4" "3:6" "4:8" "5:10" "6:12")
SCENARIOS=("normal" "positive" "negative")

mkdir -p "${V3_DATA_DIR}/Attack" "${V3_DATA_DIR}/Normal"
LOG_FILE="${V3_DATA_DIR}/collection.log"

echo "========================================="
echo "GCN v3 Data Collection"
echo "  Cores:     ${NCPU}"
echo "  Sim time:  ${SIM_TIME}s"
echo "  Output:    ${V3_DATA_DIR}"
echo "  Log:       ${LOG_FILE}"
echo "========================================="

# Build job list — each job is a make invocation
JOBS=()
JOB_TAGS=()
for AP_STA in "${AP_STA_PAIRS[@]}"; do
    NAP="${AP_STA%%:*}"
    NSTA="${AP_STA##*:}"
    for SCENARIO in "${SCENARIOS[@]}"; do
        for SEED in "${SEEDS[@]}"; do
            TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
            TAG="nap${NAP}_nsta${NSTA}_seed${SEED}_${SCENARIO}_${SIM_TIME}s"
            EXP_ID="${TIMESTAMP}-v3collect-${TAG}"
            # Map scenario name to make target suffix
            case "${SCENARIO}" in
                normal)   MAKE_TARGET="run-mlo-normal"   ;;
                positive) MAKE_TARGET="run-mlo-positive" ;;
                negative) MAKE_TARGET="run-mlo-negative" ;;
            esac
            JOBS+=("make ${MAKE_TARGET} EXP_ID=${EXP_ID} NAP=${NAP} NSTA=${NSTA} SEED=${SEED} SIM_TIME=${SIM_TIME} V3_COLLECT=1 V3_DATA_DIR=${V3_DATA_DIR}")
            JOB_TAGS+=("${TAG}")
        done
    done
done

TOTAL="${#JOBS[@]}"
echo "Total jobs: ${TOTAL}"
echo "" | tee -a "${LOG_FILE}"

run_job() {
    local job="$1"
    local idx="$2"
    local tag="${JOB_TAGS[$((idx - 1))]}"
    echo "[${idx}/${TOTAL}] START: ${tag}"
    if eval "${job}" >> "${LOG_FILE}" 2>&1; then
        echo "[${idx}/${TOTAL}] DONE:  ${tag}"
        return 0
    else
        echo "[${idx}/${TOTAL}] FAIL:  ${tag}" >&2
        return 1
    fi
}
export -f run_job
export TOTAL
export -a JOB_TAGS

# GNU parallel if available, else bash semaphore
if command -v parallel &>/dev/null; then
    echo "Using GNU parallel with ${NCPU} workers"
    seq 1 "${TOTAL}" | \
        parallel -j "${NCPU}" --progress \
        'run_job "${JOBS[$(({}  - 1))]}" {}'
    # Note: GNU parallel approach — export JOBS array
    export JOBS_STR
    JOBS_STR=$(printf '%s\n' "${JOBS[@]}")
    printf '%s\n' "${JOBS[@]}" | \
        parallel -j "${NCPU}" --progress \
        --env TOTAL --env JOB_TAGS \
        'idx={#}; job="{}"; tag="${JOB_TAGS[$((idx-1))]}"; echo "[${idx}/${TOTAL}] START: ${tag}"; if eval "${job}" >> "'"${LOG_FILE}"'" 2>&1; then echo "[${idx}/${TOTAL}] DONE: ${tag}"; else echo "[${idx}/${TOTAL}] FAIL: ${tag}" >&2; fi'
else
    echo "GNU parallel not found — using bash semaphore (${NCPU} workers)"
    pids=()
    idx=0
    for job in "${JOBS[@]}"; do
        (( ++idx ))
        (
            tag="${JOB_TAGS[$((idx - 1))]}"
            echo "[${idx}/${TOTAL}] START: ${tag}"
            if eval "${job}" >> "${LOG_FILE}" 2>&1; then
                echo "[${idx}/${TOTAL}] DONE:  ${tag}"
            else
                echo "[${idx}/${TOTAL}] FAIL:  ${tag}" >&2
            fi
        ) &
        pids+=($!)
        # Throttle to NCPU concurrent jobs
        while (( ${#pids[@]} >= NCPU )); do
            new_pids=()
            for p in "${pids[@]}"; do
                if kill -0 "${p}" 2>/dev/null; then
                    new_pids+=("${p}")
                fi
            done
            pids=("${new_pids[@]}")
            (( ${#pids[@]} >= NCPU )) && sleep 1
        done
    done
    wait
fi

echo ""
echo "========================================="
echo "Data collection complete!"
NORMAL_COUNT=$(ls "${V3_DATA_DIR}/Normal/"*.json 2>/dev/null | wc -l)
ATTACK_COUNT=$(ls "${V3_DATA_DIR}/Attack/"*.json 2>/dev/null | wc -l)
echo "  Normal:  ${NORMAL_COUNT} files"
echo "  Attack:  ${ATTACK_COUNT} files"
echo "  Total:   $(( NORMAL_COUNT + ATTACK_COUNT )) / ${TOTAL} expected"
echo "  Log:     ${LOG_FILE}"
echo "========================================="
