# Research Evidence and Results Digest (Updated)

This file consolidates concrete evidence points for your final report/paper drafting.

## 1. Chronology Snapshot (Repository docs)

- **2026-02-12**: WP8 live integration tests and dashboard visibility checks (`WP8-LIVE-TEST-FINAL-SUMMARY.md`).
- **2026-02-13**: WP8 final recommendation favors retraining; WP9 pilot planning and execution docs created.
- **2026-02-15**: pipeline/model investigations (`GCN-MODEL-ANALYSIS.md`, `PIPELINE-FIX-SUMMARY.md`, `GCN-MODEL-v2.1.0-DEPLOYMENT.md`, `ROOT-CAUSE-ANALYSIS-COMPLETE.md`).
- **2026-02-27**: additional dashboard/pipeline state wrap-up docs.

---

## 2. Scenario-Level Behavioral Evidence

From project docs and summaries:

| Scenario | Bias | Typical effect in docs |
|---|---:|---|
| Normal | 0 | Baseline MLO behavior |
| Positive attack | +5000 | Backoff inflation, major throughput collapse |
| Negative attack | -5000 | Aggressive access, altered fairness and throughput |

Frequently cited observed direction:
- Positive attack: strong backoff increase and severe throughput degradation.
- Negative attack: lower backoff with still-degraded/unstable performance behavior.

---

## 3. Telemetry and Segment Math

## 3.1 Event expansion logic

- Converter emits **13 metrics per window**.
- Window interval is **0.1s**.
- Example: 2000 windows -> ~26,000 metric events.

## 3.2 Segmenting logic

- Segment length: **256 windows**.
- Approximate segments from 2000 windows: ~7 complete segments (non-overlapping).
- Approximate segments from 14,000 windows: ~54 complete segments.

---

## 4. Dataset Artifacts Observed in This Workspace

## 4.1 Pilot set (`training_data/scenarios`)

Observed local counts:

| Class | Count |
|---|---:|
| Normal | 14 |
| Positive attack | 8 |
| Negative attack | 7 |
| **Total** | **29** |

Manifest summary (`training_data/manifest_pilot.csv`):
- `pilot_total=29`
- `pilot_normal=14`
- `pilot_positive=8`
- `pilot_negative=7`

## 4.2 Extended set (`training_data_extended/scenarios`)

Observed local counts:

| Class | Count |
|---|---:|
| Normal | 123 |
| Positive attack | 68 |
| Negative attack | 64 |
| **Total** | **255** |

Manifest summary (`training_data_extended/manifest.csv`):
- `extended_total=257`
- `extended_normal=123`
- `extended_positive=70`
- `extended_negative=64`

Network-type grouping in manifest:
- `light=44`
- `moderate=165`
- `dense=25`
- `very_dense=23`

### Evidence note

Your scripts and docs often target **~284 combined scenarios** (pilot + extended), but local staged JSON files currently show nearby, not exact, counts. Mention this as a data-packaging consistency issue.

---

## 5. Model Registry Evidence

Registry folders present:
- `v1.0.0`
- `v2.0.0`
- `v2.1.0`

`current` marker in this checkout: plain file with `v2.0.0`.

`test_results.json` values found in all three version folders are currently identical in this workspace:

- Accuracy: `0.9948717948717949`
- Precision: `0.9886363636363636`
- Recall: `1.0`
- F1: `0.9942857142857143`
- AUC: `1.0`
- Confusion matrix: `[[107,1],[0,87]]`

### Evidence note

Narrative docs describe version-by-version behavior changes; artifact files currently look duplicated. Treat version-performance claims carefully and ground them in dated run logs where possible.

---

## 6. Pipeline/Model Debugging Evidence Highlights

## 6.1 Confirmed engineering fixes

- Delta-field rename alignment fixed in windowizer (`delta_converter.py`).
- Detector feature keys updated to delta-based names (`feature_processor.py`).
- DB schema for predictions and model registry exists (`003_gcn_schema.sql`).
- Dashboard/backend troubleshooting items documented in WP10 notes.

## 6.2 Root-cause investigation narrative

A major documented hypothesis in `ROOT-CAUSE-ANALYSIS-COMPLETE.md`:
- High apparent offline model metrics can coexist with poor production behavior if training “normal” distribution is unrealistic vs deployment normal distribution.

This is a strong paper point under domain shift / dataset representativeness.

---

## 7. Evidence from Newly Added Notes (Your Readme-Files)

## 7.1 Dataset notes

- Strong class-separation signatures in delay/loss/throughput/backoff were observed.
- Explicit mention of class imbalance risk and recommended mitigation.

## 7.2 GNN notes

- Method framed as graph over temporal windows with node features and temporal adjacency.
- Emphasis on clean code modularization and data-loader design.

## 7.3 MLO notes

- Clear rationale for backoff-bias based attack emulation.
- KPI instrumentation across network + MAC + PHY layers.
- Code evolution logs support iterative maturity and bug-fix progression.

---

## 8. Suggested Quantitative Reporting Blocks for Final Paper

Use these blocks in results tables/figures:

1. **Scenario Effects Table**
- Normal vs positive vs negative bias with throughput/backoff/delay/loss deltas.

2. **Pipeline Throughput Table**
- windows -> events -> segments conversion counts per run.

3. **Model Quality Table**
- Offline test metrics + online false-positive observations by experiment type.

4. **Dataset Composition Table**
- Pilot + extended counts by class and network-type.

5. **Stability/Robustness Table**
- List of fixed issues (field mismatch, schema/path issues, operational bugs) and observed impact.

---

## 9. Citable Internal Evidence File Set

Core references inside repo:
- `docs/WP8-LIVE-TEST-FINAL-SUMMARY.md`
- `docs/WP8-FINAL-RECOMMENDATION.md`
- `docs/GCN-MODEL-ANALYSIS.md`
- `docs/PIPELINE-FIX-SUMMARY.md`
- `docs/GCN-MODEL-v2.1.0-DEPLOYMENT.md`
- `docs/ROOT-CAUSE-ANALYSIS-COMPLETE.md`
- `docs/CURRENT-STATE.md`
- `scripts/generate_pilot_data.sh`
- `scripts/generate_extended_dataset.sh`
- `scripts/prepare_full_dataset.sh`

Plus your new context additions:
- `Pathum - Work in progress/Readme-Files/Datasets/*`
- `Pathum - Work in progress/Readme-Files/GNNs/*`
- `Pathum - Work in progress/Readme-Files/MLOs/*`
- `Pathum - Work in progress/Literature review.txt`

