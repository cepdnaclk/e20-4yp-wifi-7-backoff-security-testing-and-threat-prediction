# Implementation Plan: stitch_dynamic.py

## Date
2026-03-15

## Objective

Implement `twin/gnn/training_data/stitch_dynamic.py` — a script that synthesises dynamic
training files for GCN v4 by concatenating 400-window slices from existing static simulation
files. Each output file contains 2–5 phases with distinct bias values, separated by sharp
transitions. The script populates `v4/train/Dynamic/`, `v4/val/Dynamic/`, and
`v4/test/Dynamic/` without running any new NS-3 simulations.

## Background

WP13 requires dynamic training data (files where the attack bias changes mid-simulation) to
teach the GCN detector to handle phase transitions. The dataset plan
(`docs/WP13-SYNTHETIC-DYNAMIC-DATASET-PLAN.md`) specifies 30 phase patterns and ~1,382 new
synthetic files. The training pipeline (`dataset_v4.py`) already handles `Dynamic/` folder
files via majority-vote per-segment labeling — no pipeline changes are needed, only the data
generation script.

---

## Precise Data Inventory (Ground Truth from Filesystem)

### Window format (all v4 static files, 800 windows each)
```
Fields: window, bias, num_ap, num_sta, net_throughput_mbps, net_avg_delay_ms,
        net_avg_jitter_ms, net_packet_loss_ratio, net_active_flows, mac_total_tx,
        mac_total_rx, mac_total_ack, mac_total_retrans, mac_drop_count, phy_drop_count,
        avg_backoff_slots, channel_busy_ratio
```
- `window` is a sequential 0-based integer (0–799 in static files).
- `bias` is constant throughout static files (0 for Normal, nonzero for Attack).
- `mac_total_tx` and all `mac_total_*` fields are NOT cumulative across the simulation —
  they are already zero in the last window of an 80s file (observed: mac_total_tx=0 at
  window 799). Delta computation in `convert_to_deltas()` is a no-op for these fields in
  practice. Stitching therefore does NOT introduce counter discontinuities: each source
  slice already starts from low/zero cumulative values.

### Train split — complete (nap, nsta, seed) inventory
| Topology | Seeds with Normal | Seeds with Attack | Attack biases available |
|----------|-------------------|-------------------|------------------------|
| nap1/nsta2 | 42,111,123,222,321,333,456,654,789,987 (10) | same 10 | +/-1000, +/-2000, +/-5000 |
| nap2/nsta4 | 42,111,123,222,321,333,456,654,789,987 (10) | same 10 | +/-1000, +/-2000, +/-5000 |
| nap3/nsta2 | 42,111,123,321,456,654,789,987 (8) | same 8 | seed111: +1000,+2000,+5000 only; all others: +/-1000,+/-2000,+/-5000 |
| nap4 | NO train static files | NO train static files | — |

**Critical edge case:** `nap3/nsta2/seed111` has ONLY positive attack files (+1000, +2000,
+5000). No negative attack file exists for this seed+topology. The stitcher must skip any
pattern requiring a negative phase for this combination (D-02, D-04, D-05, D-06, D-08,
D-09, D-10, D-11, D-12, D-14, D-15, D-16, D-19, D-23, D-24, D-25 negative variants).

### Val split — complete inventory
| Topology | Seeds with Normal | Seeds with Attack | Attack biases |
|----------|-------------------|-------------------|---------------|
| nap1/nsta2 | 444, 777, 888 | 444, 777, 888 | +/-5000 |
| nap2/nsta4 | 444, 777, 888 | 444, 777, 888 | +/-5000 |
| nap3/nsta2 | 444, 777, 888 | 444, 777, 888 | +/-5000 |
| nap3/nsta6 | 444, 777, 888 | 444, 777, 888 | +/-5000 |
| nap4/nsta2 | 444, 777, 888 | 444, 777, 888 | +/-5000 |
| nap4/nsta8 | 777, 888 only (no 444) | 777 (both signs); 888 (positive only) | +/-5000 for 777; +5000 only for 888 |

