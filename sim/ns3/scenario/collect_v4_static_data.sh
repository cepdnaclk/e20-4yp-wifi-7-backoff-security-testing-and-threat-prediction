#!/usr/bin/env bash
# GCN v4 static data collection.
# Topology: nap 1-4 only (nap 5-6 excluded — too slow).
# Attack bias range: 1000, 2000, 5000 (train/val) + 500, 4000 additional (test only).
# Seed pools: train=42..333, val=777/888/444, test=555/999/1234  — strictly disjoint.
# Output goes to pre-partitioned v4 folder structure (train/val/test) — no random split.
#
# Usage:
#   NCPU=8 bash collect_v4_static_data.sh [--split train|val|test]
#   NCPU=8 SPLIT=train bash collect_v4_static_data.sh
#
# Output structure:
#   <V4_DATA_DIR>/train/Static/Normal/  nap2_nsta4_seed42_normal_80s.json
#   <V4_DATA_DIR>/train/Static/Attack/  nap2_nsta4_seed42_positive1000_80s.json
#   <V4_DATA_DIR>/val/Static/Normal/
#   <V4_DATA_DIR>/val/Static/Attack/
#   <V4_DATA_DIR>/test/Static/Normal/
#   <V4_DATA_DIR>/test/Static/Attack/
#
# Pipeline isolation: these runs never touch Kafka / Harmonizer / Windowizer.
# The NS-3 container writes mlo_output.json to artifacts/, which is then
# copied to the training data dir via V4_COLLECT=1.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "${REPO_ROOT}"

NCPU="${NCPU:-$(nproc)}"
# V4_DATA_DIR_ABS is the absolute host path for mkdir/ls operations.
# V4_DATA_DIR_REL is the REPO-RELATIVE path passed to make (Docker maps /work → REPO_ROOT).
V4_DATA_DIR_ABS="${V4_DATA_DIR:-${REPO_ROOT}/twin/gnn/training_data/v4}"
V4_DATA_DIR_REL="${V4_DATA_DIR_ABS#${REPO_ROOT}/}"

# Parse --split flag
SPLIT="${SPLIT:-train}"
for arg in "$@"; do
    case "${arg}" in
        --split=*) SPLIT="${arg#*=}" ;;
        --split)   shift; SPLIT="${1:-train}" ;;
    esac
done

echo "============================================================"
echo "GCN v4 STATIC Data Collection"
echo "  Split:   ${SPLIT}"
echo "  Cores:   ${NCPU}"
echo "  Output:  ${V4_DATA_DIR_ABS}"
echo "============================================================"

# ── Seed pools ─────────────────────────────────────────────────────────────
case "${SPLIT}" in
    train) SEEDS=(42 123 456 789 321 654 987 111 222 333) ;;
    val)   SEEDS=(777 888 444) ;;
    test)  SEEDS=(555 999 1234) ;;
    *)     echo "ERROR: SPLIT must be train|val|test"; exit 1 ;;
esac

AP_STA_PAIRS=("1:2" "2:4" "3:2" "4:2")   # nap1-4; nap3/4 use 2 STA to keep sim time manageable
SCENARIOS=("normal" "positive" "negative")

# ── Output directories ──────────────────────────────────────────────────────
# ABS paths for host-side mkdir/ls; REL paths for make (Docker /work mounting)
OUT_NORMAL_ABS="${V4_DATA_DIR_ABS}/${SPLIT}/Static/Normal"
OUT_ATTACK_ABS="${V4_DATA_DIR_ABS}/${SPLIT}/Static/Attack"
OUT_NORMAL_REL="${V4_DATA_DIR_REL}/${SPLIT}/Static/Normal"
OUT_ATTACK_REL="${V4_DATA_DIR_REL}/${SPLIT}/Static/Attack"
mkdir -p "${OUT_NORMAL_ABS}" "${OUT_ATTACK_ABS}"
LOG_FILE="${V4_DATA_DIR_ABS}/collection_static_${SPLIT}.log"
echo "Log: ${LOG_FILE}"

# ── Attack bias values by split ────────────────────────────────────────────
# Train: 1000, 2000, 5000 (covers full attack range)
# Val:   5000 only (standard evaluation during training)
# Test:  500, 1000, 2000, 4000, 5000 (full evaluation range — test generalisation)
case "${SPLIT}" in
    train) ATTACK_BIASES=(1000 2000 5000) ;;
    val)   ATTACK_BIASES=(5000) ;;
    test)  ATTACK_BIASES=(500 1000 2000 4000 5000) ;;
