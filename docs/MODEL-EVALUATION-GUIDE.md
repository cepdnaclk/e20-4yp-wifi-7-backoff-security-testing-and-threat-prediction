# Model Evaluation Guide — GCN v3.0.0 vs v2.0.0

Comprehensive evaluation matrix for comparing GCN model versions on the NDT Wi-Fi 7 MLO Security platform.

---

## Seed Assignment Rule

> **For the same AP count, every scenario (normal / positive / negative) must use a different seed.**
> It is acceptable to reuse the same seeds across different AP counts.

**Why this matters:** NS-3 is fully deterministic — same seed + same scenario = identical simulation output
every time. Running `normal 1AP seed=42` twice produces exactly the same data, making it a wasted run.
By assigning different seeds to different scenarios at the same AP count, each experiment has genuinely
independent network conditions (different packet timings, backoff draws, channel events), which gives
the model a more realistic and diverse evaluation.

**Seed convention used throughout this document:**

| Scenario | Seed group A | Seed group B | Seed group C | Seed group D | Seed group E |
|----------|-------------|-------------|-------------|-------------|-------------|
| normal   | 10          | 20          | 30          | 40          | 50          |
| positive | 42          | 52          | 62          | 72          | 82          |
| negative | 99          | 109         | 119         | 129         | 139         |

- Within any seed group, each scenario has a unique seed → no duplicate data
- Across AP counts, reusing the same seed group is fine (different topology size = different simulation)

---

## Overview

The goal is to systematically measure detection accuracy across scenarios, AP counts, biases, seeds,
and segment lengths — for both GCN v3.0.0 (multi-AP, variable segment length) and GCN v2.0.0
(single-AP, fixed 256-window).

**Decision threshold:** p_attack > 0.5 → prediction = 1 (attack)

**Pass/Fail criteria:**
- Normal experiment: attack_rate < 10% → PASS
- Attack experiment: attack_rate > 90% → PASS

---

## Setup

### 1. Clear previous evaluation data

```bash
make db-reset-experiments
```

Or manually:
```bash
docker exec -it clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "
  TRUNCATE gcn_predictions;
  TRUNCATE metrics;
"
```

### 2. Use the date range filter

In Experiment View use **Last 2h / Last 6h / Last 24h** quick buttons to focus on your current session.
Click **All time** to see all historical data.

### 3. Sim time guidelines

| Segment Length | Min for ≥1 complete segment (1AP/2STA) | Recommended |
|---------------|----------------------------------------|-------------|
| 64w           | 60s                                    | 80s         |
| 128w          | 100s                                   | 120s        |
| 256w          | 180s                                   | 200s        |

> Note: the windowizer always flushes a partial segment at run end, so even a shorter sim (e.g. 80s)
> will produce 1 result for 256w. For multiple segments (better statistics), use the recommended time.

---

## Test Matrix

### Tier 1 — Core Accuracy (Required)

Minimum experiments to establish a baseline. Two seed groups per model to confirm consistency.

**Seed group A** (first independent run per scenario):

| # | Scenario | APs/STAs | Seed | Sim Time | Bias  | Seg Len | Models         | Expected |
|---|----------|----------|------|----------|-------|---------|----------------|----------|
| 1 | normal   | 1/2      |  10  | 80s      | —     | 256     | v3.0.0, v2.0.0 | PASS     |
| 2 | positive | 1/2      |  42  | 80s      | 5000  | 256     | v3.0.0, v2.0.0 | PASS     |
| 3 | negative | 1/2      |  99  | 80s      | 5000  | 256     | v3.0.0, v2.0.0 | PASS     |

**Seed group B** (second independent run — confirms results are not seed-specific):

| # | Scenario | APs/STAs | Seed | Sim Time | Bias  | Seg Len | Models         | Expected |
|---|----------|----------|------|----------|-------|---------|----------------|----------|
| 4 | normal   | 1/2      |  20  | 80s      | —     | 256     | v3.0.0, v2.0.0 | PASS     |
| 5 | positive | 1/2      |  52  | 80s      | 5000  | 256     | v3.0.0, v2.0.0 | PASS     |
| 6 | negative | 1/2      | 109  | 80s      | 5000  | 256     | v3.0.0, v2.0.0 | PASS     |

**Total: 12 experiments** (6 scenario runs × 2 models)

---

### Tier 2 — Multi-AP (v3.0.0 only)

GCN v2.0.0 is not designed for multi-AP. Same seed groups as Tier 1 are reused — this is acceptable
because AP count changes the topology, making the simulation genuinely different.

