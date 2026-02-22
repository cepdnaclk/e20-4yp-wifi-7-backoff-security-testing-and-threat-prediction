# WP8: GCN Model Data Mismatch - Complete Summary

**Date**: 2026-02-12
**Status**: Configuration alignment applied ✅
**Next**: Test aligned simulation

---

## 🎯 Problem Identified

The pipeline was showing **100% false positive rate** on normal traffic due to data distribution mismatch between:
- **Original GCN training data**: Generated with specific ns-3 configuration
- **Pipeline data**: Generated with different ns-3 configuration

### Key Differences Found

| Parameter | Original Training | Current Pipeline | Difference |
|-----------|------------------|------------------|------------|
| **Simulation Time** | 1400s (14,000 windows) | 2.0s (20 windows) | 700x shorter ❌ |
| **Throughput** | 412 Mbps (stable ±25) | 509 Mbps (variable ±97) | +97 Mbps ❌ |
| **Active Flows** | 6 flows | 12 flows | 2x more ❌ |
| **Topology** | 1 AP + 2 STAs | 2 APs + 2 STAs | Different ❌ |
| **Data Rate** | ~50-69 Mbps/flow | 800 Mbps | 16x higher ❌ |

**Root Cause**: The model learned "normal = 412 Mbps ±25" but pipeline sends "509 Mbps ±97", which the model classifies as abnormal (attack).

---

## ✅ Solution Applied: Configuration Alignment

Instead of retraining the model (1-2 days), we aligned the pipeline's ns-3 configuration to match the original training data.

### Changes Made

#### 1. Simulation Time (CRITICAL)
```bash
File: sim/ns3/scenario/run_mlo_scenario.sh
Line 26: SIM_TIME="${5:-2.0}" → SIM_TIME="${5:-1400.0}"
```
- **Before**: 2 seconds (20 windows)
- **After**: 1400 seconds (14,000 windows)
- **Matches**: Original training data exactly ✅

#### 2. Network Topology
```cpp
Files: wifi7-mlo-Normal.cc, wifi7-mlo-Positive.cc, wifi7-mlo-Negative.cc
Line 1055: uint32_t nSta = 2, nAp = 2 → nAp = 1
```
- **Before**: 2 APs + 2 STAs = 4 nodes → 12 flows
- **After**: 1 AP + 2 STAs = 3 nodes → 6 flows
- **Matches**: Original's 6 active flows ✅

#### 3. Data Rate
```cpp
Files: wifi7-mlo-Normal.cc, wifi7-mlo-Positive.cc, wifi7-mlo-Negative.cc
Line 1112: DataRate("800Mbps") → DataRate("50Mbps")
```
- **Before**: 800 Mbps → ~509 Mbps total throughput
- **After**: 50 Mbps → ~412 Mbps total throughput (expected)
- **Matches**: Original's 412 Mbps ✅

---

## 📊 Expected Outcome

After alignment, pipeline data should match training data:

| Metric | Target (Original) | Expected After Alignment |
|--------|------------------|-------------------------|
| Total Windows | 14,000 | 14,000 ✅ |
| Throughput Mean | 412 Mbps | ~412 Mbps ✅ |
| Throughput Std | 25 Mbps | ~25 Mbps ✅ |
| Active Flows | 6 | 6 ✅ |
| False Positive Rate | < 10% (original model) | < 20% ✅ |

---

## 🧪 Testing Plan

### Phase 1: Run Aligned Simulation (~25 min)

```bash
cd /home/cobrakali/github/ndt-wifi7-mlo-security
make ns3-build
make ns3-run-scenario EXP_ID=aligned-normal-test-42 SCENARIO=normal SEED=42
```

**What happens**:
- Simulation runs for 1400 seconds (~23 minutes)
- Generates 14,000 windows of data
- Creates `sim/ns3/artifacts/aligned-normal-test-42/mlo_output.json`

### Phase 2: Compare Statistics (~2 min)

```bash
python3 docs/scripts/compare_alignment.py aligned-normal-test-42
```

**Success criteria**:
- ✅ Throughput difference < 50 Mbps
- ✅ Throughput variability ratio < 2.5x
- ✅ Active flows = 6

### Phase 3: Test with GCN Model (~10 min)

```bash
make exporter-run EXP_ID=aligned-normal-test-42
sleep 60

docker exec clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "
SELECT
    COUNT(*) as total_segments,
    SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) as detected_attacks,
    ROUND(SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 1) as false_positive_rate
FROM gcn_predictions
WHERE experiment_id = 'aligned-normal-test-42';
"
```

**Success criteria**:
- ✅ False positive rate < 20% (ideally < 10%)

### Phase 4: Test Attack Scenarios (if Phase 3 succeeds)

```bash
# Positive attack
make ns3-run-scenario EXP_ID=aligned-positive-test-42 SCENARIO=positive SEED=42
make exporter-run EXP_ID=aligned-positive-test-42

# Negative attack
make ns3-run-scenario EXP_ID=aligned-negative-test-42 SCENARIO=negative SEED=42
make exporter-run EXP_ID=aligned-negative-test-42

# Check detection rate (should be > 85%)
```

