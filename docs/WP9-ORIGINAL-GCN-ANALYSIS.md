# Original GCN Training Data Analysis

**Date**: 2026-02-13
**Purpose**: Understand the original GCN training data structure to inform retraining plan

---

## 📊 Complete Data Structure

### Distribution Summary

| Category | Count | Percentage |
|----------|-------|------------|
| **Normal** | 12 | 5.9% |
| **Attacks** | 192 | 94.1% |
| - Positive Bias | 96 | 47.1% |
| - Negative Bias | 96 | 47.1% |
| **Total** | 204 | 100% |

---

## 🎯 Bias Values Used (Critical Finding!)

The original used **8 bias levels** with logarithmic spacing:

| Bias Value | Positive Scenarios | Negative Scenarios | Total | Attack Type |
|------------|-------------------|-------------------|-------|-------------|
| **50** | 12 | 12 | 24 | Very Subtle |
| **100** | 12 | 12 | 24 | Subtle |
| **250** | 12 | 12 | 24 | Moderate |
| **500** | 12 | 12 | 24 | Moderate-Strong |
| **1000** | 12 | 12 | 24 | Strong |
| **2500** | 12 | 12 | 24 | Very Strong |
| **5000** | 12 | 12 | 24 | Extreme |
| **10000** | 12 | 12 | 24 | Maximum |

**Key Insight**: The low bias values (50-500) are **CRITICAL** for detecting subtle attacks!

**Logarithmic Spacing Rationale**:
- 50 → 100 = 2x (significant change when small)
- 100 → 250 = 2.5x
- 250 → 500 = 2x
- 500 → 1000 = 2x
- 1000 → 2500 = 2.5x
- 2500 → 5000 = 2x
- 5000 → 10000 = 2x

This ensures good coverage across the full attack spectrum.

---

## 🏗️ Scenario Configurations

The original used **4 different network scenarios** representing varying network densities:

### Scenario 1: Light Network
- **Active Flows**: ~6
- **Throughput**: ~412 Mbps
- **Network Load**: Low contention
- **Description**: Baseline configuration (likely 1 AP + 2 STAs)

### Scenario 2: Moderate Network
- **Active Flows**: ~8.7
- **Throughput**: ~325 Mbps
- **Network Load**: Moderate contention
- **Description**: More stations or higher traffic

### Scenario 3: Dense Network
- **Active Flows**: ~10.2
- **Throughput**: ~303 Mbps
- **Network Load**: High contention
- **Description**: Dense deployment

### Scenario 4: Very Dense Network
- **Active Flows**: ~11.9
- **Throughput**: ~261 Mbps
- **Network Load**: Very high contention
- **Description**: Maximum density tested

**Note**: Exact station counts not documented, but inferred from flow counts:
- 6 flows ≈ 3 nodes (1 AP + 2 STAs) in full mesh
- 8-9 flows ≈ 4 nodes (1 AP + 3 STAs)
- 10-12 flows ≈ 4-5 nodes

---

## 🔄 Sessions vs Scenarios

**Sessions** (1, 2, 3):
- Essentially **repetitions** of the same configurations
- Different random seeds
- Same scenario parameters
- Purpose: Increase data diversity through randomness

**Scenarios** (1, 2, 3, 4):
- Different **network configurations**
- Different network densities
- Different throughput characteristics
- Purpose: Test model on varied network conditions

---

## 📁 File Organization

### Naming Convention
```
session_X_scenario_Y_[normal|positive_bias_Z|negative_bias_Z]_run_R.json

Where:
- X = Session number (1-3)
- Y = Scenario number (1-4)
- Z = Bias value (50, 100, 250, 500, 1000, 2500, 5000, 10000)
- R = Run number (varies)
```

### Directory Structure
```
Wifi7_Datasets/
├── Normal/
│   ├── session_1_scenario_1_normal_run_1.json
│   ├── session_1_scenario_2_normal_run_1.json
│   ├── session_1_scenario_3_normal_run_1.json
│   ├── session_1_scenario_4_normal_run_1.json
│   ├── session_2_scenario_1_normal_run_1.json
│   ├── ... (12 total)
│
└── Attack/
    ├── session_1_scenario_1_positive_bias_50_run_10.json
    ├── session_1_scenario_1_negative_bias_50_run_2.json
    ├── session_1_scenario_2_positive_bias_100_run_11.json
    ├── ... (192 total)
```

---

## 📈 Data Characteristics

### File Properties
- **Windows per file**: 14,000 (1400 seconds × 10 windows/sec)
- **Window duration**: 100ms
- **Total simulation time**: 1400 seconds
- **Features per window**: 13 base features

