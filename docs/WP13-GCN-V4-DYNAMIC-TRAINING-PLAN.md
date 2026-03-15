# WP13 — GCN v4 Dynamic Generalization Training Plan

**Status:** In Progress — Data + model code complete; training pending
**Last updated:** 2026-03-15
**Depends on:** WP12 (GCN v3.0.0 complete, deployed)
**Goal:** Train GCN v4.0.0 that correctly classifies segments in dynamic multi-phase scenarios where attack conditions change mid-simulation.

**Implementation progress:**
- Data collection infrastructure: DONE (collect_v4_static_data.sh, collect_v4_dynamic_data.sh)
- Synthetic stitching: DONE (twin/gnn/stitch_dynamic.py)
- Model code: DONE (dataset_v4.py, train_v4.py, run_training_v4.py, training_v4.yaml, Dockerfile)
- Dataset on disk: DONE (2,878 total files across train/val/test)
- Training: PENDING (make gcn-trainer-build && make gcn-train-v4)
- Evaluation and deployment: PENDING

---

## 1. Why GCN v3 Fails on Dynamic Data

### Root Cause

GCN v3.0.0 was trained exclusively on **static files** — every window in a training file has the same `bias` value (either all-normal or all-attack). The model learned to classify entire temporal sequences of uniform signal. It has **never seen a segment containing a phase transition**.

During a dynamic experiment (e.g., `NEG→NORM→POS`), transition segments contain windows with **mixed bias values** — the first half may be negative-attack windows, the second half normal windows. The GCN has no training signal for this pattern and defaults to uncertain or incorrect predictions.

### Observed Failure Modes

| Condition | v3 Behavior | Expected |
|-----------|-------------|----------|
| Pure normal segment | ✅ Correct (Normal) | Normal |
| Pure attack segment | ✅ Correct (Attack) | Attack |
| Attack→Normal transition segment | ❌ Often misclassified | Normal (majority) |
| Normal→Attack transition segment | ❌ Often misclassified | Attack (majority) |
| Alternating short-phase segments | ❌ Unreliable | Per-segment majority |

---

## 2. GCN v4 Objectives

1. **Dynamic generalization**: Correctly classify segments in multi-phase scenarios with any ordering of normal/positive/negative
2. **Transition awareness**: Handle segments that span phase boundaries using majority-vote labeling
3. **No data leakage**: Strict seed/topology/ordering isolation between train, val, and test sets
4. **Broader coverage**: Varied AP counts, bias strengths, sim durations, and phase orderings
5. **Improved architecture**: Wider network (hidden=128) with 3 GCN layers for richer temporal context

---

## 3. Seed & Split Partitioning (No Leakage)

Seeds are the primary leakage control. Each pool is **mutually exclusive**.

| Pool | Seeds | Used For |
|------|-------|---------|
| **Train** | 42, 123, 456, 789, 321, 654, 987, 111, 222, 333 | All training data |
| **Val** | 777, 888, 444 | Validation during training |
| **Test** | 555, 999, 1234, 2000, 3000 | Final evaluation only |

Additional isolation:
- **Topology**: nap5, nap6 are **test-only** (never in training) as topology generalization test
- **Phase orderings**: Patterns T1–T4 (5-phase) are **test-only** orderings never seen during training
- **Bias strengths**: Test includes bias=10000 (never in training, generalization test)
- **Sim durations**: Test uses 200s runs (longer than any training run)

---

## 4. Static Data Plan

### 4.1 Topology Coverage

| Config | NAP | NSTA | Total STA |
|--------|-----|------|-----------|
| 1AP    |   1 |    2 |         2 |
| 2AP    |   2 |    4 |         8 |
| 3AP    |   3 |    6 |        18 |
| 4AP    |   4 |    8 |        32 |
| 5AP*   |   5 |   10 |        50 | ← test-only
| 6AP*   |   6 |   12 |        72 | ← test-only

(*) 5AP and 6AP used only in test set to measure topology generalization.

### 4.2 Bias Strengths

| Label | Bias Value | Type |
|-------|-----------|------|
| Normal | 0 | No attack |
| Positive (weak) | +3000 | Victim starvation, weak |
| Positive (standard) | +5000 | Victim starvation, standard |
| Positive (strong) | +8000 | Victim starvation, aggressive |
| Negative (weak) | -3000 | Aggressive backoff, weak |
| Negative (standard) | -5000 | Aggressive backoff, standard |
| Negative (strong) | -8000 | Aggressive backoff, aggressive |

