#!/usr/bin/env bash
# generate_extended_dataset.sh
# Generate 256 MORE scenarios for ~2000 total GCN segments
# - 10 cores parallel (2/3 of 16)
# - 200s simulation time
# - 128 normal + 128 attack (perfect 50-50 balance)
# - Timeline: ~6.5 hours

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Configuration
MAX_PARALLEL=10  # Use 2/3 of cores (10/16)
SIM_TIME=200.0   # Fast mode
BATCH_SIZE=10    # 10 scenarios per batch

echo "========================================"
echo "WP9 Extended Dataset Generation"
echo "========================================"
echo "Goal: Generate 256 MORE scenarios"
echo "Current: 29 scenarios (~580 segments)"
echo "Target: 285 scenarios (~2000 segments)"
echo ""
echo "Mode: PARALLEL (10 scenarios at once)"
echo "Cores: 10 (2/3 of 16)"
echo "Sim time: ${SIM_TIME}s per scenario"
echo "Expected: ~6.5 hours"
echo "========================================"
echo ""

# Create directories
mkdir -p training_data_extended/scenarios/{normal/{light,moderate,dense,very_dense},positive_attack/bias_{0050,0100,0250,0500,1000,2500,5000,10000},negative_attack/bias_neg{0050,0100,0250,0500,1000,2500,5000,10000}}
mkdir -p training_data_extended/logs

# Manifest
MANIFEST="training_data_extended/manifest.csv"
echo "exp_id,scenario,bias,seed,sim_time,network_type,window_count,json_file,jsonl_file,timestamp" > "$MANIFEST"

# Progress tracking
echo "batch,scenarios_in_batch,status,timestamp" > training_data_extended/batch_progress.log

# Function to run scenario in background
run_scenario_bg() {
    local scenario=$1
    local bias=$2
    local seed=$3
    local sim_time=$4
    local network_type=$5
    local bias_label=$6
    local output_dir=$7

    local exp_id="extended-$(date +%Y%m%d)-${scenario}-${bias_label}-seed${seed}"
    local log_file="training_data_extended/logs/${exp_id}.log"

    (
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
        if [ -f "$json_file" ]; then
            window_count=$(grep -c '"window":' "$json_file" 2>/dev/null || echo 0)
            mkdir -p "$output_dir"
            cp "$json_file" "${output_dir}/${exp_id}.json"

            # Log to manifest
            timestamp=$(date -Iseconds)
            jsonl_file="sim/ns3/artifacts/${exp_id}/telemetry.jsonl"
            echo "${exp_id},${scenario},${bias},${seed},${sim_time},${network_type},${window_count},${json_file},${jsonl_file},${timestamp}" >> "$MANIFEST"
        fi
    ) > "$log_file" 2>&1 &
}

wait_batch() {
    local batch_num=$1
    echo "Waiting for batch $batch_num to complete..."
    wait
    timestamp=$(date -Iseconds)
    echo "${batch_num},10,complete,${timestamp}" >> training_data_extended/batch_progress.log
    echo "✅ Batch $batch_num complete"
    echo ""
}

# ========================================
# NORMAL SCENARIOS: 128 scenarios
# ========================================

echo "========================================"
echo "PHASE 1: Normal Scenarios (128 total)"
echo "========================================"

# Light network (40 scenarios) - 4 batches
for batch in {1..4}; do
    echo "Batch $batch: Light network (10 scenarios)"
    start_seed=$(( (batch-1) * 10 + 100 ))
    for i in {0..9}; do
        seed=$((start_seed + i))
        run_scenario_bg "normal" 0 $seed $SIM_TIME "light" "normal" "training_data_extended/scenarios/normal/light"
    done
    wait_batch $batch
done

# Moderate network (35 scenarios) - 3.5 batches → 4 batches
for batch in {5..7}; do
    echo "Batch $batch: Moderate network (10 scenarios)"
    start_seed=$(( (batch-5) * 10 + 200 ))
    for i in {0..9}; do
        seed=$((start_seed + i))
        run_scenario_bg "normal" 0 $seed $SIM_TIME "moderate" "normal" "training_data_extended/scenarios/normal/moderate"
    done
    wait_batch $batch
done

# Last 5 moderate
echo "Batch 8: Moderate network (5 scenarios)"
for seed in {230..234}; do
    run_scenario_bg "normal" 0 $seed $SIM_TIME "moderate" "normal" "training_data_extended/scenarios/normal/moderate"
done
# Fill batch with dense
for seed in {300..304}; do
    run_scenario_bg "normal" 0 $seed $SIM_TIME "dense" "normal" "training_data_extended/scenarios/normal/dense"
done
wait_batch 8

# Dense network (remaining 25) - 3 batches
for batch in {9..10}; do
    echo "Batch $batch: Dense network (10 scenarios)"
    start_seed=$(( (batch-9) * 10 + 305 ))
    for i in {0..9}; do
        seed=$((start_seed + i))
        run_scenario_bg "normal" 0 $seed $SIM_TIME "dense" "normal" "training_data_extended/scenarios/normal/dense"
    done
    wait_batch $batch
done

# Very dense network (23 scenarios) - 2.3 batches → 3 batches
for batch in {11..12}; do
    echo "Batch $batch: Very dense network (10 scenarios)"
    start_seed=$(( (batch-11) * 10 + 400 ))
    for i in {0..9}; do
        seed=$((start_seed + i))
        run_scenario_bg "normal" 0 $seed $SIM_TIME "very_dense" "normal" "training_data_extended/scenarios/normal/very_dense"
    done
    wait_batch $batch
