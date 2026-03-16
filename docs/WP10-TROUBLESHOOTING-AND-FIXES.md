# WP10: Pipeline and Dashboard Troubleshooting Log

This document summarizes the troubleshooting and fixes applied to the NDT Wi-Fi 7 MLO Security pipeline and the Custom Dashboard to ensure the end-to-end simulation flow works as expected.

## 1. Simulation Freezing / Hanging (Docker Daemon)
**Issue:** Running `make run-exp` or `make run-mlo-exp` caused the Docker daemon to lock up. All `docker` commands (such as `docker ps` and `docker info`) became unresponsive, and terminal commands trying to interact with the mounted volumes hung indefinitely.
**Fix:** Restarted the Docker daemon on the host (`sudo systemctl restart docker`). Additionally, to avoid permission issues when running the `ns-3` docker image, directory permissions for the generated simulation artifacts were updated so the Docker container has proper write access.

## 2. Excessive Simulation Time
**Issue:** The `ns-3` MLO scenario was taking over an hour to finish.
**Root Cause:** The default simulation time inside `sim/ns3/scenario/run_mlo_scenario.sh` was hardcoded to `1400.0` seconds instead of a small value for testing.
**Fix:** Modified `sim/ns3/scenario/run_mlo_scenario.sh` to set `SIM_TIME="${5:-30.0}"` by default, reducing the simulation runtime to a rapid 30 seconds for quick end-to-end testing.

## 3. Missing Kafka Topics
**Issue:** The `exporter` service crashed at startup with a `FATAL ERROR: Kafka topic 'wifi7.telemetry.v0_1' does not exist`. 
**Fix:** Initialized the required Kafka topics. Running `make kafka-init` and `make kafka-topics-create` ensured all data ingestion pipes for both normal telemetry and GCN features were properly created in the Redpanda broker.

## 4. Exporter State Permission Denied
**Issue:** The `exporter` service successfully read the simulation data but crashed with `PermissionError: [Errno 13] Permission denied: '/state/exporter_state.json'` when attempting to save the offset.
**Fix:** The `.exporter_state` directory on the host lacked appropriate write permissions for the container user. Fixed by running `sudo chmod -R 777 .exporter_state`.

## 5. Dashboard "Model Intelligence" Tab Returning 404
**Issue:** 
The Dashboard UI's "Model Intelligence" tab was completely failing to load and instead showed a `404 Not Found` error.
**Root Causes & Fixes Applied:**
1. **API Route Mismatch:** The frontend was requesting `/api/models/inference-stats`, but the backend was mapped to `/api/models/active/inference_stats`. Corrected the FastAPI route in `dashboard/app/backend/api/models.py`.
2. **Postgres Syntax Error:** The backend `inference-stats` route was crashing internally due to a Postgres error: `operator does not exist: bigint % unknown`. The `PERCENTILE_CONT()` statistical function requires floating point inputs, but the database schema uses an integer for `inference_time_ms`. Fixed the query in `dashboard/app/backend/db/queries.py` by casting the column: `ORDER BY inference_time_ms::float`.
3. **Registry Path Misconfiguration:** The `/api/models/active` route was returning 404 because the API backend couldn't locate the GCN models registry on disk. In `docker-compose.dashboard.yml`, the environment variable was named `REGISTRY_PATH`, but the backend code expected `GCN_REGISTRY_PATH`. Fixed the variable name in the Docker compose file.
4. **Rebuild:** Rebuilt the `ndt/dashboard:local` Docker image and restarted the dashboard container to apply the backend fixes.

---

**Summary Strategy for Future Runs:**
If the pipeline ever fails to start correctly, generally verify:
1. Ensure the simulation time is reasonably bounded (`SIM_TIME`).
2. Verify Kafka topics exist (`make kafka-list`).
3. Guarantee that mounted state and artifact directories are writable (`sudo chmod -R 777`).
4. Rebuild the dashboard image if backend code modifications are expected but missing.