**Critical edge cases in val:**
- `nap4/nsta8/seed444`: no Normal file, no Attack files — cannot generate any synthetic files.
- `nap4/nsta8/seed888`: only `positive5000` attack, no negative — skip negative-phase patterns.
- `nap4/nsta8/seed777`: has both signs, fully usable.

### Test split — complete inventory
| Topology | Seeds with Normal | Seeds with Attack | Attack biases |
|----------|-------------------|-------------------|---------------|
| nap1/nsta2 | 555, 999, 1234 | 555, 999, 1234 | +/-500, +/-1000, +/-2000, +/-4000, +/-5000 |
| nap2/nsta4 | 555, 999, 1234 | 555, 999, 1234 | +/-1000, +/-2000, +/-4000, +5000 (555/999/1234); nap2/seed1234 missing -5000 |
| nap3, nap4 | NO test static files | NO test static files | — |

**Critical edge case in test:** `nap2/nsta4/seed1234` is missing `negative5000` attack file.
The stitcher must check file existence at runtime rather than assuming the full bias matrix
is complete.

### Existing real Dynamic files (must be preserved — stitcher must skip these exactly)
| Split | Count | Patterns present | Key detail |
|-------|-------|-----------------|------------|
| train | 46 | D-01 (28 files), D-02 (6 files), D-13 (12 files) | D-01 exists for seeds 42,123,321,456,654,789 across nap1,nap2,nap3/nsta2,nap3/nsta6,nap4/nsta2 |
| val | 14 | D-01 (10 files), D-04 (4 files) | D-01 for nap1-4, seeds 777,888; D-04 for nap1-2, seeds 777,888 |
| test | 17 | D-01 (14 files), D-09 (3 files) | D-01 for nap1-2, all 3 seeds; D-09 for nap1, seeds 1234,555,999 |

The skip-existing check must match the exact filename convention used by real files.

---

## Key Design Decisions (from the plan — implement exactly as specified)

### Phase slice convention
- Source files have 800 windows (0-indexed 0–799).
- Primary phase (first use of a source file): slice `source[200:600]` → 400 windows.
- Secondary phase (second use of the same normal source file in one synthetic file):
  use `source[0:200] + source[600:800]` → two contiguous 200-window segments concatenated
  to form a single 400-window phase. This is the non-overlapping strategy specified in
  section 7.1 of the plan. NOTE: The pseudocode in section 9 uses `offset=0` which would
  produce `source[0:400]` — this OVERLAPS with `source[200:600]` at indices 200-399.
  **Resolution for implementation:** use the non-overlapping strategy from section 7.1:
  concatenate `source[0:200]` and `source[600:800]`. This avoids window-level duplication
  within a single synthetic file.

### Window renumbering
- The `window` field must be rewritten as a sequential 0-based integer across the full
  synthetic file, regardless of what the source file's `window` field contained.
- All other fields (including `bias`, `num_ap`, `num_sta`, and all metric fields) are
  copied verbatim from the source window.

### Cumulative counter behavior
- `mac_total_tx`, `mac_total_rx`, etc. are already near zero at all points in the 80s
  static source files (observed: mac_total_tx=0 at window 799). No counter reset or
  adjustment is needed when stitching phases together. The `convert_to_deltas()` function
  in `preprocessing.py` will compute correct deltas at training time because each window
  already stores the absolute cumulative value and the delta is taken between adjacent
  windows within the loaded JSON list.
- Consequence: there is a "jump" in cumulative values at phase boundaries (from near-zero
  at end of phase N to near-zero at start of phase N+1 sliced from a different file).
  This is intentional — the delta across a transition boundary will be small because both
  sides are near zero, which is actually correct behavior (the bias change, not a counter
  jump, is the signal).

### Bias field
- Copied verbatim from the source file. No modification needed.
- The dataset loader uses `bias` per-window for majority-vote labeling.

### num_ap and num_sta fields
- Copied verbatim from source file. All phases of one synthetic file must come from
  sources with the same `num_ap` and `num_sta`. The stitcher enforces this.
- Single-AP augmentation (from pilot/extended datasets) is deferred — not implemented
  in this script.

---

## Files to Create / Modify

