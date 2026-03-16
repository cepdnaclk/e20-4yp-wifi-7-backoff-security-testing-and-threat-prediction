#!/usr/bin/env python3
"""
stitch_dynamic.py — Generate synthetic dynamic training files by stitching
windows from existing static source files.

Each synthetic file contains 2–5 phases, where each phase is sourced from
a static file with a constant bias value.  The resulting files are placed in
the v4 Dynamic/ directories alongside real NS-3 dynamic files.

Key design rules:
  - Same seed + same nap/nsta for all phases in one file.
  - 400 windows per phase taken from the middle of an 800-window source file.
  - Repeated phases of the same type use non-overlapping offsets.
  - Output file is skipped if it already exists (real or previous synthetic).
  - bias field preserved from source; window field renumbered 0-based.

Usage:
    python stitch_dynamic.py                    # generate all splits
    python stitch_dynamic.py --split train
    python stitch_dynamic.py --split val
    python stitch_dynamic.py --split test
    python stitch_dynamic.py --dry-run          # preview without writing
    python stitch_dynamic.py --overwrite        # regenerate existing files
    python stitch_dynamic.py --summary          # print inventory after generation
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parents[2]
V4_ROOT     = REPO_ROOT / "twin" / "gnn" / "training_data" / "v4"
V3_ROOT     = REPO_ROOT / "twin" / "gnn" / "training_data" / "v3"

# ── Seed pools (strictly disjoint — no leakage) ────────────────────────────
SEEDS = {
    "train": [42, 111, 123, 222, 321, 333, 456, 654, 789, 987],
    "val":   [444, 777, 888],
    "test":  [555, 999, 1234],
}

# nap → nsta mapping (matches collection scripts)
NAP_NSTA = {1: 2, 2: 4, 3: 2, 4: 2}

# Windows per phase (taken from middle of 800-window source file)
PHASE_LEN = 400

# Slice offsets for repeated use of the same source type within one file.
# Each entry gives the start index; slice is [offset : offset + PHASE_LEN].
# Three non-overlapping 400-window slices from an 800-window file:
#   [0:400], [400:800] are fully disjoint.
#   [200:600] overlaps both but sits in the steady-state centre.
# Usage order: 1st occurrence → [200:600], 2nd → [0:400], 3rd → [400:800]
PHASE_OFFSETS = [200, 0, 400]


# ── Phase pattern catalogue ────────────────────────────────────────────────
# Each entry: (pattern_id, pattern_name, phases, group, bias_override)
#   phases:        list of phase specs  (see below)
#   group:         A/B/C/D/E/T
#   bias_override: None → use split defaults; [list] → only these attack biases
#
# Phase spec (uniform patterns):  ("N"|"P"|"G", sign)
#   N = Normal  (bias=0)
#   P = Positive attack (bias > 0, sign=+1)
#   G = Negative attack (bias < 0, sign=-1)
#
# Phase spec (uneven patterns):   ("N"|"P"|"G", sign, length)
#   length overrides PHASE_LEN for that specific phase.

PATTERNS = [
    # ── Group A: 2-phase (800 windows) ──────────────────────────────────────
    ("D-01", "norm-pos",           [("N",0), ("P",+1)],                       "A", None),
    ("D-02", "norm-neg",           [("N",0), ("G",-1)],                       "A", None),
    ("D-03", "pos-norm",           [("P",+1), ("N",0)],                       "A", None),
    ("D-04", "neg-norm",           [("G",-1), ("N",0)],                       "A", None),
    ("D-05", "pos-neg",            [("P",+1), ("G",-1)],                      "A", None),
    ("D-06", "neg-pos",            [("G",-1), ("P",+1)],                      "A", None),

    # ── Group B: 3-phase (1200 windows) ─────────────────────────────────────
    ("D-07", "norm-pos-norm",      [("N",0), ("P",+1), ("N",0)],              "B", None),
    ("D-08", "norm-neg-norm",      [("N",0), ("G",-1), ("N",0)],              "B", None),
    ("D-09", "neg-norm-pos",       [("G",-1), ("N",0), ("P",+1)],             "B", None),
    ("D-10", "pos-norm-neg",       [("P",+1), ("N",0), ("G",-1)],             "B", None),
    ("D-11", "pos-neg-pos",        [("P",+1), ("G",-1), ("P",+1)],            "B", None),
    ("D-12", "neg-pos-neg",        [("G",-1), ("P",+1), ("G",-1)],            "B", None),

    # ── Group C: 4-phase (1600 windows) ─────────────────────────────────────
    ("D-13", "neg-norm-pos-norm",  [("G",-1), ("N",0), ("P",+1), ("N",0)],   "C", None),
    ("D-14", "norm-pos-norm-neg",  [("N",0), ("P",+1), ("N",0), ("G",-1)],   "C", None),
    ("D-15", "pos-norm-neg-norm",  [("P",+1), ("N",0), ("G",-1), ("N",0)],   "C", None),
    ("D-16", "neg-pos-norm-neg",   [("G",-1), ("P",+1), ("N",0), ("G",-1)],  "C", None),

    # ── Group D: uneven phase lengths ────────────────────────────────────────
    # (type, sign, length) tuples override PHASE_LEN per phase
    ("D-17", "neg-norm-early",     [("G",-1,267), ("N",0,533)],               "D", None),
    ("D-18", "norm-pos-late",      [("N",0,533), ("P",+1,267)],               "D", None),
    ("D-19", "neg-norm-pos-uneven",[("G",-1,300), ("N",0,400), ("P",+1,500)],"D", None),
    ("D-20", "pos-neg-early",      [("P",+1,150), ("G",-1,650)],              "D", None),
    ("D-21", "norm-neg-narrow",    [("N",0,300), ("G",-1,200), ("N",0,300)],  "D", None),

    # ── Group E: weak-bias (train only — val/test have no ±1000/±2000 files) ─
    ("D-22", "norm-weak-pos1000",  [("N",0), ("P",+1)],                       "E", [1000]),
    ("D-23", "norm-weak-neg1000",  [("N",0), ("G",-1)],                       "E", [1000]),
    ("D-24", "weak-neg-norm-pos",  [("G",-1), ("N",0), ("P",+1)],             "E", [1000]),
    ("D-25", "mid-pos-norm-neg",   [("P",+1), ("N",0), ("G",-1)],             "E", [2000]),

    # ── Group T: test-only 5-phase (never appears in train or val) ───────────
    ("T-01", "norm-neg-norm-pos-norm", [("N",0),("G",-1),("N",0),("P",+1),("N",0)], "T", None),
    ("T-02", "pos-norm-pos-neg-norm",  [("P",+1),("N",0),("P",+1),("G",-1),("N",0)],"T", None),
    ("T-03", "neg-norm-neg-pos-neg",   [("G",-1),("N",0),("G",-1),("P",+1),("G",-1)],"T",None),
    ("T-04", "pos-neg-pos-norm-neg",   [("P",+1),("G",-1),("P",+1),("N",0),("G",-1)],"T",None),
    ("T-05", "norm-pos-neg-pos-norm",  [("N",0),("P",+1),("G",-1),("P",+1),("N",0)], "T", None),
]

# Attack biases available per split
SPLIT_BIASES = {
    "train": [5000, 2000, 1000],   # generate 3 variants per pattern
    "val":   [5000],
    "test":  [5000, 4000, 2000, 1000, 500],
}

# Which pattern groups belong to which split
SPLIT_GROUPS = {
    "train": {"A", "B", "C", "D", "E"},
    "val":   {"A", "B", "C"},        # representative subset
    "test":  {"A", "B", "C", "T"},   # T-patterns only in test
}

# Val uses only a representative subset of patterns (not all 25)
VAL_PATTERN_IDS = {"D-01", "D-02", "D-04", "D-07", "D-08", "D-09", "D-13", "D-14"}


# ── Source file resolution ─────────────────────────────────────────────────

def get_source_path(split: str, nap: int, nsta: int, seed: int, bias: int) -> Optional[Path]:
    """
    Find a static source file for the given (split, nap, nsta, seed, bias).
    Returns the Path if it exists, None otherwise.

    For train split, also searches v3/ data (seeds 42-45) as a supplementary source.
    """
    if bias == 0:
        subdir = "Normal"
        fname  = f"nap{nap}_nsta{nsta}_seed{seed}_normal_80s.json"
    else:
        subdir = "Attack"
        sign   = "positive" if bias > 0 else "negative"
        fname  = f"nap{nap}_nsta{nsta}_seed{seed}_{sign}{abs(bias)}_80s.json"

    # Primary: v4 split directory
    path = V4_ROOT / split / "Static" / subdir / fname
    if path.exists():
        return path

    # Supplementary for train: v3 data (seeds 42-45, bias ±5000 only)
    if split == "train" and abs(bias) in (0, 5000):
        v3_subdir = "Normal" if bias == 0 else "Attack"
        # v3 uses nsta proportional to nap (1:2, 2:4, 3:6, 4:8)
        v3_nsta_map = {1: 2, 2: 4, 3: 6, 4: 8}
        v3_nsta = v3_nsta_map.get(nap, nsta)
        if bias == 0:
            v3_fname = f"nap{nap}_nsta{v3_nsta}_seed{seed}_normal_80s.json"
        else:
            sign = "positive" if bias > 0 else "negative"
            v3_fname = f"nap{nap}_nsta{v3_nsta}_seed{seed}_{sign}_80s.json"
        v3_path = V3_ROOT / v3_subdir / v3_fname
        if v3_path.exists():
            return v3_path

    return None


def output_path_for(split: str, nap: int, nsta: int, seed: int,
                    pid: str, pname: str, total_windows: int,
                    attack_bias: int) -> Path:
    """Build the output file path for a synthetic dynamic file."""
    out_dir = V4_ROOT / split / "Dynamic"
    sim_time = total_windows // 10   # 800 windows → 80s, 1200 → 120s, etc.
    # For the default (highest) bias, match real NS-3 naming (no bias suffix).
    # For other biases, append _b{bias} so files don't collide.
    default_bias = SPLIT_BIASES[split][0]
    if attack_bias == default_bias or attack_bias == 0:
        fname = f"nap{nap}_nsta{nsta}_seed{seed}_{pid}_{pname}_{sim_time}s.json"
    else:
        fname = f"nap{nap}_nsta{nsta}_seed{seed}_{pid}_{pname}_b{attack_bias}_{sim_time}s.json"
    return out_dir / fname


# ── Window slicing ─────────────────────────────────────────────────────────

def load_windows(path: Path) -> list:
    with open(path) as f:
        return json.load(f)


def get_slice(windows: list, offset: int, length: int) -> list:
    """Extract `length` windows starting at `offset`, clamped to file length."""
    end = min(offset + length, len(windows))
    actual_len = end - offset
    if actual_len < length * 0.5:
        raise ValueError(
            f"Requested {length} windows at offset {offset} from file with "
            f"{len(windows)} windows — only {actual_len} available (< 50%)."
        )
    return windows[offset:end]


# ── Core stitching ─────────────────────────────────────────────────────────

def stitch_file(phase_sources: list, output_path: Path, dry_run: bool = False) -> int:
    """
    Stitch windows from multiple source files into one synthetic dynamic file.

    Args:
        phase_sources: list of (source_path, expected_bias, offset, length)
        output_path:   destination file
        dry_run:       if True, validate sources but don't write

    Returns:
        Total windows written (or that would be written).
    """
    result = []
    global_idx = 0

    for src_path, expected_bias, offset, length in phase_sources:
        windows = load_windows(src_path)
        sliced  = get_slice(windows, offset, length)

        # Validate bias consistency in slice
        biases_found = {w["bias"] for w in sliced}
        if len(biases_found) != 1:
            raise ValueError(
                f"Mixed biases {biases_found} in slice of {src_path.name} "
                f"[{offset}:{offset+length}]. Static source files must have constant bias."
            )
        actual_bias = next(iter(biases_found))
        if actual_bias != expected_bias:
            raise ValueError(
                f"Expected bias={expected_bias}, found bias={actual_bias} "
                f"in {src_path.name}"
            )

        for w in sliced:
            entry = dict(w)
            entry["window"] = global_idx
            result.append(entry)
            global_idx += 1

    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f)

    return len(result)


# ── Phase plan builder ─────────────────────────────────────────────────────

def build_phase_sources(phases: list, split: str,
                        nap: int, nsta: int, seed: int,
                        attack_bias: int) -> Optional[list]:
    """
    Resolve source files for each phase of a pattern.

    Returns a list of (source_path, expected_bias, offset, length) tuples,
    or None if any required source file is missing.

    Tracks occurrence counts per (type, bias) to assign non-overlapping offsets.
    """
    phase_sources = []
    # occurrence_count[(type, bias)] tracks how many times this source type was used
    occurrence_count: dict = {}

    for phase_spec in phases:
        # Unpack phase spec — may include length override
        if len(phase_spec) == 2:
            ptype, sign = phase_spec
            length = PHASE_LEN
        else:
            ptype, sign, length = phase_spec

        # Resolve the bias for this phase
        if ptype == "N":
            bias = 0
        elif ptype == "P":
            bias = +attack_bias * sign  # sign=+1
        else:  # G
            bias = attack_bias * sign   # sign=-1, so bias is negative

        # Find source file
        src = get_source_path(split, nap, nsta, seed, bias)
        if src is None:
            return None   # source missing — skip this combination

        # Determine offset (non-overlapping per occurrence of same source type)
        key = (ptype, bias)
        count = occurrence_count.get(key, 0)
        offset = PHASE_OFFSETS[count % len(PHASE_OFFSETS)]
        occurrence_count[key] = count + 1

        # For uneven phases: clamp length to what's available at this offset
        actual_length = min(length, 800 - offset)

        phase_sources.append((src, bias, offset, actual_length))

    return phase_sources


# ── Split generator ────────────────────────────────────────────────────────

def generate_split(split: str, dry_run: bool = False,
                   overwrite: bool = False) -> dict:
    """
    Generate all synthetic dynamic files for one split.

    Returns stats dict with counts: generated, skipped, missing_source, errors.
    """
    stats = {"generated": 0, "skipped": 0, "missing_source": 0, "errors": 0,
             "total_windows": 0}
    allowed_groups = SPLIT_GROUPS[split]
    biases = SPLIT_BIASES[split]

    print(f"\n{'='*70}")
    print(f"Generating synthetic dynamic files — split: {split.upper()}")
    print(f"  Patterns groups: {sorted(allowed_groups)}")
    print(f"  Attack biases:   {biases}")
    print(f"  Seeds:           {SEEDS[split]}")
    print(f"  NAP/NSTA:        {NAP_NSTA}")
    print(f"  Dry run:         {dry_run}")
    print(f"{'='*70}")

    for pid, pname, phases, group, bias_override in PATTERNS:
        # Filter by split-allowed groups
        if group not in allowed_groups:
            continue

        # Val: only run representative subset of patterns
        if split == "val" and pid not in VAL_PATTERN_IDS:
            continue

        # Determine which attack biases to use for this pattern
        if bias_override is not None:
            # Group E or specific overrides — only generate if source exists
            pattern_biases = bias_override
        else:
            pattern_biases = biases

        # Group E and D patterns: train only
        if group in ("D", "E") and split != "train":
            continue

        # Group T: test only
        if group == "T" and split != "test":
            continue

        for nap, nsta in NAP_NSTA.items():
            # Val/test nap4 files are sparse — try anyway, skip if source missing
            for seed in SEEDS[split]:
                for attack_bias in pattern_biases:
                    # Build output path
                    # Calculate total windows
                    total_windows = sum(
                        ps[2] if len(ps) == 3 else PHASE_LEN
                        for ps in phases
                    )
                    # For uneven patterns, phases have 3-tuples (type, sign, length)
                    total_windows = 0
                    for ps in phases:
                        if len(ps) == 3:
                            total_windows += ps[2]
                        else:
                            total_windows += PHASE_LEN

                    out_path = output_path_for(
                        split, nap, nsta, seed, pid, pname,
                        total_windows, attack_bias
                    )

                    # Skip if file already exists (real or previous synthetic)
                    if out_path.exists() and not overwrite:
                        stats["skipped"] += 1
                        continue

                    # Resolve source files for each phase
                    phase_sources = build_phase_sources(
                        phases, split, nap, nsta, seed, attack_bias
                    )
                    if phase_sources is None:
                        stats["missing_source"] += 1
                        continue

                    # Stitch and write
                    action = "DRY-RUN" if dry_run else "WRITE"
                    try:
                        n_windows = stitch_file(phase_sources, out_path, dry_run)
                        stats["generated"] += 1
                        stats["total_windows"] += n_windows
                        if stats["generated"] % 100 == 0 or dry_run:
                            print(f"  [{action}] {out_path.name}  ({n_windows}w)")
                    except Exception as e:
                        print(f"  [ERROR] {out_path.name}: {e}", file=sys.stderr)
                        stats["errors"] += 1

    return stats


# ── Summary ────────────────────────────────────────────────────────────────

def print_summary():
    """Print current file counts in all Dynamic directories."""
    print(f"\n{'='*70}")
    print("DATASET SUMMARY")
    print(f"{'='*70}")
    for split in ("train", "val", "test"):
        dyn_dir = V4_ROOT / split / "Dynamic"
        real  = [f for f in dyn_dir.glob("*.json") if "_b" not in f.name
                 and not f.name.startswith("nap") or True]
        # Distinguish by checking for _b suffix
        all_files  = list(dyn_dir.glob("*.json")) if dyn_dir.exists() else []
        syn_files  = [f for f in all_files if "_b" in f.stem]
        base_files = [f for f in all_files if f not in syn_files]
        norm_dir = V4_ROOT / split / "Static" / "Normal"
        atk_dir  = V4_ROOT / split / "Static" / "Attack"
        n_norm = len(list(norm_dir.glob("*.json"))) if norm_dir.exists() else 0
        n_atk  = len(list(atk_dir.glob("*.json")))  if atk_dir.exists()  else 0
        print(f"\n  [{split.upper()}]")
        print(f"    Static/Normal : {n_norm} files")
        print(f"    Static/Attack : {n_atk} files")
        print(f"    Dynamic total : {len(all_files)} files")
        print(f"      base (no bias suffix): {len(base_files)}")
        print(f"      bias variants (_bXXXX): {len(syn_files)}")


# ── Entry point ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic dynamic GCN v4 training files."
    )
    parser.add_argument(
        "--split", choices=["train", "val", "test", "all"], default="all",
        help="Which split to generate (default: all)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate sources and preview output without writing files"
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Regenerate files even if they already exist"
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="Print dataset summary after generation"
    )
    args = parser.parse_args()

    splits = ["train", "val", "test"] if args.split == "all" else [args.split]

    total_stats = {"generated": 0, "skipped": 0, "missing_source": 0,
                   "errors": 0, "total_windows": 0}

    for split in splits:
        stats = generate_split(split, dry_run=args.dry_run, overwrite=args.overwrite)
        for k in total_stats:
            total_stats[k] += stats[k]

        print(f"\n  {split.upper()} results:")
        print(f"    Generated      : {stats['generated']}")
        print(f"    Skipped        : {stats['skipped']} (already exist)")
        print(f"    Missing source : {stats['missing_source']}")
        print(f"    Errors         : {stats['errors']}")
        print(f"    Total windows  : {stats['total_windows']:,}")

    print(f"\n{'='*70}")
    print("OVERALL")
    print(f"  Generated      : {total_stats['generated']}")
    print(f"  Skipped        : {total_stats['skipped']}")
    print(f"  Missing source : {total_stats['missing_source']}")
    print(f"  Errors         : {total_stats['errors']}")
    print(f"  Total windows  : {total_stats['total_windows']:,}")
    print(f"{'='*70}")

    if args.summary or not args.dry_run:
        print_summary()


if __name__ == "__main__":
    main()
