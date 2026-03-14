#!/usr/bin/env python3
"""
Evaluation matrix runner — MODEL-EVALUATION-GUIDE.md
Runs experiments tier-by-tier, polls for completion, reports pass/fail.
Usage:
    python3 scripts/run_eval_matrix.py [--tier 1] [--dry-run]
"""

import argparse
import time
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime

BASE = "http://localhost:8888"
POLL_INTERVAL  = 8   # seconds between status polls
LAUNCH_TIMEOUT = 90  # seconds to wait for active=true after launch
# No hard RUN_TIMEOUT — multi-AP sims can take 1-2 hours. We poll until the
# pipeline reports inactive, then look up the result in history.


def api(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data,
                                  headers={"Content-Type": "application/json"},
                                  method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def wait_for_completion(exp_id):
    """
    Wait for a specific experiment to finish. No hard timeout — polls indefinitely
    so that long multi-AP simulations are never cancelled mid-run.
    Returns 'success' | 'failed'.
    """
    # Phase 1: wait for active=true (max LAUNCH_TIMEOUT seconds)
    deadline = time.time() + LAUNCH_TIMEOUT
    became_active = False
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        s = api("GET", "/api/run/status")
        if s.get("active") and s.get("experiment_id"):
            became_active = True
            break

    if not became_active:
        # Never became active — may have completed very fast
        hist = api("GET", "/api/run/history")
        entry = next((h for h in hist.get("history", []) if h["experiment_id"] == exp_id), None)
        if entry and entry.get("outcome") in ("success", "failed", "cancelled"):
            return entry["outcome"]
        return "failed"

    # Phase 2: poll until inactive — no timeout, just keep waiting
    elapsed = 0
    while True:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        s = api("GET", "/api/run/status")
        if not s.get("active"):
            # Give history a moment to be written
            time.sleep(3)
            hist = api("GET", "/api/run/history")
            entry = next((h for h in hist.get("history", []) if h["experiment_id"] == exp_id), None)
            if entry:
                return entry["outcome"]
            # Fall back to latest entry
            latest = hist.get("history", [{}])[0]
            return latest.get("outcome", "failed")
        if elapsed % 60 == 0:
            print(f"    still running… ({elapsed//60}m elapsed)")


def check_prediction_result(exp_id, scenario):
    """Fetch summary and evaluate pass/fail against guide criteria."""
    try:
        s = api("GET", f"/api/experiments/{exp_id}/summary")
        seg = s.get("segment_count", 0)
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


def run_experiment(exp, dry_run=False):
    scenario    = exp["scenario"]
    seed        = exp["seed"]
    sim_time    = exp.get("sim_time", 200)
    bias        = exp.get("bias", 5000) if scenario != "normal" else 0
    num_ap      = exp.get("num_ap", 1)
    num_sta     = exp.get("num_sta", num_ap * 2)
    seg_len     = exp.get("seg_len", 256)
    gcn_version = exp["gcn_version"]
    tier        = exp.get("tier", "?")

    label = f"[T{tier}] {scenario:8s} {num_ap}AP seed={seed:3d} seg={seg_len} bias={bias:5d} {gcn_version}"
    print(f"\n{'─'*70}")
    print(f"  {label}")
    print(f"{'─'*70}")

    if dry_run:
        print("  [DRY RUN — skipping]")
        return {"label": label, "outcome": "dry-run", "pass_fail": "—", "segments": 0, "attack_rate": 0}

    # Cancel any active run first
    status = api("GET", "/api/run/status")
    if status.get("active"):
        print("  ! Cancelling active run …")
        api("POST", "/api/run/cancel")
        time.sleep(5)

    payload = {
        "scenario":       scenario,
        "seed":           seed,
        "sim_time":       sim_time,
        "bias":           bias,
        "num_ap":         num_ap,
        "num_sta":        num_sta,
        "segment_length": seg_len,
        "gcn_version":    gcn_version,
    }

    print(f"  Launching …  {datetime.now().strftime('%H:%M:%S')}")
    resp = api("POST", "/api/run/launch", payload)
    exp_id = resp.get("experiment_id", "")
    if not exp_id:
        print(f"  ERROR launching: {resp}")
        return {"label": label, "outcome": "failed", "pass_fail": "ERROR", "segments": 0, "attack_rate": 0}

    print(f"  experiment_id: {exp_id}")

    outcome = wait_for_completion(exp_id)
    print(f"  outcome: {outcome}   ({datetime.now().strftime('%H:%M:%S')})")

    if outcome != "success":
        return {"label": label, "outcome": outcome, "pass_fail": "ERROR", "segments": 0, "attack_rate": 0, "exp_id": exp_id}

    seg, rate, conf, model, pf = check_prediction_result(exp_id, scenario)
    conf_str = f"{conf*100:.1f}%" if conf is not None else "—"
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
    }