| File | Action | Purpose |
|------|--------|---------||
| `twin/gnn/training_data/stitch_dynamic.py` | **Create** | Main stitcher script |
| `twin/gnn/training_data/validate_dataset.py` | **Create** | Post-generation leakage + format checker |
| `Makefile` | **Modify** | Add `gcn-stitch-dynamic`, `gcn-validate-dataset`, `gcn-stitch-all` targets |

No changes to: `dataset_v4.py`, `preprocessing.py`, `train_v4.py`, `run_training_v4.py`.

---

## Implementation Steps

### Step 1: Core stitching function
**File:** `twin/gnn/training_data/stitch_dynamic.py`

Implement `stitch_synthetic_dynamic_file(phases, phase_lengths, output_path, source_offsets=None)`.

Where:
- `phases`: list of `(source_path: Path, expected_bias: int)` tuples
- `phase_lengths`: list of ints (400 per phase for standard patterns)
- `output_path`: Path to write the output JSON
- `source_offsets`: list of ints OR list of `(start, end)` tuples for non-contiguous slices

The function must:
1. For each phase: open the source JSON file, validate the bias of all windows in the
   requested slice is uniform and equals `expected_bias`, then collect the windows.
2. For normal-phase second use: collect windows as two sub-slices
   `source[0:200]` + `source[600:800]`, concatenated in memory, then renumber.
3. Renumber the global `window` field sequentially from 0 across the entire output file.
4. Write the result as a JSON array to `output_path`. Use `json.dump(result, f)` —
   no indentation, compact format to keep file sizes reasonable.
5. Raise a descriptive error (not `assert`) if any validation fails — callers will log
   and continue rather than crash.

**Verification:** After the function runs on one test case, open the output and confirm:
- `len(output) == sum(phase_lengths)`
- `output[0]['window'] == 0`, `output[-1]['window'] == len(output)-1`
- Bias values are correct per phase
- `num_ap` and `num_sta` are consistent throughout

### Step 2: Source file resolver
**File:** `twin/gnn/training_data/stitch_dynamic.py`

Implement `get_source_file(data_root: Path, split: str, nap: int, nsta: int, seed: int, bias: int) -> Optional[Path]`.

Where `bias=0` means Normal, positive means positive attack, negative means negative attack.

The filename pattern (confirmed from actual filesystem):
- Normal: `nap{nap}_nsta{nsta}_seed{seed}_normal_80s.json`
- Attack positive: `nap{nap}_nsta{nsta}_seed{seed}_positive{abs(bias)}_80s.json`
- Attack negative: `nap{nap}_nsta{nsta}_seed{seed}_negative{abs(bias)}_80s.json`

Returns `None` if file does not exist. Callers check for `None` and skip the combination.

**Verification:** Call with each known combination from the inventory above and confirm
all files resolve to existing paths. Call with `nap=4, seed=42, split='train'` (which
has no static train files) and confirm it returns `None`.

### Step 3: Output existence checker
**File:** `twin/gnn/training_data/stitch_dynamic.py`

Implement `output_file_exists(output_dir: Path, nap: int, nsta: int, seed: int, pattern_id: str, pattern_name: str, total_windows: int) -> bool`.

The filename convention for synthetic output files:
```
nap{nap}_nsta{nsta}_seed{seed}_{pattern_id}_{pattern_name}_{sim_time}s.json
```
where `sim_time = total_windows // 10` (800 windows → 80s, 1200 → 120s, 1600 → 160s, 2000 → 200s).

This function checks both the exact file and also any file matching the pattern
`*_seed{seed}_{pattern_id}_*` in case the name was generated with slightly different
bias-variant suffixes. For simplicity, only check the exact filename as computed above.

Real files use the same convention (e.g., `nap1_nsta2_seed42_D-01_norm-pos_80s.json`),
so the function correctly skips them.

**Verification:** Call with `nap=1, nsta=2, seed=42, pattern_id='D-01', pattern_name='norm-pos', total_windows=800` pointing at the train Dynamic dir — should return `True` (real file exists).

### Step 4: Phase pattern catalogue
**File:** `twin/gnn/training_data/stitch_dynamic.py`

