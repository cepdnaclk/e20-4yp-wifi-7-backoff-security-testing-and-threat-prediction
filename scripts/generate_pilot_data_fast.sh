#!/usr/bin/env bash
# generate_pilot_data_fast.sh
# FAST VERSION: 200s simulation time instead of 1400s
# Generate remaining pilot scenarios (9-15 normal + all attacks)
# - Continue from scenario 9 (already have 1-8)
# - 22 scenarios remaining
# - ~200s simulation time = ~15 min per scenario
# - Total time: ~5-6 hours

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================"
echo "WP9 Pilot Study - FAST Data Generation"
echo "========================================"
echo "Mode: FAST (200s simulation time)"
echo "Continuing from: Scenario 9"
echo "Remaining: 22 scenarios"
echo "  - Normal: 7 (scenarios 9-15)"
echo "  - Positive attacks: 8"
echo "  - Negative attacks: 7"
echo "Expected time: 5-6 hours (vs 38+ hours with 1400s)"
echo "========================================"
echo ""

# Create directories (already exist, but safe to re-run)
mkdir -p training_data/scenarios/{normal/light,positive_attack/bias_{0050,0100,0500,1000,5000},negative_attack/bias_neg{0050,0100,0500,1000,5000}}
mkdir -p training_data/logs

# Use existing manifest or create new
MANIFEST="training_data/manifest_pilot.csv"
if [ ! -f "$MANIFEST" ]; then
    echo "exp_id,scenario,bias,seed,sim_time,network_type,window_count,json_file,jsonl_file,timestamp" > "$MANIFEST"
fi

# Helper function to run scenario
run_scenario() {
    local scenario=$1    # normal, positive, negative
    local bias=$2        # bias value
    local seed=$3        # random seed
    local sim_time=$4    # simulation time (NOW 200s instead of 1400s)
    local network_type=$5  # light, moderate, dense, very_dense
    local bias_label=$6  # for directory name (e.g., bias_0050)
    local output_dir=$7  # relative path to output dir

    local exp_id="pilot-$(date +%Y%m%d)-${scenario}-${bias_label}-seed${seed}"

    echo ""
    echo "========================================"
    echo "Running: $exp_id"
    echo "  Scenario: $scenario"
    echo "  Bias: $bias"
    echo "  Seed: $seed"
    echo "  Network: $network_type"
    echo "  Sim time: ${sim_time}s ⚡ FAST MODE"
    echo "========================================"

    # Run simulation (non-interactive mode)
    if [ "$scenario" = "normal" ]; then
        docker run --rm \
          --user "$(id -u):$(id -g)" \
          -v "$PWD":/work \
          ndt/ns3:local \
          bash -lc "/work/sim/ns3/scenario/run_mlo_scenario.sh $exp_id normal $seed 0 $sim_time" || {
            echo "ERROR: Simulation failed for $exp_id"
            return 1
        }
    elif [ "$scenario" = "positive" ]; then
        docker run --rm \
          --user "$(id -u):$(id -g)" \
          -v "$PWD":/work \
          ndt/ns3:local \
          bash -lc "/work/sim/ns3/scenario/run_mlo_scenario.sh $exp_id positive $seed $bias $sim_time" || {
            echo "ERROR: Simulation failed for $exp_id"
            return 1
        }
    elif [ "$scenario" = "negative" ]; then
        docker run --rm \
          --user "$(id -u):$(id -g)" \
          -v "$PWD":/work \
          ndt/ns3:local \
          bash -lc "/work/sim/ns3/scenario/run_mlo_scenario.sh $exp_id negative $seed $bias $sim_time" || {
            echo "ERROR: Simulation failed for $exp_id"
            return 1
        }
    fi

    # Verify outputs
    json_file="sim/ns3/artifacts/${exp_id}/mlo_output.json"
    jsonl_file="sim/ns3/artifacts/${exp_id}/telemetry.jsonl"

    if [ ! -f "$json_file" ]; then
        echo "ERROR: JSON output not found: $json_file"
        return 1
    fi

    window_count=$(grep -c '"window":' "$json_file" 2>/dev/null || echo 0)

    # Copy to training data directory
    mkdir -p "$output_dir"
    cp "$json_file" "${output_dir}/${exp_id}.json"

    # Log to manifest
    timestamp=$(date -Iseconds)
    echo "${exp_id},${scenario},${bias},${seed},${sim_time},${network_type},${window_count},${json_file},${jsonl_file},${timestamp}" >> "$MANIFEST"

    echo "✅ Complete: $exp_id ($window_count windows)"
}

# ========================================
# PHASE 1: REMAINING NORMAL SCENARIOS (7 files)
# ========================================

echo ""
echo "========================================"
echo "Phase 1: Generating remaining NORMAL scenarios"
echo "Already have: 1-8 (from previous run)"
echo "Generating: 9-15 (7 scenarios)"
echo "========================================"

# Continue from seed 9
for seed in $(seq 9 15); do
    run_scenario "normal" 0 $seed 200.0 "light" "normal" \
        "training_data/scenarios/normal/light"
