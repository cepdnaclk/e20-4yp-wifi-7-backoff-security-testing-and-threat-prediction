# Update-Docs Command

Update project documentation after completing work.

## Usage
```
/update-docs <what was completed>
```

## Examples
```
/update-docs WP7
/update-docs harmonizer health checks
/update-docs new attack scenario
```

## What This Does
1. Invokes the `@documenter` sub-agent
2. Documenter reads session context and recent changes
3. Identifies which docs need updating
4. Updates WP docs, ADRs, CURRENT-STATE, etc.
5. Creates new ADRs for documented decisions
6. Saves update log

## Instructions
Use the @documenter agent to update project documentation.

The documenter should:
1. Read `.claude/docs/context/current-session.md` for what changed
2. Check which documentation needs updating:
   - `docs/CURRENT-STATE.md`
   - `docs/WP*-*.md` (relevant WP)
   - `docs/ALL-ADRS.md` and `docs/adr/`
   - `docs/QUICK-REFERENCE.md`
   - `CLAUDE.md`
3. Create any new ADRs for decisions made
4. Update all relevant documents
5. Save update log to `.claude/docs/updates/`

What was completed: $ARGUMENTS

## When to Use
- After completing a work package
- After making significant changes
- After making architectural decisions
- Before ending a major work session