Define a data structure (list of dicts or namedtuples) holding all phase patterns.
Each pattern entry needs:
- `pattern_id`: e.g., `"D-03"`
- `pattern_name`: e.g., `"pos-norm"` (matches filename convention)
- `phases`: list of phase types, each one of `"N"` (Normal), `"P"` (Positive attack),
  `"G"` (neGative attack)
- `bias_magnitude`: the magnitude of the attack bias for this pattern (5000 for standard,
  1000 or 2000 for weak-bias Group E patterns)

The full list of patterns to generate (excluding those already fully covered by real files):

**Group A — 2-phase (800 windows, 80s):**
- D-01: `norm-pos`, [N,P], bias=5000 — skip where real file exists, generate rest
- D-02: `norm-neg`, [N,G], bias=5000 — skip where real file exists, generate rest
- D-03: `pos-norm`, [P,N], bias=5000
- D-04: `neg-norm`, [G,N], bias=5000 — skip where real val file exists
- D-05: `pos-neg`, [P,G], bias=5000
- D-06: `neg-pos`, [G,P], bias=5000

**Group B — 3-phase (1200 windows, 120s):**
- D-07: `norm-pos-norm`, [N,P,N], bias=5000
- D-08: `norm-neg-norm`, [N,G,N], bias=5000
- D-09: `neg-norm-pos`, [G,N,P], bias=5000 — skip where real test file exists
- D-10: `pos-norm-neg`, [P,N,G], bias=5000
- D-11: `pos-neg-pos`, [P,G,P], bias=5000
- D-12: `neg-pos-neg`, [G,P,G], bias=5000

**Group C — 4-phase (1600 windows, 160s):**
- D-13: `neg-norm-pos-norm`, [G,N,P,N], bias=5000 — skip where real file exists
- D-14: `norm-pos-norm-neg`, [N,P,N,G], bias=5000
- D-15: `pos-norm-neg-norm`, [P,N,G,N], bias=5000
- D-16: `neg-pos-norm-neg`, [G,P,N,G], bias=5000

**Group D — uneven phases (phase lengths NOT all 400):**
- D-17: `neg-norm-uneven`, [G,N], phase_lengths=[267,533], bias=5000
- D-18: `norm-pos-uneven`, [N,P], phase_lengths=[533,267], bias=5000
- D-19: `neg-norm-pos-uneven`, [G,N,P], phase_lengths=[300,400,500], bias=5000
- D-20: `pos-neg-early`, [P,G], phase_lengths=[150,650], bias=5000
- D-21: `norm-neg-narrow`, [N,G,N], phase_lengths=[300,200,300], bias=5000

**Group E — weak bias (2-3 phase, bias=1000 or 2000, train-only):**
- D-22: `norm-weak-pos`, [N,P], bias=1000, phase_lengths=[400,400]
- D-23: `norm-weak-neg`, [N,G], bias=1000, phase_lengths=[400,400]
- D-24: `weak-neg-norm-weak-pos`, [G,N,P], bias=1000, phase_lengths=[400,400,400]
- D-25: `mid-pos-norm-mid-neg`, [P,N,G], bias=2000, phase_lengths=[400,400,400]

**Group T — test-only, 5-phase (2000 windows, 200s):**
- T-01: `norm-neg-norm-pos-norm`, [N,G,N,P,N], bias=5000, test split only
- T-02: `pos-norm-pos-neg-norm`, [P,N,P,G,N], bias=5000, test split only
- T-03: `neg-norm-neg-pos-neg`, [G,N,G,P,G], bias=5000, test split only
- T-04: `pos-neg-pos-norm-neg`, [P,G,P,N,G], bias=5000, test split only
- T-05: `norm-pos-neg-pos-norm`, [N,P,G,P,N], bias=5000, test split only

