# Plan Command

Create an implementation plan before coding complex features.

## Usage
```
/plan <task description>
```

## Examples
```
/plan WP7 one-command pipeline
/plan add attack scenario to ns-3
/plan implement baseline detector
/plan add new metric to telemetry
```

## What This Does
1. Invokes the `@planner` sub-agent
2. Planner reads project documentation (CURRENT-STATE, ADRs, WP docs)
3. Analyzes codebase for existing patterns
4. Creates detailed implementation plan
5. Saves plan to `.claude/docs/plans/`
6. Updates session context

## Instructions
Use the @planner agent to create an implementation plan for: $ARGUMENTS

The planner should:
1. Read `.claude/docs/context/current-session.md` first
2. Read `docs/CURRENT-STATE.md` for project state
3. Check `docs/ALL-ADRS.md` for existing patterns
4. Check relevant WP docs if extending existing work
5. Create a comprehensive plan
6. Save to `.claude/docs/plans/<task>-plan.md`

After the planner completes, read the generated plan before implementing.