**2 APs / 4 STAs — Seed group A:**

| #  | Scenario | APs/STAs | Seed | Sim Time | Bias  | Seg Len | Model  | Expected |
|----|----------|----------|------|----------|-------|---------|--------|----------|
|  7 | normal   | 2/4      |  10  | 80s      | —     | 256     | v3.0.0 | PASS     |
|  8 | positive | 2/4      |  42  | 80s      | 5000  | 256     | v3.0.0 | PASS     |
|  9 | negative | 2/4      |  99  | 80s      | 5000  | 256     | v3.0.0 | PASS     |

**4 APs / 8 STAs — Seed group A:**

| #  | Scenario | APs/STAs | Seed | Sim Time | Bias  | Seg Len | Model  | Expected |
|----|----------|----------|------|----------|-------|---------|--------|----------|
| 10 | normal   | 4/8      |  10  | 80s      | —     | 256     | v3.0.0 | PASS     |
| 11 | positive | 4/8      |  42  | 80s      | 5000  | 256     | v3.0.0 | PASS     |
| 12 | negative | 4/8      |  99  | 80s      | 5000  | 256     | v3.0.0 | PASS     |

**Total: 6 experiments**

---

### Tier 3 — Segment Length Sensitivity (v3.0.0 only)

Each segment length uses its own seed group to ensure independent base conditions per scenario.

**seg=128 — Seed group A:**

| #  | Scenario | APs/STAs | Seed | Sim Time | Bias  | Seg Len | Model  | Expected |
|----|----------|----------|------|----------|-------|---------|--------|----------|
| 13 | normal   | 1/2      |  10  | 120s     | —     | 128     | v3.0.0 | PASS     |
| 14 | positive | 1/2      |  42  | 120s     | 5000  | 128     | v3.0.0 | PASS     |
| 15 | negative | 1/2      |  99  | 120s     | 5000  | 128     | v3.0.0 | PASS     |

**seg=64 — Seed group B:**

| #  | Scenario | APs/STAs | Seed | Sim Time | Bias  | Seg Len | Model  | Expected |
|----|----------|----------|------|----------|-------|---------|--------|----------|
| 16 | normal   | 1/2      |  20  | 80s      | —     | 64      | v3.0.0 | PASS     |
| 17 | positive | 1/2      |  52  | 80s      | 5000  | 64      | v3.0.0 | PASS     |
| 18 | negative | 1/2      | 109  | 80s      | 5000  | 64      | v3.0.0 | PASS     |

**Total: 6 experiments**

---

### Tier 4 — Bias Sensitivity

Find the minimum detectable bias level. Within each bias level, scenarios use different seeds.
Since we are varying bias (not seed), each bias level uses its own seed group to avoid correlation.

**Bias = 1000 — Seed group C:**

| #  | Scenario | APs/STAs | Seed | Sim Time | Bias | Seg Len | Models         | Expected |
|----|----------|----------|------|----------|------|---------|----------------|----------|
| 19 | positive | 1/2      |  62  | 80s      | 1000 | 256     | v3.0.0, v2.0.0 | ?        |
| 20 | negative | 1/2      | 119  | 80s      | 1000 | 256     | v3.0.0, v2.0.0 | ?        |

**Bias = 2000 — Seed group D:**

| #  | Scenario | APs/STAs | Seed | Sim Time | Bias | Seg Len | Models         | Expected |
|----|----------|----------|------|----------|------|---------|----------------|----------|
| 21 | positive | 1/2      |  72  | 80s      | 2000 | 256     | v3.0.0, v2.0.0 | ?        |
| 22 | negative | 1/2      | 129  | 80s      | 2000 | 256     | v3.0.0, v2.0.0 | ?        |

**Bias = 10000 — Seed group E:**

| #  | Scenario | APs/STAs | Seed | Sim Time | Bias  | Seg Len | Models         | Expected |
|----|----------|----------|------|----------|-------|---------|----------------|----------|
| 23 | positive | 1/2      |  82  | 80s      | 10000 | 256     | v3.0.0, v2.0.0 | PASS     |
| 24 | negative | 1/2      | 139  | 80s      | 10000 | 256     | v3.0.0, v2.0.0 | PASS     |

**Total: 12 experiments** — use results to determine the minimum bias the model reliably detects

---

### Tier 5 — Seed Generalisation

Run across 5 independent seed groups to verify results hold across diverse network conditions.
Each group assigns a unique seed per scenario — no two scenarios in the same group share a seed.

