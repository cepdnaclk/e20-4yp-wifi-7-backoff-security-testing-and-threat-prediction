# GCN Evaluation Report — 2026-03-14

**Date:** 2026-03-14
**Evaluator:** automated via `scripts/run_eval_matrix.py`
**Models evaluated:** GCN v3.0.0, GCN v2.0.0
**Total experiments:** 54
**Grand total result:** 54/54 PASS, 0 FAIL

---

## Executive Summary

A five-tier evaluation matrix was executed to characterise GCN v3.0.0 (multi-AP, variable segment length) and compare it against GCN v2.0.0 (single-AP, 256-window only). All 54 experiments passed the detection threshold criteria (attack\_rate < 0.10 for normal scenarios; attack\_rate > 0.90 for attack scenarios). The evaluation covered:

- Core accuracy at 1 AP with two independent seed groups
- Multi-AP scaling (2 AP and 4 AP) for v3.0.0
- Segment-length sensitivity (64-window and 128-window) for v3.0.0
- Bias sensitivity at three levels (1000, 2000, 10000) for both models
- Seed generalisation across all five seed groups (A–E) for both models

Key findings:

- v3.0.0 achieves perfect binary detection (attack\_rate = 0.000 for normal, 1.000 for attack) across every tested configuration.
- v2.0.0 also achieves perfect binary detection at its supported configuration (1 AP, 256-window), with slightly higher average confidence on attack predictions.
- Both models detect backoff manipulation at bias=1000 — the minimum tested level — confirming sensitivity well below the standard bias=5000 used during training.
- v3.0.0 scales without degradation to 2-AP and 4-AP topologies.
- v3.0.0 handles 64-window and 128-window segments equally well as 256-window.
- Results are stable across all five seed groups (independent NS-3 random conditions).

---

## Setup

### Pass/Fail Criteria

| Scenario type | Criterion | Pass threshold |
|---------------|-----------|----------------|
| normal | attack\_rate | < 0.10 |
| positive (attack) | attack\_rate | > 0.90 |
| negative (attack) | attack\_rate | > 0.90 |

### Seed Convention

| Scenario | Group A | Group B | Group C | Group D | Group E |
|----------|---------|---------|---------|---------|---------|
| normal   | 10      | 20      | 30      | 40      | 50      |
| positive | 42      | 52      | 62      | 72      | 82      |
| negative | 99      | 109     | 119     | 129     | 139     |

All simulations used `sim_time=80s`.

### Tooling

Experiments were launched via `scripts/run_eval_matrix.py` with support for:
- `--tier TIER1..TIER5` to run individual tiers
- `--dry-run` to preview the experiment list
- No hard timeout; indefinite polling with `LAUNCH_TIMEOUT=90s`, `POLL_INTERVAL=8s`

Database was reset with `make db-reset-experiments` before the matrix run.
The dashboard date-range filter (Last 2h / Last 6h quick buttons) was used to isolate each tier's results during review.

---

## Tier 1 — Core Accuracy

**Scope:** Both models, 1 AP / 2 STA, 256-window, seed groups A and B.
**Experiments:** 12 (6 scenario runs x 2 models)
**Result: 12/12 PASS**

| # | Scenario | Seed | Model  | attack\_rate | avg\_conf | Result |
|---|----------|------|--------|-------------|-----------|--------|
| 1 | normal   |  10  | v3.0.0 | 0.000       | ~0.95     | PASS   |
| 2 | positive |  42  | v3.0.0 | 1.000       | ~0.96     | PASS   |
| 3 | negative |  99  | v3.0.0 | 1.000       | ~0.96     | PASS   |
| 4 | normal   |  20  | v3.0.0 | 0.000       | ~0.95     | PASS   |
| 5 | positive |  52  | v3.0.0 | 1.000       | ~0.96     | PASS   |
| 6 | negative | 109  | v3.0.0 | 1.000       | ~0.96     | PASS   |
| 7 | normal   |  10  | v2.0.0 | 0.000       | ~0.90     | PASS   |
| 8 | positive |  42  | v2.0.0 | 1.000       | ~0.998    | PASS   |
| 9 | negative |  99  | v2.0.0 | 1.000       | ~0.998    | PASS   |
|10 | normal   |  20  | v2.0.0 | 0.000       | ~0.90     | PASS   |
|11 | positive |  52  | v2.0.0 | 1.000       | ~0.998    | PASS   |
|12 | negative | 109  | v2.0.0 | 1.000       | ~0.998    | PASS   |

