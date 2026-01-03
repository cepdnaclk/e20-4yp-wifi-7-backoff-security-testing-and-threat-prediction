# Pipeline + Wi-Fi 7 MLO Integration Notes

## Context
The existing WP7 pipeline expects ns-3 simulations to write a JSONL file at:

- sim/ns3/artifacts/<EXP_ID>/telemetry.jsonl

The exporter reads this file line-by-line and publishes each line to Kafka. The
harmonizer consumes Kafka events and writes a single row per metric into the
TimescaleDB metrics table. This contract is defined in docs/CURRENT-STATE.md.

## Why JSONL (One Metric Per Line)
- The telemetry contract is event-based: one JSON object = one metric event.
- Kafka ingestion is a stream of independent events.
- TimescaleDB schema is row-per-metric: experiment_id, ts, metric_name, value, unit.
- JSONL allows incremental streaming and resume offsets.

## Current MLO Scratch Programs
New files in sim/ns3/scratch:
- wifi7-mlo-Negative.cc
- wifi7-mlo-Normal.cc
- wifi7-mlo-Positive.cc

These programs currently write JSON arrays to hard-coded paths like:
- Wifi7_Datasets/Attack/session_2_scenario_1_bias_neg5000.json
- Wifi7_Datasets/Normal/session_2_scenario_1.json

They also define jsonPath/xmlPath CLI args but do not use them, and they do not
write telemetry.jsonl or include EXP_ID.

## Required Integration Changes
1) Keep .cc files in sim/ns3/scratch (scenario scripts live in sim/ns3/scenario).
2) Update each .cc to write to jsonPath instead of a hard-coded file path.
3) Add a new scenario runner script (e.g., sim/ns3/scenario/run_wifi7_mlo.sh)
   that:
   - Creates sim/ns3/artifacts/<EXP_ID>/
   - Runs ns-3 with the selected scratch program
   - Writes JSON output to a path inside artifacts/<EXP_ID>/
   - Converts that JSON array into telemetry.jsonl
4) Add a Makefile target to run the new scenario and then run the exporter.

## Mapping Windowed Output to Pipeline Telemetry
Each JSON object in the array represents a time window. The pipeline requires
one metric per JSONL line. So each window row must be expanded to multiple
metric events.

Example source row (one window):
- {"window":0, "net_throughput_mbps":..., "net_avg_delay_ms":..., ...}

Example JSONL output (multiple lines, same timestamp):
- {"metric":"net_throughput_mbps","value":123.4,...}
- {"metric":"net_avg_delay_ms","value":5.6,...}
- {"metric":"net_packet_loss_ratio","value":0.01,...}

## Preserving Window Identity
Recommended: derive timestamps from window index.
- ts = start_time + (window_index * 0.1s)
- All metrics from the same window share the same ts.

Alternative options:
- Emit a separate metric line for window_index
- Extend schema to add a window field (requires harmonizer+DB changes)

## Recommendation for GNN Training
ToDo : The the original JSON array output is used for GNN datasets. but the gnn also will be needed to intergrate into this pipeline. So will have to comeup with a way to do that later and while generate
telemetry.jsonl for pipeline ingestion. This preserves full fidelity while
integrating with the existing Kafka/DB/Grafana flow. ( see the buleprint and suggessted workflow if need)