Training uses bias=±3000, ±5000, ±8000. Test includes ±10000 for generalization check.

### 4.3 Static Simulation Matrix

**Training set (10 train seeds):**

| Group | Scenarios | Bias | NAP | SIM_TIME | Seeds | Files |
|-------|-----------|------|-----|----------|-------|-------|
| S-T1 | normal, pos, neg | ±5000 | 1,2,3,4 | 80s | all 10 | 4×3×10=**120** |
| S-T2 | normal, pos, neg | ±5000 | 1,2,3,4 | 120s | 42,123,456,789 | 4×3×4=**48** |
| S-T3 | pos, neg | ±3000 | 1,2,3,4 | 80s | 42,123,456,789,321 | 4×2×5=**40** |
| S-T4 | pos, neg | ±8000 | 1,2,3,4 | 80s | 42,123,456,789,321 | 4×2×5=**40** |

**Static training total: 248 files**

**Validation set (3 val seeds):**

| Group | Scenarios | Bias | NAP | SIM_TIME | Seeds | Files |
|-------|-----------|------|-----|----------|-------|-------|
| S-V1 | normal, pos, neg | ±5000 | 1,2,3,4 | 80s | 777,888,444 | 4×3×3=**36** |

**Validation total: 36 files**

**Test set (5 test seeds + extended topology):**

| Group | Description | NAP | SIM_TIME | Seeds | Files |
|-------|-------------|-----|----------|-------|-------|
| S-Test1 | Standard (nap1-4, ±5000) | 1,2,3,4 | 80s | 555,999,1234 | 4×3×3=**36** |
| S-Test2 | Extended topology (nap5-6) | 5,6 | 80s | 555,999 | 2×3×2=**12** |
| S-Test3 | Strong bias (±10000) | 1,2,3,4 | 80s | 555,999 | 4×2×2=**16** |
| S-Test4 | Long sim (200s) | 1,2,3,4 | 200s | 555,999 | 4×3×2=**24** |

**Test total: 88 files**

---

## 5. Dynamic Data Plan

### 5.1 Phase Pattern Catalogue

Each pattern is described as bias sequence with 40-second phases.

#### Group A: 2-Phase (80s, 2 phases × 40s)

| ID | Name | PHASES string | Label sequence |
|----|------|---------------|----------------|
| D-01 | norm→pos | `0:0,40:5000` | N→A |
| D-02 | norm→neg | `0:0,40:-5000` | N→A |
| D-03 | pos→norm | `0:5000,40:0` | A→N |
| D-04 | neg→norm | `0:-5000,40:0` | A→N |
| D-05 | pos→neg | `0:5000,40:-5000` | A→A |
| D-06 | neg→pos | `0:-5000,40:5000` | A→A |

#### Group B: 3-Phase (120s, 3 phases × 40s)

| ID | Name | PHASES string | Label sequence |
|----|------|---------------|----------------|
| D-07 | norm→pos→norm | `0:0,40:5000,80:0` | N→A→N |
| D-08 | norm→neg→norm | `0:0,40:-5000,80:0` | N→A→N |
| D-09 | neg→norm→pos | `0:-5000,40:0,80:5000` | A→N→A |
| D-10 | pos→norm→neg | `0:5000,40:0,80:-5000` | A→N→A |
| D-11 | pos→neg→pos | `0:5000,40:-5000,80:5000` | A→A→A |
| D-12 | neg→pos→neg | `0:-5000,40:5000,80:-5000` | A→A→A |

#### Group C: 4-Phase (160s, 4 phases × 40s)

| ID | Name | PHASES string | Label sequence |
|----|------|---------------|----------------|
| D-13 | neg→norm→pos→norm | `0:-5000,40:0,80:5000,120:0` | A→N→A→N |
| D-14 | norm→pos→norm→neg | `0:0,40:5000,80:0,120:-5000` | N→A→N→A |
| D-15 | pos→norm→neg→norm | `0:5000,40:0,80:-5000,120:0` | A→N→A→N |
| D-16 | neg→pos→norm→neg | `0:-5000,40:5000,80:0,120:-5000` | A→A→N→A |

