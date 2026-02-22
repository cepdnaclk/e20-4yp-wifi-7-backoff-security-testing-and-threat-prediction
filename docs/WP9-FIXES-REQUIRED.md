# WP9 GCN Retraining Plan - Required Fixes

**Date**: 2026-02-13
**Status**: 7 critical fixes required before implementation

---

## Quick Fix List

Apply these changes to `docs/WP9-GCN-MODEL-RETRAINING-PLAN.md`:

### Fix 1: Line 314-315 (Section 1.5)

**Find**:
```
Each: 15 positive + 15 negative = 30 scenarios per bias level
Total: 8 × 30 = 240 attack scenarios
```

**Replace with**:
```
Each: 8 positive + 8 negative = 16 scenarios per bias level
Total: 8 × 16 = 128 attack scenarios
```

---

### Fix 2: Lines 380-396 (Section 2.1 - Directory Structure)

**Find** (16 occurrences):
```
# 15 files
```

**Replace with**:
```
# 8 files
```

**Affected lines**:
- 380: `bias_0050/         # 15 files` → `bias_0050/         # 8 files`
- 381: `bias_0100/         # 15 files` → `bias_0100/         # 8 files`
- 382: `bias_0250/         # 15 files` → `bias_0250/         # 8 files`
- 383: `bias_0500/         # 15 files` → `bias_0500/         # 8 files`
- 384: `bias_1000/         # 15 files` → `bias_1000/         # 8 files`
- 385: `bias_2500/         # 15 files` → `bias_2500/         # 8 files`
- 386: `bias_5000/         # 15 files` → `bias_5000/         # 8 files`
- 387: `bias_10000/        # 15 files` → `bias_10000/        # 8 files`
- 389: `bias_neg0050/      # 15 files` → `bias_neg0050/      # 8 files`
- 390: `bias_neg0100/      # 15 files` → `bias_neg0100/      # 8 files`
- 391: `bias_neg0250/      # 15 files` → `bias_neg0250/      # 8 files`
- 392: `bias_neg0500/      # 15 files` → `bias_neg0500/      # 8 files`
- 393: `bias_neg1000/      # 15 files` → `bias_neg1000/      # 8 files`
- 394: `bias_neg2500/      # 15 files` → `bias_neg2500/      # 8 files`
- 395: `bias_neg5000/      # 15 files` → `bias_neg5000/      # 8 files`
- 396: `bias_neg10000/     # 15 files` → `bias_neg10000/     # 8 files`

---

### Fix 3: Line 724 (Section 4.3 - Training Output)

**Find**:
```
Total segments: ~2304 (1152 normal, 1152 attack)  ✅ BALANCED
```

**Replace with**:
```
Total segments: ~8960 (4480 normal, 4480 attack)  ✅ BALANCED
```

---

### Fix 4: Line 1265 (Section 6 Step 1.3)

**Find**:
```
**Expected Duration**: ~24-48 hours (255 simulations × 15 min avg = 64 hours compute, parallelizable)
```

**Replace with**:
```
**Expected Duration**: ~24-48 hours (256 simulations × 15 min avg = 64 hours compute, parallelizable)
```

---

### Fix 5: Lines 1433, 1444-1446, 1457 (Phase 4 README Template)

**Find**:
```markdown
**Training Dataset**: data_v2 (300 pipeline-generated scenarios)

...

## Training Details

- **Dataset**: 255 scenarios (15 normal ~6%, 240 attack ~94%)
- **Train/Val/Test**: 178 / 39 / 38 files
- **Segments**: ~2295 total (256-window segments)

...

**15 scenarios per bias level per direction (positive/negative)**
```

**Replace with**:
```markdown
**Training Dataset**: data_v2 (256 pipeline-generated scenarios with BALANCED 50-50 distribution)

...

## Training Details

- **Dataset**: 256 scenarios (128 normal = 50%, 128 attack = 50%) ✅ BALANCED
- **Train/Val/Test**: 180 / 38 / 38 files
- **Segments**: ~8960 total (256-window segments, 4480 normal + 4480 attack)

...

**8 scenarios per bias level per direction (positive/negative)**
```

Also update the "Changes from v1.0.0" section (around line 1459):

