# WP12 — GCN v3: Multi-AP & Multi-Segment-Length Training Plan

**Status:** COMPLETE
**Created:** 2026-03-13
**Completed:** 2026-03-13
**Depends on:** WP11 complete (dashboard live), NS-3 C++ binary updates

---

## Completion Summary

All phases implemented. GCN v3.0.0 trained and deployed with the following results:

| Metric | Result |
|--------|--------|
| Test F1 | **0.9978** |
| Accuracy | **99.73%** |
| Precision | **1.0000** (zero false positives) |
| Recall | **0.9957** (1 missed attack out of 230) |
| ROC-AUC | **1.0000** |
| Training epochs | 21 (early stopped, patience=20) |
| Training data | 48 files: 16 Normal + 32 Attack (nap1-4, 4 seeds) |
| Active registry symlink | `twin/registry/gcn/current` → `v3.0.0` |

### Phases Completed

| Phase | Status |
|-------|--------|
| Phase 1 — NS-3 multi-AP support | Complete |
| Phase 2 — Data collection (nap1-4) | Complete (48/48 target files) |
| Phase 3 — Training pipeline updates | Complete |
| Phase 4 — GCN v3 training | Complete (v3.0.0) |
| Phase 5 — Registry & deployment | Complete |
| Phase 6 — Dashboard Experiment Launcher | Complete |
| Phase 7 — Validation (Playwright) | Deferred to v3.1.0 |

### Post-Deployment Evaluation (2026-03-14)

A five-tier evaluation matrix was executed after deployment, covering 54 experiments across both GCN v3.0.0 and v2.0.0. All 54 passed. Full results in `docs/EVALUATION-RESULTS-2026-03-14.md`.

| Tier | Description | Result |
|------|-------------|--------|
| Tier 1 (12 exp) | Core accuracy: 1AP, 256w, seeds A+B, v3+v2 | 12/12 PASS |
| Tier 2 (6 exp) | Multi-AP: 2AP+4AP, v3.0.0 only | 6/6 PASS |
| Tier 3 (6 exp) | Segment length: seg=128+64, v3.0.0 only | 6/6 PASS |
| Tier 4 (12 exp) | Bias sensitivity: bias=1000/2000/10000, v3+v2 | 12/12 PASS |
| Tier 5 (18 exp) | Seed generalisation: groups C+D+E, v3+v2 | 18/18 PASS |
| **Total** | | **54/54 PASS** |

Key findings from evaluation:
- v3.0.0 achieves attack\_rate = 0.000 (normal) and 1.000 (attack) across every tested configuration.
- Both models detect attacks at bias=1000, one-fifth of the training bias (5000).
- v3.0.0 scales without degradation to 2-AP and 4-AP topologies.
- v3.0.0 handles seg=64 and seg=128 as reliably as seg=256.
- Results are stable across all five independent NS-3 seed groups.

### Deferred Items (v3.1.0)
- nap5/6 data collection: use SIM_TIME=30s (~45min/run vs 2.5h); 12 runs x 45min = ~9h, NCPU=6 to parallelise
- Playwright end-to-end test for Run Experiment dashboard section
- Minimum-bias evaluation: test bias=500 and bias=250 to determine true lower detection limit

### Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| NS-3 binary accepts --nAp, --nSta, --seed | Complete |
| 48 training files in twin/gnn/training_data/v3/ | Complete |
| v3 model F1 >= 0.92 overall | Complete (F1=0.9978) |
| v3 model in registry at twin/registry/gcn/v3.0.0/ | Complete |
| current symlink updated to v3.0.0 | Complete |
| Dashboard "Run Experiment" section functional | Complete (backend + frontend; rebuild needed) |
| Multi-AP predictions (nAp=1-4) work | Complete |
| Multi-length predictions (seg=32/64/128/256) work | Complete |

---

---

## 1. Goal

Train **GCN v3.0.0** — a generalised attack detector that works across:

| Dimension | v2.x coverage | v3.0.0 target |
|-----------|---------------|---------------|
| Access points (nAp) | 1 AP only | 1, 2, 3, 4, 5, 6 APs |
| Stations per AP (nSta) | 2 stations | 2, 4, 6, 8 stations |
| Segment length (windows) | 256 only | 32, 64, 128, 256 windows |
| Scenarios | normal / attack-pos / attack-neg | same (all 3) |
| Seeds | 42 only | 42, 43, 44, 45 (4 per config) |

The dashboard (WP10) will be extended with an **Experiment Launcher** panel so users can configure and run NS-3 scenarios from the browser and see live predictions without touching the terminal.

---

## 2. Why v2 Cannot Handle These Variations

