# Wrapup Command

Create a session summary for continuity before ending work.

## Usage
```
/wrapup
/wrapup <optional notes about the session>
```

## Examples
```
/wrapup
/wrapup completed WP7, need to test with multiple experiments
/wrapup hit blocker on Kafka connection, needs investigation
/wrapup good progress on detector, 80% complete
```

## What This Does
1. Invokes the `@wrapper` sub-agent
2. Wrapper scans git status and recent work
3. Reads any plans/reviews created
4. Creates comprehensive session summary
5. Updates `.claude/docs/context/current-session.md`
6. Prepares context for next session

## Instructions
Use the @wrapper agent to create a session summary.

The wrapper should:
1. Read current `.claude/docs/context/current-session.md`
2. Check `git status` for changed files
3. Review `.claude/docs/plans/` for any plans created
4. Review `.claude/docs/reviews/` for any reviews done
5. Create comprehensive summary including:
   - What was completed
   - What's in progress
   - Decisions made
   - Next priorities
6. REPLACE contents of `.claude/docs/context/current-session.md`

Additional notes from user: $ARGUMENTS

**IMPORTANT:** Run this at the END of each work session to ensure continuity.
