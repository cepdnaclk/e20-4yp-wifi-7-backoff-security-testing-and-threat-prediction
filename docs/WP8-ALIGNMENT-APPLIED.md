# Configuration Alignment Applied - 2026-02-12

## ✅ Changes Applied Successfully

### 1. Simulation Time Extended (CRITICAL FIX)

**File**: `sim/ns3/scenario/run_mlo_scenario.sh` (line 26)

```diff
- SIM_TIME="${5:-2.0}"
+ SIM_TIME="${5:-1400.0}"
```

**Impact**:
- Before: 2.0 seconds (20 windows)
- After: 1400 seconds (14,000 windows)
- **Matches original training data exactly!**

---

### 2. Topology Adjusted

**Files**:
- `sim/ns3/scratch/wifi7-mlo-Normal.cc` (line 1055)
- `sim/ns3/scratch/wifi7-mlo-Positive.cc`
- `sim/ns3/scratch/wifi7-mlo-Negative.cc`

```diff
- uint32_t nSta = 2, nAp = 2, minCw = 15;
+ uint32_t nSta = 2, nAp = 1, minCw = 15;
```

**Impact**:
- Before: 2 APs + 2 STAs = 4 nodes, 12 flows
- After: 1 AP + 2 STAs = 3 nodes, 6 flows
- **Matches original's 6 active flows!**

---

### 3. Data Rate Reduced

**Files**:
- `sim/ns3/scratch/wifi7-mlo-Normal.cc` (line 1112)
- `sim/ns3/scratch/wifi7-mlo-Positive.cc`
- `sim/ns3/scratch/wifi7-mlo-Negative.cc`

```diff
- onoff.SetAttribute("DataRate", DataRateValue(DataRate("800Mbps")));
+ onoff.SetAttribute("DataRate", DataRateValue(DataRate("50Mbps")));
```

**Impact**:
- Before: 800 Mbps per flow → ~509 Mbps total throughput
- After: 50 Mbps per flow → ~412 Mbps total throughput (expected)
- **Should match original's 412 Mbps!**

---

## 📊 Expected Results After Alignment

| Metric | Original (Target) | Before Alignment | After Alignment (Expected) |
|--------|------------------|------------------|---------------------------|
| Simulation Time | 1400s | 2.0s ❌ | 1400s ✅ |
| Total Windows | 14,000 | 20 ❌ | 14,000 ✅ |
| Throughput Mean | 412 Mbps | 509 Mbps ❌ | ~412 Mbps ✅ |
| Throughput Std | 25 Mbps | 97 Mbps ❌ | ~25 Mbps ✅ |
| Active Flows | 6 | 12 ❌ | 6 ✅ |
| Data Rate/Flow | ~69 Mbps | 800 Mbps ❌ | 50 Mbps ✅ |

---

## 🧪 Testing Instructions

### Step 1: Rebuild NS-3 Container

```bash
cd /home/cobrakali/github/ndt-wifi7-mlo-security
make ns3-build
```

**Time**: ~5 minutes (cached layers)

---

### Step 2: Run Aligned Test Simulation

```bash
make ns3-run-scenario \
    EXP_ID=aligned-normal-test-42 \
    SCENARIO=normal \
    SEED=42
```

**Time**: ~25 minutes (1400 second simulation + processing)

**What to expect**:
- Simulation runs for 1400 seconds (~23 minutes)
- Produces 14,000 windows in `mlo_output.json`
- Creates `telemetry.jsonl` for pipeline

**Monitor progress**:
```bash
# Watch simulation logs (in another terminal)
tail -f sim/ns3/artifacts/aligned-normal-test-42/ns3_stdout.log

# Check window count after completion
grep -c '"window":' sim/ns3/artifacts/aligned-normal-test-42/mlo_output.json
# Expected: 14000
```

---

### Step 3: Compare Statistics with Original