### 2.1 Multi-AP Topology

The current NS-3 scenario hardcodes `nSta=2, nAp=1`. All v2 training data comes from this single topology. The StandardScaler's mean/std are therefore calibrated for a single-AP network:

- `net_throughput_mbps` — single AP total; doubles when nAp=2
- `avg_backoff_slots` — contention grows non-linearly with more STAs
- `mac_tx_delta` / `mac_rx_delta` — scale directly with nSta

Feeding a 2-AP run to v2 produces z-scores outside the scaler's training distribution → the GCN receives malformed inputs → predictions are unreliable.

**Ratio metrics are more robust** (`net_packet_loss_ratio`, `channel_busy_ratio`, `retrans_rate`) but absolute metrics are not. v2 should not be used for multi-AP data.

### 2.2 Variable Segment Length

The GCN architecture (global_mean_pool) is **topology-agnostic** — it can process graphs of any node count. However:

1. The scaler was fit on 256-window segments; shorter segments have different feature distributions (delta features accumulate over fewer windows → smaller absolute values).
2. The temporal chain edge structure changes (32-node graph has 62 edges vs 510 for 256 nodes) — the GCN must learn message-passing dynamics at different temporal scales.
3. The windowizer pipeline currently will not emit a segment until 256 windows accumulate — this threshold must become configurable.

---

## 3. Phase Breakdown

```
Phase 1 — NS-3 multi-AP support         (C++ binary changes)
Phase 2 — Data collection campaign      (simulation runs)
Phase 3 — Training pipeline updates     (multi-length + multi-AP scaler)
Phase 4 — GCN v3 training               (train.py config changes)
Phase 5 — Registry & deployment         (v3.0.0 registry entry, current symlink)
Phase 6 — Dashboard Experiment Launcher (new UI section + backend API)
Phase 7 — Validation                    (Playwright end-to-end tests)
```

---

## 4. Phase 1 — NS-3 Multi-AP Support

### 4.1 Problem

The active NS-3 C++ files (`mlo-wifi7-normal.cc`, `mlo-wifi7-positive.cc`, `mlo-wifi7-negative.cc`) have `nAp` and `nSta` **hardcoded** and not exposed as `cmd.AddValue` parameters. The `--seed` parameter is also absent — seeds are currently only used as labels in EXP_ID, not forwarded to the NS-3 random number generator.

### 4.2 Required C++ Changes (per `.cc` file)

Add the following `cmd.AddValue` calls in each scenario's `main()`:

```cpp
uint32_t nAp  = 1;   // default unchanged
uint32_t nSta = 2;   // default unchanged
uint32_t seed = 42;  // default seed

CommandLine cmd;
cmd.AddValue("bias",    "Backoff bias",                 bias);
cmd.AddValue("time",    "Simulation time (s)",          simTime);
cmd.AddValue("jsonPath","Output JSON path",             jsonPath);
cmd.AddValue("xmlPath", "Output XML path",              xmlPath);
cmd.AddValue("nAp",     "Number of access points",      nAp);
cmd.AddValue("nSta",    "Stations per AP",              nSta);
cmd.AddValue("seed",    "Random seed (RngSeedManager)", seed);
cmd.Parse(argc, argv);

RngSeedManager::SetSeed(seed);
RngSeedManager::SetRun(1);
```

NS-3's `WifiMacHelper`, `NodeContainer`, and `YansWifiChannelHelper` already support dynamic `nAp`/`nSta` — the loop that creates STAs and APs just needs to use the variable instead of a literal.

### 4.3 Shell Script Changes (`run_mlo_scenario.sh`)

Add new optional environment variables, with defaults matching current behaviour:

```bash
NAP="${NAP:-1}"          # Number of access points
NSTA="${NSTA:-2}"        # Stations per AP
SEED="${SEED:-42}"       # Random seed forwarded to NS-3

# Pass to binary:
./ns3 run "scratch/${CC_FILE%.cc}" -- \
    --bias="${BIAS}" \
    --time="${SIM_TIME}" \
    --jsonPath="${JSON_OUTPUT}" \
    --nAp="${NAP}" \
    --nSta="${NSTA}" \
    --seed="${SEED}"
```

### 4.4 Makefile Additions

```makefile
# New variables with defaults
NAP  ?= 1
NSTA ?= 2

run-mlo-exp:
	NAP=$(NAP) NSTA=$(NSTA) SEED=$(SEED) SIM_TIME=$(SIM_TIME) \
	  bash sim/ns3/scenario/run_mlo_scenario.sh $(EXP_ID) $(SCENARIO)

# Parallel v3 data collection — runs all 72 simulations using NCPU cores
gcn-collect-data:
	NCPU=$(NCPU) SIM_TIME=$(SIM_TIME) bash sim/ns3/scenario/collect_v3_data.sh
```