**Train bias variants:** For train split only, patterns D-01 through D-16 should be
generated with 3 variants for each combination: bias=1000, bias=2000, bias=5000. The
default (no suffix) uses bias=5000. Variants use suffixes `_b1000` and `_b2000` in the
pattern name. Example:
```
nap1_nsta2_seed42_D-03_pos-norm_80s.json          # bias=5000 (default)
nap1_nsta2_seed42_D-03_pos5000-norm_80s.json       # same, explicit name OK
nap1_nsta2_seed42_D-03b_pos2000-norm_80s.json      # bias=2000 variant
nap1_nsta2_seed42_D-03c_pos1000-norm_80s.json      # bias=1000 variant
```
Only generate bias=1000 and bias=2000 variants for train. Val/test use bias=5000 only
(since val/test attack files only have bias=5000).

**WARNING on bias variant naming:** The exact naming convention for bias variants is
partially specified in the plan (section 7.3) but needs to be nailed down before
implementation. Recommend: use `_b{bias}` suffix on the pattern name for non-5000 bias.
E.g., `D-03_pos-norm-b2000_80s.json`. The exact choice must be consistent so the
skip-existing check works correctly.

### Step 5: Normal-source reuse (multi-normal phase patterns)
**File:** `twin/gnn/training_data/stitch_dynamic.py`

For patterns that have two or more Normal phases (D-07, D-08, D-09, D-12, D-13, D-14,
D-15, D-16, D-21, T-01, T-02, T-03, T-04, T-05), the same normal source file is used
for all Normal phases. The slices must be non-overlapping:

- First Normal phase in the pattern → windows `source[200:600]` (400 windows)
- Second Normal phase in the pattern → windows `source[0:200]` + `source[600:800]`
  (concatenated in memory to form 400 windows)
- If a third Normal phase is needed (T-patterns with 3 Normal phases): this would require
  windows that overlap with the first and second uses. Since 800-window sources cannot
  provide 3 non-overlapping 400-window slices, use a different strategy for a third Normal
  phase: use the same slice as the first use (source[200:600]). The repeated windows are
  acceptable for a third occurrence because in 5-phase files the model needs the normal
  signal, not uniqueness.

The implementation must track, per synthetic file being generated, how many times each
source file has been used as a Normal phase and select the appropriate slice.

**Verification:** Open a generated D-07 (norm-pos-norm) file and confirm:
- Windows 0–399 have `bias=0` (normal phase 1)
- Windows 400–799 have `bias=5000` (pos phase)
- Windows 800–1199 have `bias=0` (normal phase 2)
- Windows 0–399 and 800–1199 have NO window indices in common from the source file
  (check the source window field values — phase 1 has source windows 200–599, phase 3
  has source windows 0–199 and 600–799)

### Step 6: Per-split generator function
**File:** `twin/gnn/training_data/stitch_dynamic.py`

Implement `generate_split(split: str, data_root: Path, output_base_dir: Path, patterns: list, dry_run: bool = False) -> dict`.

Returns a summary dict `{"generated": N, "skipped_existing": N, "skipped_missing_source": N, "errors": N}`.

The function iterates:
```
for each (nap, nsta) topology available in that split:
  for each seed in the available seeds for that topology:
    for each pattern in patterns:
      for each bias_magnitude (1 for val/test ±5000; 3 for train ±1000,±2000,±5000):
        check output_file_exists → skip if True
        resolve all source files via get_source_file → skip if any returns None
        if not dry_run: call stitch_synthetic_dynamic_file(...)
        log result
```

The topology+seed loop MUST be driven by what actually exists in the Static/Normal
directory, not by hardcoded seed lists. Use `get_source_file()` with `bias=0` to check
if a normal source exists.

**Why filesystem-driven rather than hardcoded:** The inventory above shows unexpected
absences (nap3/nsta2/seed111 missing negative, nap4/nsta8/seed444 missing entirely,
nap2/nsta4/seed1234 missing negative5000). Filesystem-driven resolution handles these
without special-casing.

### Step 7: Post-generation file validator
**File:** `twin/gnn/training_data/validate_dataset.py`

Implement `validate_synthetic_file(path: Path, verbose: bool = False) -> list[str]`.

