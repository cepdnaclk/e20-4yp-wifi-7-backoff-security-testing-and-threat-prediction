#!/usr/bin/env python3
"""
Overnight Gap-Fill Run — 2026-03-14
Fills missing multi-AP scenarios so every combination of
(2AP / 3AP / 4AP) × (normal / positive / negative) has
at least 3 independent seed-group runs.

Gap analysis (see docs/OVERNIGHT-GAP-FILL-PLAN-2026-03-15.md):
  2AP: groups B + C missing  (6 runs)
  3AP: groups A + B + C missing  (9 runs)
  4AP: groups B + C missing  (6 runs)
  Total: 21 runs  (~6-8 h estimated)

Usage:
    # Full overnight run (all 21 experiments)
    python3 scripts/run_overnight_gaps.py

    # Dry-run — print plan without executing
    python3 scripts/run_overnight_gaps.py --dry-run

    # Specific AP count only
    python3 scripts/run_overnight_gaps.py --ap 3
    python3 scripts/run_overnight_gaps.py --ap 2 4

    # Resume from a specific index (if interrupted mid-run)
    python3 scripts/run_overnight_gaps.py --start 7

IMPORTANT: Does NOT clear existing data — all new experiments are
additive to the current DB state.
"""

import argparse
import time
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime

BASE = "http://localhost:8888"
POLL_INTERVAL  = 10   # seconds between status polls
LAUNCH_TIMEOUT = 120  # seconds to wait for active=true after launch


