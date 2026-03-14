# Overnight Gap-Fill Plan — Multi-AP Coverage

**Date:** 2026-03-14 (run overnight, results expected 2026-03-15)
**Goal:** Bring every (AP count × scenario) combination up to **3 independent seed-group runs** so comparisons in the Experiment View are meaningful.
**Script:** `scripts/run_overnight_gaps.py`
**Data policy:** Existing DB data is **preserved** — all new runs are additive.

---

## Current State (as of 2026-03-14)

| AP | Scenario | Groups present | Groups missing |
|----|----------|---------------|----------------|
| 2AP | normal   | A (seed=10)   | B, C |
| 2AP | positive | A (seed=42)   | B, C |
| 2AP | negative | A (seed=99)   | B, C |
| 3AP | normal   | _(none)_      | A, B, C |
| 3AP | positive | seed=22 only (non-standard) | A, B, C |
| 3AP | negative | _(none)_      | A, B, C |
| 4AP | normal   | A (seed=10)   | B, C |
| 4AP | positive | A (seed=42)   | B, C |
| 4AP | negative | A (seed=99)   | B, C |

**1AP coverage** is already comprehensive (Tiers 1, 4, 5 — Groups A–E, both v2 and v3). No 1AP gaps.

---

## Seed Convention (from MODEL-EVALUATION-GUIDE.md)

| Group | normal | positive | negative |
|-------|--------|----------|----------|
| A     | 10     | 42       | 99       |
| B     | 20     | 52       | 109      |
| C     | 30     | 62       | 119      |

Within each group, every scenario has a different seed — no duplicate data for the same AP count.
Reusing the same seed group across AP counts is fine (different topology = different simulation).

---

## Planned Runs — 21 Experiments

All runs use: `sim_time=80`, `seg_len=256`, `gcn_version=v3.0.0`, `bias=5000` (attacks) / `0` (normal).

### 2AP — 6 runs (Groups B + C)

| # | Scenario | Seed | AP/STA | Group | Note |
|---|----------|------|--------|-------|------|
| 1 | normal   | 20   | 2AP/4STA | B   | — |
| 2 | positive | 52   | 2AP/4STA | B   | — |
| 3 | negative | 109  | 2AP/4STA | B   | — |
| 4 | normal   | 30   | 2AP/4STA | C   | — |
| 5 | positive | 62   | 2AP/4STA | C   | — |
| 6 | negative | 119  | 2AP/4STA | C   | — |

### 3AP — 9 runs (Groups A + B + C — all new)

| # | Scenario | Seed | AP/STA | Group | Note |
|---|----------|------|--------|-------|------|
| 7  | normal   | 10  | 3AP/6STA | A   | — |
| 8  | positive | 42  | 3AP/6STA | A   | — |
| 9  | negative | 99  | 3AP/6STA | A   | — |
| 10 | normal   | 20  | 3AP/6STA | B   | — |
| 11 | positive | 52  | 3AP/6STA | B   | — |
| 12 | negative | 109 | 3AP/6STA | B   | — |
| 13 | normal   | 30  | 3AP/6STA | C   | — |
| 14 | positive | 62  | 3AP/6STA | C   | — |
| 15 | negative | 119 | 3AP/6STA | C   | — |

### 4AP — 6 runs (Groups B + C)

| # | Scenario | Seed | AP/STA | Group | Note |
|---|----------|------|--------|-------|------|
| 16 | normal   | 20  | 4AP/8STA | B   | — |
| 17 | positive | 52  | 4AP/8STA | B   | — |
| 18 | negative | 109 | 4AP/8STA | B   | — |
| 19 | normal   | 30  | 4AP/8STA | C   | — |
| 20 | positive | 62  | 4AP/8STA | C   | — |
| 21 | negative | 119 | 4AP/8STA | C   | — |

---

## Time Estimate

| AP | Runs | Est. per run | Est. total |
|----|------|-------------|------------|
| 2AP | 6  | 10–15 min   | ~75 min    |
| 3AP | 9  | 15–20 min   | ~157 min   |
| 4AP | 6  | 25–35 min   | ~180 min   |
| **Total** | **21** | | **~6–7 hours** |

