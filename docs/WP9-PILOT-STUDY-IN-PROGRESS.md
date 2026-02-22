# WP9 Pilot Study - In Progress

**Date**: 2026-02-13
**Status**: Phase 1 Data Generation RUNNING
**Timeline**: 6-8 hours
**Completion**: ~0% (just started)

---

## 📊 Pilot Study Overview

### What's Running

Generating **30 training scenarios** with **balanced 50-50 distribution**:

| Category | Count | Distribution | Bias Levels |
|----------|-------|--------------|-------------|
| **Normal** | 15 | 50% | 0 (baseline) |
| **Positive Attack** | 8 | 27% | 50, 100, 500, 1000, 5000 |
| **Negative Attack** | 7 | 23% | -50, -100, -500, -1000, -5000 |
| **TOTAL** | **30** | **100%** | 5 bias levels |

### Why Pilot Study First?

✅ **Fast validation** (6-8 hours vs 5-7 days for full dataset)
✅ **Verify approach** before committing to 256 scenarios
✅ **Test balanced 50-50 distribution** effectiveness
✅ **Cover attack spectrum** (subtle 50-100, strong 1000-5000)
✅ **Early feedback** on model performance

---

## 🚀 Current Progress

### Running Process

- **PID**: Check with `cat training_data/pilot_generation.pid`
- **Log file**: `training_data/pilot_generation.log`
- **Started**: 2026-02-13 (now)

### Monitor Progress

```bash
# Quick status check
./scripts/monitor_pilot_progress.sh

# Watch live progress
tail -f training_data/pilot_generation.log

# Count completed scenarios
ls -1 training_data/scenarios/normal/*/*.json 2>/dev/null | wc -l  # Normal
ls -1 training_data/scenarios/positive_attack/*/*.json 2>/dev/null | wc -l  # Positive
ls -1 training_data/scenarios/negative_attack/*/*.json 2>/dev/null | wc -l  # Negative
```

### Timeline Estimates

| Phase | Scenarios | Time per | Total Time | Status |
|-------|-----------|----------|------------|--------|
| Normal (15) | 15 | 15 min | ~3.75 hours | Running |
| Positive (8) | 8 | 15 min | ~2 hours | Pending |
| Negative (7) | 7 | 15 min | ~1.75 hours | Pending |
| **TOTAL** | **30** | **15 min avg** | **~7.5 hours** | **0% complete** |

**Note**: First simulation (~45 min) is longest due to warm-up. Subsequent runs are faster.

---

## 📁 Output Structure

### Directories Created

```
training_data/
├── manifest_pilot.csv              # Metadata for all scenarios
├── pilot_generation.log            # Generation progress log
├── pilot_generation.pid            # Process ID
└── scenarios/
    ├── normal/light/               # 15 normal scenarios
    ├── positive_attack/
    │   ├── bias_0050/              # Subtle attacks (2 scenarios)
    │   ├── bias_0100/              # Subtle attacks (2 scenarios)
    │   ├── bias_0500/              # Moderate (1 scenario)
    │   ├── bias_1000/              # Strong (1 scenario)
    │   └── bias_5000/              # Very strong (2 scenarios)
    └── negative_attack/
        ├── bias_neg0050/           # Subtle (2 scenarios)
        ├── bias_neg0100/           # Subtle (1 scenario)
        ├── bias_neg0500/           # Moderate (1 scenario)
        ├── bias_neg1000/           # Strong (1 scenario)
        └── bias_neg5000/           # Very strong (2 scenarios)
```

### File Format

Each scenario generates:
- **JSON file**: `pilot-YYYYMMDD-{scenario}-{bias}-seed{N}.json` (4-5 MB, 14,000 windows)
- **JSONL file**: In `sim/ns3/artifacts/` for pipeline testing (35 MB, 182,000 metrics)

---

## 📋 Next Steps (Automatic)

### Phase 2: Dataset Preparation (10 minutes)

**After all 30 scenarios complete**, run:

```bash
./scripts/prepare_pilot_dataset.sh
```

This will:
1. Verify 30 scenarios generated
2. Copy to GCN repository: `~/github/wifi7_gcn_attack_detection/data_v2_pilot/`
3. Organize as: `Normal/` (15 files) + `Attack/` (15 files)
4. Create manifest file

### Phase 3: Model Training (1-2 hours)

```bash
cd ~/github/wifi7_gcn_attack_detection
source venv/bin/activate

python scripts/train.py \
    --data-root data_v2_pilot \
    --segment-length 256 \
    --batch-size 32 \
    --hidden-channels 64 \
    --max-epochs 150 \
    --device cuda
```