---

## 🎯 Decision Matrix

### Outcome A: Alignment Successful ✅
- Throughput diff < 50 Mbps
- False positive rate < 20%
- Attack detection > 85%

**Action**:
1. ✅ **USE MODEL v1.0.0** - No retraining needed!
2. ✅ Update documentation (mark WP8 complete)
3. ✅ Deploy to production

**Benefits**:
- Saved 1-2 days of retraining time
- Keep proven 99.4% F1 model
- Production-ready immediately

---

### Outcome B: Partial Success ⚠️
- Throughput diff 50-100 Mbps
- False positive rate 20-50%

**Action**:
1. Fine-tune configuration:
   - Try lower MCS (HeMcs11 → HeMcs7)
   - Adjust data rate (40-60 Mbps range)
2. Re-test with model
3. If FP rate still > 20% → Proceed to retraining

---

### Outcome C: Alignment Failed ❌
- Throughput diff > 100 Mbps OR
- False positive rate > 50%

**Action**:
1. Analyze why alignment failed
2. **RETRAIN MODEL** with pipeline data (WP8-MODEL-ANALYSIS-AND-RETRAINING-GUIDE.md)
3. Timeline: 1-2 days for retraining

---

## 📁 Documentation Created

| File | Purpose |
|------|---------|
| `WP8-NS3-CONFIGURATION-ALIGNMENT.md` | Initial alignment analysis |
| `WP8-CONFIGURATION-ALIGNMENT-IMPLEMENTATION.md` | Detailed implementation guide |
| `WP8-ALIGNMENT-APPLIED.md` | What was changed and testing instructions |
| `WP8-SUMMARY.md` | This file - complete overview |
| `docs/scripts/compare_alignment.py` | Automated comparison script |

**Supporting docs** (from earlier WP8 analysis):
- `WP8-MODEL-ANALYSIS-AND-RETRAINING-GUIDE.md` - Retraining procedure (if needed)
- `WP8-ANSWER-TO-USER-QUESTIONS.md` - Why data is different
- `WP8-WHY-DATA-IS-DIFFERENT.md` - ML principles explained

---

## ⏱️ Time Comparison

| Approach | Time Investment | Model Quality | Risk |
|----------|----------------|---------------|------|
| **Configuration Alignment** ⭐ | **~1 hour** | Proven 99.4% F1 | Low (reversible) |
| Retraining | 1-2 days | Expected 85%+ F1 | Medium (new model) |

**Chosen**: Configuration Alignment (try first, fallback to retraining if fails)

---

## 🚀 Next Steps (READY TO EXECUTE)

### Immediate (Now):

```bash
# 1. Rebuild ns-3 with aligned configuration
make ns3-build

# 2. Run aligned simulation (takes ~25 min)
make ns3-run-scenario EXP_ID=aligned-normal-test-42 SCENARIO=normal SEED=42
```

### After simulation completes:

```bash
# 3. Compare statistics
python3 docs/scripts/compare_alignment.py aligned-normal-test-42

# 4. Test with GCN model
make exporter-run EXP_ID=aligned-normal-test-42
sleep 60
# Check false positive rate in database
```

### Based on results:
- ✅ **If successful**: Test attack scenarios, deploy to production
- ⚠️  **If partial**: Fine-tune configuration, re-test
- ❌ **If failed**: Proceed with retraining approach

---

## 💡 Key Insights

1. **Same format ≠ Same distribution**: Both datasets have identical JSON structure but different numerical values

2. **ML models learn distributions, not concepts**: The model learned "normal = 412 Mbps" not "backoff manipulation detection"

3. **Configuration alignment is faster than retraining**: 1 hour vs 1-2 days

4. **Your insight was correct**: Asking "can we align configurations instead of retraining?" was the right question!

---

## 🎓 What We Learned

### Problem Diagnosis
- ✅ Model v1.0.0 is identical to original (verified file hashes)
- ✅ Model is excellent (99.4% F1 on original data)
- ✅ Issue is data distribution mismatch, not model quality

### Root Cause
- Pipeline simulation time was 700x too short (2s vs 1400s)
- Pipeline throughput 24% higher (509 vs 412 Mbps)
- Pipeline had 2x more flows (12 vs 6)

### Solution Strategy
- Try configuration alignment first (faster, less risky)
- Fallback to retraining if alignment fails
- Both approaches are valid, alignment is more efficient

---

## ✅ Current Status

- 🎯 **Problem**: Fully understood and documented
- ⚙️ **Solution**: Configuration alignment applied
- 🧪 **Testing**: Ready to execute
- 📊 **Timeline**: ~1 hour to validate
- 🚀 **Next**: Run aligned simulation and compare results

---

**Created**: 2026-02-12
**Your Question**: "Can we make the pipeline use the same ns-3 configuration as the original GCN training data?"
**Answer**: YES! And we just did it. 🎉

**Ready for testing!**
