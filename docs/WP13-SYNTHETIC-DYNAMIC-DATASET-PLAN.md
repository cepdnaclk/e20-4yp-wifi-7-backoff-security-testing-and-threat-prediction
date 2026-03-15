# WP13 — Synthetic Dynamic Dataset Generation Plan

**Status:** Planning
**Date:** 2026-03-15
**Author:** Planner agent (research + plan only; no code written)
**Depends on:** WP12 (v3.0.0 deployed), v4 static data collection (complete for train/val; partial for test)

---

## 1. Objective

Generate a synthetic dynamic dataset by programmatically stitching together windows from existing static simulation files. Each synthetic "dynamic" file contains 2–4 contiguous phases, where each phase is sourced from a single static file with a uniform bias value. The resulting dataset populates `twin/gnn/training_data/v4/train/Dynamic/`, `val/Dynamic/`, and `test/Dynamic/` to supplement the small set of real NS-3 dynamic files already collected.

The primary goal is to produce GCN v4 training data that contains realistic phase transitions (e.g., normal → positive-attack → normal) without running new NS-3 simulations, using only windows that already exist on disk.

---

## 2. Background and Motivation

### 2.1 Why Synthetic Stitching?

The WP13 GCN v4 plan (see `docs/WP13-GCN-V4-DYNAMIC-TRAINING-PLAN.md`) specifies 528 dynamic training files. The NS-3 `run_mlo_dynamic.sh` script is the canonical source for real dynamic files, but:

- Each NS-3 run takes 30–160 seconds of wall-clock time per file.
- 528 files × ~60s average ≈ 9 hours on 8 cores.
- The infrastructure for running dynamic NS-3 scenarios (PHASES env var parsing) has already been built and partially used.

Synthetic stitching can produce the same training signal in **minutes** by concatenating windows from static source files that are already on disk. Since each static file has a constant bias throughout, slicing 400 windows from it and appending to another file's 400 windows creates an artificial phase transition that is physically valid: the telemetry sequences are real NS-3 outputs, just temporally joined.

### 2.2 Current State of Dynamic Files

| Split | Real dynamic files (NS-3) | Pattern IDs present |
|-------|---------------------------|---------------------|
| train | 46 | D-01, D-02, D-13 only |
| val | 14 | D-01, D-04 only |
| test | 17 | D-01, D-09 only |

The synthetic plan must **add** files for the missing patterns, not replace the real ones. Real NS-3 files remain in their folders and are used as-is.

---

## 3. Complete Data Inventory

### 3.1 Multi-AP Static Data (Primary Source)

These files have `num_ap` and `num_sta` fields and are fully compatible with the v4 GCN training pipeline's multi-AP normalisation.

| Dataset | Split | Subfolder | Files | Windows/file | Seeds | nap | Biases |
|---------|-------|-----------|-------|-------------|-------|-----|--------|
| v4 Static Normal | train | `v4/train/Static/Normal/` | 28 | 800 | 42,111,123,222,321,333,456,654,789,987 | 1,2,3 | 0 |
| v4 Static Attack | train | `v4/train/Static/Attack/` | 165 | 800 | same 10 seeds | 1,2,3 | ±1000,±2000,±5000 |
| v4 Static Normal | val | `v4/val/Static/Normal/` | 17 | 800 | 444,777,888 | 1,2,3,4 | 0 |
| v4 Static Attack | val | `v4/val/Static/Attack/` | 33 | 800 | 444,777,888 | 1,2,3,4 | ±5000 only |
| v4 Static Normal | test | `v4/test/Static/Normal/` | 6 | 800 | 555,999,1234 | 1,2 | 0 |
| v4 Static Attack | test | `v4/test/Static/Attack/` | 59 | 800 | 555,999,1234 | 1,2 | ±500,±1000,±2000,±4000,±5000 |
| v3 Normal | — | `v3/Normal/` | 16 | 800 | 42,43,44,45 | 1,2,3,4 | 0 |
| v3 Attack | — | `v3/Attack/` | 32 | 800 | 42,43,44,45 | 1,2,3,4 | ±5000 |

**Notes:**
- v4 nap3 train Normal seeds are 8 (not 10): seeds 42,111,123,321,456,654,789,987 (seeds 222,333 missing for nap3).
- v4 nap3 train Attack: same 8 seeds × 6 biases = 48 files. nap1/nap2 have 10 seeds × 6 biases = 60 each.
- v4 val nap4 Normal: only seeds 777,888 (not 444) — 2 files. val Attack nap4: only seeds 777,888 — 2 files.
- v4 test: nap1 and nap2 only (nap3/nap4 absent in test Static).
- v3 seeds (42–45) do NOT overlap with v4 seeds. They are a separate pool usable without leakage.

### 3.2 Single-AP Static Data (Secondary Source — Augmentation Only)

These files lack `num_ap`/`num_sta` fields. The preprocessing pipeline falls back to no multi-AP normalisation when these fields are absent. They are suitable only for single-AP synthetic files.

| Dataset | Location | Files | Windows/file | Seeds | Biases |
|---------|----------|-------|-------------|-------|--------|
| Pilot (ndt-wifi7) | `training_data/scenarios/` | 29 | 2000–14000 | 1–15 | 0, ±50,±100,±500,±1000,±5000 |
| Extended (ndt-wifi7) | `training_data_extended/scenarios/` | 255 | 2000 | 100–422 | 0, ±50,±100,±250,±500,±1000,±2500,±5000,±10000 |
| wifi7_gcn v2 prod | `/home/cobrakali/github/wifi7_gcn_attack_detection/data_v2_production/` | 284 | 2000 | 1–422 | 0, ±50–±10000 |
| Wifi7_Datasets (Normal) | `/home/cobrakali/github/wifi7_gcn_attack_detection/Wifi7_Datasets/Normal/` | 12 | 14000 | session/scenario naming | 0 |
| Wifi7_Datasets (Attack) | `/home/cobrakali/github/wifi7_gcn_attack_detection/Wifi7_Datasets/Attack/` | 192 | 1000 | session/scenario naming | ±50–±10000 |