def api(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def wait_for_completion(exp_id: str) -> str:
    """
    Poll until the experiment finishes. No hard timeout so long
    multi-AP simulations are never killed mid-run.
    Returns 'success' | 'failed' | 'cancelled'.
    """
    # Phase 1: wait up to LAUNCH_TIMEOUT for active=true
    deadline = time.time() + LAUNCH_TIMEOUT
    became_active = False
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        s = api("GET", "/api/run/status")
        if s.get("active") and s.get("experiment_id"):
            became_active = True
            break

    if not became_active:
        hist = api("GET", "/api/run/history")
        entry = next(
            (h for h in hist.get("history", []) if h["experiment_id"] == exp_id),
            None,
        )
        if entry and entry.get("outcome") in ("success", "failed", "cancelled"):
            return entry["outcome"]
        return "failed"

    # Phase 2: poll until inactive — no timeout
    elapsed = 0
    while True:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        s = api("GET", "/api/run/status")
        if not s.get("active"):
            time.sleep(5)  # give history a moment to flush
            hist = api("GET", "/api/run/history")
            entry = next(
                (h for h in hist.get("history", []) if h["experiment_id"] == exp_id),
                None,
            )
            if entry:
                return entry["outcome"]
            latest = hist.get("history", [{}])[0]
            return latest.get("outcome", "failed")
        if elapsed % 120 == 0:
            print(f"    still running… ({elapsed // 60}m elapsed)")


def check_result(exp_id: str, scenario: str):
    """Fetch summary and return pass/fail."""
    try:
        s = api("GET", f"/api/experiments/{exp_id}/summary")
        seg  = s.get("segment_count", 0)
        rate = s.get("attack_rate", 0.0)
        conf = s.get("avg_confidence")
        model = s.get("model_version", "?")
        if scenario == "normal":
            pf = "PASS" if rate < 0.10 else "FAIL"
        else:
            pf = "PASS" if rate > 0.90 else "FAIL"
        return seg, rate, conf, model, pf
    except Exception as e:
        return 0, 0.0, None, "?", f"ERROR({e})"


def run_one(exp: dict, dry_run: bool = False) -> dict:
    scenario = exp["scenario"]
    seed     = exp["seed"]
    num_ap   = exp["num_ap"]
    num_sta  = exp["num_sta"]
    sim_time = exp.get("sim_time", 80)
    bias     = exp.get("bias", 5000) if scenario != "normal" else 0
    seg_len  = exp.get("seg_len", 256)
    gcn      = exp.get("gcn_version", "v3.0.0")
    group    = exp.get("group", "?")

    label = (
        f"[{num_ap}AP | group {group}] "
        f"{scenario:8s} seed={seed:3d}  "
        f"bias={bias:5d}  seg={seg_len}  {gcn}"
    )
    print(f"\n{'─' * 72}")
    print(f"  {label}")
    print(f"{'─' * 72}")

    if dry_run:
        print("  [DRY RUN — skipping]")
        return {"label": label, "outcome": "dry-run", "pass_fail": "—",
                "segments": 0, "attack_rate": 0}

    # Cancel any active run first
    status = api("GET", "/api/run/status")
    if status.get("active"):
        print("  ! Active run detected — cancelling …")
        api("POST", "/api/run/cancel")
        time.sleep(8)

    payload = {
        "scenario":       scenario,
        "seed":           seed,
        "sim_time":       sim_time,
        "bias":           bias,
        "num_ap":         num_ap,
        "num_sta":        num_sta,
        "segment_length": seg_len,
        "gcn_version":    gcn,
    }

    print(f"  Launching …  {datetime.now().strftime('%H:%M:%S')}")
    resp   = api("POST", "/api/run/launch", payload)
    exp_id = resp.get("experiment_id", "")
    if not exp_id:
        print(f"  ERROR launching: {resp}")
        return {"label": label, "outcome": "failed", "pass_fail": "ERROR",
                "segments": 0, "attack_rate": 0}

    print(f"  experiment_id: {exp_id}")
    outcome = wait_for_completion(exp_id)
    print(f"  outcome: {outcome}   ({datetime.now().strftime('%H:%M:%S')})")

    if outcome != "success":
        return {"label": label, "outcome": outcome, "pass_fail": "ERROR",
                "segments": 0, "attack_rate": 0, "exp_id": exp_id}

    seg, rate, conf, model, pf = check_result(exp_id, scenario)
    conf_str = f"{conf * 100:.1f}%" if conf is not None else "—"
    print(f"  segments={seg}  attack_rate={rate:.3f}  avg_conf={conf_str}  model={model}  → {pf}")

    return {
        "label":       label,
        "exp_id":      exp_id,
        "outcome":     outcome,
        "pass_fail":   pf,
        "segments":    seg,
        "attack_rate": rate,
        "confidence":  conf,
        "model":       model,
        "scenario":    scenario,
        "num_ap":      num_ap,
        "seed":        seed,
    }


# ── Experiment definitions ─────────────────────────────────────────────────────
# Seed convention (from MODEL-EVALUATION-GUIDE.md):
#   Group A: normal=10,  positive=42,  negative=99
#   Group B: normal=20,  positive=52,  negative=109
#   Group C: normal=30,  positive=62,  negative=119
#
# Existing multi-AP coverage (as of 2026-03-14):
#   2AP: Group A only  → add Groups B + C
#   3AP: positive-seed22 only (non-standard)  → add Groups A + B + C
#   4AP: Group A only  → add Groups B + C

_COMMON = dict(sim_time=80, bias=5000, seg_len=256, gcn_version="v3.0.0")

# ── 2AP gaps: Groups B and C ────────────────────────────────────────────────
GAP_2AP = [
    # Group B
    dict(num_ap=2, num_sta=4, scenario="normal",   seed=20,  bias=0,    group="B", **{k: v for k, v in _COMMON.items() if k != "bias"}),
    dict(num_ap=2, num_sta=4, scenario="positive", seed=52,  group="B", **_COMMON),
    dict(num_ap=2, num_sta=4, scenario="negative", seed=109, group="B", **_COMMON),
    # Group C
    dict(num_ap=2, num_sta=4, scenario="normal",   seed=30,  bias=0,    group="C", **{k: v for k, v in _COMMON.items() if k != "bias"}),
    dict(num_ap=2, num_sta=4, scenario="positive", seed=62,  group="C", **_COMMON),
    dict(num_ap=2, num_sta=4, scenario="negative", seed=119, group="C", **_COMMON),
]

# ── 3AP gaps: Groups A, B, and C (all missing) ─────────────────────────────
GAP_3AP = [
    # Group A
    dict(num_ap=3, num_sta=6, scenario="normal",   seed=10,  bias=0,    group="A", **{k: v for k, v in _COMMON.items() if k != "bias"}),
    dict(num_ap=3, num_sta=6, scenario="positive", seed=42,  group="A", **_COMMON),
    dict(num_ap=3, num_sta=6, scenario="negative", seed=99,  group="A", **_COMMON),
    # Group B
    dict(num_ap=3, num_sta=6, scenario="normal",   seed=20,  bias=0,    group="B", **{k: v for k, v in _COMMON.items() if k != "bias"}),
    dict(num_ap=3, num_sta=6, scenario="positive", seed=52,  group="B", **_COMMON),
    dict(num_ap=3, num_sta=6, scenario="negative", seed=109, group="B", **_COMMON),
    # Group C
    dict(num_ap=3, num_sta=6, scenario="normal",   seed=30,  bias=0,    group="C", **{k: v for k, v in _COMMON.items() if k != "bias"}),
    dict(num_ap=3, num_sta=6, scenario="positive", seed=62,  group="C", **_COMMON),
    dict(num_ap=3, num_sta=6, scenario="negative", seed=119, group="C", **_COMMON),
]

# ── 4AP gaps: Groups B and C ────────────────────────────────────────────────
GAP_4AP = [
    # Group B
    dict(num_ap=4, num_sta=8, scenario="normal",   seed=20,  bias=0,    group="B", **{k: v for k, v in _COMMON.items() if k != "bias"}),
    dict(num_ap=4, num_sta=8, scenario="positive", seed=52,  group="B", **_COMMON),
    dict(num_ap=4, num_sta=8, scenario="negative", seed=109, group="B", **_COMMON),
    # Group C
    dict(num_ap=4, num_sta=8, scenario="normal",   seed=30,  bias=0,    group="C", **{k: v for k, v in _COMMON.items() if k != "bias"}),
    dict(num_ap=4, num_sta=8, scenario="positive", seed=62,  group="C", **_COMMON),
    dict(num_ap=4, num_sta=8, scenario="negative", seed=119, group="C", **_COMMON),
]

ALL_GAPS = {2: GAP_2AP, 3: GAP_3AP, 4: GAP_4AP}


def print_summary(results: list):
    print(f"\n{'═' * 72}")
    print("  OVERNIGHT GAP-FILL SUMMARY")
    print(f"{'═' * 72}")
    total  = len(results)
    passed = sum(1 for r in results if r["pass_fail"] == "PASS")
    failed = sum(1 for r in results if r["pass_fail"] == "FAIL")
    errors = sum(1 for r in results if r["pass_fail"] not in ("PASS", "FAIL", "—"))
    print(f"  Total: {total}   PASS: {passed}   FAIL: {failed}   ERROR: {errors}")
    print()
    for r in results:
        icon = "✓" if r["pass_fail"] == "PASS" else ("✗" if r["pass_fail"] == "FAIL" else "!")
        rate = f"atk={r['attack_rate']:.2f}" if r.get("attack_rate") is not None else ""
        seg  = f"seg={r['segments']}"         if r.get("segments")     else ""
        print(f"  {icon} {r['label']}  {seg}  {rate}")
    print(f"{'═' * 72}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Overnight gap-fill: add missing 2AP/3AP/4AP seed-group runs."
    )
    parser.add_argument(
        "--ap", type=int, nargs="+", default=[2, 3, 4],
        help="Which AP counts to fill (default: 2 3 4)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print plan without running any experiments",
    )
    parser.add_argument(
        "--start", type=int, default=0,
        help="Skip the first N experiments (resume after interruption)",
    )
    args = parser.parse_args()

    experiments = []
    for ap in args.ap:
        experiments.extend(ALL_GAPS.get(ap, []))

    if args.start > 0:
        print(f"  Resuming from experiment {args.start + 1} (skipping first {args.start})")
        experiments = experiments[args.start:]

    print(f"\nOvernight Gap-Fill — {len(experiments)} experiments  (AP counts: {args.ap})")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("NOTE: existing DB data is preserved — new runs are additive.\n")
    if args.dry_run:
        print("[DRY RUN]\n")

    results = []
    for i, exp in enumerate(experiments, 1):
        print(f"\nProgress: {i}/{len(experiments)}")
        result = run_one(exp, dry_run=args.dry_run)
        results.append(result)
        # Brief pause between experiments to let containers settle
        if not args.dry_run and i < len(experiments):
            time.sleep(12)

    print_summary(results)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = f"/tmp/overnight-gaps-{ts}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved: {out_path}\n")


if __name__ == "__main__":
    main()
