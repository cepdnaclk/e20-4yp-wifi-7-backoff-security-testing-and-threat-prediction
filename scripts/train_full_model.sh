#!/usr/bin/env bash
# train_full_model.sh
# Train GCN model v2.0.0 (production) on full balanced dataset (284 scenarios)

set -euo pipefail

GCN_DIR=~/github/wifi7_gcn_attack_detection

echo "========================================"
echo "WP9 Production Model Training"
echo "========================================"
echo "Training GCN model v2.0.0 on 284 scenarios"
echo ""

# Check if dataset prepared
if [ ! -d "$GCN_DIR/data_v2_production/Normal" ] || [ ! -d "$GCN_DIR/data_v2_production/Attack" ]; then
    echo "❌ ERROR: Dataset not prepared"
    echo "Run: ./scripts/prepare_full_dataset.sh"
    exit 1
fi

# Count files
normal_count=$(ls "$GCN_DIR/data_v2_production/Normal/" 2>/dev/null | wc -l)
attack_count=$(ls "$GCN_DIR/data_v2_production/Attack/" 2>/dev/null | wc -l)
total_count=$((normal_count + attack_count))

echo "Dataset verification:"
echo "  Normal files: $normal_count"
echo "  Attack files: $attack_count"
echo "  Total:        $total_count"
echo ""

if [ "$total_count" -lt 250 ]; then
    echo "⚠️  WARNING: Only $total_count files found (expected ~284)"
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
echo "Dataset: data_v2_production (284 scenarios, 50-50 balanced)"
echo "Segment length: 256 windows"
echo "Batch size: 32"
echo "Hidden channels: 64"
echo "Max epochs: 200"
echo "Device: cuda (GPU) if available, else cpu"
echo ""
echo "Target metrics:"
echo "  - F1 Score: > 0.80"
echo "  - False Positive Rate: < 10%"
echo "  - Recall: > 0.85"
echo ""
echo "Expected duration: 2-3 hours"
echo "========================================"
echo ""

# Create output directory for production model
mkdir -p models/v2.0.0

# Run training
python scripts/train.py \
    --data-root data_v2_production \
    --segment-length 256 \
    --batch-size 32 \
    --hidden-channels 64 \
    --max-epochs 200 \
    --device cuda \
    2>&1 | tee training_v2.0.0.log

# Check if training completed
if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "Training Complete!"
    echo "========================================"

    # Copy model artifacts
    if [ -f "checkpoints/best_model.pt" ]; then
        cp checkpoints/best_model.pt models/v2.0.0/
        echo "✅ Model saved: models/v2.0.0/best_model.pt"
    fi

    if [ -f "checkpoints/scaler.json" ]; then
        cp checkpoints/scaler.json models/v2.0.0/
        echo "✅ Scaler saved: models/v2.0.0/scaler.json"
    fi

    # Create config file
    cat > models/v2.0.0/config.yaml <<EOF
# GCN Model v2.0.0 Configuration
version: "2.0.0"
created: $(date -Iseconds)
dataset: "data_v2_production"
scenarios: $total_count
distribution: "50-50 balanced"
segment_length: 256
batch_size: 32
hidden_channels: 64
max_epochs: 200
device: cuda
training_log: "training_v2.0.0.log"
EOF
    echo "✅ Config saved: models/v2.0.0/config.yaml"

    echo ""
    echo "Training log: $GCN_DIR/training_v2.0.0.log"
    echo ""

    # Extract final metrics
    echo "Final metrics:"
    grep -A 10 "Test Results\|Final" training_v2.0.0.log | tail -15 || echo "Check training_v2.0.0.log for metrics"

    echo ""
    echo "========================================"
    echo "Next Steps"
    echo "========================================"
    echo "1. Review metrics in training_v2.0.0.log"
    echo "2. Verify performance:"
    echo "   - F1 > 0.80 ✓"
    echo "   - FPR < 10% ✓"
    echo "   - Recall > 0.85 ✓"
    echo "3. Deploy to pipeline:"
    echo "   - Copy models/v2.0.0/ to twin/registry/gcn/"
    echo "   - Update symlink: twin/registry/gcn/current → v2.0.0"
    echo "   - Restart GCN detector"
    echo "4. Validate on live pipeline data"
    echo "========================================"
else
    echo ""
    echo "❌ Training failed!"
    echo "Check log: $GCN_DIR/training_v2.0.0.log"
    exit 1
fi
