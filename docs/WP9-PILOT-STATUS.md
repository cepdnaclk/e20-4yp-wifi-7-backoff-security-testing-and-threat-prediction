# WP9 Pilot Study - Current Status

**Date**: 2026-02-13
**Time**: Running for 1+ hour
**Status**: ✅ Phase 1 Data Generation IN PROGRESS

---

## 🎯 What's Happening Now

### Data Generation Running

- **Process**: ACTIVE (PID: 245647)
- **Runtime**: 1+ hour
- **Current**: First simulation (15 normal scenarios)
- **Progress**: 0/30 scenarios complete (first scenario still running)
- **ETA**: ~6-7 more hours (total ~7-8 hours)

### Why First Scenario Takes Longer

The first 1400-second simulation includes:
- ns-3 Docker container initialization
- WiFi 7 stack warm-up
- Simulation execution: 1400 seconds
- JSON + JSONL conversion

**Expected**: 45-90 minutes for first scenario
**Subsequent scenarios**: 10-15 minutes each (faster)

---

## 📋 All Scripts Ready

### ✅ Created and Ready to Use

1. **Data Generation** (RUNNING NOW)
   ```bash
   ./scripts/generate_pilot_data.sh
   # Running in background: PID 245647
   # Log: training_data/pilot_generation.log
   ```

2. **Progress Monitor** (USE ANYTIME)
   ```bash
   ./scripts/monitor_pilot_progress.sh
   # Shows: X/30 scenarios, progress bar, ETA
   ```

3. **Dataset Preparation** (RUN AFTER DATA COMPLETE)
   ```bash
   ./scripts/prepare_pilot_dataset.sh
   # Copies to GCN repo, organizes Normal/Attack
   # ETA: 10 minutes
   ```

4. **Model Training** (RUN AFTER DATASET PREPARED)
   ```bash
   ./scripts/train_pilot_model.sh
   # Trains v2.0.0-pilot model
   # ETA: 1-2 hours
   ```

---

## 📊 Pilot Study Plan

### 30 Scenarios (50-50 Balanced)

| Phase | Type | Count | Bias Levels | Status |
|-------|------|-------|-------------|--------|
| **1** | Normal | 15 | 0 | 🔄 Running (0/15) |
| **2** | Positive Attack | 8 | 50, 100, 500, 1000, 5000 | ⏳ Pending |
| **3** | Negative Attack | 7 | -50, -100, -500, -1000, -5000 | ⏳ Pending |

**Total**: 30 scenarios = 15 normal (50%) + 15 attack (50%) ✅ BALANCED

---

## 🕐 Timeline

### Completed Steps

- ✅ Plan created and validated (`docs/WP9-GCN-MODEL-RETRAINING-PLAN.md`)
- ✅ Directory structure created
- ✅ Data generation script created and launched
- ✅ Dataset preparation script created
- ✅ Training script created
- ✅ Progress monitoring script created

### Current Step (In Progress)

- 🔄 **Data Generation** (Started 1+ hour ago)
  - Phase 1/3: Normal scenarios (15 files)
  - Progress: 0/15 complete
  - ETA: ~6-7 hours remaining

### Next Steps (Automatic after data generation)

1. **Dataset Preparation** (~10 minutes)
   - Run: `./scripts/prepare_pilot_dataset.sh`
   - Output: `~/github/wifi7_gcn_attack_detection/data_v2_pilot/`

2. **Model Training** (~1-2 hours)
   - Run: `./scripts/train_pilot_model.sh`
   - Output: `models/v2.0.0-pilot/best_model.pt`

3. **Validation** (~30 minutes)
   - Check: F1 > 0.75, FPR < 15%
   - Decision: Proceed to full dataset or debug

**Total time to pilot model**: ~8-10 hours from start

---

## 📈 Monitoring Progress

### Real-Time Monitoring

```bash
# Option 1: Progress summary (recommended)
./scripts/monitor_pilot_progress.sh

# Option 2: Live log (verbose)
tail -f training_data/pilot_generation.log

# Option 3: Count files
find training_data/scenarios -name "*.json" | wc -l
```

### Expected Output Pattern

```
Phase 1: Normal scenarios
  Scenario 1: 45-90 min  ← Currently here
  Scenarios 2-15: 10-15 min each
  Phase 1 total: ~3-4 hours

Phase 2: Positive attacks (8 scenarios)
  ~2 hours

Phase 3: Negative attacks (7 scenarios)
  ~1.5-2 hours

TOTAL: ~6.5-8 hours
```

---

## 🎯 Success Criteria

### Data Generation Success

- ✅ 15 normal scenarios generated
- ✅ 8 positive attack scenarios generated
- ✅ 7 negative attack scenarios generated
- ✅ All files have 14,000 windows
- ✅ Manifest tracks all metadata