Returns a list of error strings (empty = OK). Checks:
1. File is valid JSON array.
2. `window` field is sequential: `[w["window"] for w in data] == list(range(len(data)))`.
3. All 16 required fields are present in every window.
4. `num_ap` and `num_sta` are consistent across all windows.
5. Bias transitions only occur on expected multiples of the phase length (400 for standard
   patterns). This check is best-effort: detect the transition points and verify they are
   at multiples of 200 (divisor is 200 not 400 to account for uneven Group D patterns).
6. Total window count is consistent with the filename's `{N}s` suffix (N×10 = window count).

Also implement `verify_no_leakage(v4_root: Path) -> list[str]`:
- For each file in each Dynamic split directory, extract the seed from the filename.
- Verify the seed is in the expected pool for that split:
  - train: {42,111,123,222,321,333,456,654,789,987}
  - val: {444,777,888}
  - test: {555,999,1234}

### Step 8: CLI interface
**File:** `twin/gnn/training_data/stitch_dynamic.py`

```
python twin/gnn/training_data/stitch_dynamic.py \
    --data-root twin/gnn/training_data/v4 \
    --split train|val|test|all \
    --patterns A,B,C,D,E,T      (default: all appropriate for split) \
    --dry-run                   (print what would be generated, write nothing) \
    --skip-existing             (default True; set False to regenerate) \
    --bias-variants             (default True for train, False for val/test)
```

The `--patterns T` flag is only active when `--split test`.
The `--patterns D,E` flag is only active when `--split train` (Groups D and E need
bias values only available in train).

### Step 9: Makefile targets
**File:** `Makefile`

```makefile
V4_DATA_DIR ?= twin/gnn/training_data/v4

gcn-stitch-dynamic:
    python twin/gnn/training_data/stitch_dynamic.py \
        --data-root $(V4_DATA_DIR) \
        --split $(SPLIT) \
        --patterns $(PATTERNS)

gcn-validate-dataset:
    python twin/gnn/training_data/validate_dataset.py \
        --data-root $(V4_DATA_DIR)

gcn-stitch-all:
    $(MAKE) gcn-stitch-dynamic SPLIT=train PATTERNS=A,B,C,D,E
    $(MAKE) gcn-stitch-dynamic SPLIT=val   PATTERNS=A,B
    $(MAKE) gcn-stitch-dynamic SPLIT=test  PATTERNS=T,A
    $(MAKE) gcn-validate-dataset
```

---

## Integration Points

- **`dataset_v4.py`**: reads `Dynamic/*.json` files from each split directory. The
  `_is_dynamic()` method checks for a `Dynamic` component in the file path. The
  `_preprocess_files()` method calls `convert_to_deltas()` then `segment_windows()` then
  `get_label_from_segment_dynamic()` — all of which work correctly on stitched files
  without any changes.
- **`preprocessing.py`**: `convert_to_deltas()` computes deltas between adjacent windows.
  At phase transitions, the delta will reflect the actual value difference between the
  last window of phase N and first window of phase N+1. Given that cumulative counters
  are near-zero throughout 80s files, this delta will be small and non-negative, which
  is fine.
- **`extract_features()`**: reads `num_ap` and `num_sta` from `windows[0]`. Since all
  phases use the same topology source, these fields are consistent.
- **`run_training_v4.py`**: calls `load_v4_files(data_root)` which globs `Dynamic/*.json`.
  No changes needed.

---

## Testing Strategy

- [ ] Dry-run the stitcher for train split, count planned files: `make gcn-stitch-dynamic SPLIT=train PATTERNS=A --dry-run`
- [ ] Generate a small subset (train, Pattern A only, nap1 only): confirm 6 files produced per seed (D-01 through D-06, 3 bias variants) minus real-file skips
- [ ] Manually inspect one generated file: check window count, bias pattern, sequential window field, num_ap/nsta consistency
- [ ] Run `make gcn-validate-dataset` and confirm zero errors
- [ ] Run `make gcn-stitch-all` and compare file counts against the expected numbers in Section 10 of the plan
- [ ] Verify no new files appear in val/Dynamic with train seeds: `ls twin/gnn/training_data/v4/val/Dynamic/ | grep -E 'seed(42|111|123|222|321|333|456|654|789|987)'` → should produce no output
- [ ] Import the generated files in Python via `load_v4_files()` and call `create_v4_datasets_with_scaler()` to confirm no loading errors

