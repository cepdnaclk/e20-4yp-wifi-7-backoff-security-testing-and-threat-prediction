#!/usr/bin/env bash
# convert_mlo_json_to_jsonl.sh
# Converts MLO JSON array output to pipeline-compatible JSONL format
#
# Usage: ./convert_mlo_json_to_jsonl.sh <json_file> <exp_id> <start_time_iso>
#
# Example:
#   ./convert_mlo_json_to_jsonl.sh mlo_output.json 20260103-1400-mlo-normal-42 2026-01-03T14:00:00+00:00

set -euo pipefail

JSON_FILE="${1:-}"
EXP_ID="${2:-}"
START_TIME="${3:-}"

if [ -z "${JSON_FILE}" ] || [ -z "${EXP_ID}" ] || [ -z "${START_TIME}" ]; then
    echo "Usage: $0 <json_file> <exp_id> <start_time_iso>"
    echo "Example: $0 mlo_output.json 20260103-1400-mlo-normal-42 2026-01-03T14:00:00+00:00"
    exit 1
fi

if [ ! -f "${JSON_FILE}" ]; then
    echo "ERROR: JSON file not found: ${JSON_FILE}"
    exit 1
fi

# Output file in same directory as input
OUT_DIR="$(dirname "${JSON_FILE}")"
OUT_FILE="${OUT_DIR}/telemetry.jsonl"

echo "Converting ${JSON_FILE} to JSONL format..."
echo "  Experiment ID: ${EXP_ID}"
echo "  Start time: ${START_TIME}"

# Use Python for conversion (available in ns-3 container, jq may not be)
python3 << PYTHON_SCRIPT
import json
import sys
from datetime import datetime, timedelta, timezone

json_file = "${JSON_FILE}"
exp_id = "${EXP_ID}"
start_time_str = "${START_TIME}"
out_file = "${OUT_FILE}"

# Parse start time
try:
    # Handle various ISO formats
    start_time_str = start_time_str.replace('+00:00', 'Z').replace('+0000', 'Z')
    if start_time_str.endswith('Z'):
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
    else:
        start_time = datetime.fromisoformat(start_time_str)
except Exception as e:
    print(f"Warning: Could not parse start time '{start_time_str}', using current time")
    start_time = datetime.now(timezone.utc)

# Window interval
WINDOW_INTERVAL = 0.1  # seconds

# Metrics to extract with their units
METRICS = {
    "net_throughput_mbps": "Mbps",
    "net_avg_delay_ms": "ms",
    "net_avg_jitter_ms": "ms",
    "net_packet_loss_ratio": "ratio",
    "net_active_flows": "count",
    "mac_total_tx": "count",
    "mac_total_rx": "count",
    "mac_total_ack": "count",
    "mac_total_retrans": "count",
    "mac_drop_count": "count",
    "phy_drop_count": "count",
    "avg_backoff_slots": "slots",
    "channel_busy_ratio": "ratio",
}

# Read JSON
with open(json_file, 'r') as f:
    windows = json.load(f)

# Convert to JSONL
output_lines = []
for window in windows:
    window_idx = window.get("window", 0)
    ts = start_time + timedelta(seconds=window_idx * WINDOW_INTERVAL)
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{int(ts.microsecond/1000):03d}Z"

    for metric_name, unit in METRICS.items():
        value = window.get(metric_name, 0)
        line = json.dumps({
            "experiment_id": exp_id,
            "ts": ts_str,
            "source": "ns3",
            "schema_version": "v0.1",
            "entity_id": "network",
            "metric": metric_name,
            "value": value,
            "unit": unit
        }, separators=(',', ':'))
        output_lines.append(line)

# Write output
with open(out_file, 'w') as f:
    f.write('\n'.join(output_lines))
    if output_lines:
        f.write('\n')

print(f"Wrote {len(output_lines)} metrics to {out_file}")
print(f"  Windows: {len(windows)}")
print(f"  Metrics per window: {len(METRICS)}")
PYTHON_SCRIPT

# Verify output
if [ ! -f "${OUT_FILE}" ]; then
    echo "ERROR: JSONL output not created"
    exit 1
fi

LINE_COUNT=$(wc -l < "${OUT_FILE}")
echo "Conversion complete: ${LINE_COUNT} lines written to ${OUT_FILE}"