**Critical observations on single-AP data:**
1. The `num_ap` and `num_sta` fields are **absent**. The v4 pipeline's `extract_features()` function falls back to no-normalisation when these are missing (documented in `preprocessing.py` comments). Single-AP synthetic files will have `num_ap=1, num_sta=2` injected by the stitcher.
2. Files in `data_v2_production/` and `training_data_extended/` with the same name (e.g., `extended-20260214-normal-normal-seed100.json`) are **byte-for-byte identical** across both repositories. They must be counted only once.
3. Seeds 111, 123, 222, 321, 333 appear in both v4 multi-AP train data AND single-AP extended data. However, **verified that these produce different window values** because NS-3 uses different topology parameters (nSta differs). Same seed number ≠ same simulation when topology differs. There is no data leakage.
4. `Wifi7_Datasets/` uses `session_N_scenario_M_run_P` naming — no numerical seeds. These are independently generated and do not overlap with any other dataset.

### 3.3 Summary: Available Windows Per Phase

| Source pool | Eligible biases | Windows available (train phase budget) |
|------------|----------------|---------------------------------------|
| v4 train Normal (nap1) | 0 | 10 files × 800 = 8000 |
| v4 train Normal (nap2) | 0 | 10 files × 800 = 8000 |
| v4 train Normal (nap3) | 0 | 8 files × 800 = 6400 |
| v4 train Attack nap1 | ±1000,±2000,±5000 | 60 files × 800 = 48000 |
| v4 train Attack nap2 | ±1000,±2000,±5000 | 60 files × 800 = 48000 |
| v4 train Attack nap3 | ±1000,±2000,±5000 | 45 files × 800 = 36000 |
| v3 Normal (nap1-4) | 0 | 16 × 800 = 12800 |
| v3 Attack (nap1-4) | ±5000 | 32 × 800 = 25600 |

---

## 4. Key Design Decisions

### 4.1 Synthetic vs Real NS-3 Files: Complementary, Not Competing

Synthetic files **supplement** real NS-3 dynamic files. The 46 real train files already in `v4/train/Dynamic/` remain unchanged. The stitcher writes only to patterns and nap/seed combinations not already present.

Before generating a synthetic file, the stitcher checks whether a real file with the same `nap_nstaX_seedY_D-ZZ_*` name already exists in the target directory. If it does, the stitcher skips that combination.

### 4.2 Phase Length Standard: 400 Windows

Each phase in a synthetic file uses exactly **400 windows** from the source static file, taken from the **middle** of the file (windows 200–599 of an 800-window file). This avoids:
- The first ~10 windows where some metrics are zero (simulation warm-up).
- The last ~10 windows where the simulation winds down.
- Taking from the start or end makes the phase ordering in the synthetic file exploitable as a shortcut.

Using windows 200–599 (400 windows) from an 800-window source gives 400 high-quality steady-state windows per phase.

**Slice convention:**
```
source_file[200:600]  →  400 windows (0-indexed, inclusive of 200, exclusive of 600)
```

For files with 2000 windows (single-AP extended/pilot), use windows 500–1499 (1000 windows per phase is also valid; see Section 5.1 for single-AP plan).

### 4.3 Window Index Renumbering

The `window` field in each window dictionary must be renumbered sequentially in the synthetic file, starting from 0. When stitching 4 phases of 400 windows each:

```
Phase 1 (windows 0–399):    source_A[200:600] → window field set to 0,1,...,399
Phase 2 (windows 400–799):  source_B[200:600] → window field set to 400,401,...,799
Phase 3 (windows 800–1199): source_C[200:600] → window field set to 800,...,1199
Phase 4 (windows 1200–1599):source_D[200:600] → window field set to 1200,...,1599
```

The `bias` field in each window is **preserved as-is** from the source file. The label for each window is determined entirely by its `bias` value at read time (0=normal, nonzero=attack) by the dataset loader.

### 4.4 Multi-AP Field Injection

Multi-AP source files (v4/v3) already have `num_ap` and `num_sta` fields. The stitcher must verify these are consistent across phases:
- **Requirement:** All phases in a single synthetic file MUST come from sources with the same `num_ap` and `num_sta`.
- Single-AP sources (pilot/extended) lack these fields; the stitcher injects `num_ap=1, num_sta=2` into each window.

### 4.5 Bias Field Preservation

The `bias` field is the sole source of per-window truth label. It must be preserved exactly from the source file. The dataset loader (`WiFi7AttackDatasetV4`) reads `bias` per window to assign per-segment majority-vote labels.

### 4.6 No Mixing Within a Phase

Each phase must source all 400 windows from a **single source file** with a **single consistent bias value**. The source file's bias must be constant (all windows same bias). This is guaranteed for all v4 Static files (verified above) and v3 files (verified above).

### 4.7 Segment Boundary Alignment

At 400-window phase boundaries, with segment length 256 and stride 64:
- Segments starting near offset 320 (e.g., 320, 384) span the transition at window 400.
- This is **intentional**: the model must learn to classify transition segments.
- No effort is made to align transitions to segment boundaries. Mid-segment transitions are desirable training signal.

---

## 5. Source File to Split Assignment

### 5.1 Primary: Multi-AP Sources (v4 + v3)

The split assignment for multi-AP sources is determined entirely by the seed pool already established for v4:

| Pool | Seeds | Source files |
|------|-------|-------------|
| **Train** | 42,111,123,222,321,333,456,654,789,987 | `v4/train/Static/Normal/`, `v4/train/Static/Attack/`, `v3/Normal/` (seeds 42–45), `v3/Attack/` (seeds 42–45) |
| **Val** | 444,777,888 | `v4/val/Static/Normal/`, `v4/val/Static/Attack/` |
| **Test** | 555,999,1234 | `v4/test/Static/Normal/`, `v4/test/Static/Attack/` |

**CRITICAL: No source file may appear in both train and val/test synthetic files.**
- Since seed pools are mutually exclusive, this is guaranteed for v4 sources.
- v3 seeds (42–45) overlap with v4 train seeds (42 is in v4 train). Use v3 files only in the **train** split.

### 5.2 Secondary: Single-AP Sources

The single-AP extended/pilot data uses seeds 1–422. These do not overlap with any v4 seed pool. Assignment:

| Pool | Single-AP Seeds |
|------|----------------|
| **Train (single-AP)** | Seeds 100–350 (extended normal + attack), seeds 1–12 (pilot) |
| **Val (single-AP)** | Seeds 351–400 (extended normal), seeds 13–14 (pilot) |
| **Test (single-AP)** | Seeds 401–422 (extended normal), seed 15 (pilot) |

These pools are exclusive. Seeds within the single-AP train pool are never used in val/test, and vice versa.

**Why split by seed range (not file name)?** The extended dataset seeds 100–422 are a contiguous range from a single generation run. Splitting by range preserves the statistical independence between splits (different simulation seeds = different RF channel states).

### 5.3 Concrete Source File Pools

#### Train split sources:
- `v4/train/Static/Normal/*.json` → Normal phases, nap1–3, seeds 42,111,123,222,321,333,456,654,789,987
- `v4/train/Static/Attack/*.json` → Attack phases, nap1–3, seeds same, biases ±1000/±2000/±5000
- `v3/Normal/*.json` → Normal phases, nap1–4, seeds 42,43,44,45 (additional topology diversity)
- `v3/Attack/*.json` → Attack phases, nap1–4, seeds 42,43,44,45, bias ±5000

#### Val split sources:
- `v4/val/Static/Normal/*.json` → Normal phases, nap1–4, seeds 444,777,888
- `v4/val/Static/Attack/*.json` → Attack phases, nap1–4, seeds 444,777,888, bias ±5000

#### Test split sources:
- `v4/test/Static/Normal/*.json` → Normal phases, nap1–2, seeds 555,999,1234
- `v4/test/Static/Attack/*.json` → Attack phases, nap1–2, seeds 555,999,1234, biases ±500/±1000/±2000/±4000/±5000

---

## 6. Phase Pattern Catalogue

Patterns are designated by the same IDs used in the WP13 GCN v4 plan and in the existing dynamic files (`D-ZZ`). Patterns already present in real NS-3 files are marked. The stitcher will skip generating a synthetic file if a real file for that (nap,seed,pattern) already exists.

### Group A: 2-Phase (800 windows = 2×400)

Each file: 800 total windows; transition at window 400.

| ID | Name | Phase sequence | Label sequence | Notes |
|----|------|----------------|----------------|-------|
| D-01 | norm→pos | norm_phase / pos_phase | N→A | Real files exist (skip if present) |
| D-02 | norm→neg | norm_phase / neg_phase | N→A | Real files exist (skip if present) |
| D-03 | pos→norm | pos_phase / norm_phase | A→N | MISSING — must synthesise |
| D-04 | neg→norm | neg_phase / norm_phase | A→N | Real val files exist; missing from train |
| D-05 | pos→neg | pos_phase / neg_phase | A→A | MISSING — must synthesise |
| D-06 | neg→pos | neg_phase / pos_phase | A→A | MISSING — must synthesise |

### Group B: 3-Phase (1200 windows = 3×400)

Each file: 1200 total windows; transitions at windows 400 and 800.

| ID | Name | Phase sequence | Label sequence | Notes |
|----|------|----------------|----------------|-------|
| D-07 | norm→pos→norm | norm / pos / norm | N→A→N | MISSING — must synthesise |
| D-08 | norm→neg→norm | norm / neg / norm | N→A→N | MISSING — must synthesise |
| D-09 | neg→norm→pos | neg / norm / pos | A→N→A | Real test files exist; missing from train |
| D-10 | pos→norm→neg | pos / norm / neg | A→N→A | MISSING — must synthesise |
| D-11 | pos→neg→pos | pos / neg / pos | A→A→A | MISSING — must synthesise |
| D-12 | neg→pos→neg | neg / pos / neg | A→A→A | MISSING — must synthesise |

### Group C: 4-Phase (1600 windows = 4×400)

Each file: 1600 total windows; transitions at windows 400, 800, 1200.

| ID | Name | Phase sequence | Label sequence | Notes |
|----|------|----------------|----------------|-------|
| D-13 | neg→norm→pos→norm | neg/norm/pos/norm | A→N→A→N | Real files exist (skip if present) |
| D-14 | norm→pos→norm→neg | norm/pos/norm/neg | N→A→N→A | MISSING — must synthesise |
| D-15 | pos→norm→neg→norm | pos/norm/neg/norm | A→N→A→N | MISSING — must synthesise |
| D-16 | neg→pos→norm→neg | neg/pos/norm/neg | A→A→N→A | MISSING — must synthesise |

### Group D: Uneven Phase Lengths (800–1200 windows)

These patterns expose the model to non-50/50 phase splits. Phase counts may not be multiples of 256. The transition does NOT fall at a segment boundary for any standard segment length, which creates more diverse transition-segment training examples.

| ID | Name | Phase lengths (windows) | Total | Notes |
|----|------|------------------------|-------|-------|
| D-17 | neg→norm (1/3 : 2/3) | 267+533 | 800 | Short attack, long recovery |
| D-18 | norm→pos (2/3 : 1/3) | 533+267 | 800 | Long benign, short attack burst |
| D-19 | neg→norm→pos (uneven) | 300+400+500 | 1200 | Asymmetric 3-phase |
| D-20 | pos→neg (early flip) | 150+650 | 800 | Very short initial phase |
| D-21 | norm→neg→norm (narrow) | 300+200+300 | 800 | Narrow middle attack window |

**Implementation note for Group D:** Source files must still provide 400+ windows from their middle. For phase lengths <400, take the first N windows of the 400-window slice. For phase lengths >400, take the first M windows of the source. The slice is always drawn from source[200:200+phase_len], capped at source[200:600].

### Group E: Weak-Bias Dynamic (800–1200 windows, bias=±1000 or ±2000)

These use the v4 train Static Attack files with bias ±1000 and ±2000 (available in train only).

| ID | Name | Phase sequence | Bias values |
|----|------|----------------|-------------|
| D-22 | norm→weak_pos | norm(400) / pos1000(400) | 0→+1000 |
| D-23 | norm→weak_neg | norm(400) / neg1000(400) | 0→-1000 |
| D-24 | weak_neg→norm→weak_pos | neg1000(400)/norm(400)/pos1000(400) | -1000→0→+1000 |
| D-25 | mid_pos→norm→mid_neg | pos2000(400)/norm(400)/neg2000(400) | +2000→0→-2000 |

### Group T: Test-Only Patterns (Never in Training)

