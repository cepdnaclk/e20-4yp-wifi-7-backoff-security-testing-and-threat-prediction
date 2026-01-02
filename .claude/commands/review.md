# Review Command

Review recently written code for quality and issues.

## Usage
```
/review
/review <specific files or scope>
```

## Examples
```
/review
/review telemetry/harmonizer/
/review the docker-compose changes
/review WP7 implementation
```

## What This Does
1. Invokes the `@reviewer` sub-agent
2. Reviewer reads session context to know what changed
3. Checks code against project patterns (ADRs)
4. Creates review report with issues by severity
5. Saves report to `.claude/docs/reviews/`
6. Updates session context

## Instructions
Use the @reviewer agent to review recent code changes.

The reviewer should:
1. Read `.claude/docs/context/current-session.md` for what was done
2. Read `docs/ALL-ADRS.md` to check against project patterns
3. Review changed files
4. Check for common issues (permissions, networking, schemas)
5. Create review with issues by severity
6. Save to `.claude/docs/reviews/<date>-<feature>-review.md`

Scope: $ARGUMENTS (if empty, review all recently changed files)

After review completes, address any critical issues before proceeding.