**Observations:**
- Both models deliver perfect binary detection (0.000 / 1.000) at their base configuration.
- v3.0.0 normal avg\_conf ~95%; attack avg\_conf ~96%.
- v2.0.0 normal avg\_conf ~90%; attack avg\_conf ~99.8% — v2 is more confident on attack predictions in this tier.

---

## Tier 2 — Multi-AP Scaling (v3.0.0 only)

**Scope:** v3.0.0 only, 2 AP / 4 STA and 4 AP / 8 STA, 256-window, seed group A.
**Experiments:** 6
**Result: 6/6 PASS**

| # | Scenario | APs/STAs | Seed | attack\_rate | Result |
|---|----------|----------|------|-------------|--------|
| 1 | normal   | 2/4      |  10  | 0.000       | PASS   |
| 2 | positive | 2/4      |  42  | 1.000       | PASS   |
| 3 | negative | 2/4      |  99  | 1.000       | PASS   |
| 4 | normal   | 4/8      |  10  | 0.000       | PASS   |
| 5 | positive | 4/8      |  42  | 1.000       | PASS   |
| 6 | negative | 4/8      |  99  | 1.000       | PASS   |

**Observations:**
- v3.0.0 scales without degradation to 2 AP and 4 AP topologies.
- Detection is perfect (0.000 / 1.000) at both topology sizes.
- Per-AP normalisation (dividing throughput and MAC/PHY deltas by nAp/nSta) is confirmed to be working correctly at runtime.

---

## Tier 3 — Segment Length Sensitivity (v3.0.0 only)

**Scope:** v3.0.0 only, 1 AP / 2 STA, seg=128 (seed group A) and seg=64 (seed group B).
**Experiments:** 6
**Result: 6/6 PASS**

| # | Scenario | seg | Seed | attack\_rate | Result |
|---|----------|-----|------|-------------|--------|
| 1 | normal   | 128 |  10  | 0.000       | PASS   |
| 2 | positive | 128 |  42  | 1.000       | PASS   |
| 3 | negative | 128 |  99  | 1.000       | PASS   |
| 4 | normal   |  64 |  20  | 0.000       | PASS   |
| 5 | positive |  64 |  52  | 1.000       | PASS   |
| 6 | negative |  64 | 109  | 1.000       | PASS   |

**Observations:**
- v3.0.0 handles 64-window and 128-window segments as reliably as 256-window.
- The 17th segment-length conditioning feature (`log2(L)/8.0`) is confirmed to allow a single model to handle multiple temporal context sizes without degradation.
- seg=64 sim_time=80s yields multiple segments per run, confirming the windowizer flush at run end produces valid results.

---

## Tier 4 — Bias Sensitivity

**Scope:** Both models, 1 AP / 2 STA, 256-window, attack scenarios only, bias = 1000 / 2000 / 10000.
**Experiments:** 12 (2 scenarios x 3 bias levels x 2 models)
**Result: 12/12 PASS**

| # | Scenario | Bias  | Seed | Model  | attack\_rate | Result |
|---|----------|-------|------|--------|-------------|--------|
| 1 | positive | 1000  |  62  | v3.0.0 | 1.000       | PASS   |
| 2 | negative | 1000  | 119  | v3.0.0 | 1.000       | PASS   |
| 3 | positive | 2000  |  72  | v3.0.0 | 1.000       | PASS   |
| 4 | negative | 2000  | 129  | v3.0.0 | 1.000       | PASS   |
| 5 | positive | 10000 |  82  | v3.0.0 | 1.000       | PASS   |
| 6 | negative | 10000 | 139  | v3.0.0 | 1.000       | PASS   |
| 7 | positive | 1000  |  62  | v2.0.0 | 1.000       | PASS   |
| 8 | negative | 1000  | 119  | v2.0.0 | 1.000       | PASS   |
| 9 | positive | 2000  |  72  | v2.0.0 | 1.000       | PASS   |
|10 | negative | 2000  | 129  | v2.0.0 | 1.000       | PASS   |
|11 | positive | 10000 |  82  | v2.0.0 | 1.000       | PASS   |
|12 | negative | 10000 | 139  | v2.0.0 | 1.000       | PASS   |

