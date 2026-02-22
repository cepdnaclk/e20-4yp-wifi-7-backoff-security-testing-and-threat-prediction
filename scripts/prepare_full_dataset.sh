#!/usr/bin/env bash
# prepare_full_dataset.sh
# Organize full dataset (pilot + extended) for GCN training v2.0.0

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PIPELINE_DIR="$PWD"
GCN_DIR=~/github/wifi7_gcn_attack_detection

echo "========================================"
echo "WP9 Full Dataset Preparation"
echo "========================================"
echo "Combining pilot (29) + extended (255) = 284 scenarios"
echo ""

# Verify data generation complete
echo "Checking pilot data..."
pilot_normal=$(find training_data/scenarios/normal -name "*.json" 2>/dev/null | wc -l)
pilot_positive=$(find training_data/scenarios/positive_attack -name "*.json" 2>/dev/null | wc -l)
pilot_negative=$(find training_data/scenarios/negative_attack -name "*.json" 2>/dev/null | wc -l)
pilot_total=$((pilot_normal + pilot_positive + pilot_negative))

echo "Pilot data:"
echo "  Normal:    $pilot_normal"
echo "  Positive:  $pilot_positive"
echo "  Negative:  $pilot_negative"
echo "  Total:     $pilot_total"
echo ""

echo "Checking extended data..."
ext_normal=$(find training_data_extended/scenarios/normal -name "*.json" 2>/dev/null | wc -l)
ext_positive=$(find training_data_extended/scenarios/positive_attack -name "*.json" 2>/dev/null | wc -l)
ext_negative=$(find training_data_extended/scenarios/negative_attack -name "*.json" 2>/dev/null | wc -l)
ext_total=$((ext_normal + ext_positive + ext_negative))

echo "Extended data:"
echo "  Normal:    $ext_normal"
echo "  Positive:  $ext_positive"
echo "  Negative:  $ext_negative"
echo "  Total:     $ext_total"
echo ""

total_scenarios=$((pilot_total + ext_total))
echo "Combined total: $total_scenarios scenarios"
echo ""

if [ "$total_scenarios" -lt 250 ]; then
    echo "⚠️  WARNING: Only $total_scenarios scenarios found (expected ~284)"
    echo "Continue anyway? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        echo "Aborted."
        exit 1
    fi
fi

# Create GCN dataset directories
echo "Creating dataset directories in GCN repository..."
rm -rf "$GCN_DIR/data_v2_production"
mkdir -p "$GCN_DIR/data_v2_production"/{Normal,Attack}
mkdir -p "$GCN_DIR/data_v2_production_splits"

# Copy pilot normal scenarios
echo ""
echo "Copying pilot normal scenarios..."
pilot_normal_copied=0
for json_file in training_data/scenarios/normal/*/*.json; do
    if [ -f "$json_file" ]; then
        cp "$json_file" "$GCN_DIR/data_v2_production/Normal/"
        pilot_normal_copied=$((pilot_normal_copied + 1))
    fi
done
echo "Copied $pilot_normal_copied pilot normal scenarios"

# Copy extended normal scenarios
echo ""
echo "Copying extended normal scenarios..."
ext_normal_copied=0
for json_file in training_data_extended/scenarios/normal/*/*.json; do
    if [ -f "$json_file" ]; then
        cp "$json_file" "$GCN_DIR/data_v2_production/Normal/"
        ext_normal_copied=$((ext_normal_copied + 1))
    fi
done
echo "Copied $ext_normal_copied extended normal scenarios"

# Copy pilot attack scenarios
echo ""
echo "Copying pilot attack scenarios..."
pilot_attack_copied=0
for json_file in training_data/scenarios/positive_attack/*/*.json training_data/scenarios/negative_attack/*/*.json; do
    if [ -f "$json_file" ]; then
        cp "$json_file" "$GCN_DIR/data_v2_production/Attack/"
        pilot_attack_copied=$((pilot_attack_copied + 1))
    fi
done
echo "Copied $pilot_attack_copied pilot attack scenarios"

# Copy extended attack scenarios
echo ""
echo "Copying extended attack scenarios..."
ext_attack_copied=0
for json_file in training_data_extended/scenarios/positive_attack/*/*.json training_data_extended/scenarios/negative_attack/*/*.json; do
    if [ -f "$json_file" ]; then
        cp "$json_file" "$GCN_DIR/data_v2_production/Attack/"
        ext_attack_copied=$((ext_attack_copied + 1))
    fi
done
echo "Copied $ext_attack_copied extended attack scenarios"

# Combine manifests
echo ""
echo "Creating combined manifest..."
{
    echo "exp_id,scenario,bias,seed,sim_time,network_type,window_count,json_file,jsonl_file,timestamp"
    if [ -f "training_data/manifest_pilot.csv" ]; then
        tail -n +2 training_data/manifest_pilot.csv
    fi
    if [ -f "training_data_extended/manifest.csv" ]; then
        tail -n +2 training_data_extended/manifest.csv
    fi
} > "$GCN_DIR/data_v2_production_manifest.csv"
echo "✅ Manifest created"

# Verify
echo ""
echo "========================================"
echo "Verification"
echo "========================================"

gcn_normal_count=$(ls "$GCN_DIR/data_v2_production/Normal/" 2>/dev/null | wc -l)
gcn_attack_count=$(ls "$GCN_DIR/data_v2_production/Attack/" 2>/dev/null | wc -l)
gcn_total=$((gcn_normal_count + gcn_attack_count))

echo "Files in GCN repository:"
echo "  Normal: $gcn_normal_count"
echo "  Attack: $gcn_attack_count"
echo "  Total:  $gcn_total"
echo ""

normal_pct=$((gcn_normal_count * 100 / gcn_total))
attack_pct=$((gcn_attack_count * 100 / gcn_total))
echo "Distribution:"
echo "  Normal: $normal_pct%"
echo "  Attack: $attack_pct%"
echo ""

if [ "$normal_pct" -ge 45 ] && [ "$normal_pct" -le 55 ]; then
    echo "✅ BALANCED: Near 50-50 split!"
else
    echo "⚠️  Distribution: $normal_pct% normal vs $attack_pct% attack"
fi

# Calculate estimated GCN segments
avg_windows=2000  # 200s simulation ≈ 2000 windows
segment_size=256
segments_per_scenario=$((avg_windows / segment_size))
estimated_segments=$((gcn_total * segments_per_scenario))

echo ""
echo "Estimated GCN segments: ~$estimated_segments"
echo ""

echo "========================================"
echo "Dataset Ready for Training!"
echo "========================================"
echo "Location: $GCN_DIR/data_v2_production/"
echo "Manifest: $GCN_DIR/data_v2_production_manifest.csv"
echo ""
echo "Next step:"
echo "  ./scripts/train_full_model.sh"
echo ""
echo "Expected training time: 2-3 hours"
echo "Expected performance: F1 > 0.80, FPR < 10%"
echo "========================================"