### 4.5 Feature Normalisation Strategy for Multi-AP

Absolute metrics must be normalised per-AP before feeding to the model so the scaler's learned distribution applies regardless of topology. This is done in `feature_processor.py` at inference time (and in preprocessing at training time):

| Feature | Normalisation |
|---------|--------------|
| `net_throughput_mbps` | divide by `nAp` |
| `mac_tx_delta` | divide by `nSta` (total) |
| `mac_rx_delta` | divide by `nSta` |
| `mac_ack_delta` | divide by `nSta` |
| `mac_retrans_delta` | divide by `nSta` |
| `mac_drop_delta` | divide by `nSta` |
| `phy_drop_delta` | divide by `nSta` |
| All ratio/delay metrics | unchanged (already normalised by definition) |

The topology (`nAp`, `nSta`) must be stored alongside each simulation run's JSON output and included in the Kafka message headers (or a new JSON field `num_ap: N`) so the windowizer and GCN detector can apply the correct normalisation at runtime.

**Implementation:** Add `num_ap` and `num_sta` fields to each window in the NS-3 JSON output. The windowizer passes these through in the windowed feature message. The GCN `FeatureProcessor` reads them and divides before scaling.

---

## 5. Phase 2 — Data Collection Campaign

### 5.1 Simulation Time and Window Budget

Each NS-3 run uses **SIM_TIME=80s**, producing **800 windows** (80s ÷ 0.1s per window).

Window budget per run by segment length (non-overlapping):

| Segment length | Windows needed | Segments from 800 windows | Leftover |
|---------------|---------------|--------------------------|----------|
| 32            | 32            | **25**                   | 0        |
| 64            | 64            | **12**                   | 32       |
| 128           | 128           | **6**                    | 32       |
| 256           | 256           | **3**                    | 32       |

At 256-window segments, 3 segments per run is on the low side. **Compensation strategy:** use **sliding window segmentation** (overlapping) for the 256-window length only, with stride=64 (75% overlap):

```
Sliding window formula: floor((N - L) / stride) + 1
With N=800, L=256, stride=64: floor(544/64) + 1 = 9 segments per run
```

This gives **9 segments per 80s run at 256-window length** — 3× more than non-overlapping — without increasing simulation time. Shorter lengths (32/64/128) produce enough segments with non-overlapping stride and do not need sliding window.

**Overlap caveat:** Overlapping segments share some windows, so they are not fully independent. To mitigate training data leakage, overlapping segments from the same file are kept in the **same train/val/test split partition** (split by file, not by segment).

### 5.2 Target Dataset Size

To train a robust v3 model we need diverse coverage. Target:

| nAp | nSta | Scenario | Seeds | SIM_TIME | Runs | Seg@256 (sliding) | Seg@128 | Seg@64 | Seg@32 |
|-----|------|----------|-------|----------|------|-------------------|---------|--------|--------|
| 1   | 2    | normal     | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |
| 1   | 2    | attack-pos | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |
| 1   | 2    | attack-neg | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |
| 2   | 4    | normal     | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |
| 2   | 4    | attack-pos | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |
| 2   | 4    | attack-neg | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |
| 3   | 6    | normal     | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |
| 3   | 6    | attack-pos | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |
| 3   | 6    | attack-neg | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |
| 4   | 8    | normal     | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |
| 4   | 8    | attack-pos | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |
| 4   | 8    | attack-neg | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |
| 5   | 10   | normal     | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |
| 5   | 10   | attack-pos | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |
| 5   | 10   | attack-neg | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |
| 6   | 12   | normal     | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |
| 6   | 12   | attack-pos | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |
| 6   | 12   | attack-neg | 42-45 | 80s | 4 | 36 | 24 | 48 | 100 |

**Total runs:** 18 configs × 4 seeds = **72 NS-3 runs**
**Total segments (all lengths combined):** 72 × (9 + 6 + 12 + 25) = **72 × 52 = 3,744 segments**
**Estimated NS-3 CPU time (sequential):** ~72 × 4 min = ~5 CPU-hours
**Estimated wall-clock time (8 cores parallel):** ~38 minutes
**Estimated disk:** ~72 × 800 windows × 2KB/window ≈ **115 MB raw JSON**

### 5.3 Parallel Data Collection

NS-3 is CPU-bound and single-threaded per simulation. The PC's multiple cores can be used to run several simulations simultaneously, drastically reducing wall-clock time.

**Parallel execution script:** `sim/ns3/scenario/collect_v3_data.sh`