#### Group D: Uneven Transitions (80s–120s, asymmetric timings — train diversity)

These expose the model to non-even phase boundaries (simulates real-world irregular attack timing):

| ID | Name | PHASES string | SIM_TIME |
|----|------|---------------|----------|
| D-17 | neg→norm (1/3:2/3) | `0:-5000,27:0` | 80s |
| D-18 | norm→pos (2/3:1/3) | `0:0,53:5000` | 80s |
| D-19 | neg→norm→pos (uneven) | `0:-5000,30:0,70:5000` | 120s |
| D-20 | pos→neg (early flip) | `0:5000,15:-5000` | 80s |
| D-21 | norm→neg→norm (narrow) | `0:0,30:-5000,50:0` | 80s |

#### Group E: Weak-Bias Dynamic (bias=±3000)

| ID | PHASES string | SIM_TIME |
|----|---------------|----------|
| D-22 | `0:0,40:3000` | 80s |
| D-23 | `0:0,40:-3000` | 80s |
| D-24 | `0:-3000,40:0,80:3000` | 120s |
| D-25 | `0:3000,40:0,80:-3000` | 120s |

#### Group T (Test-Only, Never Seen in Training): 5-Phase (200s)

| ID | Name | PHASES string |
|----|------|---------------|
| T-01 | norm→neg→norm→pos→norm | `0:0,40:-5000,80:0,120:5000,160:0` |
| T-02 | pos→norm→pos→neg→norm | `0:5000,40:0,80:5000,120:-5000,160:0` |
| T-03 | neg→norm→neg→pos→neg | `0:-5000,40:0,80:-5000,120:5000,160:-5000` |
| T-04 | pos→neg→pos→norm→neg | `0:5000,40:-5000,80:5000,120:0,160:-5000` |
| T-05 | norm→pos→neg→pos→norm | `0:0,40:5000,80:-5000,120:5000,160:0` |

### 5.2 Dynamic Simulation Matrix

**Training set (patterns D-01 to D-25):**

| Group | Patterns | NAP | Seeds | SIM_TIME | Files |
|-------|----------|-----|-------|----------|-------|
| A (2-phase) | D-01 to D-06 | 1,2,3,4 | 42,123,456,789,321,654 (6) | 80s | 6×4×6=**144** |
| B (3-phase) | D-07 to D-12 | 1,2,3,4 | 42,123,456,789,321,654 (6) | 120s | 6×4×6=**144** |
| C (4-phase) | D-13 to D-16 | 1,2,3,4 | 42,123,456,789,321,654 (6) | 160s | 4×4×6=**96** |
| D (uneven) | D-17 to D-21 | 1,2,3,4 | 42,123,456,789 (4) | varies | 5×4×4=**80** |
| E (weak bias) | D-22 to D-25 | 1,2,3,4 | 42,123,456,789 (4) | 80–120s | 4×4×4=**64** |

**Dynamic training total: 528 files**

**Validation set:**

| Group | Patterns | NAP | Seeds | Files |
|-------|----------|-----|-------|-------|
| A–C | D-01,D-04,D-07,D-09,D-13,D-14 (6 patterns) | 1,2,3,4 | 777,888 | 6×4×2=**48** |

**Dynamic validation total: 48 files**

**Test set (held-out patterns T-01 to T-05 + extended topology):**

| Group | Patterns | NAP | Seeds | Files |
|-------|----------|-----|-------|-------|
| T (5-phase, never in train) | T-01 to T-05 | 1,2,3,4 | 555,999,1234 | 5×4×3=**60** |
| Extended topology | D-01,D-09,D-13 | 5,6 | 555,999 | 3×2×2=**12** |

**Dynamic test total: 72 files**

---

## 6. Dataset Summary

### Planned (from design)

| Split | Static | Dynamic | Total |
|-------|--------|---------|-------|
| Train | 248 | 528 | **776** |
| Val | 36 | 48 | **84** |
| Test | 88 | 72 | **160** |
| **Grand Total** | **372** | **648** | **1,020** |

### Actual on Disk (2026-03-15)

The actual dataset was built using a different approach from the original plan. Static data collection used a narrower but more varied seed/bias matrix. Dynamic data was generated synthetically via `twin/gnn/stitch_dynamic.py` rather than running 528+ separate NS-3 simulations, yielding a much larger dynamic set.

