# Configuration Alignment Implementation Guide

**Date**: 2026-02-12
**Goal**: Align pipeline ns-3 configuration to match original GCN training data
**Expected Result**: Reuse model v1.0.0 without retraining

---

## 🎯 Configuration Differences Identified

### Critical Findings

| Parameter | Original (Target) | Current Pipeline | Impact |
|-----------|------------------|------------------|--------|
| **Simulation Time** | 1400s (14,000 windows) | **2.0s (20 windows)** | ❌ CRITICAL |
| **Throughput Mean** | 412 Mbps | 509 Mbps | ❌ 24% higher |
| **Throughput Std** | 25 Mbps | 97 Mbps | ❌ 3.8x more variable |
| **Active Flows** | 6 | 12 (4-node mesh) | ❌ Double |
| **Data Rate** | ~50 Mbps/flow | **800 Mbps** | ❌ 16x higher |
| **Topology** | 1 AP + 2 STAs (likely) | 2 APs + 2 STAs | ❌ Wrong |
| **Backoff Mean** | 9.96 slots | 10.55 slots | ✅ Close |
| **Channel Busy** | 0.88 (88%) | Unknown | ⚠️ Check |

---

## 📋 Implementation Steps

### Step 1: Fix Simulation Time (CRITICAL)

**File**: `sim/ns3/scenario/run_mlo_scenario.sh`

**Current** (line 26):
```bash
SIM_TIME="${5:-2.0}"
```

**Change to**:
```bash
SIM_TIME="${5:-1400.0}"
```

**Rationale**: Original training data has 14,000 windows × 0.1s = 1400 seconds

---

### Step 2: Adjust Network Topology

**File**: `sim/ns3/scratch/wifi7-mlo-Normal.cc`

**Current** (line 1055):
```cpp
uint32_t nSta = 2, nAp = 2, minCw = 15;
```

**Change to**:
```cpp
uint32_t nSta = 2, nAp = 1, minCw = 15;
```

**Rationale**:
- 1 AP + 2 STAs = 3 nodes
- Full mesh traffic = 6 flows (2→1, 1→2, 2→0, 0→2, 1→0, 0→1)
- Matches original's 6 active flows

---

### Step 3: Reduce Data Rate

**File**: `sim/ns3/scratch/wifi7-mlo-Normal.cc`

**Current** (line 1112):
```cpp
onoff.SetAttribute("DataRate", DataRateValue(DataRate("800Mbps")));
```

**Change to**:
```cpp
onoff.SetAttribute("DataRate", DataRateValue(DataRate("50Mbps")));
```

**Rationale**:
- 6 flows × ~69 Mbps/flow = 414 Mbps total (matches original 412 Mbps)
- Reduced from 800 Mbps to allow realistic WiFi 7 throughput

---

### Step 4: (Optional) Lower MCS for Stability

**File**: `sim/ns3/scratch/wifi7-mlo-Normal.cc`

**Current** (line 1084):
```cpp
wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager", "DataMode", StringValue("HeMcs11"));
```

**Consider changing to**:
```cpp
wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager", "DataMode", StringValue("HeMcs7"));
```

**Rationale**:
- HeMcs11 is very high modulation (requires excellent signal)
- HeMcs7 is more stable, might reduce throughput variability
- Original has very stable throughput (std = 25 Mbps)
- **Try this only if Step 1-3 don't achieve stable throughput**

---

## 🔧 Implementation Commands

### Option A: Manual Edit

```bash
cd /home/cobrakali/github/ndt-wifi7-mlo-security

# 1. Fix simulation time
nano sim/ns3/scenario/run_mlo_scenario.sh
# Change line 26: SIM_TIME="${5:-2.0}" → SIM_TIME="${5:-1400.0}"

# 2. Fix topology
nano sim/ns3/scratch/wifi7-mlo-Normal.cc
# Change line 1055: uint32_t nSta = 2, nAp = 2 → nAp = 1

# 3. Fix data rate
# Still in wifi7-mlo-Normal.cc
# Change line 1112: DataRate("800Mbps") → DataRate("50Mbps")
```

### Option B: Automated via sed

```bash
cd /home/cobrakali/github/ndt-wifi7-mlo-security

# 1. Fix simulation time (2.0 → 1400.0)
sed -i 's/SIM_TIME="${5:-2\.0}"/SIM_TIME="${5:-1400.0}"/g' \
    sim/ns3/scenario/run_mlo_scenario.sh

# 2. Fix topology (nAp = 2 → nAp = 1)
sed -i 's/uint32_t nSta = 2, nAp = 2/uint32_t nSta = 2, nAp = 1/g' \
    sim/ns3/scratch/wifi7-mlo-Normal.cc

# 3. Fix data rate (800Mbps → 50Mbps)
sed -i 's/DataRate("800Mbps")/DataRate("50Mbps")/g' \
    sim/ns3/scratch/wifi7-mlo-Normal.cc
```

