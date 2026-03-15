#!/usr/bin/env bash
# GCN v4 dynamic data collection.
# Runs multi-phase NS-3 scenarios covering all 25 training + 5 held-out test patterns.
#
# Topology:  nap 1-4 only (nap5-6 excluded — generation is too slow).
# Bias:      ±5000 (standard) for groups A/B/C.  ±1000/2000 (weak) for group E.
# Threshold: 0.3 applied at training time — not relevant for data collection.
# Seeds:     train=42,123,456,789,321,654 | val=777,888 | test=555,999,1234
#
# Usage:
#   NCPU=8 bash collect_v4_dynamic_data.sh [--split train|val|test]
#   NCPU=8 PATTERNS=A,B bash collect_v4_dynamic_data.sh --split train
#
# Output:
#   <V4_DATA_DIR>/train/Dynamic/   nap2_nsta4_seed42_D01_norm-pos_80s.json
#   <V4_DATA_DIR>/val/Dynamic/
#   <V4_DATA_DIR>/test/Dynamic/    (includes held-out T-patterns)
#
# Pipeline isolation: only NS-3 container is used.
# No Kafka / Harmonizer / Windowizer / Dashboard interaction.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "${REPO_ROOT}"

NCPU="${NCPU:-$(nproc)}"
V4_DATA_DIR_ABS="${V4_DATA_DIR:-${REPO_ROOT}/twin/gnn/training_data/v4}"
V4_DATA_DIR_REL="${V4_DATA_DIR_ABS#${REPO_ROOT}/}"

SPLIT="${SPLIT:-train}"
PATTERNS_FILTER="${PATTERNS:-}"   # e.g. "A,B" to run only groups A and B
for arg in "$@"; do
    case "${arg}" in
        --split=*)    SPLIT="${arg#*=}" ;;
        --split)      shift; SPLIT="${1:-train}" ;;
        --patterns=*) PATTERNS_FILTER="${arg#*=}" ;;
    esac
done

echo "============================================================"
echo "GCN v4 DYNAMIC Data Collection"
echo "  Split:    ${SPLIT}"
echo "  Patterns: ${PATTERNS_FILTER:-all for split}"
echo "  Cores:    ${NCPU}"
echo "  Output:   ${V4_DATA_DIR_ABS}"
echo "============================================================"

# ── Seed pools ─────────────────────────────────────────────────────────────
case "${SPLIT}" in
    train) SEEDS=(42 123 456 789 321 654) ;;
    val)   SEEDS=(777 888) ;;
    test)  SEEDS=(555 999 1234) ;;
    *)     echo "ERROR: SPLIT must be train|val|test"; exit 1 ;;
esac

AP_STA_PAIRS=("1:2" "2:4" "3:2" "4:2")   # nap1-4; nap3/4 use 2 STA to keep sim time manageable

OUT_DIR_ABS="${V4_DATA_DIR_ABS}/${SPLIT}/Dynamic"
OUT_DIR_REL="${V4_DATA_DIR_REL}/${SPLIT}/Dynamic"
mkdir -p "${OUT_DIR_ABS}"
LOG_FILE="${V4_DATA_DIR_ABS}/collection_dynamic_${SPLIT}.log"
echo "Log: ${LOG_FILE}"

# ── Phase pattern catalogue ────────────────────────────────────────────────
# Format: "ID|NAME|PHASES|SIM_TIME|GROUP|SEED_SUBSET"
# SEED_SUBSET: "all" = use all split seeds; "core" = use first 4 seeds only
declare -a PATTERNS_ALL

# GROUP A: 2-phase (80s, bias=±5000) — all 6 split seeds
PATTERNS_ALL+=("D-01|norm-pos|0:0,40:5000|80|A|all")
PATTERNS_ALL+=("D-02|norm-neg|0:0,40:-5000|80|A|all")
PATTERNS_ALL+=("D-03|pos-norm|0:5000,40:0|80|A|all")
PATTERNS_ALL+=("D-04|neg-norm|0:-5000,40:0|80|A|all")
PATTERNS_ALL+=("D-05|pos-neg|0:5000,40:-5000|80|A|all")
PATTERNS_ALL+=("D-06|neg-pos|0:-5000,40:5000|80|A|all")