esac

# ── Build job list ─────────────────────────────────────────────────────────
JOBS=()
JOB_TAGS=()

for AP_STA in "${AP_STA_PAIRS[@]}"; do
    NAP="${AP_STA%%:*}"
    NSTA="${AP_STA##*:}"

    for SEED in "${SEEDS[@]}"; do
        for SCENARIO in "${SCENARIOS[@]}"; do

            if [ "${SCENARIO}" = "normal" ]; then
                # Normal — bias=0, one file per seed/nap, 80s
                TAG="nap${NAP}_nsta${NSTA}_seed${SEED}_normal_80s"
                TS="$(date +%Y%m%d-%H%M%S)"
                EXP_ID="${TS}-v4s-${TAG}"
                JOBS+=("make run-mlo-normal EXP_ID=${EXP_ID} NAP=${NAP} NSTA=${NSTA} SEED=${SEED} SIM_TIME=80 V4_COLLECT=1 V4_DATA_DIR=${OUT_NORMAL_REL} V4_TAG=${TAG}")
                JOB_TAGS+=("${TAG}")
            else
                # Attack — one file per bias value
                for BIAS in "${ATTACK_BIASES[@]}"; do
                    TAG="nap${NAP}_nsta${NSTA}_seed${SEED}_${SCENARIO}${BIAS}_80s"
                    TS="$(date +%Y%m%d-%H%M%S)"
                    EXP_ID="${TS}-v4s-${TAG}"
                    BIAS_ARG="${BIAS}"
                    [ "${SCENARIO}" = "negative" ] && BIAS_ARG="-${BIAS}"

                    case "${SCENARIO}" in
                        positive) MAKE_TARGET="run-mlo-positive" ;;
                        negative) MAKE_TARGET="run-mlo-negative" ;;
                    esac

                    JOBS+=("make ${MAKE_TARGET} EXP_ID=${EXP_ID} NAP=${NAP} NSTA=${NSTA} SEED=${SEED} SIM_TIME=80 BIAS=${BIAS_ARG} V4_COLLECT=1 V4_DATA_DIR=${OUT_ATTACK_REL} V4_TAG=${TAG}")
                    JOB_TAGS+=("${TAG}")
                done
            fi

        done
    done
done

TOTAL="${#JOBS[@]}"
echo "Total jobs: ${TOTAL}" | tee -a "${LOG_FILE}"
echo "Starting with ${NCPU} parallel workers..."

# ── Parallel runner ────────────────────────────────────────────────────────
pids=()
idx=0
for job in "${JOBS[@]}"; do
    (( ++idx ))
    job_idx=${idx}
    tag="${JOB_TAGS[$((job_idx - 1))]}"
    (
        # Determine destination dir for this tag
        if [[ "${tag}" == *"_normal_"* ]]; then
            DEST_DIR="${OUT_NORMAL_ABS}"
        else
            DEST_DIR="${OUT_ATTACK_ABS}"
        fi
        if [ -f "${DEST_DIR}/${tag}.json" ]; then
            echo "[${job_idx}/${TOTAL}] SKIP:  ${tag} (already exists)"
        else
            echo "[${job_idx}/${TOTAL}] START: ${tag}"
            if eval "${job}" >> "${LOG_FILE}" 2>&1; then
                echo "[${job_idx}/${TOTAL}] DONE:  ${tag}"
            else
                echo "[${job_idx}/${TOTAL}] FAIL:  ${tag}" >&2
            fi
        fi
    ) &
    pids+=($!)

    while (( ${#pids[@]} >= NCPU )); do
        new_pids=()
        for p in "${pids[@]}"; do
            kill -0 "${p}" 2>/dev/null && new_pids+=("${p}")
        done
        pids=("${new_pids[@]}")
        (( ${#pids[@]} >= NCPU )) && sleep 1
    done
done
wait

echo ""
echo "============================================================"
echo "Static collection complete! (${SPLIT})"
N=$(ls "${OUT_NORMAL_ABS}"/*.json 2>/dev/null | wc -l)
A=$(ls "${OUT_ATTACK_ABS}"/*.json 2>/dev/null | wc -l)
echo "  Normal: ${N} files"
echo "  Attack: ${A} files"
echo "  Total:  $(( N + A )) / ${TOTAL} expected"
echo "  Log:    ${LOG_FILE}"
echo "============================================================"
