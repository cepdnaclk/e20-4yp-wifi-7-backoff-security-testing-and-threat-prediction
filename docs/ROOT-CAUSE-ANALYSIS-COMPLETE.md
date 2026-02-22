# Root Cause Analysis: GCN Model False Positives

**Date:** 2026-02-15
**Issue:** Model v2.1.0 achieves 99.49% test accuracy but 100% false positive rate in production
**Status:** ✅ ROOT CAUSE IDENTIFIED

---

## Executive Summary

The GCN model v2.1.0 performs perfectly on test data (99.49% accuracy) but fails in production because **the training data does not represent realistic network conditions**. The training data labeled as "normal" has 83.8% packet loss and 124ms delay - which is severely degraded traffic, not normal traffic.

---

## The Mystery

**Training/Test Performance:**
- Accuracy: 99.49%
- Recall: 100%
- F1 Score: 99.43%
- Standalone test: 6/6 files correctly classified ✓

**Production Performance:**
- Normal traffic: 0/25 correctly classified (100% false positives) ❌
- Attack traffic: All correctly classified as attacks ✓

---

## Investigation Results

### 1. Feature Distribution Comparison

#### Training Data "Normal" Traffic:
```
Packet Loss:     83.8% (!!!)
Delay:          124ms
Jitter:         0.83ms
Backoff Slots:  18.0
Active Flows:   8
Throughput:     430 Mbps
Channel Busy:   84%
Bias:           0
```

#### Validation Experiment Normal Traffic:
```
Packet Loss:     2.5% ✓ (realistic!)
Delay:          4.3ms ✓ (healthy!)
Jitter:         0.26ms ✓
Backoff Slots:  9.7
Active Flows:   6
Throughput:     304 Mbps
Channel Busy:   79%
Bias:           0
```

#### Differences:
| Metric | Training | Validation | Difference |
|--------|----------|------------|------------|
| **Packet Loss** | 83.8% | 2.5% | **-97%** 😱 |
| **Delay** | 124ms | 4.3ms | **-96%** 😱 |
| **Jitter** | 0.83ms | 0.26ms | **-68%** |
| **Backoff Slots** | 18.0 | 9.7 | **-46%** |
| **Active Flows** | 8 | 6 | **-26%** |
| **Throughput** | 430 Mbps | 304 Mbps | **-29%** |

### 2. Attack Data Comparison

#### Training Data Attack Traffic:
```
Packet Loss:     93.9%
Delay:          380ms
Backoff Slots:  4.4 ⬇️ (KEY DIFFERENCE!)
Bias:           -2500
```

#### Validation Experiment Attack Traffic:
```
Packet Loss:     48.5%
Delay:          138ms
Backoff Slots:  2.3 ⬇️
Bias:           -500
```

---

## Root Cause Explanation

### What the Model Learned:

The model learned from the training data that:

1. **"Normal" traffic** = High packet loss (83.8%) + High delay (124ms) + **HIGH backoff slots (18.0)**
2. **"Attack" traffic** = Even higher packet loss (93.9%) + Very high delay (380ms) + **LOW backoff slots (4.4)**

The **PRIMARY discriminator** the model learned: **Attacks have LOW backoff slots!**

### Why Production Fails:

When the model sees validation normal traffic:
- Packet loss: 2.5% (MUCH lower than training "normal" 83.8%)
- Delay: 4.3ms (MUCH lower than training "normal" 124ms)
- **Backoff slots: 9.7** (closer to training attack 4.4 than training normal 18.0!)

**The model thinks:**
> "This has low backoff slots (9.7, closer to attack 4.4), low packet loss (not like training normal 83.8%), and low delay (not like training normal 124ms). This doesn't match my learned pattern for 'normal' traffic. Must be an attack!"

### The Fundamental Problem:

**The training data is not representative of realistic network conditions.**

- 83.8% packet loss is NOT normal traffic - it's severely degraded/failing network
- 2.5% packet loss (validation) IS actual normal, healthy traffic
- The model was trained to recognize degraded traffic as "normal" and healthy traffic appears anomalous

---

## Why Standalone Test Worked

The standalone test used the SAME training data files that the model was trained on:
- It tested on: `session_2_scenario_3_normal_run_1.json`
- This file has: 83.8% packet loss, 124ms delay, 18.0 backoff
- Model predicted: Normal ✓

**The standalone test worked because test data = training distribution!**

But when we deploy to production with REALISTIC normal traffic (2.5% loss, 4ms delay), it fails.

---

## Grafana Dashboard Status

### Data Available in Database:

**v2.1.0 Predictions:**
- Experiment: `20260215-validation-normal-01`
- Total Segments: 25
- Predicted Normal: 0
- Predicted Attack: 25 (100% false positives)
- Average Confidence: 100%
- Average Inference Time: 24.08ms
- Model Version: v2.1.0 ✓

**v2.0.0 Predictions (for comparison):**
- Same experiment: 705 segments, all predicted as attack
- Also 100% false positives

### What's Displaying in Grafana:

The Grafana dashboard at http://localhost:3000 shows:

1. **Latest Predictions**: ✓ Working
   - Shows all 25 segments from validation-normal-01
   - All marked as "Attack" (red)
   - Confidence: 100%

2. **Model Information**: ✓ Working
   - Model Version: v2.1.0
   - Device: CPU
   - Parameters: 7,650

3. **Performance Metrics**: ✓ Working
   - Average Inference Time: 24.08ms per segment
   - Prediction Rate: Real-time

4. **Timeline Visualization**: ✓ Working
   - Shows predictions over time (05:04 - 05:07 UTC)
   - All segments shown as attack detections

