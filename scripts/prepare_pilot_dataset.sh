#!/usr/bin/env bash
# prepare_pilot_dataset.sh
# Organize pilot study data for GCN training

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PIPELINE_DIR="$PWD"
GCN_DIR=~/github/wifi7_gcn_attack_detection

echo "========================================"
echo "WP9 Pilot Dataset Preparation"
echo "========================================"
echo ""

# Verify data generation complete
normal_count=$(find training_data/scenarios/normal -name "*.json" 2>/dev/null | wc -l)
positive_count=$(find training_data/scenarios/positive_attack -name "*.json" 2>/dev/null | wc -l)
negative_count=$(find training_data/scenarios/negative_attack -name "*.json" 2>/dev/null | wc -l)
total_count=$((normal_count + positive_count + negative_count))

echo "Data generation status:"
echo "  Normal:    $normal_count / 15"
echo "  Positive:  $positive_count / 8"
echo "  Negative:  $negative_count / 7"
echo "  Total:     $total_count / 30"
echo ""

if [ "$total_count" -lt 30 ]; then
    echo "⚠️  WARNING: Only $total_count/30 scenarios generated"
    echo "Expected 30 scenarios. Continue anyway? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        echo "Aborted. Complete data generation first."
        exit 1
    fi
fi

# Create GCN dataset directories
echo "Creating dataset directories in GCN repository..."
mkdir -p "$GCN_DIR/data_v2_pilot"/{Normal,Attack}
mkdir -p "$GCN_DIR/data_v2_pilot_splits"

# Copy normal scenarios
echo ""
echo "Copying normal scenarios..."
normal_copied=0
for json_file in training_data/scenarios/normal/*/*.json; do
    if [ -f "$json_file" ]; then
        cp -v "$json_file" "$GCN_DIR/data_v2_pilot/Normal/"
        normal_copied=$((normal_copied + 1))
    fi
done
echo "Copied $normal_copied normal scenarios"

# Copy positive attack scenarios
echo ""
echo "Copying positive attack scenarios..."
positive_copied=0
for json_file in training_data/scenarios/positive_attack/*/*.json; do
    if [ -f "$json_file" ]; then
        cp -v "$json_file" "$GCN_DIR/data_v2_pilot/Attack/"
        positive_copied=$((positive_copied + 1))
    fi
done
echo "Copied $positive_copied positive attack scenarios"

# Copy negative attack scenarios
echo ""
echo "Copying negative attack scenarios..."
negative_copied=0
for json_file in training_data/scenarios/negative_attack/*/*.json; do
    if [ -f "$json_file" ]; then
        cp -v "$json_file" "$GCN_DIR/data_v2_pilot/Attack/"
        negative_copied=$((negative_copied + 1))
    fi
done
echo "Copied $negative_copied negative attack scenarios"

# Copy manifest
if [ -f "training_data/manifest_pilot.csv" ]; then
    cp -v training_data/manifest_pilot.csv "$GCN_DIR/data_v2_pilot_manifest.csv"
    echo "Manifest copied"
fi

# Verify
echo ""
echo "========================================"
echo "Verification"
echo "========================================"

gcn_normal_count=$(ls "$GCN_DIR/data_v2_pilot/Normal/" 2>/dev/null | wc -l)
gcn_attack_count=$(ls "$GCN_DIR/data_v2_pilot/Attack/" 2>/dev/null | wc -l)
gcn_total=$((gcn_normal_count + gcn_attack_count))

echo "Files in GCN repository:"
echo "  Normal: $gcn_normal_count"
echo "  Attack: $gcn_attack_count"
echo "  Total:  $gcn_total"
echo ""

if [ "$gcn_normal_count" -eq "$gcn_attack_count" ]; then
    echo "✅ BALANCED: Perfect 50-50 split!"
else
    echo "⚠️  Not perfectly balanced: $gcn_normal_count normal vs $gcn_attack_count attack"
fi

echo ""
echo "========================================"
echo "Dataset Ready for Training!"
echo "========================================"
echo "Location: $GCN_DIR/data_v2_pilot/"
echo "Manifest: $GCN_DIR/data_v2_pilot_manifest.csv"
echo ""
echo "Next steps:"
echo "  1. cd $GCN_DIR"
echo "  2. source venv/bin/activate"
echo "  3. python scripts/train.py \\"
echo "       --data-root data_v2_pilot \\"
echo "       --segment-length 256 \\"
echo "       --batch-size 32 \\"
echo "       --hidden-channels 64 \\"
echo "       --max-epochs 150 \\"
echo "       --device cuda"
echo ""
echo "Expected training time: 1-2 hours"
echo "Expected performance: F1 > 0.75, FPR < 15%"
echo "========================================"