| Split | Static (Normal+Attack) | Dynamic (synthetic) | Total |
|-------|----------------------|--------------------|----|
| Train | 28 Normal + 165 Attack = **193** | **1,852** | **2,045** |
| Val | 17 Normal + 33 Attack = **50** | **98** | **148** |
| Test | 6 Normal + 59 Attack = **65** | **620** | **685** |
| **Grand Total** | **308** | **2,570** | **2,878** |

The synthetic stitching approach produced substantially more dynamic training files than originally planned (1,852 vs 528) because it can generate many phase-pattern combinations from the same pool of static source files without requiring additional NS-3 simulation time.

### v3 vs v4 Comparison

| Metric | v3 | v4 |
|--------|----|----|
| Training files | 48 | 776 |
| Dynamic files in training | 0 | 528 |
| Seeds used (train) | 4 (42,43,44,45) | 10 |
| Bias values | ±5000 only | ±3000, ±5000, ±8000 |
| Sim durations | 80s only | 80s, 120s, 160s |
| Phase patterns | 0 (static only) | 25 (train) + 5 (test-only) |
| Topology (train) | nap1-4 | nap1-4 |
| Topology (test) | nap1-4 | nap1-6 |

---

## 7. Dynamic Segment Labeling Strategy

### Problem

In dynamic files, each window has its own `bias` value (changes mid-simulation). The current v3 label function reads only `windows[0]['bias']`, which is wrong for dynamic data.

### Solution: Majority-Vote Segment Labeling with 30% Threshold

For each segment (slice of L windows), count how many windows have `bias != 0`:
- If **> 30% of windows** have `abs(bias) > 0` → **Attack (label=1)**
- If **<= 30% of windows** have `abs(bias) > 0` → **Normal (label=0)**

The 30% threshold (rather than the originally planned 50%) was chosen to make the model more sensitive to early-onset attacks within a segment — erring on the side of detecting attack conditions as soon as they are present in a meaningful fraction of a segment.

This correctly handles:
- Pure segments (100% same bias) → exact label
- Transition segments (mixed) → majority label with attack-sensitive threshold
- Short-attack segments (late flip) → detected as attack if >30% windows are attack

### Implementation (dataset_v4.py)

```python
def get_label_from_segment_dynamic(segment: List[Dict], threshold: float = 0.30) -> int:
    """
    Threshold-vote label for a single segment.
    Used for dynamic files where bias changes per window.

    Returns 1 (Attack) if > threshold fraction of windows have bias != 0.
    Default threshold=0.30 (more sensitive than 0.50 majority vote).
    """
    attack_windows = sum(1 for w in segment if w.get('bias', 0) != 0)
    return 1 if attack_windows > threshold * len(segment) else 0
```

### Dataset Folder Structure

```
twin/gnn/training_data/v4/
  Static/
    Normal/              ← bias=0 throughout (all windows normal)
      nap1_nsta2_seed42_normal_80s.json
      ...
    Attack/              ← bias≠0 throughout (all windows attack)
      nap1_nsta2_seed42_positive5000_80s.json
      nap1_nsta2_seed42_negative5000_80s.json
      nap1_nsta2_seed42_positive3000_80s.json
      ...
  Dynamic/               ← bias changes mid-file (per-segment labeling)
    nap1_nsta2_seed42_D01_norm-pos_80s.json
    nap1_nsta2_seed42_D09_neg-norm-pos_120s.json
    ...
```

The dataset loader detects which folder a file comes from and applies the appropriate labeling strategy:
- `Static/Normal/` or `Static/Attack/` → file-level label (existing v3 behavior)
- `Dynamic/` → per-segment majority vote (new v4 behavior)

---

## 8. Model Architecture: GCN v4.0.0

### Changes from v3

| Parameter | v3 | v4 | Rationale |
|-----------|----|----|-----------|
| `hidden_channels` | 64 | 128 | Wider = more capacity for complex patterns |
| `num_layers` | 2 | 3 | Deeper = more temporal context in graph messages |
| `dropout` | 0.3 | 0.4 | Higher dropout = better generalization with more data |
| `in_channels` | 17 | 17 | Same features (backward compatible) |
| `pooling` | mean | mean | Unchanged |

### Architecture Detail