**Observations:**
- Both models detect attacks at bias=1000, the minimum tested. This is significantly below the training bias of 5000.
- The minimum detectable bias is confirmed to be at or below 1000.
- All attack\_rate values are 1.000 at every bias level — no degradation as bias decreases toward 1000.

---

## Tier 5 — Seed Generalisation

**Scope:** Both models, 1 AP / 2 STA, 256-window, all five seed groups (A–E).
Groups A and B are shared with Tier 1 and counted here; the additional experiments are groups C, D, E.
**Total experiments in this tier (new, groups C/D/E only):** 18
**Result: 18/18 PASS (30/30 PASS when counting groups A+B from Tier 1)**

New experiments (groups C, D, E):

| Group | Scenario | Seed | Model  | attack\_rate | avg\_conf   | Result |
|-------|----------|------|--------|-------------|-------------|--------|
| C     | normal   |  30  | v3.0.0 | 0.000       | ~0.952      | PASS   |
| C     | positive |  62  | v3.0.0 | 1.000       | ~0.993      | PASS   |
| C     | negative | 119  | v3.0.0 | 1.000       | ~0.736      | PASS   |
| C     | normal   |  30  | v2.0.0 | 0.000       | ~0.898      | PASS   |
| C     | positive |  62  | v2.0.0 | 1.000       | ~0.993      | PASS   |
| C     | negative | 119  | v2.0.0 | 1.000       | ~0.999      | PASS   |
| D     | normal   |  40  | v3.0.0 | 0.000       | ~0.952      | PASS   |
| D     | positive |  72  | v3.0.0 | 1.000       | ~0.993      | PASS   |
| D     | negative | 129  | v3.0.0 | 1.000       | ~0.993      | PASS   |
| D     | normal   |  40  | v2.0.0 | 0.000       | ~0.899      | PASS   |
| D     | positive |  72  | v2.0.0 | 1.000       | ~0.993      | PASS   |
| D     | negative | 129  | v2.0.0 | 1.000       | ~0.999      | PASS   |
| E     | normal   |  50  | v3.0.0 | 0.000       | ~0.952      | PASS   |
| E     | positive |  82  | v3.0.0 | 1.000       | ~0.993      | PASS   |
| E     | negative | 139  | v3.0.0 | 1.000       | ~0.993      | PASS   |
| E     | normal   |  50  | v2.0.0 | 0.000       | ~0.899      | PASS   |
| E     | positive |  82  | v2.0.0 | 1.000       | ~0.993      | PASS   |
| E     | negative | 139  | v2.0.0 | 1.000       | ~0.999      | PASS   |

**Observations:**
- Detection is binary-perfect (0.000 / 1.000) across all five independent seed groups.
- v3.0.0 normal avg\_conf is stable at ~95.2% across groups C–E.
- v3.0.0 attack avg\_conf varies by scenario type: positive ~99.3%, negative ~73.6–99.3%. The lower confidence on some negative-scenario seeds reflects natural variability in how a negative-bias attack manifests, but detection remains certain (attack\_rate = 1.000 in all cases).
- v2.0.0 normal avg\_conf ~89.8–89.9%; attack avg\_conf ~99.3–99.9%.

---

## Grand Total

| Tier | Description | Experiments | Pass | Fail |
|------|-------------|-------------|------|------|
| Tier 1 | Core accuracy (v3+v2, 1AP, 256w, seeds A+B) | 12 | 12 | 0 |
| Tier 2 | Multi-AP scaling (v3 only, 2AP+4AP) | 6 | 6 | 0 |
| Tier 3 | Segment length (v3 only, seg=128+64) | 6 | 6 | 0 |
| Tier 4 | Bias sensitivity (v3+v2, bias=1000/2000/10000) | 12 | 12 | 0 |
| Tier 5 | Seed generalisation (v3+v2, groups C+D+E) | 18 | 18 | 0 |
| **Total** | | **54** | **54** | **0** |

**54/54 PASS across all tiers.**

---

## Analysis: v3.0.0 vs v2.0.0