# GROUP B: 3-phase (120s, bias=±5000) — all split seeds
PATTERNS_ALL+=("D-07|norm-pos-norm|0:0,40:5000,80:0|120|B|all")
PATTERNS_ALL+=("D-08|norm-neg-norm|0:0,40:-5000,80:0|120|B|all")
PATTERNS_ALL+=("D-09|neg-norm-pos|0:-5000,40:0,80:5000|120|B|all")
PATTERNS_ALL+=("D-10|pos-norm-neg|0:5000,40:0,80:-5000|120|B|all")
PATTERNS_ALL+=("D-11|pos-neg-pos|0:5000,40:-5000,80:5000|120|B|all")
PATTERNS_ALL+=("D-12|neg-pos-neg|0:-5000,40:5000,80:-5000|120|B|all")

# GROUP C: 4-phase (160s, bias=±5000) — first 4 seeds (longer sim)
PATTERNS_ALL+=("D-13|neg-norm-pos-norm|0:-5000,40:0,80:5000,120:0|160|C|core")
PATTERNS_ALL+=("D-14|norm-pos-norm-neg|0:0,40:5000,80:0,120:-5000|160|C|core")
PATTERNS_ALL+=("D-15|pos-norm-neg-norm|0:5000,40:0,80:-5000,120:0|160|C|core")
PATTERNS_ALL+=("D-16|neg-pos-norm-neg|0:-5000,40:5000,80:0,120:-5000|160|C|core")

# GROUP D: uneven transition timings (diversity) — first 4 seeds
PATTERNS_ALL+=("D-17|neg-norm-early|0:-5000,27:0|80|D|core")
PATTERNS_ALL+=("D-18|norm-pos-late|0:0,53:5000|80|D|core")
PATTERNS_ALL+=("D-19|neg-norm-pos-uneven|0:-5000,30:0,70:5000|120|D|core")
PATTERNS_ALL+=("D-20|pos-neg-early|0:5000,15:-5000|80|D|core")
PATTERNS_ALL+=("D-21|norm-neg-narrow|0:0,30:-5000,50:0|80|D|core")

# GROUP E: weak bias (±1000, ±2000) — trains sensitivity to low-strength attacks
PATTERNS_ALL+=("D-22|norm-pos-weak1000|0:0,40:1000|80|E|core")
PATTERNS_ALL+=("D-23|norm-neg-weak1000|0:0,40:-1000|80|E|core")
PATTERNS_ALL+=("D-24|neg-norm-pos-2000|0:-2000,40:0,80:2000|120|E|core")
PATTERNS_ALL+=("D-25|pos-norm-neg-2000|0:2000,40:0,80:-2000|120|E|core")

# GROUP T: test-only 5-phase (200s) — NEVER used in train or val
PATTERNS_ALL+=("T-01|norm-neg-norm-pos-norm|0:0,40:-5000,80:0,120:5000,160:0|200|T|all")
PATTERNS_ALL+=("T-02|pos-norm-pos-neg-norm|0:5000,40:0,80:5000,120:-5000,160:0|200|T|all")
PATTERNS_ALL+=("T-03|neg-norm-neg-pos-neg|0:-5000,40:0,80:-5000,120:5000,160:-5000|200|T|all")
PATTERNS_ALL+=("T-04|pos-neg-pos-norm-neg|0:5000,40:-5000,80:5000,120:0,160:-5000|200|T|all")
PATTERNS_ALL+=("T-05|norm-pos-neg-pos-norm|0:0,40:5000,80:-5000,120:5000,160:0|200|T|all")