```
Input: [L, 17]  (L windows, 17 features each)
  → GCNConv(17, 128) + BatchNorm + ReLU + Dropout(0.4)
  → GCNConv(128, 128) + BatchNorm + ReLU + Dropout(0.4)  [+ residual]
  → GCNConv(128, 128) + BatchNorm + ReLU + Dropout(0.4)  [+ residual]
  → global_mean_pool  →  [batch, 128]
  → Linear(128, 64) + ReLU
  → Linear(64, 2)
  → softmax → {0: Normal, 1: Attack}
```

Same 17-feature input as v3: backward compatible with existing windowizer and inference path.

---

## 9. Training Configuration

### training_v4.yaml

```yaml
version: "4.0.0"
in_channels: 17
hidden_channels: 128
num_layers: 3
dropout: 0.4
pooling: mean

segment_lengths: [32, 64, 128, 256]
segment_strides:
  32: 32
  64: 64
  128: 128
  256: 64

multi_ap_normalise: true
use_derived_features: true
use_class_weights: true

batch_size: 64
learning_rate: 0.0005
weight_decay: 0.0001
max_epochs: 300
patience: 30
random_seed: 42

test_size: 0.0    # Manual split via seed pools
val_size: 0.0     # Manual split via seed pools

data_root: /data
checkpoint_dir: checkpoints_v4.0.0
log_dir: logs_v4.0.0
device: cuda
```

### Key Training Changes vs v3

- **Batch size**: 32→64 (more stable with 16× more data)
- **Learning rate**: 0.001→0.0005 (lower LR for wider network)
- **Max epochs**: 200→300 (more data needs more epochs)
- **Patience**: 20→30 (prevent premature stopping)
- **Manual split**: No random file split — uses pre-partitioned train/val/test folders by seed pool

---

## 10. Data Generation Steps

### Step 1: Create v4 Directories

```bash
mkdir -p twin/gnn/training_data/v4/Static/Normal
mkdir -p twin/gnn/training_data/v4/Static/Attack
mkdir -p twin/gnn/training_data/v4/Dynamic
mkdir -p twin/gnn/training_data/v4/Val/Static/Normal
mkdir -p twin/gnn/training_data/v4/Val/Static/Attack
mkdir -p twin/gnn/training_data/v4/Val/Dynamic
mkdir -p twin/gnn/training_data/v4/Test/Static/Normal
mkdir -p twin/gnn/training_data/v4/Test/Static/Attack
mkdir -p twin/gnn/training_data/v4/Test/Dynamic
```

### Step 2: Generate Static Training Data (Parallel)

```bash
# Standard bias ±5000, 80s (all 10 train seeds, nap1-4)
NCPU=8 bash sim/ns3/scenario/collect_v4_static_data.sh

# This generates 248 static training files automatically partitioned
```

### Step 3: Generate Dynamic Training Data (Parallel)

```bash
# All 25 dynamic patterns (D-01 to D-25), nap1-4, 6 train seeds
NCPU=8 bash sim/ns3/scenario/collect_v4_dynamic_data.sh --split train

# Generates 528 dynamic training files
```

### Step 4: Generate Validation Data (Parallel)

```bash
NCPU=4 bash sim/ns3/scenario/collect_v4_static_data.sh --split val
NCPU=4 bash sim/ns3/scenario/collect_v4_dynamic_data.sh --split val
```

### Step 5: Generate Test Data (Sequential — smaller)

```bash
NCPU=4 bash sim/ns3/scenario/collect_v4_static_data.sh --split test
NCPU=4 bash sim/ns3/scenario/collect_v4_dynamic_data.sh --split test
```

### Estimated Wall-Clock Time (with NCPU=8)

| Dataset | Files | Avg time/file | Total (8 cores) |
|---------|-------|--------------|-----------------|
| Static train (80s) | 168 | ~30s | ~10.5 min |
| Static train (120s) | 48 | ~45s | ~4.5 min |
| Static train (alt bias) | 80 | ~30s | ~5 min |
| Dynamic (80s) | 144+80+64=288 | ~30s | ~18 min |
| Dynamic (120s) | 144 | ~45s | ~13.5 min |
| Dynamic (160s) | 96 | ~60s | ~12 min |
| Val + Test | 160+84=244 | ~40s | ~20 min |
| **Total estimate** | **1,020** | | **~85 min** |

---

## 11. Training Steps

