#!/usr/bin/env bash
# generate_pilot_parallel.sh
# PARALLEL VERSION: Run 4 scenarios simultaneously
# - Uses 4 cores (half of 16 available)
# - 200s simulation time (FAST mode)
# - Continue from scenario 9 (have 1-8)
# - ~90 minutes total (vs 5.5 hours sequential)

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Configuration
MAX_PARALLEL=4  # Use half the cores (8/16)
SIM_TIME=200.0  # Fast mode

echo "========================================"
echo "WP9 Pilot - PARALLEL Generation"
echo "========================================"
echo "Mode: PARALLEL (4 scenarios at once)"
echo "Simulation time: ${SIM_TIME}s per scenario"
echo "CPU cores used: 4 (half of 16)"
echo "Remaining: 22 scenarios"
echo "Expected time: ~90 minutes"
echo "========================================"
echo ""

# Create directories
mkdir -p training_data/scenarios/{normal/light,positive_attack/bias_{0050,0100,0500,1000,5000},negative_attack/bias_neg{0050,0100,0500,1000,5000}}
mkdir -p training_data/logs

# Manifest
MANIFEST="training_data/manifest_pilot.csv"
if [ ! -f "$MANIFEST" ]; then
    echo "exp_id,scenario,bias,seed,sim_time,network_type,window_count,json_file,jsonl_file,timestamp" > "$MANIFEST"
fi

# Function to run a single scenario in background
run_scenario_bg() {
    local scenario=$1
    local bias=$2
    local seed=$3
    local sim_time=$4
    local network_type=$5
    local bias_label=$6
    local output_dir=$7

    local exp_id="pilot-$(date +%Y%m%d)-${scenario}-${bias_label}-seed${seed}"
    local log_file="training_data/logs/${exp_id}.log"

    echo "Starting: $exp_id (background)" >> training_data/parallel_progress.log

    # Run in background, redirect output to log
    (
        echo "========================================"
        echo "Running: $exp_id"
        echo "  Scenario: $scenario"
        echo "  Bias: $bias"
        echo "  Seed: $seed"
        echo "  Sim time: ${sim_time}s"
        echo "========================================"

        # Run simulation
        if [ "$scenario" = "normal" ]; then
            docker run --rm \
              --user "$(id -u):$(id -g)" \
              -v "$PWD":/work \
              ndt/ns3:local \
              bash -lc "/work/sim/ns3/scenario/run_mlo_scenario.sh $exp_id normal $seed 0 $sim_time"
        elif [ "$scenario" = "positive" ]; then
            docker run --rm \
              --user "$(id -u):$(id -g)" \
              -v "$PWD":/work \
              ndt/ns3:local \
              bash -lc "/work/sim/ns3/scenario/run_mlo_scenario.sh $exp_id positive $seed $bias $sim_time"
        elif [ "$scenario" = "negative" ]; then
            docker run --rm \
              --user "$(id -u):$(id -g)" \
              -v "$PWD":/work \
              ndt/ns3:local \
              bash -lc "/work/sim/ns3/scenario/run_mlo_scenario.sh $exp_id negative $seed $bias $sim_time"
        fi

        # Copy to training data
        json_file="sim/ns3/artifacts/${exp_id}/mlo_output.json"
        jsonl_file="sim/ns3/artifacts/${exp_id}/telemetry.jsonl"

        if [ -f "$json_file" ]; then
            window_count=$(grep -c '"window":' "$json_file" 2>/dev/null || echo 0)
            mkdir -p "$output_dir"
            cp "$json_file" "${output_dir}/${exp_id}.json"

            # Log to manifest
            timestamp=$(date -Iseconds)
            echo "${exp_id},${scenario},${bias},${seed},${sim_time},${network_type},${window_count},${json_file},${jsonl_file},${timestamp}" >> "$MANIFEST"

            echo "✅ Complete: $exp_id ($window_count windows)" >> training_data/parallel_progress.log
        else
            echo "❌ Failed: $exp_id" >> training_data/parallel_progress.log
        fi
    ) > "$log_file" 2>&1 &
}

# Function to wait for parallel jobs to finish
wait_for_batch() {
    local batch_name=$1
    echo ""
    echo "Waiting for batch to complete: $batch_name"
    wait
    echo "✅ Batch complete: $batch_name"
}

# Track progress
echo "exp_id,status,timestamp" > training_data/parallel_progress.log

# ========================================
# BATCH 1: Normal 9-12 (4 parallel)
# ========================================
echo ""
echo "========================================"
echo "BATCH 1: Normal scenarios 9-12"
echo "========================================"
for seed in 9 10 11 12; do
    run_scenario_bg "normal" 0 $seed $SIM_TIME "light" "normal" "training_data/scenarios/normal/light"