done

echo "Batch 13: Very dense network (3 scenarios) + Positive attacks (7)"
for seed in {420..422}; do
    run_scenario_bg "normal" 0 $seed $SIM_TIME "very_dense" "normal" "training_data_extended/scenarios/normal/very_dense"
done

# ========================================
# POSITIVE ATTACKS: 64 scenarios (8 bias × 8 each)
# ========================================

echo "Starting positive attacks in batch 13..."

# 3 scenarios already queued, add 7 more for full batch
run_scenario_bg "positive" 50 100 $SIM_TIME "light" "bias_0050" "training_data_extended/scenarios/positive_attack/bias_0050"
run_scenario_bg "positive" 50 101 $SIM_TIME "light" "bias_0050" "training_data_extended/scenarios/positive_attack/bias_0050"
run_scenario_bg "positive" 100 100 $SIM_TIME "light" "bias_0100" "training_data_extended/scenarios/positive_attack/bias_0100"
run_scenario_bg "positive" 100 101 $SIM_TIME "light" "bias_0100" "training_data_extended/scenarios/positive_attack/bias_0100"
run_scenario_bg "positive" 250 100 $SIM_TIME "moderate" "bias_0250" "training_data_extended/scenarios/positive_attack/bias_0250"
run_scenario_bg "positive" 250 101 $SIM_TIME "moderate" "bias_0250" "training_data_extended/scenarios/positive_attack/bias_0250"
run_scenario_bg "positive" 500 100 $SIM_TIME "moderate" "bias_0500" "training_data_extended/scenarios/positive_attack/bias_0500"
wait_batch 13

# Continue with positive attacks - batches 14-19 (60 scenarios ÷ 10 = 6 batches)
# Simplified: Just generate all 8 bias levels × 8 scenarios each = 64 total
# Distribute across 6.4 batches → 7 batches

bias_levels=(50 50 50 50 50 50 50 50 100 100 100 100 100 100 100 100 250 250 250 250 250 250 250 250 500 500 500 500 500 500 500 500 1000 1000 1000 1000 1000 1000 1000 1000 2500 2500 2500 2500 2500 2500 2500 2500 5000 5000 5000 5000 5000 5000 5000 5000 10000 10000 10000 10000 10000 10000 10000)
batch_num=14
scenario_count=0

for bias in "${bias_levels[@]}"; do
    seed=$((100 + scenario_count))
    bias_label=$(printf "bias_%04d" $bias)
    run_scenario_bg "positive" $bias $seed $SIM_TIME "moderate" "$bias_label" "training_data_extended/scenarios/positive_attack/$bias_label"

    scenario_count=$((scenario_count + 1))

    if [ $((scenario_count % 10)) -eq 0 ]; then
        wait_batch $batch_num
        batch_num=$((batch_num + 1))
    fi
done

# ========================================
# NEGATIVE ATTACKS: 64 scenarios
# ========================================

echo "========================================"
echo "PHASE 3: Negative Attacks (64 scenarios)"
echo "========================================"

neg_bias_levels=(-50 -50 -50 -50 -50 -50 -50 -50 -100 -100 -100 -100 -100 -100 -100 -100 -250 -250 -250 -250 -250 -250 -250 -250 -500 -500 -500 -500 -500 -500 -500 -500 -1000 -1000 -1000 -1000 -1000 -1000 -1000 -1000 -2500 -2500 -2500 -2500 -2500 -2500 -2500 -2500 -5000 -5000 -5000 -5000 -5000 -5000 -5000 -5000 -10000 -10000 -10000 -10000 -10000 -10000 -10000 -10000)
scenario_count=0

for bias in "${neg_bias_levels[@]}"; do
    seed=$((100 + scenario_count))
    bias_abs=${bias#-}
    bias_label=$(printf "bias_neg%04d" $bias_abs)
    run_scenario_bg "negative" $bias $seed $SIM_TIME "moderate" "$bias_label" "training_data_extended/scenarios/negative_attack/$bias_label"

    scenario_count=$((scenario_count + 1))

    if [ $((scenario_count % 10)) -eq 0 ]; then
        wait_batch $batch_num
        batch_num=$((batch_num + 1))
    fi
done

# Wait for final batch
if [ $((scenario_count % 10)) -ne 0 ]; then
    wait_batch $batch_num
fi

# ========================================
# SUMMARY
# ========================================

echo ""
echo "========================================"
echo "Extended Dataset Generation Complete!"
echo "========================================"

normal_count=$(find training_data_extended/scenarios/normal -name "*.json" 2>/dev/null | wc -l)
positive_count=$(find training_data_extended/scenarios/positive_attack -name "*.json" 2>/dev/null | wc -l)
negative_count=$(find training_data_extended/scenarios/negative_attack -name "*.json" 2>/dev/null | wc -l)
total_new=$((normal_count + positive_count + negative_count))

echo "NEW scenarios generated:"
echo "  Normal:    $normal_count / 128"
echo "  Positive:  $positive_count / 64"
echo "  Negative:  $negative_count / 64"
echo "  Total:     $total_new / 256"
echo ""
echo "COMBINED with existing 29 scenarios:"
echo "  Total scenarios: $((total_new + 29))"
echo "  Estimated segments: ~2000 ✅"
echo ""
echo "Next: Combine datasets and prepare for GCN training"
echo "========================================"