### Step 6: Build GCN v4 Trainer Image

```bash
make gcn-trainer-build
```

### Step 7: Train GCN v4

```bash
make gcn-train-v4 OUTPUT_DIR=twin/registry/gcn/v4.0.0
```

Behind the scenes:
```bash
docker run --rm --gpus all \
  --user "$(id -u):$(id -g)" \
  -v $(pwd)/twin/gnn/training_data/v4:/data:ro \
  -v $(pwd)/twin/registry/gcn/v4.0.0:/output \
  -v $(pwd)/twin/gnn/trainer/training_v4.yaml:/config/training_v4.yaml:ro \
  ndt/gcn-trainer:local \
  --config /config/training_v4.yaml \
  --data-root /data \
  --output-dir /output
```

### Step 8: Deploy GCN v4

```bash
make gcn-deploy VERSION=v4.0.0
```

### Step 9: Restart Detector

```bash
docker compose -f docker-compose.pipeline.yml restart gcn-detector
```

---

## 12. Evaluation Protocol

### 12.1 Standard Metrics (vs v3 baseline)

Run the same static benchmark experiments used for v3 certification:

| Tier | Description | Expected v4 |
|------|-------------|-------------|
| T1 | Core accuracy (nap1-2, 256w) | F1 ≥ 0.995 |
| T2 | Multi-AP (nap3-4) | F1 ≥ 0.990 |
| T3 | Segment lengths (32/64/128w) | F1 ≥ 0.985 |
| T4 | Bias sensitivity (±3000, ±8000) | F1 ≥ 0.980 |
| T5 | Seed generalization (test seeds) | F1 ≥ 0.980 |

### 12.2 Dynamic Benchmark (New in v4)

Run the 4 benchmark window-size experiments using the same dynamic scenario:

```
Scenario: neg→norm→pos (9 segments)
PHASES: 0:-5000,67:0,137:5000
SIM_TIME: 231s
NAP: 2, NSTA: 4, SEED: 42
```

For each window size (32w, 64w, 128w, 256w):
- Measure per-segment accuracy
- Measure transition-segment accuracy (segments spanning phase boundaries)
- Measure false-positive rate during normal phase
- Measure false-negative rate during attack phase

### 12.3 Held-Out Dynamic Patterns (Test-Only)

Run held-out test patterns T-01 to T-05 (5-phase, never seen in training):

| Pattern | Expected |
|---------|----------|
| T-01: norm→neg→norm→pos→norm | Correct classification in each phase |
| T-02: pos→norm→pos→neg→norm | Correct classification in each phase |
| T-03: neg→norm→neg→pos→neg | Correct classification in each phase |
| T-04: pos→neg→pos→norm→neg | Correct classification in each phase |
| T-05: norm→pos→neg→pos→norm | Correct classification in each phase |

### 12.4 Topology Generalization (Test-Only)

Run standard 3-scenario experiments on nap5, nap6 (never in v4 training):
- Expected: F1 ≥ 0.95 on never-seen topologies

### 12.5 v3 vs v4 Head-to-Head Comparison

Using the dashboard compare mode, run each test scenario and compare predictions side-by-side for the same experiment.

---

## 13. Code Changes Required

### 13.1 preprocessing.py — Add Dynamic Label Function

Add `get_label_from_segment_dynamic(segment)` for per-segment majority-vote labeling. The existing `get_label_from_windows()` function is unchanged for static files.

### 13.2 dataset.py — Add Dynamic Folder Support

The `WiFi7AttackDataset` class detects whether a file is from the `Dynamic/` folder and uses per-segment labeling instead of file-level labeling. Key change: label is computed **per segment** from the windows in that segment, not once per file.

### 13.3 training script — Add v4 Data Loading

The training script needs to handle the new `Static/Normal/`, `Static/Attack/`, and `Dynamic/` directory structure. A new `load_v4_files()` function returns pre-partitioned train/val/test file lists based on the folder structure (no random split needed — split is determined by which seed pool was used during data generation).

### 13.4 Makefile — Add v4 Targets