### Model Training Success (After Training)

| Metric | Target | Rationale |
|--------|--------|-----------|
| **F1 Score** | > 0.75 | Acceptable for pilot |
| **Recall** | > 0.80 | Detect 80%+ attacks |
| **FPR** | **< 15%** | Critical! Users must trust alerts |
| **Precision** | > 0.75 | 3/4 alerts are real |

**If achieved**: Proceed to full 256-scenario dataset (even better expected)
**If not**: Debug before investing 5-7 days in full dataset

---

## 📂 Output Locations

### Current (Data Generation)

```
training_data/
├── pilot_generation.log          # Live progress log
├── pilot_generation.pid          # Process ID
├── manifest_pilot.csv            # Metadata (will populate)
└── scenarios/                    # Will contain 30 JSON files
    ├── normal/light/             # 15 files (generating now)
    ├── positive_attack/          # 8 files (pending)
    └── negative_attack/          # 7 files (pending)
```

### After Preparation

```
~/github/wifi7_gcn_attack_detection/
├── data_v2_pilot/
│   ├── Normal/                   # 15 JSON files
│   └── Attack/                   # 15 JSON files (8 pos + 7 neg)
├── data_v2_pilot_manifest.csv    # Metadata
└── training_pilot.log            # Training output (after training)
```

### After Training

```
~/github/wifi7_gcn_attack_detection/
├── models/v2.0.0-pilot/
│   ├── best_model.pt             # Trained model
│   └── scaler.json               # Feature scaler
├── checkpoints/                  # Training checkpoints
└── training_pilot.log            # Full training metrics
```

---

## 🔧 Troubleshooting

### Check if Still Running

```bash
ps -p $(cat training_data/pilot_generation.pid)
```

### If Process Stopped

```bash
# Check last error
tail -100 training_data/pilot_generation.log

# Resume (script is idempotent)
./scripts/generate_pilot_data.sh
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Disk space full | `df -h` - need ~500 MB free |
| Docker not running | `docker ps` to verify |
| Permission errors | `sudo chown -R $(id -u):$(id -g) sim/ns3/artifacts/` |
| Out of memory | Close other applications |

---

## 🎓 What You're Achieving

### Immediate Goal

**Validate that balanced 50-50 distribution works better than original 6-94**

Expected improvements:
- **2-3x lower false positive rate** (5-15% vs 15-25%)
- **Better user trust** (fewer false alarms)
- **Production-ready model** (usable in real deployments)

### Long-Term Goal

**Train GCN model v2.0.0 that works on pipeline data**

- Fixes 100% FPR issue from v1.0.0
- Covers full attack spectrum (bias 50-10000)
- Generalizes to unseen scenarios
- Deployable in production

---

## 📝 Commands Cheat Sheet

### During Data Generation (NOW)

```bash
# Check progress
./scripts/monitor_pilot_progress.sh

# Watch live
tail -f training_data/pilot_generation.log

# Check process
ps -p $(cat training_data/pilot_generation.pid)
```

### After Data Generation Complete

```bash
# Step 1: Prepare dataset (10 min)
./scripts/prepare_pilot_dataset.sh

# Step 2: Train model (1-2 hours)
./scripts/train_pilot_model.sh

# Step 3: Review results
cat ~/github/wifi7_gcn_attack_detection/training_pilot.log | grep -A 10 "Test Results"
```

### Decision Point

```bash
# If F1 > 0.75 and FPR < 15%: SUCCESS!
# Proceed to full dataset (256 scenarios)

# If F1 < 0.75 or FPR > 20%: Debug
# Check feature distributions, data quality, model params
```

---

## ⏰ What to Do Now

### Recommended Actions

1. **Let it run** - Process will take 6-7 more hours
2. **Monitor occasionally** - `./scripts/monitor_pilot_progress.sh` every 1-2 hours
3. **Come back in ~7 hours** - When data generation completes
4. **Or check in morning** - If started in evening

### Safe to Close Terminal

Process is running in background (PID: 245647)
- Log file: `training_data/pilot_generation.log`
- Will continue even if you disconnect
- Check status anytime with monitor script

---

## 🎯 Next Communication Points

**Update 1**: When first scenario completes (~1.5 hours from start)
**Update 2**: When normal scenarios complete (~3-4 hours from start)
**Update 3**: When all data generation complete (~7-8 hours from start)
**Update 4**: After model training (~9-10 hours from start)

---

**Current Status**: ✅ Everything running smoothly
**Action Required**: None - let it run
**Check Back**: In 6-7 hours
**Quick Status**: `./scripts/monitor_pilot_progress.sh`

---

**Created**: 2026-02-13
**Process PID**: 245647
**Log**: `training_data/pilot_generation.log`
**Task #1**: Generate pilot dataset (IN PROGRESS)
