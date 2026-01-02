# Session Context

## Last Updated
[Initial setup - not yet used]

## Project State
- **Current WP:** WP6 Complete, WP7 Next
- **Pipeline Status:** Working (manual operation)
- **Last Successful Run:** See `docs/CURRENT-STATE.md`

---

## Quick Reference

### What's Complete (WP1-WP6)
```
ns-3 → telemetry.jsonl → Exporter → Kafka → Harmonizer → DB → Grafana
```

### What's Next (WP7+)
- WP7: One-command pipeline
- WP8: Multi-scenario support
- WP9+: Security, AI

---

## Session Summary
This is the initial context file. No sessions have been run yet.

For full project context, read:
- `docs/CURRENT-STATE.md` - Complete current state
- `docs/BLUEPRINT.md` - Full implementation plan
- `docs/ALL-ADRS.md` - All architectural decisions

---

## Completed Recently
[No recent sessions]

## In Progress
[Nothing in progress]

---

## Next Session Should

### Priority 1: Start WP7
One-command pipeline implementation
- Create docker-compose for exporter + harmonizer
- Add Makefile targets: `pipeline-up`, `pipeline-down`, `run-exp`
- Test end-to-end with multiple experiments

### Priority 2: Review WP7 Plan
If a plan exists at `.claude/docs/plans/wp7-*.md`, review it first.

### Priority 3: Update Documentation
After completing WP7, run `/update-docs WP7`

---

## Commands to Run First
```bash
# Check if lab is running
make status

# If not running, start it
make up

# Verify DB has data from previous experiments
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "SELECT COUNT(*) FROM metrics;"
```

---

## Important Context
- Pipeline is currently **manual** - each step must be run separately
- WP7 goal is to make it **one-command**
- All documentation is in `docs/` folder
- ADRs should be created for significant decisions

---

## Documentation Status
| Document | Status | Notes |
|----------|--------|-------|
| `docs/CURRENT-STATE.md` | ✅ Current | Full project state |
| `docs/BLUEPRINT.md` | ✅ Current | Implementation plan |
| `docs/ALL-ADRS.md` | ✅ Current | 18 ADRs documented |
| `docs/WP1-6-*.md` | ✅ Current | All WP docs complete |
| `docs/QUICK-REFERENCE.md` | ✅ Current | Commands cheat sheet |

---

## Related Documents
- Full state: `docs/CURRENT-STATE.md`
- Blueprint: `docs/BLUEPRINT.md`
- ADRs: `docs/ALL-ADRS.md`
- Quick ref: `docs/QUICK-REFERENCE.md`