# ── Experiment definitions ─────────────────────────────────────────────────────

TIER1 = []
for gcn in ["v3.0.0", "v2.0.0"]:
    # Seed group A
    TIER1 += [
        {"tier": 1, "scenario": "normal",   "seed": 10,  "sim_time": 80, "bias": 0,    "num_ap": 1, "seg_len": 256, "gcn_version": gcn},
        {"tier": 1, "scenario": "positive", "seed": 42,  "sim_time": 80, "bias": 5000, "num_ap": 1, "seg_len": 256, "gcn_version": gcn},
        {"tier": 1, "scenario": "negative", "seed": 99,  "sim_time": 80, "bias": 5000, "num_ap": 1, "seg_len": 256, "gcn_version": gcn},
    ]
    # Seed group B
    TIER1 += [
        {"tier": 1, "scenario": "normal",   "seed": 20,  "sim_time": 80, "bias": 0,    "num_ap": 1, "seg_len": 256, "gcn_version": gcn},
        {"tier": 1, "scenario": "positive", "seed": 52,  "sim_time": 80, "bias": 5000, "num_ap": 1, "seg_len": 256, "gcn_version": gcn},
        {"tier": 1, "scenario": "negative", "seed": 109, "sim_time": 80, "bias": 5000, "num_ap": 1, "seg_len": 256, "gcn_version": gcn},
    ]

TIER2 = []
for ap, sta in [(2, 4), (4, 8)]:
    TIER2 += [
        {"tier": 2, "scenario": "normal",   "seed": 10, "sim_time": 80, "bias": 0,    "num_ap": ap, "num_sta": sta, "seg_len": 256, "gcn_version": "v3.0.0"},
        {"tier": 2, "scenario": "positive", "seed": 42, "sim_time": 80, "bias": 5000, "num_ap": ap, "num_sta": sta, "seg_len": 256, "gcn_version": "v3.0.0"},
        {"tier": 2, "scenario": "negative", "seed": 99, "sim_time": 80, "bias": 5000, "num_ap": ap, "num_sta": sta, "seg_len": 256, "gcn_version": "v3.0.0"},
    ]

TIER3 = [
    # seg=128, seed group A
    {"tier": 3, "scenario": "normal",   "seed": 10,  "sim_time": 80, "bias": 0,    "num_ap": 1, "seg_len": 128, "gcn_version": "v3.0.0"},
    {"tier": 3, "scenario": "positive", "seed": 42,  "sim_time": 80, "bias": 5000, "num_ap": 1, "seg_len": 128, "gcn_version": "v3.0.0"},
    {"tier": 3, "scenario": "negative", "seed": 99,  "sim_time": 80, "bias": 5000, "num_ap": 1, "seg_len": 128, "gcn_version": "v3.0.0"},
    # seg=64, seed group B
    {"tier": 3, "scenario": "normal",   "seed": 20,  "sim_time": 80, "bias": 0,    "num_ap": 1, "seg_len": 64,  "gcn_version": "v3.0.0"},
    {"tier": 3, "scenario": "positive", "seed": 52,  "sim_time": 80, "bias": 5000, "num_ap": 1, "seg_len": 64,  "gcn_version": "v3.0.0"},
    {"tier": 3, "scenario": "negative", "seed": 109, "sim_time": 80, "bias": 5000, "num_ap": 1, "seg_len": 64,  "gcn_version": "v3.0.0"},
]

TIER4 = []
for bias, gA, gB in [(1000, 62, 119), (2000, 72, 129), (10000, 82, 139)]:
    for gcn in ["v3.0.0", "v2.0.0"]:
        TIER4 += [
            {"tier": 4, "scenario": "positive", "seed": gA,  "sim_time": 80, "bias": bias, "num_ap": 1, "seg_len": 256, "gcn_version": gcn},
            {"tier": 4, "scenario": "negative", "seed": gB,  "sim_time": 80, "bias": bias, "num_ap": 1, "seg_len": 256, "gcn_version": gcn},
        ]