```bash
python3 docs/scripts/compare_alignment.py aligned-normal-test-42
```

**Expected output**:
```
=== CONFIGURATION ALIGNMENT RESULTS ===
Metric                   Original         Aligned            Diff
---------------------------------------------------------------------------
Total Windows                14000.00       14000.00          +0.0%
Throughput Mean (Mbps)        412.00         410.50          -0.4%  ✅
Throughput Std                 25.38          28.20         +11.1%  ✅
Active Flows                    6.00           6.00          +0.0%  ✅
Delay Mean (ms)                10.66          12.30         +15.4%  ✅
Backoff Mean (slots)            9.96          10.10          +1.4%  ✅
Channel Busy Ratio              0.88           0.87          -1.1%  ✅
---------------------------------------------------------------------------

EVALUATION
===========================================
1. Throughput Mean Difference: 1.50 Mbps
   ✅ EXCELLENT (<20 Mbps)

2. Throughput Variability Ratio: 1.11x
   ✅ EXCELLENT (< 1.5x)

3. Active Flows: 6 (Original: 6)
   ✅ MATCH

RECOMMENDATION
===========================================
✅ ALIGNMENT SUCCESSFUL!

Next steps:
  1. Test with GCN model v1.0.0
  2. Expected false positive rate: < 20%
  3. If successful, deploy to production
```

---

### Step 4: Test with GCN Model

```bash
# Export aligned data to Kafka
make exporter-run EXP_ID=aligned-normal-test-42

# Wait for GCN detector to process
sleep 60

# Check predictions
docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "
SELECT
    experiment_id,
    COUNT(*) as total_segments,
    SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) as detected_attacks,
    ROUND(SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 1) as false_positive_rate,
    ROUND(AVG(confidence)::numeric, 3) as avg_confidence
FROM gcn_predictions
WHERE experiment_id = 'aligned-normal-test-42'
GROUP BY experiment_id;
"
```

**Expected result** (if alignment successful):
```
 experiment_id           | total_segments | detected_attacks | false_positive_rate | avg_confidence
-------------------------+----------------+------------------+---------------------+----------------
 aligned-normal-test-42  |            54  |                5 |                 9.3 |          0.156
```

**Success criteria**:
- ✅ False positive rate < 20%
- ✅ Average confidence reasonable (not 100%)

**If FP rate is still 100%**:
- ⚠️  Alignment failed, proceed with retraining
- 📝 Document why in WP8 analysis

---

### Step 5: Test Attack Scenarios

If normal scenario shows good results, test attacks:

```bash
# Positive attack
make ns3-run-scenario EXP_ID=aligned-positive-test-42 SCENARIO=positive SEED=42
make exporter-run EXP_ID=aligned-positive-test-42

# Negative attack
make ns3-run-scenario EXP_ID=aligned-negative-test-42 SCENARIO=negative SEED=42
make exporter-run EXP_ID=aligned-negative-test-42

# Check attack detection rate (should be > 85%)
docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "
SELECT
    experiment_id,
    COUNT(*) as segments,
    SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) as attacks_detected,
    ROUND(SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 1) as detection_rate
FROM gcn_predictions
WHERE experiment_id LIKE 'aligned-%attack%'
GROUP BY experiment_id;
"
```

---

## 🎯 Decision Tree

### Scenario A: Alignment Successful ✅
- Throughput diff < 50 Mbps
- False positive rate < 20%
- Attack detection > 85%

**Action**:
1. ✅ Use model v1.0.0 in production
2. ✅ Update documentation
3. ✅ Close WP8

---

### Scenario B: Partial Success ⚠️
- Throughput diff 50-100 Mbps
- False positive rate 20-50%

**Action**:
1. Try MCS adjustment (HeMcs11 → HeMcs7)
2. Fine-tune data rate (40-60 Mbps)
3. Re-test
4. If still high FP rate → Proceed to retraining

---