5. **KPI Trends**: ✓ Working (but showing wrong predictions)
   - Packet loss trends
   - Delay trends
   - Backoff patterns
   - All correctly visualized from telemetry data

**The dashboard is fully functional** - it's correctly displaying the (incorrect) predictions from the mismatched model.

---

## Solution Options

### Option 1: Retrain with Realistic Data ⭐ RECOMMENDED

**Action:** Generate new training data with realistic network conditions

**Steps:**
1. Run new ns-3 simulations with proper parameters:
   - Normal traffic: 1-5% packet loss, 5-20ms delay (realistic)
   - Attack traffic: Manipulated backoff causing observable degradation

2. Ensure attack differs from normal in:
   - Backoff manipulation patterns
   - Observable performance degradation
   - NOT just arbitrary label differences

3. Retrain model v3.0.0 on realistic data

4. Validate on held-out realistic experiments

**Expected Result:** Model learns realistic normal vs attack patterns

### Option 2: Collect Production Data for Retraining

**Action:** Run validation experiments as new training data

**Steps:**
1. Label validation experiments correctly:
   - `20260215-validation-normal-01` → Normal (bias=0)
   - `20260215-validation-attack-neg-01` → Attack (bias=-500)
   - `20260215-validation-attack-pos-01` → Attack (bias=+500)

2. Add more diverse scenarios

3. Retrain model v2.2.0 on this data

4. Test on new held-out validation experiments

**Expected Result:** Model learns production-realistic patterns

### Option 3: Feature Engineering

**Action:** Remove features causing distribution mismatch

**Steps:**
1. Train model using ONLY attack-specific features:
   - `avg_backoff_slots` (manipulated in attacks)
   - `bias` (if available during inference - currently excluded)

2. Exclude network performance features that vary with conditions:
   - Packet loss
   - Delay
   - Jitter

**Expected Result:** Model focuses on backoff manipulation, not traffic quality

---

## Immediate Next Steps

### Step 1: Verify Root Cause (DONE ✓)
- [x] Compare training vs validation feature distributions
- [x] Identify key differences
- [x] Understand why model fails
- [x] Document findings

### Step 2: Generate Realistic Training Data

Create new experiments with realistic parameters:

```bash
# Normal traffic (1-3% loss, 5-10ms delay)
for seed in {1..20}; do
    make run-mlo-normal EXP_ID=realistic-normal-${seed} SEED=${seed}
done

# Negative attack (bias=-500, -1000, -2500)
for bias in -500 -1000 -2500; do
    for seed in {1..10}; do
        make run-mlo-negative EXP_ID=realistic-attack-neg-${bias}-${seed} \
            SEED=${seed} BIAS=${bias}
    done
done

# Positive attack (bias=+500, +1000, +2500)
for bias in 500 1000 2500; do
    for seed in {1..10}; do
        make run-mlo-positive EXP_ID=realistic-attack-pos-${bias}-${seed} \
            SEED=${seed} BIAS=${bias}
    done
done
```

### Step 3: Retrain Model v3.0.0

Use the new realistic data:
```bash
cd /home/cobrakali/github/wifi7_gcn_attack_detection
# Move old data to backup
mv data data_unrealistic_backup
# Create new data directory and populate with realistic experiments
mkdir -p data/{Normal,Attack}
# Convert realistic experiments to training format
# ... (conversion scripts)
# Retrain
python train_model.py  # Will use new data/
```

### Step 4: Validate End-to-End

Test v3.0.0 on held-out realistic experiments and verify:
- Normal traffic: Predicted as Normal (0)
- Attack traffic: Predicted as Attack (1)
- False positive rate < 5%
- False negative rate < 1%

---

## Technical Details

### Model Architecture (Unchanged)
```
WiFi7AttackGCN(
  in_channels=16,
  hidden_channels=64,
  num_layers=2,
  dropout=0.3,
  pooling='mean',
  parameters=7,650
)
```

### Features Used (16 total)
**Base Features (13):**
1. net_throughput_mbps
2. net_avg_delay_ms
3. net_avg_jitter_ms
4. net_packet_loss_ratio
5. net_active_flows
6. mac_tx_delta
7. mac_rx_delta
8. mac_ack_delta
9. mac_retrans_delta
10. mac_drop_delta
11. phy_drop_delta
12. avg_backoff_slots ⭐ KEY FEATURE
13. channel_busy_ratio

**Derived Features (3):**
14. retrans_rate
15. drop_rate
16. ack_ratio

**Note:** MAC features (6-11) are all zero in current simulations - not used by model

### Effective Features

Based on analysis, the model primarily uses:
- `avg_backoff_slots` ⭐ PRIMARY
- `net_packet_loss_ratio`
- `net_avg_delay_ms`
- `net_avg_jitter_ms`
- `channel_busy_ratio`

---

## Lessons Learned

1. **Test data must match production distribution**
   - Achieving 99% accuracy on test data doesn't guarantee production performance
   - Test/validation split must represent real-world conditions

2. **Domain knowledge is critical**
   - 83.8% packet loss is NOT normal traffic
   - Should have been caught during data validation

3. **Feature analysis is essential**
   - Understanding what features the model uses to discriminate
   - Validating feature distributions across train/test/production

4. **Always validate on out-of-distribution data**
   - Test on data from different sources/configurations
   - Check model robustness to distribution shifts

---

## Conclusion

**The v2.1.0 model is working correctly** - it learned patterns from the training data accurately (99.49% test accuracy).

**The problem is the training data** - it doesn't represent realistic network conditions.

**The solution** - Retrain on realistic data where "normal" means healthy traffic (low loss, low delay) and "attack" means backoff manipulation causing observable degradation.

The pipeline, Grafana dashboard, and model architecture are all functioning correctly. We just need realistic training data.