**Find**:
```markdown
## Changes from v1.0.0

- **CRITICAL**: Trained on ALL 8 bias levels (50-10000) - v1.0.0 missed bias 50-500
- Trained on pipeline-generated data (not original GCN repo data)
- Matches original GCN distribution (~6% normal, ~94% attack)
- Network densities: 4 levels (light, moderate, dense, very dense)
- Matches feature distributions from ns-3 simulations
- Should detect subtle attacks (bias 50-500) AND obvious attacks (bias 1000+)
```

**Replace with**:
```markdown
## Changes from v1.0.0

- **CRITICAL CHANGE**: BALANCED 50-50 distribution (128 normal, 128 attack) vs original 6-94
  - **Why**: 2-3x lower false positive rate, better production usability
  - Expected FPR: 5-8% (vs 15-25% with 6-94 training)
  - Slightly lower recall: 90-94% (vs 95-99%) - acceptable trade-off
- Trained on ALL 8 bias levels (50-10000) for complete attack spectrum coverage
- Trained on pipeline-generated data matching actual deployment environment
- Network densities: 4 levels (light, moderate, dense, very dense)
- Production-ready: Users will trust the system (few false alarms)
```

---

### Fix 6: Line 1648 (Section 7.2)

**Find**:
```
- Training data: ~500 MB (300 JSON files)
```

**Replace with**:
```
- Training data: ~460 MB (256 JSON files)
```

---

### Fix 7: Line 1683 (Section 7.3)

**Find**:
```bash
    echo "Bias $bias: $pos_count positive, $neg_count negative (expected: 15 each)"
```

**Replace with**:
```bash
    echo "Bias $bias: $pos_count positive, $neg_count negative (expected: 8 each)"
```

---

## Optional Fix: Lines 1664-1669 (Parallelization Batch Breakdown)

**Current**:
```bash
# Batch 1: Normal (15 files)
# Batch 2-3: Positive bias 50, 100 (30 files)
# Batch 4-5: Positive bias 250, 500 (30 files)
# Batch 6-7: Positive bias 1000-10000 (60 files)
# Batch 8-9: Negative bias 50-500 (60 files)
# Batch 10: Negative bias 1000-10000 (60 files)
```

**Better balanced**:
```bash
# Batch 1: Normal light (40 files)
# Batch 2: Normal moderate (35 files)
# Batch 3: Normal dense (30 files)
# Batch 4: Normal very dense (23 files)
# Batch 5: Positive bias 50-250 (24 files: 8+8+8)
# Batch 6: Positive bias 500-2500 (24 files: 8+8+8)
# Batch 7: Positive bias 5000-10000 (16 files: 8+8)
# Batch 8: Negative bias 50-250 (24 files: 8+8+8)
# Batch 9: Negative bias 500-2500 (24 files: 8+8+8)
# Batch 10: Negative bias 5000-10000 (16 files: 8+8)
# Total: 256 files
```

---

## Verification After Fixes

Run these commands to verify all old values are gone:

```bash
# Should return ZERO results (or only in "Original GCN" comparison contexts)
grep -n "15 positive.*15 negative" docs/WP9-GCN-MODEL-RETRAINING-PLAN.md
grep -n "240 attack" docs/WP9-GCN-MODEL-RETRAINING-PLAN.md | grep -v "Original\|v1.0"
grep -n "255 scenarios" docs/WP9-GCN-MODEL-RETRAINING-PLAN.md
grep -n "300 JSON" docs/WP9-GCN-MODEL-RETRAINING-PLAN.md
grep -n "~2304\|2295" docs/WP9-GCN-MODEL-RETRAINING-PLAN.md

# Should return MULTIPLE results showing correct values
grep -n "8 positive.*8 negative\|8 pos.*8 neg" docs/WP9-GCN-MODEL-RETRAINING-PLAN.md
grep -n "128 attack\|128 normal" docs/WP9-GCN-MODEL-RETRAINING-PLAN.md
grep -n "256 scenarios\|256 files\|256 total" docs/WP9-GCN-MODEL-RETRAINING-PLAN.md
grep -n "~8960\|8960" docs/WP9-GCN-MODEL-RETRAINING-PLAN.md
grep -n "50-50\|50%" docs/WP9-GCN-MODEL-RETRAINING-PLAN.md | wc -l  # Should be many
```

---

## Implementation Checklist After Fixes

- [ ] All 7 fixes applied
- [ ] Verification commands show no old values
- [ ] Document re-read for final consistency check
- [ ] No contradictions between sections
- [ ] Ready to begin Phase 1: Data Generation

**End of Fixes**