| Group | Scenario | APs/STAs | Seed | Sim Time | Bias  | Seg Len | Models         |
|-------|----------|----------|------|----------|-------|---------|----------------|
| A     | normal   | 1/2      |  10  | 80s      | —     | 256     | v3.0.0, v2.0.0 |
| A     | positive | 1/2      |  42  | 80s      | 5000  | 256     | v3.0.0, v2.0.0 |
| A     | negative | 1/2      |  99  | 80s      | 5000  | 256     | v3.0.0, v2.0.0 |
| B     | normal   | 1/2      |  20  | 80s      | —     | 256     | v3.0.0, v2.0.0 |
| B     | positive | 1/2      |  52  | 80s      | 5000  | 256     | v3.0.0, v2.0.0 |
| B     | negative | 1/2      | 109  | 80s      | 5000  | 256     | v3.0.0, v2.0.0 |
| C     | normal   | 1/2      |  30  | 80s      | —     | 256     | v3.0.0, v2.0.0 |
| C     | positive | 1/2      |  62  | 80s      | 5000  | 256     | v3.0.0, v2.0.0 |
| C     | negative | 1/2      | 119  | 80s      | 5000  | 256     | v3.0.0, v2.0.0 |
| D     | normal   | 1/2      |  40  | 80s      | —     | 256     | v3.0.0, v2.0.0 |
| D     | positive | 1/2      |  72  | 80s      | 5000  | 256     | v3.0.0, v2.0.0 |
| D     | negative | 1/2      | 129  | 80s      | 5000  | 256     | v3.0.0, v2.0.0 |
| E     | normal   | 1/2      |  50  | 80s      | —     | 256     | v3.0.0, v2.0.0 |
| E     | positive | 1/2      |  82  | 80s      | 5000  | 256     | v3.0.0, v2.0.0 |
| E     | negative | 1/2      | 139  | 80s      | 5000  | 256     | v3.0.0, v2.0.0 |

> Note: Groups A and B overlap with Tier 1. Run Tier 1 first — those results count toward Tier 5.

**Total: 30 experiments** (15 rows × 2 models), of which 12 are already covered by Tier 1.

---

## Metrics to Record

For each experiment, record from the Experiment View:

| Metric | Description |
|--------|-------------|
| `segment_count` | Total segments processed |
| `attack_rate` | Fraction of segments predicted as attack |
| `avg_confidence` | Mean prediction confidence |
| `model_version` | GCN version used |
| `pass_fail` | Automatic dashboard assessment |

### Derived metrics (calculate after all runs)

```
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 × Precision × Recall / (Precision + Recall)
Accuracy  = (TP + TN) / (TP + TN + FP + FN)

Where:
  TP = attack experiment → attack predicted
  TN = normal experiment → normal predicted
  FP = normal experiment → attack predicted
  FN = attack experiment → normal predicted
```

Use the **Model Intelligence > Analysis** tab to see aggregate TP/TN/FP/FN across all experiments.

---

## Experiment ID Convention

The dashboard auto-generates IDs in this format:
```
YYYY-MM-DDTHH-MM-<scenario>-<N>ap-seed<S>-<version>
```

Example: `2026-03-13-1400-positive-1ap-seed42-v300`

For manual runs, use descriptive IDs like:
```
eval-v3-positive-1ap-s42-b5000-seg256
eval-v2-positive-1ap-s42-b5000-seg256
```

---

## Running the Matrix via E2E Tests

```bash
cd tests

# Tier 1: Core accuracy (v3 + v2, 1AP, 256w)
npm run test:v3      # GCN v3 scenarios
npm run test:v2      # GCN v2 scenarios
```

Or directly:
```bash
node_modules/.bin/playwright test 01-run-experiment-v3
node_modules/.bin/playwright test 02-run-experiment-v2
```

---

## Expected Results Summary

### v3.0.0 (multi-AP, variable segment length)

| Scenario | 1AP | 2AP | 4AP | seg=256 | seg=128 | seg=64 |
|----------|-----|-----|-----|---------|---------|--------|
| normal   | ✅   | ✅   | ✅   | ✅       | ✅       | ?      |
| positive | ✅   | ✅   | ✅   | ✅       | ✅       | ?      |
| negative | ✅   | ✅   | ✅   | ✅       | ✅       | ?      |

### v2.0.0 (single-AP, 256w only)

