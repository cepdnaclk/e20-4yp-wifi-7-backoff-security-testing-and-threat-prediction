#!/usr/bin/env python3
"""
Dynamic Scenario Test Runner
Tests how GCN v3.0.0 handles experiments where bias changes mid-simulation.

Launches a set of dynamic-phase experiments through the dashboard API and
records predictions to see whether the GCN correctly tracks phase transitions.

Usage:
    python3 scripts/run_dynamic_test.py
    python3 scripts/run_dynamic_test.py --dry-run
    python3 scripts/run_dynamic_test.py --phases "0:0,20:5000,40:-5000,60:0"
"""

import argparse
import time
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime

BASE = "http://localhost:8888"
POLL_INTERVAL  = 10
LAUNCH_TIMEOUT = 180  # Dynamic sims may take longer to start


def api(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def wait_for_completion(exp_id: str) -> str:
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
            (h for h in hist.get("history", []) if h["experiment_id"] == exp_id), None
        )
        if entry and entry.get("outcome") in ("success", "failed", "cancelled"):
            return entry["outcome"]
        return "failed"

    elapsed = 0
    while True:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        s = api("GET", "/api/run/status")
        if not s.get("active"):
            time.sleep(5)
            hist = api("GET", "/api/run/history")
            entry = next(
                (h for h in hist.get("history", []) if h["experiment_id"] == exp_id), None
            )
            if entry:
                return entry["outcome"]
            latest = hist.get("history", [{}])[0]
            return latest.get("outcome", "failed")
        if elapsed % 120 == 0:
            print(f"    still running… ({elapsed // 60}m elapsed)")


def check_result(exp_id: str):
    try:
        s = api("GET", f"/api/experiments/{exp_id}/summary")
        seg  = s.get("segment_count", 0)
        rate = s.get("attack_rate", 0.0)
        conf = s.get("avg_confidence")
        model = s.get("model_version", "?")
        conf_str = f"{conf * 100:.1f}%" if conf is not None else "—"
        return seg, rate, conf_str, model
    except Exception as e:
        return 0, 0.0, "—", f"ERROR({e})"


# Default dynamic test scenarios — covering interesting transition patterns
DEFAULT_SCENARIOS = [
    {
        "label": "Normal → Positive attack",
        "phases": "0:0,20:5000",
        "seed": 42,
        "sim_time": 60,
    },
    {
        "label": "Positive → Negative attack",
        "phases": "0:5000,30:-5000",
        "seed": 42,
        "sim_time": 60,
    },
    {
        "label": "Normal → Positive → Normal",
        "phases": "0:0,20:5000,40:0",
        "seed": 42,
        "sim_time": 60,
    },
    {
        "label": "Full cycle: N → P → N → Neg → N",
        "phases": "0:0,15:5000,30:0,45:-5000,60:0",
        "seed": 42,
        "sim_time": 80,
    },
    {
        "label": "Negative → Positive (reverse)",
        "phases": "0:-5000,30:5000",
        "seed": 42,
        "sim_time": 60,
    },
]


def run_one(scenario_def: dict, dry_run: bool = False) -> dict:
    label    = scenario_def["label"]
    phases   = scenario_def["phases"]
    seed     = scenario_def.get("seed", 42)
    sim_time = scenario_def.get("sim_time", 80)

    print(f"\n{'─' * 72}")
    print(f"  {label}")
    print(f"  phases={phases}  seed={seed}  sim_time={sim_time}s")
    print(f"{'─' * 72}")

    if dry_run:
        print("  [DRY RUN — skipping]")
        return {"label": label, "phases": phases, "outcome": "dry-run"}

    # Cancel any active run
    status = api("GET", "/api/run/status")
    if status.get("active"):
        print("  ! Active run detected — cancelling …")
        api("POST", "/api/run/cancel")
        time.sleep(8)

    payload = {
        "scenario":        "dynamic",
        "phases":          phases,
        "seed":            seed,
        "sim_time":        sim_time,
        "bias":            0,
        "num_ap":          1,
        "num_sta":         2,
        "segment_length":  256,
        "gcn_version":     "v3.0.0",
    }

    print(f"  Launching …  {datetime.now().strftime('%H:%M:%S')}")
    resp   = api("POST", "/api/run/launch", payload)
    exp_id = resp.get("experiment_id", "")
    if not exp_id:
        print(f"  ERROR launching: {resp}")
        return {"label": label, "phases": phases, "outcome": "failed"}

    print(f"  experiment_id: {exp_id}")
    outcome = wait_for_completion(exp_id)
    print(f"  outcome: {outcome}   ({datetime.now().strftime('%H:%M:%S')})")

    if outcome != "success":
        return {"label": label, "phases": phases, "exp_id": exp_id, "outcome": outcome}

    seg, rate, conf_str, model = check_result(exp_id)
    print(f"  segments={seg}  attack_rate={rate:.3f}  avg_conf={conf_str}  model={model}")
    print(f"  → {rate:.1%} of windows flagged as attack")
    print(f"     (phases: {phases})")

    return {
        "label":       label,
        "exp_id":      exp_id,
        "phases":      phases,
        "outcome":     outcome,
        "segments":    seg,
        "attack_rate": rate,
        "confidence":  conf_str,
        "model":       model,
        "seed":        seed,
        "sim_time":    sim_time,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run dynamic-phase experiments and observe GCN predictions."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--phases", type=str, default=None,
        help="Run a single custom phase schedule instead of the default test suite",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sim-time", type=int, default=80)
    args = parser.parse_args()

    if args.phases:
        scenarios = [{"label": f"Custom: {args.phases}", "phases": args.phases,
                      "seed": args.seed, "sim_time": args.sim_time}]
    else:
        scenarios = DEFAULT_SCENARIOS

    print(f"\nDynamic Scenario Test — {len(scenarios)} experiments")
    print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.dry_run:
        print("[DRY RUN]\n")

    results = []
    for i, s in enumerate(scenarios, 1):
        print(f"\nProgress: {i}/{len(scenarios)}")
        result = run_one(s, dry_run=args.dry_run)
        results.append(result)
        if not args.dry_run and i < len(scenarios):
            time.sleep(12)

    print(f"\n{'═' * 72}")
    print("  DYNAMIC SCENARIO TEST SUMMARY")
    print(f"{'═' * 72}")
    for r in results:
        rate = r.get('attack_rate')
        rate_str = f"atk={rate:.2f}" if rate is not None else ""
        seg_str  = f"seg={r.get('segments', 0)}" if r.get('segments') else ""
        print(f"  {'✓' if r['outcome'] == 'success' else '!'} [{r['phases']}]  {r['label']}")
        if seg_str or rate_str:
            print(f"      {seg_str}  {rate_str}")
    print(f"{'═' * 72}\n")

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = f"/tmp/dynamic-test-{ts}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved: {out_path}\n")


if __name__ == "__main__":
    main()
