# NS-3 Configuration Alignment Guide

**Date**: 2026-02-12
**Your Question**: Can we make the pipeline use the same ns-3 configuration as the original GCN training data?

**Answer**: YES, potentially! This is a MUCH better approach than retraining if we can match the configurations.

---

## 🎯 Your Insight is Correct!

You're absolutely right! Instead of retraining, we should try to:
1. Identify what ns-3 parameters were used to generate the original training data
2. Modify the pipeline's ns-3 scenarios to use those same parameters
3. Use the existing v1.0.0 model without retraining

**This would save 1-2 days of retraining time!**

---

## 📊 Current Situation: Data Comparison

### Original Training Data Statistics

```
File: session_1_scenario_1_normal_run_1.json
Windows: 14,000
Throughput: Mean=411.74 Mbps, Std=27.45
Backoff: Mean=9.96 slots, Std=3.87
```

### Pipeline Data Statistics

```
File: 20260212-1904-normal/mlo_output.json
Windows: 300
Throughput: Mean=509.01 Mbps, Std=96.91
Backoff: Mean=10.55 slots, Std=10.34
```

### Key Differences

| Parameter | Original | Pipeline | Difference |
|-----------|----------|----------|------------|
| Simulation Length | 14,000 windows | 300 windows | 47x shorter |
| Throughput Mean | 411.74 Mbps | 509.01 Mbps | +97 Mbps (24%) |
| Throughput Std | 27.45 | 96.91 | 3.5x more variable |
| Backoff Mean | 9.96 slots | 10.55 slots | +0.59 slots |
| Backoff Std | 3.87 | 10.34 | 2.7x more variable |

---

## 🔍 What Could Cause These Differences?

### Possible NS-3 Configuration Differences

1. **Simulation Time**
   - Original: Longer (14,000 windows × 100ms = 1,400 seconds = 23 minutes)
   - Pipeline: Shorter (300 windows × 100ms = 30 seconds)
   - **Impact**: Shorter sims may not reach steady state

2. **Number of Stations**
   - Original: Unknown (could be 2, 3, or more)
   - Pipeline: Unknown (need to check)
   - **Impact**: More stations = more contention = lower throughput

3. **Traffic Pattern**
   - Original: Unknown data rate/packet size
   - Pipeline: Unknown data rate/packet size
   - **Impact**: Different traffic loads = different throughput

4. **MCS (Modulation and Coding Scheme)**
   - Original: Unknown MCS settings
   - Pipeline: Unknown MCS settings
   - **Impact**: Higher MCS = higher throughput

5. **Channel Width**
   - Original: Unknown (20/40/80/160 MHz)
   - Pipeline: Unknown
   - **Impact**: Wider channel = higher throughput

6. **Distance/Path Loss**
   - Original: Unknown station positions
   - Pipeline: Unknown
   - **Impact**: Distance affects signal strength affects throughput

---

## ✅ Action Plan: Align Configurations

### Step 1: Identify Original Simulation Parameters

**Problem**: The original training data doesn't include simulation metadata.

**Options**:

**A. Reverse Engineer from Data** ✅ DOABLE

Analyze the original data to infer parameters:

```python
# Analysis script
import json
import numpy as np

# Load original normal data
with open('Wifi7_Datasets/Normal/session_1_scenario_1_normal_run_1.json') as f:
    data = json.load(f)

# Calculate statistics
throughputs = [w['net_throughput_mbps'] for w in data if w['window'] > 0]
active_flows = [w['net_active_flows'] for w in data if w['window'] > 0]
delays = [w['net_avg_delay_ms'] for w in data if w['window'] > 0]

print(f"Avg throughput: {np.mean(throughputs):.2f} Mbps")
print(f"Avg active flows: {np.mean(active_flows):.2f}")
print(f"Avg delay: {np.mean(delays):.2f} ms")

# Infer configuration:
# - If throughput ~400 Mbps with WiFi 7, likely:
#   - 2-3 stations
#   - Medium distance
#   - Standard traffic pattern
```

**B. Contact Original Data Source** (if available)

If you have access to the person/team who generated the original dataset, ask them for:
- NS-3 scenario files (.cc files)
- Configuration parameters
- Simulation setup documentation

**C. Run Parameter Sweep**

Try different configurations until output matches:

```bash
# Try different simulation times
for simtime in 30 60 120 300 600; do
    make ns3-run-scenario EXP_ID=test-${simtime}s \
        SCENARIO=normal SEED=42 SIMTIME=${simtime}
done

# Compare outputs to find best match
```

---

### Step 2: Modify Pipeline NS-3 Scenarios

