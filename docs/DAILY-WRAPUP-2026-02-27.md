# Daily Wrap-Up - 2026-02-27

## Session Metadata
- Date (local): 2026-02-27
- Wrap-up time (local): 2026-02-27T07:46:01+05:30
- Wrap-up time (UTC): 2026-02-27T02:16:01+00:00
- Repository: `ndt-wifi7-mlo-security`

## Goal for Today
- Investigate why digital twin predictions were incorrect.
- Compare with the working pure GCN repo (`wifi7_gcn_attack_detection`).
- Fix root causes in pipeline inference path and validate end-to-end behavior.

## Completed Today
1. Performed root-cause analysis across both repositories.
2. Confirmed `v2.1.0` model artifacts were identical across repos (weights/scaler/config checksums).
3. Identified two key issues:
   - Windowizer batch-boundary corruption (partial windows were zero-filled and emitted as separate windows).
   - Active model symlink drift to `v2.1.0` (distribution mismatch for pipeline deployment).
4. Implemented windowizer/data fixes:
   - Added cross-batch pending window merge.
   - Added ordered pending-window processing by timestamp per entity.
   - Added timeout-based release of incomplete windows.
   - Added pending-window flush on shutdown.
5. Aligned delta conversion semantics with training:
   - First-window delta now uses first cumulative value (training-compatible), not `0.0`.
6. Switched active model to pipeline-trained version:
   - `twin/registry/gcn/current` -> `v2.0.0`.
7. Rebuilt and restarted pipeline services:
   - `windowizer`, `gcn-detector`, and `harmonizer`.
8. Verified live detector health and model loading:
   - `gcn-detector` healthy.
   - Logs confirmed model loaded from `/app/registry/v2.0.0`.

## Code Changes Made
- `security/detector/windowizer/windowizer.py`
  - Added pending window state and merge logic.
  - Added `_merge_pending_windows(...)`.
  - Added `_process_pending_windows(...)`.
  - Updated main loop to flush timed-out pending windows.
  - Updated shutdown to flush pending windows before exit.
- `security/detector/windowizer/delta_converter.py`
  - Changed first-window delta assignment from `0.0` to `current_value`.
- `twin/registry/gcn/current`
  - Updated symlink target from `v2.1.0` to `v2.0.0`.

## Validation Completed
### Offline replay validation (post-fix)
- Normal telemetry: `0/7` attack predictions (0.0%).
- Negative attack telemetry: `7/7` attack predictions (100.0%).
- Positive attack telemetry: `7/7` attack predictions (100.0%).

### Live pipeline checks
- Containerlab infra verified running (Redpanda, TimescaleDB, Grafana).
- Pipeline services restarted successfully.
- `gcn-detector` logs confirmed `Model loaded successfully: v2.0.0`.
- `/health` returned healthy state.

## Partial / In-Progress at Wrap-Up
- Live end-to-end replay for all three validation experiments was in progress.
- Normal validation telemetry replay completed successfully with full exporter delivery (`26,000` messages).
- Attack replay verification was interrupted before final DB summary was recorded.

## Operational Issues Encountered
- Several runs were interrupted during long-running commands.
- `make run-mlo-exp` uses a long simulation default and `-it` behavior; one run was interrupted and produced partial conversion output.
- A stale long-running exporter container (`ndt/ns3-exporter:local`, name `competent_golick`) interfered with clean replay control.

## Recommended Next Session Start
1. Ensure no stale exporter containers are running.
2. Replay `20260215-validation-attack-neg-01` and `20260215-validation-attack-pos-01` telemetry with isolated exporter state.
3. Run final DB verification query on `gcn_predictions`:
   - Normal expected near 0% attack rate.
   - Attack scenarios expected high attack rate.
4. Archive query outputs/screenshots into docs if needed.