These are generated only for the test split. They use 5-phase sequences not present in any training file.

| ID | Name | Phase sequence | Total windows |
|----|------|----------------|---------------|
| T-01 | norm→neg→norm→pos→norm | N/neg/N/pos/N | 2000 (5×400) |
| T-02 | pos→norm→pos→neg→norm | pos/N/pos/neg/N | 2000 |
| T-03 | neg→norm→neg→pos→neg | neg/N/neg/pos/neg | 2000 |
| T-04 | pos→neg→pos→norm→neg | pos/neg/pos/N/neg | 2000 |
| T-05 | norm→pos→neg→pos→norm | N/pos/neg/pos/N | 2000 |

These 5-phase patterns are excluded from train and val. Their purpose is to measure held-out generalization to unseen orderings.

**Summary: 25 training patterns (D-01 to D-25) + 5 test-only patterns (T-01 to T-05) = 30 total.**

---

## 7. Phase Source Selection Rules

### 7.1 Phase Type to Source File Mapping

| Phase type | Source pool | Selection rule |
|-----------|-------------|----------------|
| Normal (bias=0) | v4 Static Normal for that split | Pick file for (nap, seed) |
| Positive-attack (bias > 0) | v4 Static Attack for that split | Pick file for (nap, seed, bias) |
| Negative-attack (bias < 0) | v4 Static Attack for that split | Pick file for (nap, seed, bias) |

For patterns with multiple normal phases (e.g., D-07: norm→pos→norm), the **same** normal source file is used for both normal phases. The two 400-window slices are taken from different offsets of the same file: phase 1 from source[200:600], phase 3 from source[0:400]. This avoids duplicating windows (since the source file has 800 windows total).

**Offset schedule for reusing the same source file in multiple phases:**

| Phase occurrence in file | Slice used |
|--------------------------|-----------|
| 1st use of source file | source[200:600] |
| 2nd use of source file | source[0:200] + source[600:800] (non-overlapping) |

Since each 400-window slice is taken from a different non-overlapping region, there is no window-level duplication within a single synthetic file even when the same source is reused.

### 7.2 Attack Bias Selection Per Pattern

For Group A/B/C patterns using standard bias:
- Default attack bias: **±5000**
- Train-only diversity: also generate variants with **±1000** and **±2000** for selected nap/seed combos

For Group E (weak-bias patterns):
- Explicitly use bias=±1000 or ±2000 per the pattern definition.

### 7.3 When Multiple Bias Options Exist (Train Only)

The v4 train Static Attack has 3 bias values: ±1000, ±2000, ±5000. For a given (nap, seed, pattern), generate **3 variants** with different attack bias values:

- `nap1_nsta2_seed42_D-03_pos-norm_80s.json` → uses bias=+5000 source for pos phase
- `nap1_nsta2_seed42_D-03b_pos2000-norm_80s.json` → uses bias=+2000 source
- `nap1_nsta2_seed42_D-03c_pos1000-norm_80s.json` → uses bias=+1000 source

This triples the training diversity without requiring new simulations.

**Naming convention for bias variants:**
```
{nap}_{nsta}_seed{seed}_{D-ID}[b|c]_{pattern-name}[_bias{value}]_{total_windows}w.json
```

Example:
```
nap1_nsta2_seed42_D-03_pos5000-norm_80s.json    ← default (bias=±5000)
nap1_nsta2_seed42_D-03b_pos2000-norm_80s.json   ← variant b (bias=±2000)
nap1_nsta2_seed42_D-03c_pos1000-norm_80s.json   ← variant c (bias=±1000)
```

Val and test use only ±5000 (since val/test Attack only has ±5000).

---

## 8. Output File Format

### 8.1 Format Specification

Output files must match the existing dynamic file format exactly. The loader in `dataset_v4.py` expects:
- A JSON array at the top level (list of window dicts).
- Each window dict has keys: `window, bias, num_ap, num_sta, net_throughput_mbps, net_avg_delay_ms, net_avg_jitter_ms, net_packet_loss_ratio, net_active_flows, mac_total_tx, mac_total_rx, mac_total_ack, mac_total_retrans, mac_drop_count, phy_drop_count, avg_backoff_slots, channel_busy_ratio`.
- The `window` field is a sequential 0-based integer across the entire file.
- The `bias` field reflects the source file's bias value per window (0 or non-zero).
- `num_ap` and `num_sta` are preserved from source (or injected as 1, 2 for single-AP sources).

### 8.2 Naming Convention

Format: `{nap}_{nsta}_seed{seed}_{D-ID}_{pattern-name}_{total_sim_duration}s.json`

The `total_sim_duration` is a pseudo-sim-time based on 0.1 seconds per window:
- 800 windows → 80s
- 1200 windows → 120s
- 1600 windows → 160s
- 2000 windows → 200s

Examples:
```
nap1_nsta2_seed42_D-03_pos-norm_80s.json          ← 2-phase, 800 windows
nap2_nsta4_seed123_D-07_norm-pos-norm_120s.json   ← 3-phase, 1200 windows
nap3_nsta2_seed456_D-13_neg-norm-pos-norm_160s.json ← 4-phase, 1600 windows
nap1_nsta2_seed789_T-01_norm-neg-norm-pos-norm_200s.json ← 5-phase test-only
```

### 8.3 Target Directories

```
twin/gnn/training_data/v4/train/Dynamic/   ← All train synthetic files
twin/gnn/training_data/v4/val/Dynamic/     ← All val synthetic files
twin/gnn/training_data/v4/test/Dynamic/    ← All test synthetic files
```

Files are mixed with existing real NS-3 dynamic files in the same directories. The dataset loader does not distinguish synthetic from real.

---

## 9. Window Stitching Algorithm (Pseudocode)