Once we identify the parameters, update the pipeline scenarios.

**Current Pipeline Scenario**: `sim/ns3/scratch/wifi7-mlo-Normal.cc`

**Key Parameters to Adjust**:

```cpp
// 1. Simulation Time
double simulationTime = 1400.0;  // Match original (1400s vs 30s)

// 2. Number of Stations
uint32_t nWifi = 2;  // Or 3, depending on original

// 3. Traffic Pattern
uint32_t payloadSize = 1472;     // Match original packet size
DataRate dataRate("10Mbps");      // Match original data rate

// 4. MCS Settings
wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                              "DataMode", StringValue("HeMcs0"),
                              "ControlMode", StringValue("HeMcs0"));

// 5. Channel Width
phy.Set("ChannelSettings", StringValue("{0, 0, BAND_5GHZ, 0}"));
// Adjust channel width

// 6. Position/Distance
positionAlloc->Add(Vector(0.0, 0.0, 0.0));   // AP position
positionAlloc->Add(Vector(1.0, 0.0, 0.0));   // STA1 position
positionAlloc->Add(Vector(2.0, 0.0, 0.0));   // STA2 position
// Adjust distances
```

---

### Step 3: Test Alignment

After modifying configurations, test if data matches:

```bash
# 1. Run modified scenario
make ns3-run-scenario EXP_ID=aligned-test SCENARIO=normal SEED=42

# 2. Compare statistics
python3 << 'EOF'
import json
import numpy as np

# Load original
with open('wifi7_gcn_attack_detection/Wifi7_Datasets/Normal/session_1_scenario_1_normal_run_1.json') as f:
    original = json.load(f)

# Load aligned
with open('sim/ns3/artifacts/aligned-test/mlo_output.json') as f:
    aligned = json.load(f)

# Compare throughput
orig_tp = np.mean([w['net_throughput_mbps'] for w in original[100:1000]])
alig_tp = np.mean([w['net_throughput_mbps'] for w in aligned[100:300]])

print(f"Original throughput: {orig_tp:.2f} Mbps")
print(f"Aligned throughput: {alig_tp:.2f} Mbps")
print(f"Difference: {abs(orig_tp - alig_tp):.2f} Mbps")

if abs(orig_tp - alig_tp) < 50:
    print("✅ GOOD MATCH!")
else:
    print("❌ Still different, adjust parameters")
EOF
```

---

### Step 4: Validate with Model

Once data matches, test with the existing model:

```bash
# 1. Export aligned data
make exporter-run EXP_ID=aligned-test

# 2. Wait for GCN prediction
sleep 30

# 3. Check result
docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "
SELECT
    experiment_id,
    COUNT(*) as total,
    SUM(CASE WHEN prediction=1 THEN 1 ELSE 0 END) as detected_attack,
    ROUND(AVG(confidence)::numeric, 3) as avg_confidence
FROM gcn_predictions
WHERE experiment_id = 'aligned-test';
"

# Expected for normal with aligned config:
# detected_attack should be 0 or very low (< 20%)
```

---

## 🎯 Quick Wins: Parameters Most Likely to Help

### Priority 1: Simulation Time ⭐⭐⭐

**Current**: 30 seconds (300 windows)
**Original**: ~1400 seconds (14,000 windows)

**Why it matters**: Short simulations may have unstable throughput (warmup period)

**Fix**:
```bash
# Edit Makefile or scenario to extend simulation time
make ns3-run-scenario EXP_ID=long-test SCENARIO=normal SEED=42 SIMTIME=1400
```

**Expected Impact**: Should stabilize throughput and reduce variability

---

### Priority 2: Number of Stations ⭐⭐

**Hypothesis**: Original might use 2 stations, pipeline might use 3+

**Why it matters**: More stations = more contention = lower throughput per station

**Fix**: Check and align the `nWifi` parameter in scenarios

---

### Priority 3: Traffic Pattern ⭐

**Hypothesis**: Original might use lower data rate

**Fix**: Adjust packet size or data rate to achieve ~400 Mbps throughput

---

## 🔬 Diagnostic Commands

### Check Current Pipeline Configuration

```bash
# View current ns-3 scenario
cat sim/ns3/scratch/wifi7-mlo-Normal.cc | grep -E "simulationTime|nWifi|payloadSize|DataRate"
```

### Analyze Original Data Patterns