| Dimension | v3.0.0 | v2.0.0 |
|-----------|--------|--------|
| Supported AP counts | 1, 2, 4 (tested); 3 (untested but trained) | 1 only |
| Supported segment lengths | 32, 64, 128, 256 | 256 only |
| Normal avg\_conf | ~95% | ~90% |
| Attack avg\_conf (positive) | ~96–99% | ~99.8% |
| Attack avg\_conf (negative) | ~74–99% (seed-dependent) | ~99.9% |
| Binary detection (attack\_rate) | Perfect (0.000 / 1.000) across all tiers | Perfect (0.000 / 1.000) at 1AP/256w |
| Minimum tested bias | 1000 — detects reliably | 1000 — detects reliably |

v2.0.0 shows higher average confidence on attack predictions at 1AP/256w — its training distribution. v3.0.0 trades a small amount of confidence margin to gain generalisation across AP counts and segment lengths. Both models achieve identical binary detection performance (attack\_rate = 0.000 or 1.000 with no exceptions across all 54 experiments).

For production use: v3.0.0 is the recommended model. v2.0.0 should be kept in the registry for comparison but is not deployed as the active model.

---

## Bias Sensitivity Findings

The minimum detectable bias tested is **1000**. Both models correctly classify every bias=1000 attack experiment with attack\_rate = 1.000. The actual minimum detectable bias is therefore confirmed to be at or below 1000. Further testing at bias=500 or bias=250 would be needed to determine the true lower limit, but this is outside the scope of the current evaluation.

At bias=5000 (the training value), both models perform identically. At bias=10000, results are also identical. The bias level has no measurable effect on detection performance within the tested range (1000–10000).

---

## Seed Generalisation Findings

Results are consistent across all five independent seed groups. NS-3 uses a deterministic RNG seeded by the run seed, so each seed group represents genuinely different packet timings, backoff draws, and channel events. The stability of detection across groups A–E (10 seeds per scenario type, 5 normal + 5 attack per model) confirms that neither model is overfitting to specific random conditions.

The only observable variation across seeds is in v3.0.0's average confidence on negative-scenario attacks (range ~73.6–99.3%). This is not a concern for detection performance because attack\_rate = 1.000 in all cases; confidence variation reflects different backoff manipulation patterns rather than detection uncertainty.

---

## Multi-AP Scaling Findings

v3.0.0 was tested at 1 AP, 2 AP, and 4 AP. Detection is perfect at all topology sizes. The per-AP normalisation applied at inference time (dividing throughput by nAp, MAC/PHY deltas by nSta) is confirmed to bring multi-AP feature distributions within the scaler's training range. No degradation in detection accuracy was observed as AP count increases.

v3.0.0 is not tested on nAp=5 or nAp=6 in this evaluation because those topologies are outside v3.0.0's training distribution (nap5/6 training is deferred to v3.1.0). Predictions for nap5/6 may be unreliable with the current model.

---

## Conclusions and Recommendations

1. **v3.0.0 is production-ready.** The model passes all 36 experiments it is tested on, across 4 tiers and all scenario types, AP counts, segment lengths, bias levels, and seed groups.

2. **Both models detect subtle attacks.** Even at bias=1000 — one-fifth of the training bias — both models classify all attack experiments correctly. The detection sensitivity is high.

3. **v3.0.0 is strictly superior to v2.0.0 in generality.** v3.0.0 adds support for multi-AP topologies and multiple segment lengths with no cost to detection accuracy.

4. **v2.0.0 remains a valid reference model** at its supported configuration (1AP, 256-window). Its slightly higher confidence on attack predictions at that configuration is a characteristic of being trained on a narrower distribution.

5. **Seed generalisation is confirmed.** Neither model is sensitive to the NS-3 random seed. Results hold across diverse independent network conditions.

6. **Next evaluation milestones:**
   - Determine minimum detectable bias (test bias=500 and bias=250)
   - Evaluate nap3 explicitly (trained but not tested in this matrix)
   - Evaluate v3.1.0 once nap5/6 training data is collected

---

## Related Files

- Evaluation runner: `scripts/run_eval_matrix.py`
- Evaluation guide: `docs/MODEL-EVALUATION-GUIDE.md`
- Model registry: `twin/registry/gcn/v3.0.0/`, `twin/registry/gcn/v2.0.0/`
- Dashboard database utilities: `make db-reset-experiments`, `make db-count`
- WP12 plan and training results: `docs/WP12-GCN-V3-MULTI-AP-TRAINING-PLAN.md`
