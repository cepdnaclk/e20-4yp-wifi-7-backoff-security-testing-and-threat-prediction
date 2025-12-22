#!/usr/bin/env bash
set -euo pipefail

EXP_ID="${1:-}"
SEED="${2:-42}"

if [ -z "${EXP_ID}" ]; then
  echo "EXP_ID required. Usage: ./run_baseline.sh <EXP_ID> [SEED]"
  exit 1
fi

OUT_DIR="/work/sim/ns3/artifacts/${EXP_ID}"
mkdir -p "${OUT_DIR}"

echo "exp_id=${EXP_ID}" > "${OUT_DIR}/meta.txt"
echo "seed=${SEED}" >> "${OUT_DIR}/meta.txt"
date -Iseconds >> "${OUT_DIR}/meta.txt"

# Placeholder telemetry JSONL. WP3 goal: prove the pipeline writes per EXP_ID.
# In the next increment we will generate real telemetry from ns-3 traces.
cat > "${OUT_DIR}/telemetry.jsonl" <<EOF
{"experiment_id":"${EXP_ID}","ts":"$(date -Iseconds)","source":"ns3","schema_version":"v0.1","entity_id":"sta-1","metric":"throughput_mbps","value":0.0,"unit":"Mbps"}
{"experiment_id":"${EXP_ID}","ts":"$(date -Iseconds)","source":"ns3","schema_version":"v0.1","entity_id":"sta-2","metric":"throughput_mbps","value":0.0,"unit":"Mbps"}
EOF

echo "Wrote: ${OUT_DIR}/telemetry.jsonl"
