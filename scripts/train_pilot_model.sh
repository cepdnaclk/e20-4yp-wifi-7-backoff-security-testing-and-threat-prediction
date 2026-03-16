#!/usr/bin/env bash
# train_pilot_model.sh
# Train GCN model v2.0.0-pilot on balanced 50-50 dataset

set -euo pipefail

GCN_DIR=~/github/wifi7_gcn_attack_detection

echo "========================================"
echo "WP9 Pilot Model Training"
echo "========================================"
echo ""

# Check if dataset prepared
if [ ! -d "$GCN_DIR/data_v2_pilot/Normal" ] || [ ! -d "$GCN_DIR/data_v2_pilot/Attack" ]; then
    echo "❌ ERROR: Dataset not prepared"
    echo "Run: ./scripts/prepare_pilot_dataset.sh"
    exit 1
fi

# Count files
normal_count=$(ls "$GCN_DIR/data_v2_pilot/Normal/" 2>/dev/null | wc -l)
attack_count=$(ls "$GCN_DIR/data_v2_pilot/Attack/" 2>/dev/null | wc -l)
total_count=$((normal_count + attack_count))

echo "Dataset verification:"
echo "  Normal files: $normal_count"
echo "  Attack files: $attack_count"
echo "  Total:        $total_count"
echo ""

if [ "$total_count" -lt 20 ]; then
    echo "⚠️  WARNING: Only $total_count files found (expected 30)"
    echo "Continue anyway? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        exit 1
    fi
fi

# Check Python environment
cd "$GCN_DIR"

if [ ! -d "venv" ]; then
    echo "❌ ERROR: Virtual environment not found"
    echo "Create it with: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

echo "Activating virtual environment..."
source venv/bin/activate

# Verify PyTorch installation
python -c "import torch; print(f'PyTorch {torch.__version__} (CUDA available: {torch.cuda.is_available()})')" || {
    echo "❌ ERROR: PyTorch not installed"
    echo "Install with: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118"
    exit 1
}

echo ""
echo "========================================"
echo "Starting Training"
echo "========================================"
echo "Dataset: data_v2_pilot (pilot study, 50-50 balanced)"
echo "Segment length: 256 windows"
echo "Batch size: 32"
echo "Hidden channels: 64"
echo "Max epochs: 150"
echo "Device: cuda (GPU) if available, else cpu"
echo ""
echo "Expected duration: 1-2 hours"
echo "========================================"
echo ""

# Create output directory for pilot model
mkdir -p models/v2.0.0-pilot

# Run training
python scripts/train.py \
    --data-root data_v2_pilot \
    --segment-length 256 \
    --batch-size 32 \
    --hidden-channels 64 \
    --max-epochs 150 \
    --device cuda \
    2>&1 | tee training_pilot.log

# Check if training completed
if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "Training Complete!"
    echo "========================================"

    # Copy model artifacts
    if [ -f "checkpoints/best_model.pt" ]; then
        cp checkpoints/best_model.pt models/v2.0.0-pilot/
        echo "✅ Model saved: models/v2.0.0-pilot/best_model.pt"
    fi

    if [ -f "checkpoints/scaler.json" ]; then
        cp checkpoints/scaler.json models/v2.0.0-pilot/
        echo "✅ Scaler saved: models/v2.0.0-pilot/scaler.json"
    fi

    echo ""
    echo "Training log: $GCN_DIR/training_pilot.log"
    echo ""

    # Extract final metrics
    echo "Final metrics:"
    grep -A 10 "Test Results\|Final" training_pilot.log | tail -15 || echo "Check training_pilot.log for metrics"

    echo ""
    echo "Next steps:"
    echo "  1. Review metrics in training_pilot.log"
    echo "  2. Check if F1 > 0.75 and FPR < 15%"
    echo "  3. If successful: Proceed with full 256-scenario dataset"
    echo "  4. If not: Debug and investigate issues"
else
    echo ""
    echo "❌ Training failed!"
    echo "Check log: $GCN_DIR/training_pilot.log"
    exit 1
fi
