# Resume Command

Resume work from the previous session by loading context.

## Usage
```
/resume
```

## What This Does
1. Reads `.claude/docs/context/current-session.md`
2. Reads `docs/CURRENT-STATE.md` for overall project state
3. Summarizes what was done last session
4. Shows what needs to be done next
5. Offers to run recommended startup commands

## Instructions
Read these files to get context:

1. `.claude/docs/context/current-session.md` - Session-specific context
2. `docs/CURRENT-STATE.md` - Overall project state

Then provide a summary in this format:

```
## Previous Session Summary
[Brief summary of what was done]

## Current Project State
- WP Status: [which WPs are complete]
- Pipeline: [working/broken]
- Last experiment: [EXP_ID if known]

## What's In Progress
- [Incomplete tasks]

## This Session Should Focus On
1. [Top priority - be specific]
2. [Second priority]
3. [Third priority]

## Recommended Startup Commands
```bash
make status  # Check if lab is running
# [other recommended commands]
```

Would you like me to run these commands? [Y/n]
```

End with: **"Ready to continue. What would you like to work on?"**

## Notes
- If context file is empty or missing, read `docs/CURRENT-STATE.md` instead
- If both are missing, inform user and offer to help set up
- Always be specific about next priorities