```python
def stitch_synthetic_dynamic_file(
    phases: list[tuple[str, int]],  # [(source_path, bias), ...]
    phase_lengths: list[int],         # windows per phase (default [400, 400, ...])
    output_path: str,
    source_offsets: list[int] = None, # start index in source file (default 200)
) -> None:
    """
    Stitch together windows from multiple static source files into one dynamic file.

    Args:
        phases:         List of (source_json_path, expected_bias) tuples.
                        expected_bias is used for validation only.
        phase_lengths:  Number of windows to take from each source.
        output_path:    Path to write the synthetic dynamic JSON file.
        source_offsets: Start index in each source file.
                        Default: 200 for primary phase, 0 for secondary use.
    """
    if source_offsets is None:
        source_offsets = [200] * len(phases)

    result_windows = []
    global_window_idx = 0

    for (source_path, expected_bias), phase_len, offset in zip(
        phases, phase_lengths, source_offsets
    ):
        # Load source file
        with open(source_path) as f:
            source_windows = json.load(f)

        # Validate
        assert len(source_windows) >= offset + phase_len, (
            f"Source {source_path} has only {len(source_windows)} windows; "
            f"need offset={offset} + phase_len={phase_len}"
        )
        slice_windows = source_windows[offset : offset + phase_len]

        # Validate bias consistency
        biases_in_slice = {w["bias"] for w in slice_windows}
        assert len(biases_in_slice) == 1, (
            f"Source {source_path} slice has mixed biases: {biases_in_slice}. "
            f"Source files must have constant bias."
        )
        actual_bias = next(iter(biases_in_slice))
        assert actual_bias == expected_bias, (
            f"Expected bias {expected_bias}, got {actual_bias} in {source_path}"
        )

        # Renumber windows and append
        for w in slice_windows:
            new_window = dict(w)  # shallow copy
            new_window["window"] = global_window_idx
            global_window_idx += 1
            result_windows.append(new_window)

    # Write output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result_windows, f)


def get_source_file(
    data_root: str,
    split: str,
    scenario: str,  # "Normal" or "Attack"
    nap: int,
    nsta: int,
    seed: int,
    bias: int,       # 0 for Normal, nonzero for Attack
    sim_time: int = 80,
) -> str:
    """
    Build the path to a static source file given its parameters.
    Returns None if file does not exist.
    """
    subdir = os.path.join(data_root, split, "Static", scenario)
    if scenario == "Normal":
        fname = f"nap{nap}_nsta{nsta}_seed{seed}_normal_{sim_time}s.json"
    else:
        sign = "positive" if bias > 0 else "negative"
        fname = f"nap{nap}_nsta{nsta}_seed{seed}_{sign}{abs(bias)}_{sim_time}s.json"
    path = os.path.join(subdir, fname)
    return path if os.path.exists(path) else None


def output_already_exists(output_dir: str, nap: int, nsta: int,
                          seed: int, pattern_id: str, pattern_name: str,
                          total_windows: int) -> bool:
    """Check if a real or synthetic file already exists for this combination."""
    sim_time = total_windows // 10  # 800 windows = 80s pseudo-time
    fname = f"nap{nap}_nsta{nsta}_seed{seed}_{pattern_id}_{pattern_name}_{sim_time}s.json"
    return os.path.exists(os.path.join(output_dir, fname))


def generate_train_synthetic_dataset(data_root: str, output_dir: str) -> None:
    """
    Top-level generator for train split synthetic dynamic files.
    """
    TRAIN_SEEDS = [42, 111, 123, 222, 321, 333, 456, 654, 789, 987]
    NAP_NSTA_MAP = {1: 2, 2: 4, 3: 2}  # nap3 uses nsta=2 for speed
    STANDARD_BIAS = 5000
    WEAK_BIASES = [1000, 2000, 5000]  # for multi-bias train variants
    PHASE_LEN = 400

    # Define all phase pattern templates
    # Format: (pattern_id, pattern_name, phase_types, attack_bias)
    # phase_types: list of 'N' (Normal) or 'P' (Positive) or 'G' (Negative)
    PATTERNS = [
        # Group A: 2-phase
        ("D-03", "pos-norm",    ["P", "N"],          STANDARD_BIAS),
        ("D-04", "neg-norm",    ["G", "N"],          STANDARD_BIAS),
        ("D-05", "pos-neg",     ["P", "G"],          STANDARD_BIAS),
        ("D-06", "neg-pos",     ["G", "P"],          STANDARD_BIAS),
        # Group B: 3-phase
        ("D-07", "norm-pos-norm",    ["N", "P", "N"], STANDARD_BIAS),
        ("D-08", "norm-neg-norm",    ["N", "G", "N"], STANDARD_BIAS),
        ("D-09", "neg-norm-pos",     ["G", "N", "P"], STANDARD_BIAS),
        ("D-10", "pos-norm-neg",     ["P", "N", "G"], STANDARD_BIAS),
        ("D-11", "pos-neg-pos",      ["P", "G", "P"], STANDARD_BIAS),
        ("D-12", "neg-pos-neg",      ["G", "P", "G"], STANDARD_BIAS),
        # Group C: 4-phase
        ("D-14", "norm-pos-norm-neg",    ["N","P","N","G"], STANDARD_BIAS),
        ("D-15", "pos-norm-neg-norm",    ["P","N","G","N"], STANDARD_BIAS),
        ("D-16", "neg-pos-norm-neg",     ["G","P","N","G"], STANDARD_BIAS),
        # Group D: uneven (handled separately with custom phase lengths)
        # Group E: weak-bias
        ("D-22", "norm-weak-pos",   ["N", "P"], 1000),
        ("D-23", "norm-weak-neg",   ["N", "G"], 1000),
        ("D-24", "weak-neg-norm-weak-pos", ["G","N","P"], 1000),
        ("D-25", "mid-pos-norm-mid-neg",   ["P","N","G"], 2000),
    ]

    for nap, nsta in NAP_NSTA_MAP.items():
        seeds = get_available_seeds(data_root, "train", nap, nsta)
        for seed in seeds:
            if seed not in TRAIN_SEEDS:
                continue

            for pattern_id, pattern_name, phase_types, attack_bias in PATTERNS:
                total_windows = len(phase_types) * PHASE_LEN
                fname_sim_time = total_windows // 10

                if output_already_exists(output_dir, nap, nsta, seed,
                                         pattern_id, pattern_name, total_windows):
                    continue  # Real NS-3 file exists — skip

                # Resolve source files for each phase
                source_files = []
                source_offsets = []
                normal_file_uses = 0

                for i, phase_type in enumerate(phase_types):
                    if phase_type == "N":
                        src = get_source_file(data_root, "train", "Normal",
                                              nap, nsta, seed, 0)
                        # If this is the 2nd use of the normal file in the same pattern,
                        # use windows [0:400] instead of [200:600]
                        offset = 200 if normal_file_uses == 0 else 0
                        normal_file_uses += 1
                    elif phase_type == "P":
                        src = get_source_file(data_root, "train", "Attack",
                                              nap, nsta, seed, +attack_bias)
                        offset = 200
                    else:  # "G" = Negative
                        src = get_source_file(data_root, "train", "Attack",
                                              nap, nsta, seed, -attack_bias)
                        offset = 200

                    if src is None:
                        break  # Source file missing — skip this combination
                    source_files.append(src)
                    source_offsets.append(offset)
                else:
                    # All phases resolved
                    expected_biases = [0 if pt=="N" else
                                       +attack_bias if pt=="P" else
                                       -attack_bias
                                       for pt in phase_types]
                    phase_defs = list(zip(source_files, expected_biases))
                    phase_lengths = [PHASE_LEN] * len(phase_types)
                    output_path = os.path.join(
                        output_dir,
                        f"nap{nap}_nsta{nsta}_seed{seed}_{pattern_id}_"
                        f"{pattern_name}_{fname_sim_time}s.json"
                    )
                    stitch_synthetic_dynamic_file(
                        phase_defs, phase_lengths, output_path, source_offsets
                    )
```

