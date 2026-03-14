# Daily Wrapup — 2026-03-13

**Work Package:** WP12 — GCN v3 Multi-AP Training + Dashboard Experiment Launcher
**Session date:** 2026-03-13
**Branch:** main (2 commits ahead of origin/main)

---

## What Was Done

### WP12 Phase 1 — NS-3 multi-AP simulation support (COMPLETE)
Extended all three NS-3 scenario files (`wifi7-mlo-{Normal,Positive,Negative}.cc`) with `--nAp`, `--nSta`, and `--seed` command-line arguments. These values are now written into the JSON window output as `num_ap` and `num_sta` fields, making each training sample AP-count-aware.

Updated `run_mlo_scenario.sh` to pass `NAP`, `NSTA`, and `SEED` env vars into the Docker container, and added a `V3_COLLECT` copy hook so completed runs are automatically copied to the training data directory.

Created `sim/ns3/scenario/collect_v3_data.sh` — a parallel batch script that runs 72 scenarios (nap1–6, 4 seeds, 3 scenario types) with configurable `NCPU` workers using a bash semaphore. Added the `gcn-collect-data` Makefile target as the single entry point for regenerating all v3 training data.

Removed the hardcoded Docker `-it` flag from run targets, replacing it with `$(if $(INTERACTIVE),-it,)` so containers run non-interactively when invoked from parallel subshells.

### WP12 Phase 2 — Data collection (PARTIALLY COMPLETE)
- Normal scenarios nap1–4 (16 files): complete
- Attack-positive nap1–4 (16 files): complete
- Attack-negative nap1–3 (12 files): complete
- Attack-negative nap4 (4 files): NOT collected — session ended before these completed
- nap5/6: not collected (too slow at ~2.5h per run; deferred to v3.1.0)

Current dataset: 44 files. Target for v3.0.0: 48 files (missing 4 nap4-negative).

### WP12 Phase 3 — GCN v3 training pipeline (COMPLETE)
All training code updated to support multi-AP and multi-length training:
- `preprocessing.py`: sliding-window segmentation with configurable stride, per-AP normalisation (throughput/nAp, MAC-PHY deltas/nSta), 17th segment-length conditioning feature (`log2(L)/8.0`)
- `config.py`: `in_channels=17`, `segment_lengths=[32,64,128,256]`, `segment_strides={32:32,64:64,128:128,256:64}`, `multi_ap_normalise=True`
- `train.py`: multi-length training loop iterating over all four segment lengths
- `feature_processor.py`: new `build_feature_matrix()` method with runtime multi-AP normalisation and seg-len feature; backward compatible with v2 models via scaler dimension check (`n_features_in_==16` → v2 path)
- `twin/gnn/trainer/training_v3.yaml`: complete v3 training configuration

Training has not been run yet — waiting for the 4 missing nap4-negative files.

### WP12 Phase 6 — Dashboard Experiment Launcher (COMPLETE)
Added a full "Run Experiment" section to the web dashboard:

**Backend** (`dashboard/app/backend/api/run.py`):
- `POST /run/launch`: starts an experiment as an async subprocess; returns 409 if one is already running
- `GET /run/status`: returns current stage, stdout tail, and exit code
- `POST /run/cancel`: terminates the running experiment process
- `GET /run/history`: returns past experiment runs from the runtime log

**Frontend** (`dashboard/app/frontend/src/sections/RunSection.tsx`):
- Config form: nAp (1–6), scenario (normal/positive/negative), seed, sim_time, bias, segment_length
- Live stage progress panel (polling every 2s via `GET /run/status`)
- Post-run navigation to experiment view
- Model v3 compatibility warning when segment_length != 256

`docker-compose.dashboard.yml` updated: `/repo` mounted read-only for access to Makefile; `/artifacts` changed from read-only to read-write so launched experiments can write output.

Dashboard frontend has not been rebuilt — changes are in source only. Must run `make dashboard-build && make dashboard-up`.

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| SIM_TIME | 80s (not 300s) | 300s at nap4+ takes >2.5h. 80s gives ~800 windows/file, sufficient for training with sliding window |
| nap5/6 scope | Deferred to v3.1.0 | 4 seeds × 3 scenarios × 2.5h = 30h of compute. SIM_TIME=30s strategy planned for v3.1.0 |
| Seg-len feature | 17th input: `log2(L)/8.0` | Allows one model to handle all four window sizes; avoids training separate models |
| Per-AP normalisation | Applied at train AND inference | Ensures model generalises across AP counts; feature_processor reads `num_ap` from DB |
| Docker `-it` flag | Conditional on INTERACTIVE=1 | Required for non-interactive parallel Docker runs; TTY mode still available for debugging |

---

## Dataset State at Session End

```
twin/gnn/training_data/v3/
├── Normal/     16 files  (nap1–4, seeds 42–45)  ✅ COMPLETE
├── Attack/     28 files  (nap1–3 both types, nap4 positive only)  ⚠ MISSING 4 files
└── collection.log
```

Missing: `nap4_nsta8_seed{42,43,44,45}_negative_80s.json` (4 files)

---

## What Remains for v3.0.0

1. Kill any running nap5/6 containers
2. Collect nap4-negative (4 runs, ~40 min each or parallelise with NCPU=4)
3. `make gcn-train OUTPUT_DIR=twin/registry/gcn/v3.0.0`
4. Verify `test_results.json` for F1 >= 0.92
5. `make gcn-deploy VERSION=v3.0.0`
6. `make dashboard-build && make dashboard-up`
7. Test Run Experiment section end-to-end
8. `git push origin main`

---

## Commits This Session

| Hash | Message |
|------|---------|
| `1f9f4d8` | feat(WP12): GCN v3 multi-AP training pipeline + dashboard experiment launcher |
| `35ba8ab` | fix(WP12): fix collect_v3_data.sh to invoke make (runs NS-3 via Docker) |

Both commits are on local `main`, not yet pushed.

---

## Files Changed (Summary)

**NS-3 simulation:** `sim/ns3/scratch/wifi7-mlo-{Normal,Positive,Negative}.cc`, `sim/ns3/scenario/run_mlo_scenario.sh`, `sim/ns3/scenario/collect_v3_data.sh` (new)

**GCN training:** `twin/gnn/detector/gcn_src/data/preprocessing.py`, `twin/gnn/detector/gcn_src/training/config.py`, `twin/gnn/detector/gcn_src/training/train.py`, `twin/gnn/detector/gcn_src/data/dataset.py`, `twin/gnn/detector/feature_processor.py`, `twin/gnn/trainer/training_v3.yaml` (new)

**Dashboard:** `dashboard/app/backend/api/run.py` (new), `dashboard/app/backend/main.py`, `docker-compose.dashboard.yml`, `dashboard/app/frontend/src/hooks/useRun.ts` (new), `dashboard/app/frontend/src/sections/RunSection.tsx` (new), `dashboard/app/frontend/src/App.tsx`, `dashboard/app/frontend/src/components/layout/Sidebar.tsx`

**Makefile:** 23 lines changed (new targets, new vars, non-interactive Docker flag)

**Docs:** `docs/WP12-GCN-V3-MULTI-AP-TRAINING-PLAN.md` (new, 772 lines), `docs/CURRENT-STATE.md`