done
wait_for_batch "Batch 1 (Normal 9-12)"

# ========================================
# BATCH 2: Normal 13-15 + Positive 1 (4 parallel)
# ========================================
echo ""
echo "========================================"
echo "BATCH 2: Normal 13-15 + Positive 1"
echo "========================================"
run_scenario_bg "normal" 0 13 $SIM_TIME "light" "normal" "training_data/scenarios/normal/light"
run_scenario_bg "normal" 0 14 $SIM_TIME "light" "normal" "training_data/scenarios/normal/light"
run_scenario_bg "normal" 0 15 $SIM_TIME "light" "normal" "training_data/scenarios/normal/light"
run_scenario_bg "positive" 50 1 $SIM_TIME "light" "bias_0050" "training_data/scenarios/positive_attack/bias_0050"
wait_for_batch "Batch 2 (Normal 13-15 + Pos 1)"

# ========================================
# BATCH 3: Positive 2-5 (4 parallel)
# ========================================
echo ""
echo "========================================"
echo "BATCH 3: Positive attacks 2-5"
echo "========================================"
run_scenario_bg "positive" 50 2 $SIM_TIME "light" "bias_0050" "training_data/scenarios/positive_attack/bias_0050"
run_scenario_bg "positive" 100 1 $SIM_TIME "light" "bias_0100" "training_data/scenarios/positive_attack/bias_0100"
run_scenario_bg "positive" 100 2 $SIM_TIME "light" "bias_0100" "training_data/scenarios/positive_attack/bias_0100"
run_scenario_bg "positive" 500 1 $SIM_TIME "moderate" "bias_0500" "training_data/scenarios/positive_attack/bias_0500"
wait_for_batch "Batch 3 (Positive 2-5)"

# ========================================
# BATCH 4: Positive 6-8 + Negative 1 (4 parallel)
# ========================================
echo ""
echo "========================================"
echo "BATCH 4: Positive 6-8 + Negative 1"
echo "========================================"
run_scenario_bg "positive" 1000 1 $SIM_TIME "moderate" "bias_1000" "training_data/scenarios/positive_attack/bias_1000"
run_scenario_bg "positive" 5000 1 $SIM_TIME "dense" "bias_5000" "training_data/scenarios/positive_attack/bias_5000"
run_scenario_bg "positive" 5000 2 $SIM_TIME "dense" "bias_5000" "training_data/scenarios/positive_attack/bias_5000"
run_scenario_bg "negative" -50 1 $SIM_TIME "light" "bias_neg0050" "training_data/scenarios/negative_attack/bias_neg0050"
wait_for_batch "Batch 4 (Pos 6-8 + Neg 1)"

# ========================================
# BATCH 5: Negative 2-5 (4 parallel)
# ========================================
echo ""
echo "========================================"
echo "BATCH 5: Negative attacks 2-5"
echo "========================================"
run_scenario_bg "negative" -50 2 $SIM_TIME "light" "bias_neg0050" "training_data/scenarios/negative_attack/bias_neg0050"
run_scenario_bg "negative" -100 1 $SIM_TIME "light" "bias_neg0100" "training_data/scenarios/negative_attack/bias_neg0100"
run_scenario_bg "negative" -500 1 $SIM_TIME "moderate" "bias_neg0500" "training_data/scenarios/negative_attack/bias_neg0500"
run_scenario_bg "negative" -1000 1 $SIM_TIME "moderate" "bias_neg1000" "training_data/scenarios/negative_attack/bias_neg1000"
wait_for_batch "Batch 5 (Negative 2-5)"

# ========================================
# BATCH 6: Negative 6-7 (2 parallel)
# ========================================
echo ""
echo "========================================"
echo "BATCH 6: Negative attacks 6-7"
echo "========================================"
run_scenario_bg "negative" -5000 1 $SIM_TIME "dense" "bias_neg5000" "training_data/scenarios/negative_attack/bias_neg5000"
run_scenario_bg "negative" -5000 2 $SIM_TIME "dense" "bias_neg5000" "training_data/scenarios/negative_attack/bias_neg5000"
wait_for_batch "Batch 6 (Negative 6-7)"

# ========================================
# SUMMARY
# ========================================
echo ""
echo "========================================"
echo "PARALLEL Generation Complete!"
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
echo "BALANCED 50-50 DISTRIBUTION:"
echo "  Normal: $normal_count"
echo "  Attack: $attack_count"
if [ "$normal_count" -eq "$attack_count" ]; then
    echo "  ✅ BALANCED: Perfect 50-50 split!"
fi
echo ""
echo "Mode: PARALLEL (4 concurrent, 200s simulation)"
echo "CPU usage: 4 cores (50% of available)"
echo ""
echo "Next: ./scripts/prepare_pilot_dataset.sh"
echo "========================================"