```makefile
V4_DATA_DIR ?= twin/gnn/training_data/v4

gcn-collect-v4-static:
    NCPU=$(NCPU) bash sim/ns3/scenario/collect_v4_static_data.sh

gcn-collect-v4-dynamic:
    NCPU=$(NCPU) bash sim/ns3/scenario/collect_v4_dynamic_data.sh

gcn-collect-v4: gcn-collect-v4-static gcn-collect-v4-dynamic

gcn-train-v4:
    @test -n "$(OUTPUT_DIR)" || (echo "OUTPUT_DIR required." && exit 1)
    @echo "Training GCN v4 (dynamic generalization)..."
    @docker run --rm --gpus all \
        --user "$(shell id -u):$(shell id -g)" \
        -v $(CURDIR)/twin/gnn/training_data/v4:/data:ro \
        -v $(CURDIR)/$(OUTPUT_DIR):/output \
        -v $(CURDIR)/twin/gnn/trainer/training_v4.yaml:/config/training_v4.yaml:ro \
        $(GCN_TRAINER_IMAGE) \
        --config /config/training_v4.yaml \
        --data-root /data \
        --output-dir /output
```

---

## 14. Implementation Checklist

### Phase 1: Data Generation Infrastructure (Days 1-2)

- [x] Create v4 directory structure (`twin/gnn/training_data/v4/{train,val,test}/Static/{Normal,Attack}` and `Dynamic/`)
- [x] Write `collect_v4_static_data.sh` with full seed/split partitioning
- [x] Write `collect_v4_dynamic_data.sh` with all 25+5 patterns and skip-if-exists logic
- [ ] Add Makefile targets: `gcn-collect-v4-static`, `gcn-collect-v4-dynamic`, `gcn-collect-v4` (planned; not yet added)
- [x] Static data collection completed (193 files across train/val/test splits)
- [x] Dynamic scenario data verified: `bias` field changes per window in NS-3 output

### Phase 2: Model & Training Infrastructure (Day 2-3)

- [x] Add `get_label_from_segment_dynamic()` to `dataset_v4.py` (30% threshold, not 50% as originally planned)
- [x] Create `twin/gnn/detector/gcn_src/data/dataset_v4.py` with `WiFi7AttackDatasetV4` and `load_v4_files()` for pre-partitioned folder structure
- [x] Create `twin/gnn/detector/gcn_src/training/train_v4.py` (v4 training pipeline)
- [x] Create `twin/gnn/detector/run_training_v4.py` (entry point)
- [x] Create `twin/gnn/trainer/training_v4.yaml` with v4 hyperparameters
- [x] Update `twin/gnn/trainer/Dockerfile` to include v4 training files
- [ ] Add `gcn-train-v4` Makefile target (planned)

### Phase 2b: Synthetic Dynamic Dataset (Added — not in original plan)

- [x] Create `twin/gnn/stitch_dynamic.py` with synthetic stitching algorithm
  - 400-window slices from static source middles (windows 200-600 of 800-window files)
  - Phase offsets [200,0,400] to prevent same-source-file overlap across phases
  - No-leakage: same seed files only stitched within same split
  - 30 phase patterns (groups A/B/C/D/E/T)
  - CLI flags: --split, --dry-run, --overwrite, --summary
- [x] Generated 2,570 synthetic dynamic files (1,852 train + 98 val + 620 test)

### Phase 3: Data Collection (Complete)

Dataset on disk as of 2026-03-15:
- Train: 193 Static + 1,852 Dynamic = 2,045 files
- Val: 50 Static + 98 Dynamic = 148 files
- Test: 65 Static + 620 Dynamic = 685 files
- Grand total: 2,878 files

### Phase 4: Training (PENDING)

- [ ] Verify dataset statistics: `python twin/gnn/stitch_dynamic.py --summary`
- [ ] Rebuild trainer Docker image: `make gcn-trainer-build`
- [ ] Run training: `make gcn-train-v4 OUTPUT_DIR=twin/registry/gcn/v4.0.0`
- [ ] Monitor training curves (loss, F1 on val set)
- [ ] Check for overfitting (val F1 vs train F1 gap)

### Phase 5: Evaluation (PENDING)

- [ ] Run static benchmark (Tier 1-5, same as v3 certification)
- [ ] Run dynamic benchmark (4 window sizes, neg→norm→pos)
- [ ] Run held-out pattern tests (T-01 to T-05)
- [ ] Run topology generalization test (nap5, nap6)
- [ ] Compare v3 vs v4 in dashboard side-by-side
- [ ] Deploy if v4 passes all tiers

