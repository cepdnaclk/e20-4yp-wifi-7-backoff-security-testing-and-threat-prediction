# CLAUDE.md - NDT Wi-Fi 7 MLO Security Project

This file provides guidance to Claude Code when working with this repository.

---

## Project Overview

Digital twin implementation for Wi-Fi 7 / MLO (Multi-Link Operation) backoff manipulation detection and mitigation. Currently at **WP6 complete** - full telemetry pipeline working.

### Current State (Quick)
```
✅ WP1-WP6: Complete pipeline working
   ns-3 → telemetry.jsonl → Exporter → Kafka → Harmonizer → DB → Grafana

🔲 WP7: One-command pipeline (NEXT)
🔲 WP8+: Multi-scenario, security, AI
```

---

## Documentation System

### Primary Context Files (READ THESE FIRST)
| File | Purpose | When to Read |
|------|---------|--------------|
| `docs/CURRENT-STATE.md` | Complete project state | Start of any session |
| `docs/BLUEPRINT.md` | Full implementation plan | Planning new WPs |
| `docs/ALL-ADRS.md` | All architecture decisions | Before making design choices |
| `docs/QUICK-REFERENCE.md` | Commands cheat sheet | Quick lookups |

### Work Package Documentation
| File | Content |
|------|---------|
| `docs/WP1-LOCAL-DEV-SETUP.md` | GitHub SSH, gh CLI |
| `docs/WP2-CONTAINERLAB-SKELETON.md` | Containerlab, services |
| `docs/WP3-NS3-INTEGRATION.md` | ns-3.46.1, telemetry |
| `docs/WP4-TELEMETRY-EXPORTER.md` | File → Kafka |
| `docs/WP5-HARMONIZER.md` | Kafka → DB |
| `docs/WP6-GRAFANA-DASHBOARDS.md` | Dashboards |

### ADRs (Architecture Decisions)
All decisions in `docs/adr/` - check before making architectural changes.

---

## Sub-Agent System

### Available Agents
| Agent | Purpose | When to Use |
|-------|---------|-------------|
| `@planner` | Research codebase, create implementation plans | Before complex features |
| `@reviewer` | Check code quality, find issues | After implementation |
| `@wrapper` | Create session summaries for continuity | End of work session |
| `@documenter` | Update project documentation | After completing features |

### Delegation Rules
1. **Sub-agents RESEARCH and PLAN** - they never implement code
2. **Parent agent IMPLEMENTS** - all code changes happen here
3. **Context shared via files** - `.claude/docs/context/current-session.md`
4. **ADRs created by parent** - ask parent to document decisions

### When to Use Sub-Agents
- Complex new feature → `@planner` first
- After completing implementation → `@reviewer`
- End of work session → `@wrapper`
- After completing a WP → `@documenter`

---

## Session Workflow

### Starting a Session
```
/resume
```
This reads context and shows what to work on.

### Before Complex Work
```
/plan WP7 one-command pipeline
```
Creates detailed implementation plan.

### After Implementation
```
/review
```
Checks code quality.

### End of Session
```
/wrapup completed WP7 step 1-3
```
Saves context for next session.

### After Completing a WP
```
/update-docs WP7
```
Updates documentation to reflect new state.

---

## Build & Run Commands

### Infrastructure (Containerlab)
```bash
make up        # Deploy topology
make down      # Destroy topology
make status    # Check status
make logs      # View logs
```

### NS-3 Simulation
```bash
make ns3-build                    # Build image
make ns3-run EXP_ID=...           # Run baseline
make ns3-run-example EXP_ID=...   # Run WiFi example
```

### Telemetry Pipeline
```bash
make exporter-build               # Build exporter
make harmonizer-build             # Build harmonizer
make exporter-run EXP_ID=...      # Publish to Kafka
make harmonizer-run               # Ingest to DB
```

### Experiment ID Format
```
YYYYMMDD-HHMM-<scenario>-<seed>
Example: 20251230-1400-wifi-example-42
```

---

## Architecture

### Data Flow
```
NS-3 → telemetry.jsonl → Exporter → Redpanda → Harmonizer → TimescaleDB → Grafana
```

### Key Directories
```
sim/ns3/           - Simulation scenarios and artifacts
telemetry/         - Exporters, harmonizer, contracts
clab/              - Containerlab topology and configs
udr/               - Database schemas and API
security/          - Detection, policy, actuation (future)
twin/gnn/          - GNN models (future)
docs/              - All documentation (WPs, ADRs, etc.)
.claude/           - Claude Code agent configuration
```

### Services (clab-mgmt network)
| Service | Container | Port |
|---------|-----------|------|
| Redpanda | `clab-...-bus-redpanda` | 9092 |
| TimescaleDB | `clab-...-udr-db` | 5432 |
| Grafana | `clab-...-grafana` | 3000 |

---

## Development Rules

### Git Workflow
- Never work directly on `main`
- Feature branches: `feat/<wp>-<description>`
- Clear commit messages referencing WP number
- `main` must always be runnable

### Code Standards
- Python: Type hints, docstrings
- Run with `--user "$(id -u):$(id -g)"` to avoid root-owned files
- All services must be reproducible via Makefile

### Documentation Requirements
- Update relevant WP doc when completing work
- Create ADR for significant decisions
- Run `/wrapup` at end of each session

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Exporter publishes nothing | Delete `.exporter_state/exporter_state.json` |
| Harmonizer: no DB changes | New consumer group with `earliest` |
| Grafana: no data | Check time range, verify DB rows |
| Permission denied | Run with host user mapping |
| Container networking | Use `--network clab-mgmt` |

---

## Context Management

### Session Context File
`.claude/docs/context/current-session.md` - Updated by `@wrapper` agent

### What Gets Tracked
- Completed tasks
- In-progress work
- Decisions made
- Next priorities
- Blockers/issues

### Continuity Between Sessions
1. End session with `/wrapup`
2. Start next session with `/resume`
3. Full context is preserved