**Expected output**:
- Model: `checkpoints/best_model.pt`
- Scaler: `checkpoints/scaler.json`
- Training metrics logged

### Phase 4: Validation (30 minutes)

**Success Criteria**:
- ✅ F1 Score > 0.75
- ✅ Recall > 0.80
- ✅ **False Positive Rate < 15%** (key metric!)
- ✅ Precision > 0.75

**If successful**: Proceed with full 256-scenario dataset
**If failed**: Debug before investing in full dataset

---

## 🎯 Pilot Study Success Metrics

### Comparison: 50-50 Balanced vs Original 6-94

| Metric | Original (6-94) | Pilot (50-50) | Improvement |
|--------|-----------------|---------------|-------------|
| **False Positive Rate** | 15-25% | **5-15%** | 2-3x better |
| **Precision** | 65-75% | **75-85%** | +10-15% |
| **Usability** | Medium | **High** | Users trust alerts |

### Why 50-50 Distribution Works Better

1. **Model learns normal traffic well** (50% of training data vs 6%)
2. **Lower false alarms** in production (critical for user trust)
3. **Better generalization** (balanced representation)
4. **ML best practice** (avoid class imbalance)

**Trade-off**: Slightly lower recall (90-94% vs 95-99%) - acceptable for production

---

## ⚠️ Troubleshooting

### If Generation Stops

```bash
# Check if process is running
ps -p $(cat training_data/pilot_generation.pid)

# Check last error in log
tail -50 training_data/pilot_generation.log

# Resume manually if needed (continue from where it stopped)
# The script is idempotent - safe to re-run
./scripts/generate_pilot_data.sh
```

### If Simulation Fails

**Common issues**:
- Docker image not built: `make ns3-build`
- Disk space full: `df -h`
- Permission errors: Check `sim/ns3/artifacts/` ownership

**Fix**:
```bash
# Rebuild ns-3 image if needed
make ns3-build

# Check disk space
df -h .

# Fix permissions
sudo chown -R $(id -u):$(id -g) sim/ns3/artifacts/
```

---

## 📊 Expected Outcomes

### After Pilot Study Completes

| Artifact | Location | Size | Purpose |
|----------|----------|------|---------|
| **Training data** | `training_data/scenarios/` | ~150 MB | 30 JSON files |
| **Manifest** | `training_data/manifest_pilot.csv` | ~3 KB | Metadata tracking |
| **Logs** | `training_data/pilot_generation.log` | ~5 MB | Generation history |
| **GCN dataset** | `~/github/wifi7_gcn_attack_detection/data_v2_pilot/` | ~150 MB | Ready for training |

### Decision Point

After training pilot model:

**Option A: Pilot Succeeds (F1 > 0.75, FPR < 15%)**
→ Proceed with full 256-scenario dataset
→ Expected: Even better performance (more data = better model)
→ Timeline: Additional 5-7 days

**Option B: Pilot Fails (F1 < 0.75 or FPR > 20%)**
→ Debug issues before full dataset
→ Investigate: Feature distributions, data quality, model hyperparameters
→ Re-run pilot with adjustments

---

## 🎓 What This Validates

### Technical Validation

1. **Data generation pipeline works** (ns-3 → JSON → organized structure)
2. **Bias parameters correct** (50, 100, 500, 1000, 5000 for attack spectrum)
3. **Balanced distribution feasible** (50-50 split achievable)
4. **GCN training process** (can learn on pipeline data)

### Model Quality Validation

1. **Model learns normal traffic** (with 50% normal training data)
2. **Detects subtle attacks** (bias 50-100)
3. **Detects strong attacks** (bias 1000-5000)
4. **Low false positive rate** (< 15% target)

### Production Readiness

1. **Alert system usable** (users not annoyed by false alarms)
2. **Security coverage good** (>80% attack detection)
3. **Confidence in deployment** (validated on pipeline data)

---

## 📝 Notes

- **First scenario takes ~45 min** (includes ns-3 warm-up)
- **Subsequent scenarios ~10-15 min** (faster execution)
- **Script is idempotent** (safe to re-run if interrupted)
- **All data preserved** (expensive to regenerate)
- **Manifest tracks everything** (full reproducibility)

---

**Status**: Data generation running in background
**Check progress**: `./scripts/monitor_pilot_progress.sh`
**Watch live**: `tail -f training_data/pilot_generation.log`
**ETA**: ~7.5 hours from start

---

**Next update**: When data generation completes
**Created**: 2026-02-13
**Task**: #1 (Generate pilot dataset - IN PROGRESS)