### Phase 6: Deployment (PENDING)

```bash
make gcn-deploy VERSION=v4.0.0
docker compose -f docker-compose.pipeline.yml restart gcn-detector
```

---

## 15. Expected Outcomes

| Benchmark | v3 Result | v4 Target |
|-----------|-----------|-----------|
| Static F1 (test set) | 0.9978 | ≥ 0.995 |
| Dynamic accuracy (transition segs) | ~50% | ≥ 85% |
| Dynamic accuracy (pure segs) | ~90% | ≥ 98% |
| 5-phase held-out accuracy | N/A | ≥ 80% |
| nap5/nap6 generalization F1 | ~0.85 (estimated) | ≥ 0.92 |

---

## 16. ADR Decisions (documented in ALL-ADRS.md)

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Dynamic label strategy | 30% threshold vote per segment (not 50%) | More sensitive to early attack onset in transition segments | ADR-WP13-01 |
| Architecture widening | hidden=128, 3 layers | Dynamic data has higher variance, needs more capacity than v3's hidden=64, 2 layers | ADR-WP13-02 |
| Seed isolation | Strict pool partition (train/val/test disjoint) | No leakage; enables genuine generalization measurement | ADR-WP13-03 |
| Test topology | nap5-6 held out of training | Zero-shot topology generalization test | ADR-WP13-04 |
| Bias diversity | ±1000, ±2000, ±5000 in train | Reduces model overfitting to specific attack intensity | ADR-WP13-05 |
| Dynamic folder separation | `Static/{Normal,Attack}/` + `Dynamic/` subdir per split | Clean labeling strategy selection without filename parsing | ADR-WP13-06 |
| Stride for 256-window segments | stride=64 (sliding window) vs stride=256 (non-overlapping) | Gives 9 segments vs 3 per 80s run; better transition-zone coverage | ADR-WP12-01 (carried over) |
| Synthetic stitching for dynamic data | Stitch from static source files rather than simulate all combinations | Generates far more dynamic training variants (1,852 vs 528) without additional simulation time | ADR-WP13-07 |

---

## 17. Known Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Class imbalance in dynamic data (more attack segments) | Use class weights (already implemented in training) |
| Dynamic segments confuse scaler fitting | Fit scaler on training data only (already implemented) |
| 3-layer GCN may oversmooth | Skip/residual connections prevent oversmoothing (already in architecture) |
| Wall-clock time for 1,020 simulations | Parallel collection with 8 cores; ~85 min total |
| v4 may regress on static scenarios | Tier 1-5 static evaluation gates before deployment |
| Dynamic file `bias` field not preserved | Verified: NS-3 dynamic scenario writes `bias` per window |

---

*Plan created: 2026-03-15*
*Last updated: 2026-03-15 (implementation progress update)*
*Model target: GCN v4.0.0*
*Successor to WP12 (GCN v3.0.0)*

## Files Created / Modified in WP13 (so far)

| File | Status | Purpose |
|------|--------|---------|
| `sim/ns3/scenario/collect_v4_static_data.sh` | New | Parallel NS-3 static data collector with train/val/test seed partitioning |
| `sim/ns3/scenario/collect_v4_dynamic_data.sh` | New | Parallel NS-3 dynamic data collector for 30 phase patterns |
| `sim/ns3/scenario/run_mlo_dynamic.sh` | Modified | Dynamic multi-phase NS-3 runner (phase-transition support) |
| `twin/gnn/stitch_dynamic.py` | New | Synthetic dynamic dataset stitcher (400-window phases from static sources) |
| `twin/gnn/detector/gcn_src/data/dataset_v4.py` | New | WiFi7AttackDatasetV4 with per-segment dynamic labeling |
| `twin/gnn/detector/gcn_src/training/train_v4.py` | New | v4 training pipeline (hidden=128, 3 layers) |
| `twin/gnn/detector/run_training_v4.py` | New | v4 training entry point |
| `twin/gnn/trainer/training_v4.yaml` | New | v4 training configuration |
| `twin/gnn/trainer/Dockerfile` | Modified | Updated to include v4 training files |
| `twin/gnn/detector/gcn_src/data/preprocessing.py` | Modified | Per-segment dynamic labeling function |
| `twin/gnn/training_data/v4/` | New | Pre-partitioned dataset (train/val/test, static+dynamic) |