```bash
#!/usr/bin/env bash
# Parallel NS-3 data collection for v3 training dataset
# Usage: NCPU=8 bash collect_v3_data.sh
set -e

NCPU="${NCPU:-$(nproc)}"           # default: all available cores
SIM_TIME="${SIM_TIME:-80}"
OUTPUT_DIR="twin/gnn/training_data/v3"
SEEDS=(42 43 44 45)
NAP_NSTA=("1:2" "2:4" "3:6" "4:8" "5:10" "6:12")
SCENARIOS=("normal" "positive" "negative")

mkdir -p "${OUTPUT_DIR}/Attack" "${OUTPUT_DIR}/Normal"

# Build job list
JOBS=()
for ap_sta in "${NAP_NSTA[@]}"; do
    NAP="${ap_sta%%:*}"; NSTA="${ap_sta##*:}"
    for SCENARIO in "${SCENARIOS[@]}"; do
        for SEED in "${SEEDS[@]}"; do
            TAG="nap${NAP}_nsta${NSTA}_seed${SEED}_${SCENARIO}_${SIM_TIME}s"
            EXP_ID="$(date +%Y%m%d-%H%M)-${TAG}"
            JOBS+=("NAP=${NAP} NSTA=${NSTA} SEED=${SEED} SIM_TIME=${SIM_TIME} \
                    bash sim/ns3/scenario/run_mlo_scenario.sh ${EXP_ID} ${SCENARIO}")
        done
    done
done

echo "Total jobs: ${#JOBS[@]}, running ${NCPU} at a time"

# GNU parallel if available, else bash semaphore
if command -v parallel &>/dev/null; then
    printf '%s\n' "${JOBS[@]}" | parallel -j "${NCPU}" bash -c '{}'
else
    # Bash semaphore: max NCPU background jobs
    running=0
    for job in "${JOBS[@]}"; do
        eval "$job" &
        (( ++running ))
        if (( running >= NCPU )); then
            wait -n 2>/dev/null || wait   # wait for any one job to finish
            (( --running ))
        fi
    done
    wait
fi

echo "Data collection complete. Output: ${OUTPUT_DIR}"
```

**After each run, copy the JSON output to the training data directory:**

```bash
# In run_mlo_scenario.sh — add after simulation completes:
LABEL_DIR="twin/gnn/training_data/v3"
if [ "${SCENARIO}" = "normal" ]; then
    cp "${JSON_OUTPUT}" "${LABEL_DIR}/Normal/${TAG}.json"
else
    cp "${JSON_OUTPUT}" "${LABEL_DIR}/Attack/${TAG}.json"
fi
```

**Invocation examples:**
```bash
# Use all cores
NCPU=$(nproc) bash sim/ns3/scenario/collect_v3_data.sh

# Use 8 cores only (leave headroom for other work)
NCPU=8 bash sim/ns3/scenario/collect_v3_data.sh

# Or via Makefile
make gcn-collect-data NCPU=8
```

**Expected wall-clock times by core count:**

| Cores | Sequential sim time per run | Wall-clock for 72 runs |
|-------|-----------------------------|------------------------|
| 1     | ~4 min                      | ~4.8 hours             |
| 4     | ~4 min                      | ~1.2 hours             |
| 8     | ~4 min                      | ~36 minutes            |
| 16    | ~4 min                      | ~18 minutes            |

### 5.4 Multi-Length Segment Coverage (Option A)

The same raw NS-3 JSON files are reused — segment length is a **preprocessing parameter**, not a simulation parameter. The training pipeline segments each 800-window file at all four lengths:

| Segment length | Stride | Segments from an 80s run (800 windows) | Note |
|---------------|--------|----------------------------------------|------|
| 32 windows    | 32     | **25** segments                        | Non-overlapping sufficient |
| 64 windows    | 64     | **12** segments                        | Non-overlapping sufficient |
| 128 windows   | 128    | **6** segments                         | Non-overlapping sufficient |
| 256 windows   | 64     | **9** segments (sliding window)        | Sliding compensates for short run |

For training, segments from all four lengths are pooled into a single dataset. The `segment_length` value is stored as a **node-level feature** (constant across all nodes in a graph, normalised as `log2(segment_length) / 8.0`) so the model learns to condition on temporal context size.

### 5.5 Data Directory Layout

```
twin/gnn/training_data/v3/
  Attack/
    nap1_nsta2_seed42_positive_300s.json
    nap1_nsta2_seed43_positive_300s.json
    nap1_nsta2_seed42_negative_300s.json
    ...
    nap2_nsta4_seed42_positive_300s.json
    ...
    nap6_nsta12_seed45_negative_300s.json
  Normal/
    nap1_nsta2_seed42_normal_300s.json
    ...
    nap6_nsta12_seed45_normal_300s.json
```