---

## Potential Issues and Resolutions

| Issue | Resolution |
|-------|------------|
| `nap3/nsta2/seed111` has no negative attack file | `get_source_file()` returns `None`; generator skips silently and logs |
| `nap4/nsta8/seed888` has no negative5000 file | Same: `None` return, skip |
| `nap4/nsta8/seed444` has no Normal or Attack | Same: source resolver returns `None` for Normal, skip entire seed |
| Plan section 9 pseudocode says `offset=0` for second normal use (creates 200-window overlap with first use at indices 200-399) | Use non-overlapping strategy from section 7.1: `source[0:200]` + `source[600:800]`. Implement as a helper that returns a combined list. |
| `nap2/nsta4/seed1234` missing `negative5000` in test | Filesystem check at runtime handles this gracefully |
| D-01 and D-02 already partially exist in train (only 6 of 10 seeds for each nap) | `output_file_exists()` returns True for existing seeds; generator produces the 4 missing seeds per nap automatically |
| Bias variant naming convention not fully specified | Standardize on: default (bias=5000) uses plain pattern name; bias=2000 appends `b` suffix to pattern_id; bias=1000 appends `c` suffix. E.g., `D-03`, `D-03b`, `D-03c` |
| Group T patterns (5-phase) need 3 Normal phases from one 800-window file | Third use repeats first slice (source[200:600]). Document as acceptable because the two normal phases surrounding the third are different source positions |
| Test split nap4/nsta8 has no Static files — plan section 10.3 says test is nap1+nap2 only | Confirmed: test Static has only nap1/nsta2 and nap2/nsta4. The filesystem-driven loop naturally produces no test files for nap3/nap4 |

---

## ADR Candidates

These decisions must be documented as ADRs before or immediately after implementation:

- **ADR-WP13-SYN-04:** Second-use normal source slice strategy — options are `[0:400]`
  (overlapping, simpler) vs `[0:200]+[600:800]` (non-overlapping, more correct).
  Recommend the non-overlapping strategy and document why.
- **ADR-WP13-SYN-06:** Bias variant naming convention — how to name D-03b vs D-03c files.
  Must be decided before implementation starts since it determines the skip-existing
  filename check.

The other 4 ADR candidates (SYN-01 through SYN-05 excluding SYN-04 and SYN-06) are
already decided in the plan document and can be written as ADRs by the parent agent
after implementation.

---

## Related Documentation

- `/home/cobrakali/github/ndt-wifi7-mlo-security/docs/WP13-SYNTHETIC-DYNAMIC-DATASET-PLAN.md` — full specification (sections 6, 7, 8, 9, 13 most critical)
- `/home/cobrakali/github/ndt-wifi7-mlo-security/twin/gnn/detector/gcn_src/data/dataset_v4.py` — consumer of the generated files; read before implementing to understand labeling
- `/home/cobrakali/github/ndt-wifi7-mlo-security/twin/gnn/detector/gcn_src/data/preprocessing.py` — `convert_to_deltas()` is called on stitched file contents at training time

---

## Answers to Research Questions

### 1. Exact filenames and naming pattern in train/Static/Normal

Format: `nap{N}_nsta{M}_seed{S}_normal_80s.json`

All 28 train normal files:
- nap1/nsta2: seed42, seed111, seed123, seed222, seed321, seed333, seed456, seed654, seed789, seed987 (10 files)
- nap2/nsta4: seed42, seed111, seed123, seed222, seed321, seed333, seed456, seed654, seed789, seed987 (10 files)
- nap3/nsta2: seed42, seed111, seed123, seed321, seed456, seed654, seed789, seed987 (8 files — NO seed222 or seed333)

### 2. Seeds with BOTH normal and all attack files in train, by nap

| nap/nsta | Seeds with full pos+neg coverage | Seeds with only positive | Seeds with no negative |
|----------|----------------------------------|--------------------------|------------------------|
| nap1/nsta2 | 42,111,123,222,321,333,456,654,789,987 (all 10) | — | — |
| nap2/nsta4 | 42,111,123,222,321,333,456,654,789,987 (all 10) | — | — |
| nap3/nsta2 | 42,123,321,456,654,789,987 (7 seeds) | 111 (positive only) | seed111 (missing neg) |