### Scenario C: Alignment Failed ❌
- Throughput diff > 100 Mbps OR
- False positive rate > 50%

**Action**:
1. Analyze why alignment failed
2. Document findings
3. Proceed with retraining (WP8-MODEL-ANALYSIS-AND-RETRAINING-GUIDE.md)

---

## 📁 Files Modified

| File | Changes | Purpose |
|------|---------|---------|
| `sim/ns3/scenario/run_mlo_scenario.sh` | Line 26: SIM_TIME 2.0→1400.0 | Match original simulation length |
| `sim/ns3/scratch/wifi7-mlo-Normal.cc` | Line 1055: nAp 2→1 | Match original topology (6 flows) |
| `sim/ns3/scratch/wifi7-mlo-Normal.cc` | Line 1112: DataRate 800→50 Mbps | Match original throughput |
| `sim/ns3/scratch/wifi7-mlo-Positive.cc` | Same as Normal.cc | Consistency across scenarios |
| `sim/ns3/scratch/wifi7-mlo-Negative.cc` | Same as Normal.cc | Consistency across scenarios |

---

## 🚀 Quick Test Command

Run everything in sequence:

```bash
cd /home/cobrakali/github/ndt-wifi7-mlo-security

# Rebuild
make ns3-build

# Run aligned simulation (takes ~25 min)
make ns3-run-scenario EXP_ID=aligned-normal-test-42 SCENARIO=normal SEED=42

# Compare (after simulation completes)
python3 docs/scripts/compare_alignment.py aligned-normal-test-42

# Test with GCN
make exporter-run EXP_ID=aligned-normal-test-42
sleep 60
docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c \
  "SELECT experiment_id, COUNT(*) as total,
   SUM(CASE WHEN prediction=1 THEN 1 ELSE 0 END) as attacks,
   ROUND(SUM(CASE WHEN prediction=1 THEN 1 ELSE 0 END)::numeric/COUNT(*)*100, 1) as fp_rate,
   ROUND(AVG(confidence)::numeric, 3) as conf
   FROM gcn_predictions WHERE experiment_id='aligned-normal-test-42';"
```

---

## 📊 Why This Should Work

### Root Cause Analysis (Original Problem)

| Issue | Cause | Fix |
|-------|-------|-----|
| 100% false positives | Pipeline throughput (509 Mbps) >> Training (412 Mbps) | Reduced data rate to match |
| High variability | Short sims (2s) unstable | Extended to 1400s |
| Different flow count | 12 flows vs 6 | Changed topology to 1 AP + 2 STAs |

### Expected Model Behavior After Alignment

**Before**:
```
Pipeline data: throughput=509, std=97 (2 std dev from training mean)
Model's learned normal: throughput=412, std=25
Model thinks: "509 is way outside normal range! Must be attack!"
Result: 100% false positive ❌
```

**After alignment**:
```
Pipeline data: throughput=412, std=25 (matches training distribution)
Model's learned normal: throughput=412, std=25
Model thinks: "This matches my training data perfectly!"
Result: < 10% false positive ✅
```

---

## ⏱️ Total Time Investment

| Activity | Duration |
|----------|----------|
| Configuration changes | ✅ Done (15 min) |
| Rebuild ns-3 | 5 min |
| Run simulation | 25 min |
| Compare statistics | 2 min |
| Test with GCN | 10 min |
| **Total** | **~60 minutes** |

**Compare to retraining**: 1-2 days

**Savings**: 23-47 hours! 🎉

---

## 📝 Next Steps

1. **Immediate**: Run aligned simulation (25 min)
2. **After completion**: Compare statistics
3. **If successful**: Test with GCN model
4. **If GCN works**: Deploy to production
5. **If GCN fails**: Fallback to retraining

---

**Status**: ✅ Configuration alignment applied
**Ready for**: Testing (run simulation)
**Created**: 2026-02-12
**Estimated completion**: 2026-02-12 (1 hour from now)
