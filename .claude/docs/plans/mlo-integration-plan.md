# Implementation Plan: Wi-Fi 7 MLO Files Integration into Telemetry Pipeline

## Date
2026-01-03

## Objective
Integrate the three new ns-3 MLO scratch programs (wifi7-mlo-Normal.cc, wifi7-mlo-Positive.cc, wifi7-mlo-Negative.cc) into the existing WP7 telemetry pipeline without breaking the path to WP8 multi-scenario support. This is **WP7.5** - a bridge between WP7 and WP8.

---

## Executive Summary

**Key Finding**: The codex suggestions **overcomplicate** the solution. The minimal approach is:
1. Fix **ONE line** in each .cc file (make `jsonPath` CLI arg work)
2. Create converter script (bash/jq transformation)
3. Create scenario runner (follows WP3 pattern)
4. Add Makefile targets

**Why this is better**:
- Preserves GNN training workflow (original JSON arrays untouched)
- Simple bash/jq vs complex C++ changes
- Clear separation: simulation vs pipeline concerns
- Follows existing WP3/WP7 patterns

---

## Analysis of New Files

### 1. wifi7-mlo-Normal.cc
- **Purpose**: Baseline Wi-Fi 7 MLO scenario with no attack (bias=0)
- **Topology**: 2 APs + 2 STAs, dual-band MLO (5GHz + 6GHz)
- **Traffic**: Full mesh UDP at 800 Mbps
- **Telemetry**: 18 metrics per 0.1s window
- **Current Output**: Hardcoded to `Wifi7_Datasets/Normal/session_2_scenario_1.json`

### 2. wifi7-mlo-Positive.cc
- **Purpose**: Attack scenario with positive backoff bias (+5000)
- **Mechanism**: Increases MinCW → more aggressive transmission
- **Current Output**: Hardcoded to `Wifi7_Datasets/Attack/session_2_scenario_1_bias_5000.json`

### 3. wifi7-mlo-Negative.cc
- **Purpose**: Attack scenario with negative backoff bias (-5000)
- **Mechanism**: Decreases MinCW → extremely aggressive
- **Current Output**: Hardcoded to `Wifi7_Datasets/Attack/session_2_scenario_1_bias_neg5000.json`

### Common Pattern
All three files:
- Declare `jsonPath` CLI arg but **NEVER USE IT** (critical bug)
- Write JSON arrays (not JSONL) for GNN training
- Collect 18 metrics per 0.1s window

---

## Gap Analysis

| Aspect | Current State | Required State |
|--------|---------------|----------------|
| **Output location** | Hardcoded `Wifi7_Datasets/...` | `sim/ns3/artifacts/<EXP_ID>/` |
| **Output format** | JSON array (for GNN) | JSONL (one metric per line) |
| **Experiment ID** | Not used | Must be in every metric |
| **CLI args** | `jsonPath` declared but UNUSED | Must actually use it |
| **Pipeline integration** | None | Must produce `telemetry.jsonl` |
| **Makefile targets** | None | Need `run-mlo-*` targets |

---

## Critical Evaluation of Codex Suggestions

### Codex Suggestion 1: "Update .cc files to write JSONL directly"
**Evaluation**: ❌ **REJECTED**
- Would break existing GNN training workflow
- Requires complex C++ changes in simulation logic
- Mixes simulation concerns with pipeline concerns

**Better approach**: Keep .cc files producing JSON arrays, convert to JSONL externally.

### Codex Suggestion 2: "Convert JSON array to JSONL in scenario runner"
**Evaluation**: ✅ **CORRECT**
- Preserves original GNN dataset output
- Transformation in bash/jq (easier to maintain)
- Follows separation of concerns

### Codex Suggestion 3: "Derive timestamps from window index"
**Evaluation**: ✅ **CORRECT**
- Formula: `ts = start_time + (window_index * 0.1s)`
- All metrics from same window get same timestamp
- Essential for time-series analysis in Grafana

