#!/usr/bin/env bash
set -euo pipefail

EXP_ID="${1:-}"
SEED="${2:-42}"

if [ -z "${EXP_ID}" ]; then
  echo "EXP_ID required. Usage: ./run_wifi_example_and_export.sh <EXP_ID> [SEED]"
  exit 1
fi

OUT_DIR="/work/sim/ns3/artifacts/${EXP_ID}"
mkdir -p "${OUT_DIR}"

{
  echo "exp_id=${EXP_ID}"
  echo "seed=${SEED}"
  echo "ns3_version=$(cat /opt/ns-3-dev/VERSION)"
  echo "git_sha=$(cd /work && git rev-parse --short HEAD 2>/dev/null || echo unknown)"
  date -Iseconds
} > "${OUT_DIR}/meta.txt"

TS_NOW="$(date -Iseconds)"

SRC_FILE="/work/sim/ns3/scratch/ndt_wifi_example.cc"
DST_FILE="/opt/ns-3-dev/scratch/ndt_wifi_example.cc"

if [ ! -f "${SRC_FILE}" ]; then
  echo "ERROR: missing source file in repo: ${SRC_FILE}"
  echo "Create it at: sim/ns3/scratch/ndt_wifi_example.cc"
  exit 1
fi

cp -f "${SRC_FILE}" "${DST_FILE}"

echo "Running ns-3 scratch program: scratch/ndt_wifi_example.cc"

set +e
cd /opt/ns-3-dev
./ns3 run "scratch/ndt_wifi_example.cc" -- --seed="${SEED}" \
  > "${OUT_DIR}/ns3_stdout.log" \
  2> "${OUT_DIR}/ns3_stderr.log"
rc=$?
set -e

echo "scratch/ndt_wifi_example.cc" > "${OUT_DIR}/example_used.txt"

if [ $rc -ne 0 ]; then
  echo "ERROR: ns-3 program failed"
  exit 1
fi

THROUGHPUT_Mbps="$(
  grep -Ei 'Throughput:' "${OUT_DIR}/ns3_stdout.log" \
  | grep -Eo '([0-9]+(\.[0-9]+)?)' \
  | tail -n 1 || true
)"
[ -z "${THROUGHPUT_Mbps}" ] && THROUGHPUT_Mbps="0.0"

cat > "${OUT_DIR}/telemetry.jsonl" <<EOF
{"experiment_id":"${EXP_ID}","ts":"${TS_NOW}","source":"ns3","schema_version":"v0.1","entity_id":"sim","metric":"throughput_mbps","value":${THROUGHPUT_Mbps},"unit":"Mbps"}
EOF

echo "Telemetry written to ${OUT_DIR}/telemetry.jsonl"