Start time target: **22:00 local** → expected finish by **05:00** the following morning.

---

## How to Run

### Full overnight run (all 21 experiments)

```bash
# Ensure infrastructure is running
make status
make pipeline-up   # harmonizer + windowizer + GCN detector
make dashboard-up  # :8888

# Launch overnight script (use -u for unbuffered output)
python3 -u scripts/run_overnight_gaps.py 2>&1 | tee /tmp/overnight-gaps-$(date +%Y%m%d-%H%M).log &

# Tail the log
tail -f /tmp/overnight-gaps-*.log
```

### Dry-run first — verify the plan

```bash
python3 scripts/run_overnight_gaps.py --dry-run
```

### Run a specific AP count only

```bash
python3 -u scripts/run_overnight_gaps.py --ap 2       # 2AP only (6 runs, ~75 min)
python3 -u scripts/run_overnight_gaps.py --ap 3       # 3AP only (9 runs, ~2.5 h)
python3 -u scripts/run_overnight_gaps.py --ap 4       # 4AP only (6 runs, ~3 h)
python3 -u scripts/run_overnight_gaps.py --ap 2 3     # 2AP + 3AP
```

### Resume if interrupted mid-run

```bash
# If interrupted after experiment N, resume from N+1 (0-indexed)
python3 -u scripts/run_overnight_gaps.py --start 7    # skip first 7, resume from #8
```

---

## Pass / Fail Criteria

Same as the main evaluation matrix (MODEL-EVALUATION-GUIDE.md):

| Scenario | Criterion | Threshold |
|----------|-----------|-----------|
| normal   | attack_rate < 10% | PASS |
| positive | attack_rate > 90% | PASS |
| negative | attack_rate > 90% | PASS |

---

## After the Run

### 1. Check results

The script saves a JSON results file to `/tmp/overnight-gaps-TIMESTAMP.json`. Summary is also printed at the end of the run.

```bash
cat /tmp/overnight-gaps-*.json | python3 -m json.tool | grep -E '"pass_fail"|"scenario"|"num_ap"|"seed"'
```

### 2. Verify in the dashboard

Open **http://localhost:8888** → **Experiment View**. Use the new filter buttons:
- Select **2AP** / **3AP** / **4AP** from the AP filter
- Each scenario (Normal / Positive / Negative) should now show 3 buttons

### 3. Compare in the UI

Use **Compare mode** to pit runs against each other. Recommended comparisons:
- `normal-2ap-seedA` vs `normal-2ap-seedB` vs `normal-2ap-seedC` — verify consistency
- `positive-3ap-seedA` vs `negative-3ap-seedA` — attack vs non-attack at same topology
- `positive-2ap` vs `positive-3ap` vs `positive-4ap` — scaling behaviour

### 4. Update documentation (if results are notable)

If all 21 pass, update `docs/CURRENT-STATE.md` and `docs/MODEL-EVALUATION-GUIDE.md` with the extended coverage results.

---

## Expected Post-Run Coverage

| AP | Scenario | Seed groups | Runs |
|----|----------|------------|------|
| 2AP | normal   | A, B, C    | 3 ✅ |
| 2AP | positive | A, B, C    | 3 ✅ |
| 2AP | negative | A, B, C    | 3 ✅ |
| 3AP | normal   | A, B, C    | 3 ✅ |
| 3AP | positive | A, B, C    | 3 ✅ (+ non-standard seed22) |
| 3AP | negative | A, B, C    | 3 ✅ |
| 4AP | normal   | A, B, C    | 3 ✅ |
| 4AP | positive | A, B, C    | 3 ✅ |
| 4AP | negative | A, B, C    | 3 ✅ |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Script hangs at launch | Check `make pipeline-up` and `make dashboard-up` are running |
| Experiment never becomes active | Dashboard may have restarted; check `make dashboard-logs` |
| Run fails with code ≠ 0 | Check `/tmp/last_run.log` inside the dashboard container: `docker exec ndt-dashboard cat /tmp/last_run.log` |
| Interrupted mid-run | Use `--start N` to resume from the Nth experiment (0-indexed) |
| Wrong predictions (attack on normal) | Verify `twin/registry/gcn/current` points to `v3.0.0` |