File naming convention:
`nap{N}_nsta{M}_seed{S}_{scenario}_{simtime}s.json`

Each JSON file contains the raw window array with `num_ap` and `num_sta` fields added per window.

---

## 6. Phase 3 — Training Pipeline Updates

### 6.1 Changes to `preprocessing.py`

**Multi-AP normalisation in `extract_features()`:**
```python
num_ap  = windows[0].get('num_ap',  1)
num_sta = windows[0].get('num_sta', 2)

# Per-AP / per-STA normalisation before StandardScaler
features[:, ABSOLUTE_FEATURE_INDICES] /= num_ap   # throughput
features[:, PER_STA_FEATURE_INDICES]  /= num_sta  # MAC/PHY counters
```

**Multi-length segmentation:**
The `segment_into_chunks()` function already accepts `segment_length`. The training script will call it multiple times (32, 64, 128, 256) on each file and pool the resulting `Data` objects.

**Segment-length feature:**
```python
seg_len_feature = np.full((segment_length, 1), np.log2(segment_length) / 8.0)
features = np.hstack([features, seg_len_feature])  # in_channels becomes 17
```

### 6.2 Changes to `config.py` (TrainingConfig)

```python
@dataclass
class TrainingConfig:
    ...
    in_channels: int = 17          # 16 + 1 segment-length feature
    segment_lengths: list = field(default_factory=lambda: [32, 64, 128, 256])
    multi_ap: bool = True          # enable per-AP normalisation
    ...
```

### 6.3 Changes to `train.py`

Replace the single `segment_length` loop with:
```python
all_data = []
for seg_len in config.segment_lengths:
    data = load_and_preprocess(data_root, segment_length=seg_len, config=config)
    all_data.extend(data)
# shuffle, split, train as before
```

### 6.4 Scaler Changes

The new scaler will have `mean` and `std` arrays of length **17** (16 original features + 1 segment-length feature). The `segment_length` feature has mean ≈ 0.875 and std ≈ 0.25 — the scaler will learn the correct normalisation from the training distribution.

The saved `scaler.json` format is unchanged:
```json
{"mean": [17 floats], "std": [17 floats]}
```

---

## 7. Phase 4 — GCN v3 Architecture

### 7.1 Model Changes

The only required model change is `in_channels: 16 → 17`. The rest of the architecture (2 GCN layers, hidden=64, global mean pool, MLP head) is unchanged — no retraining-breaking changes beyond the input dimension.

**Recommended v3 config (`training.yaml`):**
```yaml
version: "3.0.0"
in_channels: 17
hidden_channels: 64
num_layers: 2
dropout: 0.3
pooling: mean
segment_lengths: [32, 64, 128, 256]
multi_ap: true
use_derived_features: true
use_class_weights: true
batch_size: 32
learning_rate: 0.001
weight_decay: 0.0001
max_epochs: 200
patience: 20
random_seed: 42
test_size: 0.15
val_size: 0.15
```

### 7.2 Expected Performance

Based on v2 training history (F1=0.994 on single-AP single-length data):
- v3 will likely show slightly lower F1 on easy single-AP cases (generalisation cost)
- But will have meaningful predictions on 2–6 AP topologies where v2 produces noise
- Target: F1 ≥ 0.92 across all topologies

### 7.3 Ablation Tests (Optional)

After training, run ablation to verify each design choice:

| Experiment | What it tests |
|-----------|--------------|
| v3-no-seglenfeat | Remove segment-length feature (in_channels=16) |
| v3-256-only | Train on 256 only, multi-AP |
| v3-1ap-only | Train on 1 AP only, multi-length |
| v3-full | Full multi-AP + multi-length (the real v3) |

---

## 8. Phase 5 — Registry & Deployment

### 8.1 Registry Structure

```
twin/registry/gcn/
  v3.0.0/
    best_model.pt         ← trained weights
    scaler.json           ← 17-dim mean/std
    config.yaml           ← training config
    test_results.json     ← per-topology breakdown
    training_data_manifest.json  ← list of all 72 training files + metadata
  current -> v3.0.0       ← update symlink after validation
```

### 8.2 `test_results.json` Extended Format

v3 test results should break down by topology for interpretability:

```json
{
  "overall": {
    "accuracy": 0.94, "f1": 0.93, "precision": 0.95, "recall": 0.91, "auc": 0.97
  },
  "by_topology": {
    "nap1": {"f1": 0.99, "n_segments": 132},
    "nap2": {"f1": 0.95, "n_segments": 132},
    "nap3": {"f1": 0.93, "n_segments": 132},
    "nap4": {"f1": 0.91, "n_segments": 132},
    "nap5": {"f1": 0.90, "n_segments": 132},
    "nap6": {"f1": 0.89, "n_segments": 132}
  },
  "by_segment_length": {
    "32":  {"f1": 0.89, "n_segments": 450},
    "64":  {"f1": 0.91, "n_segments": 222},
    "128": {"f1": 0.93, "n_segments": 108},
    "256": {"f1": 0.95, "n_segments": 54}
  },
  "confusion_matrix": [[TP, FP], [FN, TN]]
}
```

### 8.3 Deployment Command

```bash
make gcn-deploy VERSION=v3.0.0
# updates: twin/registry/gcn/current -> v3.0.0
# the live GCN detector hot-reloads within 60s (watch_for_updates: true)
```

---

## 9. Phase 6 — Dashboard Experiment Launcher

### 9.1 New Dashboard Section: "Run Experiment"

A new sidebar item **"Run Experiment"** will appear between Pipeline Monitor and Experiment View. It consists of three panels:

#### Panel A — Simulation Configuration

```
┌─────────────────────────────────────────────────────┐
│  Simulation Configuration                           │
│                                                     │
│  Scenario:  ○ Normal  ● Attack (+)  ○ Attack (-)    │
│  Seed:      [  42  ]                                │
│  Sim Time:  [═══════════════●────] 120s             │
│  Bias:      [══════●────────────] 5000  (attack only)│
│                                                     │
│  Access Points:  [═●──────] 2                       │
│  Stations/AP:    [═══●───] 4                        │
│                                                     │
│  Segment Length: ○ 32  ○ 64  ● 128  ○ 256           │
│    ⚠ Uses v3 model (multi-length support)           │
│    ⚠ Only 32/64/128/256 supported                   │
│                                                     │
│  Experiment ID: [20260313-1430-attack-pos-2ap-42]   │
│                          (auto-generated, editable) │
│                                                     │
│  [        Launch Experiment        ]                │
└─────────────────────────────────────────────────────┘
```

#### Panel B — Live Run Progress

Appears after Launch, replaces the form (or slides below it):

```
┌─────────────────────────────────────────────────────┐
│  Running: 20260313-1430-attack-pos-2ap-42           │
│                                                     │
│  ████████████░░░░░░░░  62%  NS-3 Simulation         │
│                                                     │
│  ✅ NS-3 started       09:12:30                     │
│  ✅ Windows: 1247      09:12:45                     │
│  ⏳ Exporter sending…                               │
│  ○  Windowizer                                      │
│  ○  GCN Detector                                    │
│  ○  Database                                        │
│                                                     │
│  [  Cancel  ]                                       │
└─────────────────────────────────────────────────────┘
```

#### Panel C — Quick Results

Appears after the run completes. Shows a summary card with attack rate, confidence, and a "View Full Results →" button that navigates to Experiment View pre-loaded with this experiment.

### 9.2 Backend API Additions

New file: `dashboard/app/backend/api/run.py`
Router prefix: `/run`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/run/launch` | Validate params, spawn NS-3 subprocess chain |
| `GET`  | `/run/status` | Return current run state (reads `.pipeline_active.json`) |
| `POST` | `/run/cancel` | Send SIGTERM to active subprocess group |
| `GET`  | `/run/history` | Last 20 launched runs with outcomes |

**`POST /run/launch` request body:**
```json
{
  "scenario":        "attack-pos",
  "seed":            42,
  "sim_time":        120.0,
  "bias":            5000,
  "num_ap":          2,
  "num_sta":         4,
  "segment_length":  128,
  "experiment_id":   "20260313-1430-attack-pos-2ap-42"
}
```

**`POST /run/launch` response:**
```json
{
  "ok": true,
  "experiment_id": "20260313-1430-attack-pos-2ap-42",
  "message": "Experiment launched"
}
```

**Implementation notes:**
- Use `asyncio.create_subprocess_exec` (non-blocking, no shell injection risk)
- Store subprocess PID in a global state variable (`app.state.active_run`)
- Prevent concurrent runs: return `409 Conflict` if a run is already active
- Write status updates to `.pipeline_active.json` (already polled by Pipeline Monitor WS)
- The full pipeline (NS-3 → exporter → windowizer → GCN) runs end-to-end automatically via `make run-mlo-exp-stream`
- Capture stdout/stderr to a log file at `sim/ns3/artifacts/last_run.log`

### 9.3 Windowizer Segment-Length Configurability

The windowizer currently hardcodes `segment_length=256` in its config. To support launching with different segment lengths, the launcher API will:

1. Write a new `segment_length` value to `security/detector/windowizer/config.yaml` before starting the pipeline
2. Restart the windowizer container via `docker compose restart windowizer`
3. After the experiment completes, restore the default segment_length

**OR** (cleaner approach): the windowizer reads `segment_length` from the Kafka message header (set by the exporter based on the experiment config), avoiding the restart requirement. This is the preferred design for v3.

### 9.4 Frontend State Flow

```
User fills form → [Launch] →
  POST /run/launch →
  (if 409: show "run already active" warning) →
  show progress panel →
  poll GET /run/status every 2s →
  pipeline stages animate as each completes →
  run complete →
  show results summary card →
  [View Full Results] → navigates to ExperimentSection with new exp pre-selected