```bash
python3 << 'EOF'
import json
import numpy as np

# Load original data
with open('wifi7_gcn_attack_detection/Wifi7_Datasets/Normal/session_1_scenario_1_normal_run_1.json') as f:
    data = json.load(f)

# Skip warmup (first 100 windows)
data = data[100:]

# Calculate statistics
stats = {
    'throughput_mean': np.mean([w['net_throughput_mbps'] for w in data]),
    'throughput_std': np.std([w['net_throughput_mbps'] for w in data]),
    'active_flows_mean': np.mean([w['net_active_flows'] for w in data]),
    'delay_mean': np.mean([w['net_avg_delay_ms'] for w in data]),
    'backoff_mean': np.mean([w['avg_backoff_slots'] for w in data]),
    'channel_busy_mean': np.mean([w['channel_busy_ratio'] for w in data]),
}

print("=== ORIGINAL DATA CHARACTERISTICS ===")
for key, value in stats.items():
    print(f"{key}: {value:.2f}")

# These are the TARGET values your pipeline should match
EOF
```

---

## ⚠️ Challenges

### Challenge 1: Unknown Original Parameters

**Problem**: We don't have the original ns-3 .cc files

**Solution**:
- Reverse engineer from data analysis
- Try to contact original data source
- Run parameter sweep to find best match

### Challenge 2: Multiple Scenarios

**Problem**: Original dataset has multiple scenarios (session_1, session_2, etc.)

**Solution**:
- Focus on matching the most common scenario first
- Check if different sessions use different parameters

### Challenge 3: Attack Scenarios

**Problem**: Need to align both normal AND attack scenarios

**Solution**:
- Start with normal scenario alignment
- Then adjust attack scenarios (bias parameter should be main difference)

---

## ✅ Recommended Approach

### Option A: Configuration Alignment (FASTER) ⭐ RECOMMENDED

**Timeline**: 1-2 days

**Steps**:
1. Analyze original data to infer parameters (2-4 hours)
2. Modify pipeline ns-3 scenarios (2-3 hours)
3. Run test simulations (1-2 hours)
4. Iterate until data matches (4-8 hours)
5. Validate with model (1 hour)

**Pros**:
- Reuse existing trained model
- Faster than retraining
- Once aligned, always works

**Cons**:
- May not perfectly match (unknown original params)
- Requires ns-3 expertise
- Trial and error process

---

### Option B: Hybrid Approach (SAFEST)

**Timeline**: 2-3 days

**Steps**:
1. Try configuration alignment first (1 day)
2. If throughput difference < 50 Mbps: USE EXISTING MODEL ✅
3. If throughput difference > 50 Mbps: RETRAIN with pipeline data

**Pros**:
- Best of both worlds
- Fallback option if alignment fails
- Learn optimal parameters either way

---

## 🎯 Next Steps

### Immediate Actions

1. **Analyze Original Data** (30 minutes)
   ```bash
   python3 scripts/analyze_original_data.py
   ```

2. **Check Current Pipeline Config** (15 minutes)
   ```bash
   cat sim/ns3/scratch/wifi7-mlo-Normal.cc | grep -A5 -B5 "simulationTime"
   ```

3. **Try Extended Simulation** (1 hour)
   ```bash
   # Extend simulation time to match original
   make ns3-run-scenario EXP_ID=extended-test SCENARIO=normal SEED=42 SIMTIME=1400
   ```

4. **Compare Results** (15 minutes)
   ```bash
   python3 scripts/compare_data_distributions.py
   ```

---

## 📝 Decision Matrix

| Throughput Difference | Recommendation |
|-----------------------|----------------|
| < 20 Mbps | ✅ Use existing model as-is |
| 20-50 Mbps | ⚠️ Try configuration alignment |
| 50-100 Mbps | ⚠️ Try alignment, but consider retraining |
| > 100 Mbps | ❌ Retrain with pipeline data |

**Current Difference**: 97 Mbps → **Try alignment, fallback to retrain**

---

## 🎓 Summary

**Your Question**: Can we align configurations instead of retraining?

**Answer**: YES! This is a great approach and should be tried first.

**Why it's better**:
- Saves 1-2 days of retraining time
- Reuses proven model (99.4% F1)
- Once aligned, no future retraining needed

**How to do it**:
1. Analyze original data to find target statistics
2. Modify pipeline ns-3 scenarios to match
3. Key parameter: Simulation time (30s → 1400s)
4. Test until throughput matches (~400 Mbps)
5. Validate with existing model

**Success Criteria**:
- Throughput within 50 Mbps of original
- Throughput std within 2x of original
- Normal traffic shows < 20% false positive rate

**If alignment fails**: Fall back to retraining approach

---

**Created**: 2026-02-12
**Recommendation**: Try configuration alignment first, it's worth the effort!
**Expected Time**: 1-2 days vs 1-2 days for retraining, but alignment is less compute-intensive