### 9.1 Leakage Prevention Check (Pseudocode)

```python
def verify_no_leakage(train_dir: str, val_dir: str, test_dir: str) -> None:
    """
    Verify that no window from a train source appears in val or test synthetic files.
    Since split isolation is enforced by seed pools (mutually exclusive seeds),
    this check verifies that the seed embedded in each filename matches the expected pool.
    """
    TRAIN_SEEDS = {42, 111, 123, 222, 321, 333, 456, 654, 789, 987}
    VAL_SEEDS = {444, 777, 888}
    TEST_SEEDS = {555, 999, 1234}

    import re
    errors = []
    for split, dir_path, expected_seeds in [
        ("train", train_dir, TRAIN_SEEDS),
        ("val", val_dir, VAL_SEEDS),
        ("test", test_dir, TEST_SEEDS),
    ]:
        for fname in os.listdir(dir_path):
            m = re.search(r"seed(\d+)", fname)
            if m:
                seed = int(m.group(1))
                if seed not in expected_seeds:
                    # Check if it's a single-AP file (different seed range)
                    single_ap_train = set(range(100, 351)) | set(range(1, 13))
                    single_ap_val = set(range(351, 401)) | {13, 14}
                    single_ap_test = set(range(401, 423)) | {15}
                    expected_single_ap = {
                        "train": single_ap_train,
                        "val": single_ap_val,
                        "test": single_ap_test,
                    }[split]
                    if seed not in expected_single_ap:
                        errors.append(
                            f"LEAKAGE: {split}/{fname} has seed={seed} "
                            f"not in expected pool {expected_seeds | expected_single_ap}"
                        )
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        raise AssertionError("Leakage detected — see errors above")
    else:
        print("Leakage check passed: all seeds in correct pools")
```

---

## 10. Expected Dataset Sizes

### 10.1 Train Synthetic Dynamic Files

| Pattern group | Patterns | nap1 (10 seeds) | nap2 (10 seeds) | nap3 (8 seeds) | Bias variants | Total |
|---------------|----------|----------------|----------------|----------------|---------------|-------|
| A (2-phase) — missing D-03,04,05,06 | 4 patterns | 4×10=40 | 4×10=40 | 4×8=32 | ×3 (bias variants) | 336 |
| B (3-phase) — missing D-07–12 (D-09 partial) | 6 patterns | 6×10=60 | 6×10=60 | 6×8=48 | ×3 | 504 |
| C (4-phase) — missing D-14,15,16 | 3 patterns | 3×10=30 | 3×10=30 | 3×8=24 | ×3 | 252 |
| D (uneven) — D-17–21 all missing | 5 patterns | 5×10=50 | 5×10=50 | 5×8=40 | ×1 (±5000 only) | 140 |
| E (weak bias) — D-22–25 all missing | 4 patterns | 4×10=40 | 4×10=40 | 4×8=32 | ×1 (bias in name) | 112 |
| **Total new synthetic** | | | | | | **~1,344** |

Minus real files already present (D-01/D-02 all nap1-3 = ~26, D-13 partial ~18):
**Net new synthetic train files: ~1,300**

Combined with existing 46 real NS-3 train dynamic files:
**Total train Dynamic: ~1,346 files**

### 10.2 Val Synthetic Dynamic Files

Val sources: seeds 444 (nap1-4 but 444 is missing nap4 normal), 777 (nap1-4), 888 (nap1-4)
Val attacks: bias ±5000 only, nap1-4

Patterns for val (6 patterns from Groups A+B, balanced):
- D-03, D-04 (2-phase A→N), D-07, D-08 (N→A→N), D-09, D-10 (A→N→A)

| nap | Seeds with full data | Patterns | Files |
|-----|---------------------|----------|-------|
| nap1 | 777, 888 (444 has Normal) | 6 | 18 |
| nap2 | 777, 888 | 6 | 12 |
| nap3 | 777, 888 | 6 | 12 |
| nap4 | 777, 888 | 6 | 12 |

Minus real files (D-01/D-04 nap1-4 seeds 777/888 = 14 already present):
**Net new synthetic val files: ~54 - 14 = ~40**

### 10.3 Test Synthetic Dynamic Files

Test sources: seeds 555, 999, 1234 — nap1 and nap2 only; biases ±500,±1000,±2000,±4000,±5000

Test-only patterns T-01 to T-05 (5-phase, 2000 windows each):

| nap | Seeds | Patterns | Files |
|-----|-------|----------|-------|
| nap1 | 555, 999, 1234 | T-01 to T-05 | 3×5=15 |
| nap2 | 555, 999, 1234 | T-01 to T-05 | 3×5=15 |

Plus held-out bias test patterns (using weaker biases ±500, ±1000 from test Attack files):
- D-03 variant with bias=500: nap1+nap2, 3 seeds each = 6 files
- D-09 variant with bias=1000: nap1+nap2, 3 seeds = 6 files