| Scenario | 1AP | 2AP (unsupported) | seg=256 | seg<256 (unsupported) |
|----------|-----|-------------------|---------|----------------------|
| normal   | ✅   | ⚠️                 | ✅       | ⚠️                    |
| positive | ✅   | ⚠️                 | ✅       | ⚠️                    |
| negative | ✅   | ⚠️                 | ✅       | ⚠️                    |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Prediction failures: N` in GCN detector logs | Check scaler dimension vs feature count; rebuild detector container |
| Segments = 0 after run | Sim time too short for segment length; increase sim_time |
| attack_rate = 0 for attack experiment | Check bias value; ensure attack scenario selected |
| All experiments show attack_rate ~0.5 | Scaler mismatch; check model version matches container |
| Pipeline status stuck at windowizer | Windowizer may be unhealthy; check `docker logs ndt-pipeline-windowizer` |

---

## Related Files

- `twin/gnn/detector/inference_engine.py` — GCN inference, conditioning feature injection
- `twin/gnn/training_data/` — Training datasets per model version
- `twin/gnn/models/` — Trained model checkpoints
- `dashboard/app/backend/db/queries.py` — DB queries with date range filter
- `tests/e2e/` — Playwright E2E test suite

---

## Results — 2026-03-14 Full Matrix Run

The complete 5-tier matrix was executed on 2026-03-14 using `scripts/run_eval_matrix.py`.
All 54 experiments passed. Full analysis is in `docs/EVALUATION-RESULTS-2026-03-14.md`.

### Grand Total

| Tier | Description | Experiments | Pass | Fail |
|------|-------------|-------------|------|------|
| Tier 1 | Core accuracy (v3+v2, 1AP, 256w, seeds A+B) | 12 | 12 | 0 |
| Tier 2 | Multi-AP scaling (v3 only, 2AP+4AP) | 6 | 6 | 0 |
| Tier 3 | Segment length (v3 only, seg=128+64) | 6 | 6 | 0 |
| Tier 4 | Bias sensitivity (v3+v2, bias=1000/2000/10000) | 12 | 12 | 0 |
| Tier 5 | Seed generalisation (v3+v2, groups C+D+E) | 18 | 18 | 0 |
| **Total** | | **54** | **54** | **0** |

### Actual Results by Tier

**Tier 1 — Core Accuracy (12/12 PASS)**
- v3.0.0: normal avg\_conf ~95%, attack avg\_conf ~96%
- v2.0.0: normal avg\_conf ~90%, attack avg\_conf ~99.8%
- All attack\_rate values: 0.000 (normal) or 1.000 (attack)

**Tier 2 — Multi-AP (6/6 PASS)**
- v3.0.0 at 2AP/4STA and 4AP/8STA: perfect detection (0.000 / 1.000)
- Per-AP normalisation confirmed working at runtime

**Tier 3 — Segment Length (6/6 PASS)**
- v3.0.0 at seg=128 and seg=64: perfect detection (0.000 / 1.000)
- 17th segment-length conditioning feature confirmed effective

**Tier 4 — Bias Sensitivity (12/12 PASS)**
- Both models detect attacks at bias=1000 (one-fifth of training bias=5000)
- Minimum detectable bias is at or below 1000
- No degradation as bias decreases from 10000 to 1000

**Tier 5 — Seed Generalisation (18/18 PASS, groups C/D/E)**
- v3.0.0: normal avg\_conf stable ~95.2%; attack avg\_conf ~73.6–99.3% (seed-dependent for negative scenarios)
- v2.0.0: normal avg\_conf ~89.8–89.9%; attack avg\_conf ~99.3–99.9%
- Binary detection (attack\_rate) is perfect across all seeds

### Updated Expected Results Table (v3.0.0)

| Scenario | 1AP | 2AP | 4AP | seg=256 | seg=128 | seg=64 |
|----------|-----|-----|-----|---------|---------|--------|
| normal   | PASS | PASS | PASS | PASS | PASS | PASS |
| positive | PASS | PASS | PASS | PASS | PASS | PASS |
| negative | PASS | PASS | PASS | PASS | PASS | PASS |

### Updated Expected Results Table (v2.0.0)

| Scenario | 1AP | 2AP (unsupported) | seg=256 | seg<256 (unsupported) |
|----------|-----|-------------------|---------|----------------------|
| normal   | PASS | not tested | PASS | not tested |
| positive | PASS | not tested | PASS | not tested |
| negative | PASS | not tested | PASS | not tested |

### Key Conclusions

1. v3.0.0 is confirmed production-ready across all evaluated dimensions.
2. Both models are equally sensitive to low-bias attacks (bias=1000 detected reliably).
3. v3.0.0 generalises to multi-AP and multi-length scenarios without accuracy loss.
4. Seed generalisation confirmed: results hold across 5 independent NS-3 random conditions.
5. Next evaluation should determine minimum detectable bias (test bias=500, bias=250).