# Tier 5 — Seed Generalisation (groups C, D, E only; A+B covered by Tier 1)
# Group C: normal=30, positive=62, negative=119
# Group D: normal=40, positive=72, negative=129
# Group E: normal=50, positive=82, negative=139
TIER5 = []
for gcn in ["v3.0.0", "v2.0.0"]:
    TIER5 += [
        # Group C
        {"tier": 5, "scenario": "normal",   "seed": 30,  "sim_time": 80, "bias": 0,    "num_ap": 1, "seg_len": 256, "gcn_version": gcn},
        {"tier": 5, "scenario": "positive", "seed": 62,  "sim_time": 80, "bias": 5000, "num_ap": 1, "seg_len": 256, "gcn_version": gcn},
        {"tier": 5, "scenario": "negative", "seed": 119, "sim_time": 80, "bias": 5000, "num_ap": 1, "seg_len": 256, "gcn_version": gcn},
        # Group D
        {"tier": 5, "scenario": "normal",   "seed": 40,  "sim_time": 80, "bias": 0,    "num_ap": 1, "seg_len": 256, "gcn_version": gcn},
        {"tier": 5, "scenario": "positive", "seed": 72,  "sim_time": 80, "bias": 5000, "num_ap": 1, "seg_len": 256, "gcn_version": gcn},
        {"tier": 5, "scenario": "negative", "seed": 129, "sim_time": 80, "bias": 5000, "num_ap": 1, "seg_len": 256, "gcn_version": gcn},
        # Group E
        {"tier": 5, "scenario": "normal",   "seed": 50,  "sim_time": 80, "bias": 0,    "num_ap": 1, "seg_len": 256, "gcn_version": gcn},
        {"tier": 5, "scenario": "positive", "seed": 82,  "sim_time": 80, "bias": 5000, "num_ap": 1, "seg_len": 256, "gcn_version": gcn},
        {"tier": 5, "scenario": "negative", "seed": 139, "sim_time": 80, "bias": 5000, "num_ap": 1, "seg_len": 256, "gcn_version": gcn},
    ]

ALL_TIERS = {1: TIER1, 2: TIER2, 3: TIER3, 4: TIER4, 5: TIER5}


def print_summary(results):
    print(f"\n{'═'*70}")
    print("  EVALUATION SUMMARY")
    print(f"{'═'*70}")
    total = len(results)
    passed = sum(1 for r in results if r["pass_fail"] == "PASS")
    failed = sum(1 for r in results if r["pass_fail"] == "FAIL")
    errors = sum(1 for r in results if r["pass_fail"] not in ("PASS", "FAIL", "—"))
    print(f"  Total: {total}   PASS: {passed}   FAIL: {failed}   ERROR/TIMEOUT: {errors}")
    print()
    for r in results:
        icon = "✓" if r["pass_fail"] == "PASS" else ("✗" if r["pass_fail"] == "FAIL" else "!")
        rate = f"atk={r['attack_rate']:.2f}" if r.get("attack_rate") is not None else ""
        seg  = f"seg={r['segments']}" if r.get("segments") else ""
        print(f"  {icon} {r['label']}  {seg}  {rate}")
    print(f"{'═'*70}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", type=int, nargs="+", default=[1, 2, 3, 4, 5],
                        help="Which tiers to run (default: 1 2 3 4 5)")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without running")
    args = parser.parse_args()

    experiments = []
    for t in args.tier:
        experiments.extend(ALL_TIERS.get(t, []))

    print(f"\nEvaluation Matrix — {len(experiments)} experiments across tier(s) {args.tier}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.dry_run:
        print("[DRY RUN]\n")

    results = []
    for i, exp in enumerate(experiments, 1):
        print(f"\nProgress: {i}/{len(experiments)}")
        result = run_experiment(exp, dry_run=args.dry_run)
        results.append(result)

        # Pause between experiments to let containers settle
        if not args.dry_run and i < len(experiments):
            time.sleep(8)

    print_summary(results)

    # Write results JSON
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = f"/tmp/eval-results-{ts}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved: {out_path}\n")


if __name__ == "__main__":
    main()
