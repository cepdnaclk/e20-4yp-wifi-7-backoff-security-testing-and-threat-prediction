# ndt-wifi7-mlo-security

Digital twin implementation for Wi-Fi 7 / MLO backoff manipulation detection and mitigation.

## Repo structure (high level)
- clab/        Containerlab topology and service wiring
- sim/ns3/     ns-3 scenarios and telemetry outputs
- telemetry/   exporters + contracts + harmonizer (raw -> UDM)
- udr/         database + API + feature store
- security/    detector + policy + actuation/rollback
- twin/        GNN training/inference + model registry
- dashboard/   Grafana dashboards and optional UI
- experiments/ scenario matrices and runners
- docs/        ADRs and runbooks

## Conventions
- Every run must have an Experiment ID (EXP_ID).
- Do not commit artifacts/results (see .gitignore).
- main must always be runnable. Use feature branches + PRs.