**Net new synthetic test files: ~30 (T-patterns) + ~12 (bias variants) = ~42**

Minus real files (D-01/D-09 nap1-2 seeds 555/999/1234 = 9 already):
**Total test Dynamic: ~17 real + 42 new = ~59 files**

### 10.4 Grand Total

| Split | Static files | Dynamic (real) | Dynamic (synthetic) | Total |
|-------|-------------|----------------|---------------------|-------|
| Train | 193 (Normal+Attack) | 46 | ~1,300 | ~1,539 |
| Val | 50 (Normal+Attack) | 14 | ~40 | ~104 |
| Test | 65 (Normal+Attack) | 17 | ~42 | ~124 |
| **Grand Total** | **308** | **77** | **~1,382** | **~1,767** |

**Total windows (approximate):**
- Train: 193×800 + 46×1000 + 1300×1050 avg = 154,400 + 46,000 + 1,365,000 ≈ 1.57M windows
- Val: 50×800 + 54×1000 avg = 40,000 + 54,000 ≈ 94K windows
- Test: 65×800 + 59×1300 avg = 52,000 + 76,700 ≈ 129K windows
- **Grand total: ~1.79 million windows**

---

## 11. Handling Single-AP Sources (Optional Augmentation)

The single-AP datasets (pilot, extended, wifi7_gcn) can be used to augment training with additional normal-phase sources and a wider range of bias values (including bias=50, 100, 250 not present in v4 multi-AP).

### 11.1 Compatibility

- Single-AP files lack `num_ap`/`num_sta`. The stitcher injects `num_ap=1, num_sta=2` into each window dict before writing.
- Single-AP synthetic files use seeds from the single-AP train pool (100–350) which do NOT conflict with v4 multi-AP train seeds.
- The stitcher writes these to a separate sub-directory: `v4/train/Dynamic/SingleAP/` or includes them directly with a flag indicating their origin.

**Recommendation: Defer single-AP augmentation to a second phase.** The multi-AP synthetic dataset already provides ~1,300 new train files. Add single-AP files only if v4 model performance is insufficient on weak-bias detection after training on multi-AP data alone.

### 11.2 Seed Assignment for Single-AP Augmentation

| Split | Source seeds |
|-------|-------------|
| Train | Extended seeds 100–350, Pilot seeds 1–12 |
| Val | Extended seeds 351–400, Pilot seeds 13–14 |
| Test | Extended seeds 401–422, Pilot seed 15 |

### 11.3 Bias Availability for Single-AP

The extended dataset provides biases: ±50, ±100, ±250, ±500, ±1000, ±2500, ±5000, ±10000.
This enables additional Group E variants with very weak attacks (bias=±50, ±100) not possible with v4 multi-AP data.

### 11.4 Window Slice for 2000-Window Files

Single-AP files have 2000 windows. Use windows 500–1499 (1000 windows = 1 phase of 1000 windows, or split into 2 phases of 500 windows each):

```
Primary phase: source[500:900]   (400 windows)
Secondary phase: source[900:1300] (400 windows, non-overlapping with primary)
```

---

## 12. Validation Checks

The stitcher script must run the following checks before finalizing output:

### 12.1 Pre-Generation Validation

```
FOR each planned synthetic file:
  CHECK: output directory exists and is writable
  CHECK: all source files exist
  CHECK: each source file has constant bias throughout (all windows same bias)
  CHECK: source files have sufficient windows for the requested offset + phase_len
  CHECK: num_ap and num_sta are consistent across all source files for this synthetic file
  CHECK: no phase reuses windows already used in a prior phase (check offset ranges)
```

### 12.2 Post-Generation Validation

```
FOR each generated synthetic file:
  CHECK: total window count = sum of phase lengths
  CHECK: window field is sequential 0, 1, 2, ... N-1
  CHECK: bias values in the file match the expected phase sequence
  CHECK: transitions occur at the correct window indices (every PHASE_LEN windows)
  CHECK: num_ap and num_sta are present and consistent in all windows
  CHECK: all 16 standard fields (window, bias, num_ap, num_sta, 12 metric fields) are present
```

### 12.3 Leakage Validation

```
CHECK: filename seed of every synthetic file matches the seed pool for its split
CHECK: no source file used in val/test synthetic files comes from train split
CHECK: seeds used in val synthetic files are not in {train seeds}
CHECK: seeds used in test synthetic files are not in {train seeds} or {val seeds}
```

### 12.4 Dataset Statistics Report

After generation, produce a summary report:

```
Total files per split (train/val/test)
Total windows per split
Files by pattern group (A/B/C/D/E/T)
Files by nap count
Bias value distribution (for attack phases)
Percentage of transition segments (within ±256 windows of a transition point)
Class balance: Normal segments vs Attack segments (with dynamic_label_threshold=0.3)
```

---

## 13. Implementation Plan

### Phase 1: Implement the Stitcher Script (1 day)

**File to create:** `twin/gnn/training_data/stitch_dynamic.py`

**Core functions (do not write code — implement these):**
1. `stitch_synthetic_dynamic_file(phases, phase_lengths, output_path, source_offsets)`
2. `get_source_file(data_root, split, scenario, nap, nsta, seed, bias, sim_time=80)`
3. `output_already_exists(output_dir, nap, nsta, seed, pattern_id, pattern_name, total_windows)`
4. `generate_split(split, data_root, output_base_dir, patterns, nap_nsta_map, seeds, attack_biases, phase_len=400)`
5. `verify_no_leakage(train_dir, val_dir, test_dir)`
6. `validate_synthetic_file(path, expected_phase_biases, phase_len)`
7. `generate_dataset_report(base_dir)`

**CLI interface:**
```bash
python twin/gnn/training_data/stitch_dynamic.py \
    --data-root twin/gnn/training_data/v4 \
    --output-root twin/gnn/training_data/v4 \
    --split train   # or val, test, or all
    --patterns A,B,C,D,E  # or T for test-only
    --dry-run       # show what would be generated without writing
    --skip-existing # skip files already present (default: True)
```

### Phase 2: Generate Train Split (2–3 hours)

```bash
python twin/gnn/training_data/stitch_dynamic.py \
    --data-root twin/gnn/training_data/v4 \
    --split train \
    --patterns A,B,C,D,E
```