```

The `AppContext` will gain a `launchedExperimentId` field so the post-run navigation can pre-select the correct experiment.

### 9.5 Model Version Warning

If the user selects `nAp > 1` or `segment_length < 256` and the active model is v2 (which only supports `nAp=1, segment_length=256`), the UI shows a warning:

> ⚠ Active model v2.0.0 was trained on 1-AP / 256-window data only. Predictions may be unreliable for this configuration. Consider upgrading to v3.0.0.

---

## 10. Phase 7 — Validation Plan

### 10.1 Unit Tests

| Test | What it verifies |
|------|-----------------|
| `test_preprocessing_multiap.py` | Per-AP normalisation produces same scale across nAp=1–6 |
| `test_preprocessing_multilength.py` | Segments of length 32/64/128/256 all produce valid Data objects |
| `test_model_v3_forward.py` | v3 model accepts 32, 64, 128, 256 node graphs without error |
| `test_scaler_stability.py` | Scaler z-scores are within [-3, 3] for all segment lengths and AP counts |

### 10.2 Integration Test Matrix

After training and deploying v3, run the following experiments via the dashboard and verify correct detection:

| Config | Expected outcome |
|--------|-----------------|
| nAp=1, nSta=2, normal, seg=256 | 0% attack rate |
| nAp=1, nSta=2, attack-pos, seg=256 | ≥90% attack rate |
| nAp=2, nSta=4, normal, seg=128 | 0% attack rate |
| nAp=2, nSta=4, attack-neg, seg=128 | ≥85% attack rate |
| nAp=4, nSta=8, normal, seg=64 | 0% attack rate |
| nAp=4, nSta=8, attack-pos, seg=64 | ≥80% attack rate |
| nAp=6, nSta=12, normal, seg=32 | 0% attack rate |
| nAp=6, nSta=12, attack-neg, seg=32 | ≥70% attack rate |

### 10.3 Playwright End-to-End Tests

Using the existing Playwright test infrastructure:
1. Open dashboard → Run Experiment section
2. Set nAp=2, scenario=attack-pos, seed=42, sim_time=60s
3. Click Launch
4. Verify progress stages animate in sequence
5. Verify Experiment View shows the new experiment with attack predictions

---

## 11. Implementation Sequence & Dependencies

```
Step 1  [NS-3]      Add --nAp, --nSta, --seed to C++ .cc files (3 files)
Step 2  [NS-3]      Update run_mlo_scenario.sh with NAP/NSTA/SEED env vars
Step 3  [NS-3]      Add num_ap/num_sta fields to JSON output per window
Step 4  [Makefile]  Add NAP/NSTA to make run-mlo-exp target
          ↓
Step 5  [Data]      Run 72 NS-3 simulations (or batch via script)
          ↓
Step 6  [Training]  Update preprocessing.py — multi-AP normalisation
Step 7  [Training]  Update preprocessing.py — segment-length feature (in_channels → 17)
Step 8  [Training]  Update train.py — multi-length loop
Step 9  [Training]  Update TrainingConfig — segment_lengths list
Step 10 [Training]  Train v3.0.0 (make gcn-train OUTPUT_DIR=twin/registry/gcn/v3.0.0)
          ↓
Step 11 [Registry]  Populate test_results.json with per-topology breakdown
Step 12 [Registry]  make gcn-deploy VERSION=v3.0.0
          ↓
Step 13 [Backend]   Add POST /run/launch endpoint (api/run.py)
Step 14 [Backend]   Add GET /run/status and POST /run/cancel endpoints
Step 15 [Backend]   Add GET /run/history endpoint + query in queries.py
Step 16 [Backend]   Register new router in main.py
          ↓
Step 17 [Frontend]  Create RunSection.tsx with config form + progress panel
Step 18 [Frontend]  Add "Run Experiment" to sidebar navigation
Step 19 [Frontend]  Add model compatibility warning component
Step 20 [Frontend]  Add post-run results summary + navigation to ExperimentView
          ↓