### Codex Suggestion 4: "Add scenario runner script"
**Evaluation**: ✅ **CORRECT**
- Matches `run_wifi_example_and_export.sh` pattern
- Follows existing project conventions

---

## Proposed Solution

### Architecture
```
.cc file (with jsonPath fix)
    ↓
JSON array output
    ↓
Scenario runner script
    ├→ Keep original JSON (for GNN training)
    └→ Convert to telemetry.jsonl (for pipeline)
         ↓
    WP7 Pipeline (Exporter → Kafka → Harmonizer → DB → Grafana)
```

### Design Principles
1. **Minimal .cc changes** - ONE line per file
2. **Dual output** - Keep JSON for GNN + generate JSONL for pipeline
3. **Transformation in bash** - Don't complicate C++ code
4. **Follow WP3/WP7 patterns** - Reuse existing approach

---

## Implementation Steps

### Step 1: Fix .cc Files (ONE LINE CHANGE)

**Files to modify**:
- `sim/ns3/scratch/wifi7-mlo-Normal.cc`
- `sim/ns3/scratch/wifi7-mlo-Positive.cc`
- `sim/ns3/scratch/wifi7-mlo-Negative.cc`

**Current code** (around line 1069):
```cpp
std::ofstream json("Wifi7_Datasets/Normal/session_2_scenario_1.json");
```

**Change to**:
```cpp
std::ofstream json(jsonPath.c_str());
```

**Rationale**: The `jsonPath` CLI arg is already declared, just not used. This is the ONLY code change needed in the .cc files.

---

### Step 2: Create JSON-to-JSONL Converter Script

**File**: `sim/ns3/scenario/convert_mlo_json_to_jsonl.sh`

**Inputs**:
- `$1`: Path to MLO JSON array file
- `$2`: Experiment ID
- `$3`: Start time (ISO8601)

**Output**: `telemetry.jsonl` in same directory

**Logic** (jq-based):
1. Parse JSON array
2. For each window object:
   - Calculate timestamp: `start_time + (window * 0.1s)`
   - Expand 18 metrics into 18 JSONL lines
   - Add required fields: `experiment_id`, `ts`, `source`, `schema_version`, `entity_id`, `unit`
3. Write to `telemetry.jsonl`

---

### Step 3: Create MLO Scenario Runner Script

**File**: `sim/ns3/scenario/run_mlo_scenario.sh`

**Usage**: `run_mlo_scenario.sh <EXP_ID> <normal|positive|negative> [SEED]`

**Workflow**:
1. Validate inputs
2. Set scenario-specific parameters (bias value, .cc file)
3. Create artifact directory (`sim/ns3/artifacts/<EXP_ID>/`)
4. Write metadata to `meta.txt`
5. Copy .cc file to ns-3 scratch
6. Run ns-3 with `--jsonPath="${OUT_DIR}/mlo_output.json"`
7. Call converter script to create `telemetry.jsonl`
8. Verify outputs exist

---

### Step 4: Add Makefile Targets

**New targets in Makefile**:
```makefile
# Run individual scenarios
.PHONY: run-mlo-normal run-mlo-positive run-mlo-negative

run-mlo-normal:
	docker run --rm -v $(pwd):/work --user "$(id -u):$(id -g)" \
		ndt/ns3:local \
		/work/sim/ns3/scenario/run_mlo_scenario.sh $(EXP_ID) normal $(SEED)

run-mlo-positive:
	# Same pattern with "positive"

run-mlo-negative:
	# Same pattern with "negative"

# Full pipeline (simulation + exporter)
.PHONY: run-mlo-exp
run-mlo-exp:
	$(MAKE) run-mlo-$(SCENARIO) EXP_ID=$(EXP_ID)
	$(MAKE) exporter-run EXP_ID=$(EXP_ID)
```

---

### Step 5: Test End-to-End Pipeline