### Throughput Distribution by Scenario

| Scenario | Avg Throughput | Std Dev | Flow Count |
|----------|---------------|---------|------------|
| 1 | 412 Mbps | ~25 Mbps | 6 |
| 2 | 325 Mbps | ~30 Mbps | 8.7 |
| 3 | 303 Mbps | ~35 Mbps | 10.2 |
| 4 | 261 Mbps | ~40 Mbps | 11.9 |

**Observation**: As network density increases:
- Throughput decreases (more contention)
- Variability increases (more complex interactions)
- Flow count increases (more active connections)

---

## 🎓 Key Lessons for Retraining

### 1. Bias Value Coverage is Critical ✅
- **MUST include**: 50, 100, 250, 500 (subtle attacks)
- **Also include**: 1000, 2500, 5000, 10000 (obvious attacks)
- **Spacing**: Logarithmic (2-2.5x intervals)

### 2. Network Diversity Matters ✅
- Test on multiple network densities (light to very dense)
- Vary flow counts (6-12 flows)
- Vary throughput ranges (260-410 Mbps)

### 3. Data Distribution Strategy ✅
- **Original**: ~6% normal, ~94% attack (very imbalanced)
- **Recommendation**: Increase normal to 10-15% for better balance
- **Reasoning**: Model should be equally good at detecting normal vs attacks

### 4. Repetitions with Different Seeds ✅
- Use multiple random seeds for same configuration
- Increases robustness to randomness
- Prevents overfitting to specific initialization

---

## 🔄 Comparison with Current Pipeline

### Similarities ✅
- Same 13 base features
- Same 100ms window size
- Same 1400s simulation duration
- Same WiFi 7 MLO setup

### Differences ❌
- **Throughput**: Pipeline generates ~306 Mbps vs original's 412 Mbps
- **Configuration**: Pipeline uses different ns-3 parameters
- **Reason**: Different data rates, station counts, or MCS settings

### Impact on Model
- Model learned "normal = 412 Mbps ± 25"
- Pipeline produces "normal = 306 Mbps ± 12"
- **Result**: 100% false positive rate (everything flagged as attack)

---

## 📋 Recommendations for New Training Data

### Scenario Matrix (Based on Original)

**Normal Scenarios**: 15 total
- 3 baseline (6 flows, ~300 Mbps) × 5 seeds
- 4 moderate (8 flows, ~350 Mbps) × 3 seeds
- 4 dense (10 flows, ~400 Mbps) × 3 seeds
- 4 very dense (12 flows, ~450 Mbps) × 2 seeds

**Attack Scenarios**: 240 total (8 bias levels × 2 directions × 15 scenarios each)

**Bias Levels** (CRITICAL - Must Match Original):
- 50, 100, 250, 500, 1000, 2500, 5000, 10000

**Total**: 255 scenarios (15 normal + 240 attack)

**Distribution**: ~6% normal, ~94% attack (matches original)

---

## 🎯 Success Criteria

The new model v2.0.0 should achieve:

| Metric | Target | Original v1.0.0 |
|--------|--------|-----------------|
| Test F1 Score | > 0.85 | 0.994 |
| Recall (Attack Detection) | > 0.90 | 1.000 |
| Precision | > 0.85 | 0.989 |
| False Positive Rate | < 10% | ~1% |

**Note**: We expect slightly lower performance than v1.0.0 because:
- Pipeline data may have different characteristics
- We're testing generalization to new scenarios
- Target is "production-ready" (85%+) not "perfect" (99%+)

---

## 📊 Storage Requirements

**Per Scenario**:
- JSON file: ~5 MB (14,000 windows)
- JSONL file: ~35 MB (182,000 metrics)

**Total Dataset**:
- 255 scenarios × 40 MB = ~10 GB
- Manageable on modern systems
- Can be compressed for long-term storage

---

## ✅ Validation Strategy

### Phase 1: Pilot Study (30 scenarios)
- 5 normal + 25 attack (5 bias levels × 5 scenarios each)
- Validates data generation works
- Fast iteration (6-8 hours)
- Tests if model learns on pipeline data

### Phase 2: Full Dataset (255 scenarios)
- Complete coverage (all 8 bias levels)
- Full scenario diversity
- Production-ready model
- 5-7 days total

### Phase 3: Holdout Testing
- Generate 20 fresh scenarios (never seen by model)
- Test generalization
- Validate model works on unseen data

---

**Created**: 2026-02-13
**Based on**: Analysis of ~/github/wifi7_gcn_attack_detection/Wifi7_Datasets/
**Purpose**: Inform WP9 retraining plan with correct parameters