Step 21 [Tests]     Run unit tests for preprocessing changes
Step 22 [Tests]     Run integration test matrix (8 experiment configs)
Step 23 [Tests]     Run Playwright end-to-end test for dashboard launcher
```

---

## 12. Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `docs/WP12-GCN-V3-MULTI-AP-TRAINING-PLAN.md` | This document |
| `twin/gnn/training_data/v3/` | v3 training data directory |
| `sim/ns3/scenario/collect_v3_data.sh` | Parallel batch data collection script |
| `dashboard/app/backend/api/run.py` | Experiment launcher API |
| `dashboard/app/frontend/src/sections/RunSection.tsx` | Launcher UI section |
| `dashboard/app/frontend/src/hooks/useRun.ts` | Frontend hooks for run API |
| `twin/registry/gcn/v3.0.0/` | v3 model registry entry |

### Modified Files

| File | Change |
|------|--------|
| `sim/ns3/scenario/mlo-wifi7-normal.cc` | Add --nAp, --nSta, --seed cmd args |
| `sim/ns3/scenario/mlo-wifi7-positive.cc` | Same |
| `sim/ns3/scenario/mlo-wifi7-negative.cc` | Same |
| `sim/ns3/scenario/run_mlo_scenario.sh` | Add NAP, NSTA, SEED env vars |
| `Makefile` | Add NAP/NSTA to simulation targets |
| `twin/gnn/detector/gcn_src/data/preprocessing.py` | Multi-AP normalisation + seg-len feature |
| `twin/gnn/detector/gcn_src/training/train.py` | Multi-length training loop |
| `twin/gnn/detector/gcn_src/training/config.py` | segment_lengths list, in_channels=17 |
| `twin/gnn/detector/feature_processor.py` | Runtime multi-AP normalisation |
| `dashboard/app/backend/main.py` | Register /run router |
| `dashboard/app/frontend/src/App.tsx` | Add Run Experiment route |
| `docker-compose.dashboard.yml` | Add SIM_DIR volume mount for launcher |

---

## 13. Open Questions / Decisions Needed

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | How to handle segment_length at runtime for windowizer? | (a) restart with new config, (b) read from Kafka header | Option B — no restart needed |
| 2 | Should v3 keep backward compatibility with v2 scaler? | (a) separate scalers, (b) unified 17-dim scaler | Separate — v2 registry unchanged |
| 3 | nSta per AP or total stations? | (a) nSta = stations per AP, (b) nSta = total | Per AP makes more sense for multi-AP normalisation |
| 4 | Abort behaviour for launcher if NS-3 fails mid-run? | (a) surface error in UI, partial data in DB, (b) rollback experiment | Surface error; partial data is valuable |
| 5 | Dashboard model compatibility warning: hard block or soft warning? | (a) disable Launch button, (b) show warning but allow | Soft warning — allow expert overrides |
| 6 | Training infra: local GPU or need cloud? | v2 trained in <1h on CUDA. v3 has ~10× more data → ~5–10h on GPU | Plan for overnight GPU run |

---

## 14. Estimated Effort

| Phase | Estimated effort |
|-------|-----------------|
| Phase 1 — NS-3 C++ changes | 1–2 days |
| Phase 2 — Data collection | ~36–120 min wall-clock (8–16 cores parallel); write collect script = 0.5 days |
| Phase 3/4 — Training pipeline + training run | 2–3 days |
| Phase 5 — Registry + deployment | 0.5 days |
| Phase 6 — Dashboard launcher | 2–3 days |
| Phase 7 — Validation + tests | 1 day |
| **Total** | **~7–12 days** |

---

## 15. Success Criteria

- [x] NS-3 C++ binary accepts `--nAp`, `--nSta`, `--seed` on all three scenario files
- [x] Data collection: 48 files (nap1-4) stored in `twin/gnn/training_data/v3/` (nap5/6 deferred to v3.1.0)
- [x] v3 model trained with F1 ≥ 0.92 overall — achieved F1=0.9978
- [x] v3 model in registry at `twin/registry/gcn/v3.0.0/`
- [x] `current` symlink updated to v3.0.0
- [x] Dashboard "Run Experiment" section functional (backend complete; frontend rebuild needed)
- [x] Multi-AP predictions working: nAp=1-4 all return meaningful confidence scores
- [x] Multi-length predictions working: seg=32/64/128/256 all produce valid results
- [ ] Playwright test passes the full launch-to-results flow — deferred to v3.1.0

---

*WP12 is complete. Next: WP13 — Closed-loop policy actuation (detector → ZSM/SDN response).*