done

# ========================================
# PHASE 2: POSITIVE ATTACKS (8 files)
# ========================================

echo ""
echo "========================================"
echo "Phase 2: Generating POSITIVE attacks"
echo "Target: 8 files"
echo "Bias levels: 50, 100, 500, 1000, 5000"
echo "========================================"

# Bias 50 (2 scenarios)
run_scenario "positive" 50 1 200.0 "light" "bias_0050" \
    "training_data/scenarios/positive_attack/bias_0050"
run_scenario "positive" 50 2 200.0 "light" "bias_0050" \
    "training_data/scenarios/positive_attack/bias_0050"

# Bias 100 (2 scenarios)
run_scenario "positive" 100 1 200.0 "light" "bias_0100" \
    "training_data/scenarios/positive_attack/bias_0100"
run_scenario "positive" 100 2 200.0 "light" "bias_0100" \
    "training_data/scenarios/positive_attack/bias_0100"

# Bias 500 (1 scenario)
run_scenario "positive" 500 1 200.0 "moderate" "bias_0500" \
    "training_data/scenarios/positive_attack/bias_0500"

# Bias 1000 (1 scenario)
run_scenario "positive" 1000 1 200.0 "moderate" "bias_1000" \
    "training_data/scenarios/positive_attack/bias_1000"

# Bias 5000 (2 scenarios)
run_scenario "positive" 5000 1 200.0 "dense" "bias_5000" \
    "training_data/scenarios/positive_attack/bias_5000"
run_scenario "positive" 5000 2 200.0 "dense" "bias_5000" \
    "training_data/scenarios/positive_attack/bias_5000"

# ========================================
# PHASE 3: NEGATIVE ATTACKS (7 files)
# ========================================

echo ""
echo "========================================"
echo "Phase 3: Generating NEGATIVE attacks"
echo "Target: 7 files"
echo "Bias levels: -50, -100, -500, -1000, -5000"
echo "========================================"

# Bias -50 (2 scenarios)
run_scenario "negative" -50 1 200.0 "light" "bias_neg0050" \
    "training_data/scenarios/negative_attack/bias_neg0050"
run_scenario "negative" -50 2 200.0 "light" "bias_neg0050" \
    "training_data/scenarios/negative_attack/bias_neg0050"

# Bias -100 (1 scenario)
run_scenario "negative" -100 1 200.0 "light" "bias_neg0100" \
    "training_data/scenarios/negative_attack/bias_neg0100"

# Bias -500 (1 scenario)
run_scenario "negative" -500 1 200.0 "moderate" "bias_neg0500" \
    "training_data/scenarios/negative_attack/bias_neg0500"

# Bias -1000 (1 scenario)
run_scenario "negative" -1000 1 200.0 "moderate" "bias_neg1000" \
    "training_data/scenarios/negative_attack/bias_neg1000"

# Bias -5000 (2 scenarios)
run_scenario "negative" -5000 1 200.0 "dense" "bias_neg5000" \
    "training_data/scenarios/negative_attack/bias_neg5000"
run_scenario "negative" -5000 2 200.0 "dense" "bias_neg5000" \
    "training_data/scenarios/negative_attack/bias_neg5000"

# ========================================
# SUMMARY
# ========================================

echo ""
echo "========================================"
echo "FAST Pilot Data Generation Complete!"
echo "========================================"

normal_count=$(find training_data/scenarios/normal -name "*.json" 2>/dev/null | wc -l)
positive_count=$(find training_data/scenarios/positive_attack -name "*.json" 2>/dev/null | wc -l)
negative_count=$(find training_data/scenarios/negative_attack -name "*.json" 2>/dev/null | wc -l)
total_count=$((normal_count + positive_count + negative_count))
attack_count=$((positive_count + negative_count))

echo "Normal scenarios:    $normal_count / 15 expected"
echo "Positive attacks:    $positive_count / 8 expected"
echo "Negative attacks:    $negative_count / 7 expected"
echo "Total:               $total_count / 30 expected"
echo ""
echo "BALANCED 50-50 DISTRIBUTION CHECK:"
echo "  Normal: $normal_count (target: 15 = 50%)"
echo "  Attack: $attack_count (target: 15 = 50%)"
if [ "$normal_count" -eq "$attack_count" ]; then
    echo "  ✅ BALANCED: Perfect 50-50 split!"
else
    echo "  ⚠️  Close to balanced: $normal_count normal vs $attack_count attack"
fi
echo ""
echo "Mode: FAST (200s simulation time)"
echo "Avg windows per scenario: ~2,000 (sufficient for pilot)"
echo ""
echo "Manifest: $MANIFEST"
echo ""
echo "Next steps:"
echo "  1. Review manifest: cat $MANIFEST"
echo "  2. Run dataset preparation: ./scripts/prepare_pilot_dataset.sh"
echo "  3. Train model: ./scripts/train_pilot_model.sh"
echo "========================================"