# ── Filter patterns for this split ─────────────────────────────────────────
PATTERNS_FOR_SPLIT=()
for p in "${PATTERNS_ALL[@]}"; do
    IFS='|' read -r pid pname phases sim_time group seed_subset <<< "${p}"

    case "${SPLIT}" in
        train)
            # Train: groups A B C D E — NOT T
            [[ "${group}" == "T" ]] && continue
            ;;
        val)
            # Val: subset of A B C — representative patterns only
            # Use D-01,D-04,D-07,D-09,D-13,D-14
            [[ "${group}" =~ ^[DE]$ || "${group}" == "T" ]] && continue
            [[ ! "${pid}" =~ ^(D-0[147]|D-09|D-1[34])$ ]] && continue
            ;;
        test)
            # Test: T-patterns (held-out) + D-01,D-09,D-13 for coverage
            if [[ "${group}" != "T" ]]; then
                [[ ! "${pid}" =~ ^(D-01|D-09|D-13)$ ]] && continue
            fi
            ;;
    esac

    # Apply --patterns filter if provided
    if [ -n "${PATTERNS_FILTER}" ]; then
        [[ "${PATTERNS_FILTER}" != *"${group}"* ]] && continue
    fi

    PATTERNS_FOR_SPLIT+=("${p}")
done

echo "Patterns selected for split '${SPLIT}': ${#PATTERNS_FOR_SPLIT[@]}"

# ── Build job list ─────────────────────────────────────────────────────────
JOBS=()
JOB_TAGS=()

# "core" seeds = first 4 of the split's seed list
CORE_SEEDS=("${SEEDS[@]:0:4}")

for p in "${PATTERNS_FOR_SPLIT[@]}"; do
    IFS='|' read -r pid pname phases sim_time group seed_subset <<< "${p}"

    SEED_LIST=("${SEEDS[@]}")
    [ "${seed_subset}" = "core" ] && SEED_LIST=("${CORE_SEEDS[@]}")

    for AP_STA in "${AP_STA_PAIRS[@]}"; do
        NAP="${AP_STA%%:*}"
        NSTA="${AP_STA##*:}"

        for SEED in "${SEED_LIST[@]}"; do
            TAG="nap${NAP}_nsta${NSTA}_seed${SEED}_${pid}_${pname}_${sim_time}s"
            TS="$(date +%Y%m%d-%H%M%S)"
            EXP_ID="${TS}-v4d-${TAG}"

            JOBS+=("make run-mlo-dynamic EXP_ID=${EXP_ID} PHASES='${phases}' NAP=${NAP} NSTA=${NSTA} SEED=${SEED} SIM_TIME=${sim_time} V4_COLLECT=1 V4_DATA_DIR=${OUT_DIR_REL} V4_TAG=${TAG}")
            JOB_TAGS+=("${TAG}")
        done
    done
done

TOTAL="${#JOBS[@]}"
echo "Total dynamic jobs: ${TOTAL}" | tee -a "${LOG_FILE}"
echo "Starting with ${NCPU} parallel workers..."

# ── Parallel runner ────────────────────────────────────────────────────────
pids=()
idx=0
for job in "${JOBS[@]}"; do
    (( ++idx ))
    job_idx=${idx}
    tag="${JOB_TAGS[$((job_idx - 1))]}"
    (
        if [ -f "${OUT_DIR_ABS}/${tag}.json" ]; then
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
echo "Dynamic collection complete! (${SPLIT})"
COUNT=$(ls "${OUT_DIR_ABS}"/*.json 2>/dev/null | wc -l)
echo "  Dynamic: ${COUNT} files"
echo "  Expected: ${TOTAL}"
echo "  Log: ${LOG_FILE}"
echo "============================================================"

# Quick sanity: verify bias changes in a dynamic file
SAMPLE=$(ls "${OUT_DIR_ABS}"/*.json 2>/dev/null | head -1)
if [ -n "${SAMPLE}" ]; then
    python3 - <<PYEOF 2>/dev/null || true
import json, collections
with open("${SAMPLE}") as f:
    w = json.load(f)
biases = collections.Counter(x.get('bias', 0) for x in w)
print(f"Sample: ${SAMPLE##*/}")
print(f"  Windows: {len(w)}, Unique biases: {dict(biases)}")
PYEOF
fi