Expected time: ~5 minutes (pure Python file I/O, no simulation).

### Phase 3: Generate Val and Test Splits

```bash
python twin/gnn/training_data/stitch_dynamic.py --split val --patterns A,B
python twin/gnn/training_data/stitch_dynamic.py --split test --patterns T
python twin/gnn/training_data/stitch_dynamic.py --split test --patterns A --bias-variants 500,1000
```

### Phase 4: Validate and Report

```bash
python twin/gnn/training_data/stitch_dynamic.py --validate-only
```

Checks leakage, window continuity, bias field correctness.

### Phase 5: Run GCN v4 Training with Augmented Dataset

After synthetic dataset is verified, run training:

```bash
make gcn-train-v4 OUTPUT_DIR=twin/registry/gcn/v4.0.0
```

The `run_training_v4.py` and `dataset_v4.py` already handle `Dynamic/` folder files. No code changes needed to the training pipeline.

---

## 14. Files to Create / Modify

| File | Action | Purpose |
|------|--------|---------|
| `twin/gnn/training_data/stitch_dynamic.py` | **Create** | The stitcher script |
| `twin/gnn/training_data/validate_dataset.py` | **Create** | Leakage and format checker |
| `Makefile` | **Modify** | Add `gcn-stitch-dynamic` and `gcn-validate-dataset` targets |
| `docs/WP13-SYNTHETIC-DYNAMIC-DATASET-PLAN.md` | This file | Reference document |

No changes to: `dataset_v4.py`, `preprocessing.py`, `train_v4.py`, `run_training_v4.py`. These already support `Dynamic/` folder files.

---

## 15. Makefile Targets (Specification)

```makefile
V4_DATA_DIR ?= twin/gnn/training_data/v4

# Generate synthetic dynamic training data by stitching static windows
gcn-stitch-dynamic:
    python twin/gnn/training_data/stitch_dynamic.py \
        --data-root $(V4_DATA_DIR) \
        --split $(SPLIT) \
        --patterns $(PATTERNS)

# Validate the entire v4 dataset (leakage + format checks)
gcn-validate-dataset:
    python twin/gnn/training_data/validate_dataset.py \
        --data-root $(V4_DATA_DIR)

# Generate all splits at once
gcn-stitch-all:
    make gcn-stitch-dynamic SPLIT=train PATTERNS=A,B,C,D,E
    make gcn-stitch-dynamic SPLIT=val PATTERNS=A,B
    make gcn-stitch-dynamic SPLIT=test PATTERNS=T,A
    make gcn-validate-dataset
```

---

## 16. ADR Candidates

The following decisions made in this plan warrant documentation as Architecture Decision Records before implementation:

| Decision | Options Considered | Recommendation |
|----------|-------------------|----------------|
| **ADR-WP13-SYN-01:** Synthetic vs real for dynamic data | Real NS-3 only / Synthetic stitching / Both | Both: real files first, synthetic augments |
| **ADR-WP13-SYN-02:** Phase length (number of windows per phase) | 256 (one segment), 400 (half-file), 800 (full file) | 400 — avoids overlap with any segment boundary, maximizes diversity |
| **ADR-WP13-SYN-03:** Source window offset (where in source file to slice) | Start (index 0), Middle (index 200), End | Middle (200–599) — avoids sim warm-up and wind-down artifacts |
| **ADR-WP13-SYN-04:** Same-file reuse for multi-normal patterns | Forbidden / Allowed with non-overlapping offsets | Allowed with offsets 200 (first use) and 0 (second use) |
| **ADR-WP13-SYN-05:** Single-AP data inclusion | Include in phase 1 / Defer to phase 2 / Exclude | Defer: multi-AP data is sufficient; add only if weak-bias detection fails |
| **ADR-WP13-SYN-06:** Bias variants in train | Single bias (±5000) / Three biases (±1000,±2000,±5000) | Three biases — matches existing Static Attack data |

---

## 17. Potential Issues and Mitigations

| Issue | Mitigation |
|-------|-----------|
| v4 train nap3 missing seeds 222 and 333 (only 8 seeds, not 10) | Already documented; generate only for the 8 available seeds |
| v4 val nap4 normal missing seed 444 (only 777 and 888) | Only generate val nap4 files for seeds 777 and 888 |
| v4 test Static has only nap1 and nap2 | Test synthetic files are nap1 and nap2 only |
| Warm-up windows (first ~10 windows have many zeros) | Offset of 200 avoids this |
| Real NS-3 files use offset 399 for 80s transition (not 400) | The stitcher uses clean 400-window phases. Real files may use 399/401 split. No conflict because real files are never replaced. |
| Pattern D-09 (neg-norm-pos) exists in test but also needed in train | Generate train version from train seeds (42,123,...) independently from test version (seeds 555,999,1234). No overlap. |
| Group D uneven patterns may leave a short final slice | Validate that source files have enough windows for the offset + phase_len combination |
| Single-AP `num_ap`/`num_sta` field injection | Stitcher injects `num_ap=1, num_sta=2` for files from pilot/extended sources |
| Large number of synthetic files (~1,300+) may slow training data loading | PyG dataset caching mitigates this. Monitor dataset loading time before training. |
| val Attack only has bias=±5000 — val dynamic files have limited attack bias diversity | Acceptable: val is for monitoring generalization during training, not for testing |

---

## 18. Related Documents

- `docs/WP13-GCN-V4-DYNAMIC-TRAINING-PLAN.md` — overall WP13 plan; this document specifies the synthetic data strategy
- `twin/gnn/detector/gcn_src/data/dataset_v4.py` — dataset loader; handles `Dynamic/` folder automatically
- `twin/gnn/detector/gcn_src/data/preprocessing.py` — `get_label_from_segment_dynamic()`, `extract_features()`
- `twin/gnn/trainer/training_v4.yaml` — training configuration
- `twin/gnn/detector/run_training_v4.py` — training entrypoint
- `sim/ns3/scenario/collect_v4_dynamic_data.sh` — real NS-3 dynamic generator (complementary to synthetic)
- `.claude/docs/context/current-session.md` — session context

---

*Plan date: 2026-03-15*
*Researcher: Planner agent*
*Ready for implementation: Yes — all source files verified, algorithm specified, no open questions*