```bash
# Prerequisites
make up              # Start containerlab
make pipeline-up     # Start harmonizer

# Run MLO scenarios
make run-mlo-exp EXP_ID=20260103-1400-mlo-normal-42 SCENARIO=normal
make run-mlo-exp EXP_ID=20260103-1400-mlo-attack-pos-42 SCENARIO=positive
make run-mlo-exp EXP_ID=20260103-1400-mlo-attack-neg-42 SCENARIO=negative

# Verify in database
docker exec -it clab-ndt-wifi7-mlo-security-udr-db psql -U udr -d udr -c "
  SELECT experiment_id, COUNT(*), COUNT(DISTINCT metric_name)
  FROM metrics
  WHERE experiment_id LIKE '20260103-1400-mlo-%'
  GROUP BY experiment_id;
"
```

**Expected**: ~5400 rows per experiment (18 metrics × 300 windows for 30s sim), 18 distinct metrics.

---

### Step 6: Update Documentation

- Add MLO scenarios section to `docs/WP7-ONE-COMMAND-PIPELINE.md`
- Update `docs/QUICK-REFERENCE.md` with new commands
- Record decisions in ADRs if needed

---

## Files to Create/Modify

| File | Action | Effort |
|------|--------|--------|
| `sim/ns3/scratch/wifi7-mlo-Normal.cc` | Modify | 1 line |
| `sim/ns3/scratch/wifi7-mlo-Positive.cc` | Modify | 1 line |
| `sim/ns3/scratch/wifi7-mlo-Negative.cc` | Modify | 1 line |
| `sim/ns3/scenario/convert_mlo_json_to_jsonl.sh` | Create | ~50 lines |
| `sim/ns3/scenario/run_mlo_scenario.sh` | Create | ~80 lines |
| `Makefile` | Modify | ~30 lines |
| `docs/WP7-ONE-COMMAND-PIPELINE.md` | Update | ~50 lines |

---

## Integration Points

### With WP7 Pipeline
- **Exporter**: No changes - reads `telemetry.jsonl` as usual
- **Harmonizer**: No changes - processes JSONL events normally
- **Database**: No schema changes - uses existing `metrics` table
- **Grafana**: Can create new dashboards for MLO metrics

### With Future WP8 (Multi-Scenario)
- Scenario runner pattern → scenario registry
- Experiment ID → multi-scenario queries
- Ready for `scenario` field addition

### With GNN Training
- Original JSON arrays preserved
- No workflow disruption
- Both outputs coexist

---

## Addressing Troubleshooting Issues

From `docs/codex/pipeline-run-troubleshooting.md`:

### Issue: Harmonizer with AUTO_OFFSET_RESET=latest misses messages
**Mitigation**:
- Always start harmonizer BEFORE running experiments
- OR use fresh consumer group with `earliest` offset

### Issue: Exporter state prevents re-processing
**Mitigation**:
- Delete `.exporter_state/exporter_state.json` before re-running
- Or use different EXP_ID for each run

---

## Success Criteria

- [ ] All three MLO scenarios run via Makefile targets
- [ ] Each run creates both JSON array and telemetry.jsonl
- [ ] Telemetry flows through full pipeline (Kafka → DB → Grafana)
- [ ] Database contains all 18 metrics per window
- [ ] Existing ndt_wifi_example.cc scenario still works (no regression)
- [ ] Documentation updated with MLO scenario usage
- [ ] No schema changes required

---

## Risk Assessment

**Risk Level**: LOW

**Reasons**:
- Minimal code changes (1 line per .cc file)
- Follows existing patterns (WP3/WP7)
- Backwards compatible
- Well-tested approach from prior WPs

---

## Next Steps After Completion

1. **WP8 Multi-Scenario Support**: Framework ready for scenario registry
2. **Attack Detection Research**: Three scenarios can feed detection algorithms
3. **GNN Training**: Original JSON arrays preserved
4. **Grafana Dashboards**: Create MLO-specific visualizations
5. **Comparative Analysis**: Query/compare normal vs attack scenarios

---

## Plan Status

**Status**: READY FOR IMPLEMENTATION

**Blockers**: None

**Dependencies**: All prerequisites met (WP7 complete, contract defined, .cc files exist)