### 3. Bias values available in train/Static/Attack

- nap1/nsta2 and nap2/nsta4: +1000, +2000, +5000, -1000, -2000, -5000 (6 biases per seed)
- nap3/nsta2: +1000, +2000, +5000, -1000, -2000, -5000 for seeds 42,123,321,456,654,789,987;
  ONLY +1000, +2000, +5000 for seed111

### 4. Files in val and test static directories

Val: 17 Normal + 33 Attack = 50 static files
- Topologies: nap1/nsta2, nap2/nsta4, nap3/nsta2, nap3/nsta6, nap4/nsta2, nap4/nsta8
- Seeds: 444, 777, 888 (but nap4/nsta8 only has 777 and 888)
- Attack bias: ±5000 only (except nap4/nsta8/seed888 has only +5000)

Test: 6 Normal + 59 Attack = 65 static files
- Topologies: nap1/nsta2 and nap2/nsta4 ONLY
- Seeds: 555, 999, 1234
- Attack biases: ±500, ±1000, ±2000, ±4000, ±5000 for most; nap2/seed1234 missing -5000

### 5. Dynamic files already existing (to be skipped)

Train Dynamic (46 real files):
- D-01 (28 files): nap1/nsta2/seed{42,123,321,456,654,789}, nap2/nsta4/seed{same}, nap3/nsta2/seed{same}, nap3/nsta6/seed{123,42,456,789}, nap4/nsta2/seed{42,123,321,456,654,789}
- D-02 (6 files): nap1/nsta2/seed{42,123,456,654,789,321} — the same 6 seeds as nap1 D-01, only nap1
- D-13 (12 files): nap1/nsta2, nap2/nsta4, nap3/nsta2 × seeds{42,123,456,789}

Val Dynamic (14 real files):
- D-01 (10): nap1-4, seeds 777 and 888
- D-04 (4): nap1 and nap2, seeds 777 and 888

Test Dynamic (17 real files):
- D-01 (14): nap1-2/nsta2/4 × seeds {555,999,1234}; plus others for nap3-4
- D-09 (3): nap1/nsta2 × seeds {1234,555,999}

### 6. Exact JSON structure of a static file

Top-level is a JSON array of 800 dicts. Each dict:
```json
{
  "window": 0,
  "bias": 0,
  "num_ap": 1,
  "num_sta": 2,
  "net_throughput_mbps": 0,
  "net_avg_delay_ms": 0,
  "net_avg_jitter_ms": 0,
  "net_packet_loss_ratio": 0,
  "net_active_flows": 0,
  "mac_total_tx": 0,
  "mac_total_rx": 0,
  "mac_total_ack": 0,
  "mac_total_retrans": 0,
  "mac_drop_count": 0,
  "phy_drop_count": 0,
  "avg_backoff_slots": 7.83333,
  "channel_busy_ratio": 0.010074
}
```
All `mac_total_*` fields are effectively zero throughout the file (observed: mac_total_tx=0
at windows 0, 1, 798, 799). The active metrics are the net_*, avg_backoff_slots,
channel_busy_ratio fields.

### 7. Does v3 data have num_ap and num_sta fields?

Yes. Confirmed on `nap4_nsta8_seed45_negative_80s.json`:
```
num_ap: 4, num_sta: 32
```
V3 files are fully compatible with the multi-AP normalization path in `extract_features()`.

---

## Session Context Update

- Plan saved: `.claude/docs/plans/stitch-dynamic-implementation-plan.md`
- Ready for implementation: yes
- Key unresolved decisions to make before starting implementation:
  1. Exact bias variant naming (D-03 vs D-03b vs D-03c) — must choose and commit
  2. Confirm non-overlapping second-use slice strategy (`[0:200]+[600:800]`) — must
     be reflected in the ADR before coding starts
- Single-AP augmentation explicitly deferred — do not implement in this script