---

## 🧪 Testing the Alignment

### Test 1: Run Aligned Normal Scenario

```bash
# Rebuild ns-3 with changes
make ns3-build

# Run aligned normal scenario
make ns3-run-scenario \
    EXP_ID=aligned-normal-test-42 \
    SCENARIO=normal \
    SEED=42

# This will run for 1400 seconds (~23 minutes)
# You'll see progress in logs
```

### Test 2: Compare Statistics

```bash
python3 << 'EOF'
import json
import numpy as np

# Load original training data
with open('/home/cobrakali/github/wifi7_gcn_attack_detection/Wifi7_Datasets/Normal/session_1_scenario_1_normal_run_1.json') as f:
    original = json.load(f)

# Load aligned test data
with open('sim/ns3/artifacts/aligned-normal-test-42/mlo_output.json') as f:
    aligned = json.load(f)

# Skip warmup (first 100 windows)
orig_data = original[100:1000]
algn_data = aligned[100:1000] if len(aligned) > 1000 else aligned[100:]

# Calculate statistics
orig_stats = {
    'throughput_mean': np.mean([w['net_throughput_mbps'] for w in orig_data]),
    'throughput_std': np.std([w['net_throughput_mbps'] for w in orig_data]),
    'active_flows': np.mean([w['net_active_flows'] for w in orig_data]),
    'backoff_mean': np.mean([w['avg_backoff_slots'] for w in orig_data]),
    'delay_mean': np.mean([w['net_avg_delay_ms'] for w in orig_data]),
}

algn_stats = {
    'throughput_mean': np.mean([w['net_throughput_mbps'] for w in algn_data]),
    'throughput_std': np.std([w['net_throughput_mbps'] for w in algn_data]),
    'active_flows': np.mean([w['net_active_flows'] for w in algn_data]),
    'backoff_mean': np.mean([w['avg_backoff_slots'] for w in algn_data]),
    'delay_mean': np.mean([w['net_avg_delay_ms'] for w in algn_data]),
}

print("=== CONFIGURATION ALIGNMENT RESULTS ===\n")
print(f"{'Metric':<20} {'Original':<15} {'Aligned':<15} {'Diff':>10}")
print("-" * 65)

for key in orig_stats:
    orig_val = orig_stats[key]
    algn_val = algn_stats[key]
    diff = algn_val - orig_val
    diff_pct = (diff / orig_val * 100) if orig_val != 0 else 0

    print(f"{key:<20} {orig_val:>14.2f} {algn_val:>14.2f} {diff_pct:>9.1f}%")

print("\n=== DECISION ===")
tp_diff = abs(algn_stats['throughput_mean'] - orig_stats['throughput_mean'])
if tp_diff < 20:
    print("✅ EXCELLENT MATCH! Use existing model v1.0.0")
elif tp_diff < 50:
    print("✅ GOOD MATCH! Use existing model v1.0.0")
elif tp_diff < 100:
    print("⚠️  FAIR MATCH. Try model v1.0.0, monitor false positives")
else:
    print("❌ POOR MATCH. Consider retraining with pipeline data")

print(f"\nThroughput difference: {tp_diff:.2f} Mbps")
EOF
```

### Test 3: Validate with GCN Model

```bash
# Export aligned data to Kafka
make exporter-run EXP_ID=aligned-normal-test-42

# Wait for GCN predictions
sleep 60

# Check false positive rate
docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "
SELECT
    experiment_id,
    COUNT(*) as total_segments,
    SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) as detected_attacks,
    ROUND(SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 1) as false_positive_pct,
    ROUND(AVG(confidence)::numeric, 3) as avg_confidence
FROM gcn_predictions
WHERE experiment_id = 'aligned-normal-test-42'
GROUP BY experiment_id;
"

# Expected result:
# false_positive_pct should be < 20% (ideally < 10%)
# If 100%, alignment failed - consider retraining
```

---

## 📊 Success Criteria

| Metric | Target | Acceptable Range | Action if Outside |
|--------|--------|------------------|-------------------|
| Throughput Mean | 412 Mbps | 392-432 Mbps (±5%) | Adjust data rate |
| Throughput Std | 25 Mbps | 15-35 Mbps | Lower MCS or increase sim time |
| Active Flows | 6 | Exactly 6 | Check topology (should be 1 AP + 2 STAs) |
| Backoff Mean | 9.96 slots | 8-12 slots | Already good, no action needed |
| Delay Mean | 10.66 ms | 5-20 ms | Adjust traffic load if needed |
| False Positive Rate | < 10% | < 20% | If >20%, further tuning needed |

---

## ⏱️ Timeline Estimate

| Task | Duration | Notes |
|------|----------|-------|
| Make configuration changes | 15 min | Simple sed commands |
| Rebuild ns-3 container | 5 min | Cached layers |
| Run aligned simulation | 25 min | 1400s simulation |
| Compare statistics | 5 min | Python script |
| Export to Kafka + GCN test | 10 min | Full pipeline test |
| **Total** | **~60 minutes** | Much faster than 1-2 days of retraining! |

---

## 🔄 Iteration Strategy

### If Alignment Succeeds (throughput diff < 50 Mbps)
1. ✅ Use existing model v1.0.0
2. ✅ Update attack scenarios (Positive.cc, Negative.cc) with same params
3. ✅ Run full test suite
4. ✅ Deploy to production

### If Alignment Fails (throughput diff > 100 Mbps)
1. ❌ Configuration alignment is not viable
2. 🔄 Proceed with retraining approach (WP8-MODEL-ANALYSIS-AND-RETRAINING-GUIDE.md)
3. 📝 Document why alignment failed

### If Partial Success (50-100 Mbps diff)
1. ⚠️  Try additional tuning:
   - Adjust MCS (HeMcs11 → HeMcs7 or HeMcs5)
   - Fine-tune data rate (40-60 Mbps range)
   - Check channel width (80 MHz → 40 MHz)
2. 🧪 Test with model v1.0.0, monitor false positive rate
3. 📊 If FP rate > 20%, fallback to retraining

---

## 🚀 Quick Start (Copy-Paste)

```bash
cd /home/cobrakali/github/ndt-wifi7-mlo-security

# Apply all configuration changes
sed -i 's/SIM_TIME="${5:-2\.0}"/SIM_TIME="${5:-1400.0}"/g' sim/ns3/scenario/run_mlo_scenario.sh
sed -i 's/uint32_t nSta = 2, nAp = 2/uint32_t nSta = 2, nAp = 1/g' sim/ns3/scratch/wifi7-mlo-Normal.cc
sed -i 's/DataRate("800Mbps")/DataRate("50Mbps")/g' sim/ns3/scratch/wifi7-mlo-Normal.cc

# Rebuild and test
make ns3-build
make ns3-run-scenario EXP_ID=aligned-normal-test-42 SCENARIO=normal SEED=42

# Compare results (after simulation completes in ~25 min)
python3 docs/scripts/compare_alignment.py

# Test with GCN
make exporter-run EXP_ID=aligned-normal-test-42
sleep 60
docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c \
  "SELECT experiment_id, COUNT(*) as total,
   SUM(CASE WHEN prediction=1 THEN 1 ELSE 0 END) as attacks,
   ROUND(AVG(confidence)::numeric, 3) as conf
   FROM gcn_predictions WHERE experiment_id='aligned-normal-test-42';"
```

---

## 📁 Files to Modify

1. ✅ `sim/ns3/scenario/run_mlo_scenario.sh` - Line 26 (simulation time)
2. ✅ `sim/ns3/scratch/wifi7-mlo-Normal.cc` - Line 1055 (topology)
3. ✅ `sim/ns3/scratch/wifi7-mlo-Normal.cc` - Line 1112 (data rate)
4. 🔄 `sim/ns3/scratch/wifi7-mlo-Positive.cc` - Same changes (after testing normal)
5. 🔄 `sim/ns3/scratch/wifi7-mlo-Negative.cc` - Same changes (after testing normal)

---

## ✅ Advantages Over Retraining

| Aspect | Configuration Alignment | Retraining |
|--------|-------------------------|------------|
| Time | ~1 hour | 1-2 days |
| Compute | Minimal (1 simulation) | High (100+ simulations + training) |
| Model Quality | Proven 99.4% F1 | Unknown (likely 85%+) |
| Maintenance | Easy (config files) | Complex (dataset management) |
| Reversibility | Instant (git revert) | Hard (need to regenerate data) |

---

## 🎯 Next Step

**READY TO EXECUTE!**

Run the Quick Start commands above and let's see if we can align the configurations!

Expected outcome:
- ✅ Throughput: 412 ± 50 Mbps
- ✅ Active flows: 6
- ✅ False positive rate: < 20%

If successful, we save 1-2 days and reuse the excellent 99.4% F1 model!

---

**Created**: 2026-02-12
**Status**: Ready for implementation
**Est. Time**: 60 minutes
**Decision Point**: Compare statistics after aligned simulation completes
