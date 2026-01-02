# Improved Claude Code Agent System

This is an enhanced version of the Claude Code agent configuration that integrates with your comprehensive project documentation.

## What's Improved

### 1. Documentation-Aware Agents
All agents now know about and reference your project documentation:
- `docs/CURRENT-STATE.md`
- `docs/BLUEPRINT.md`
- `docs/ALL-ADRS.md`
- `docs/WP*-*.md`

### 2. New Documenter Agent
Added `@documenter` agent to keep documentation in sync after completing work.

### 3. Better Context File
Initial context references actual documentation instead of duplicating it.

### 4. ADR Integration
Agents check ADRs before making suggestions and note when new ADRs are needed.

### 5. Project-Specific Checks
Reviewer knows about common issues in this project (permissions, networking, schemas).

---

## Files Included

```
improved-agents/
├── CLAUDE.md                    # Main rules (improved)
├── agents/
│   ├── planner.md              # Plans with doc awareness
│   ├── reviewer.md             # Reviews against ADRs
│   ├── wrapper.md              # Session summaries
│   └── documenter.md           # NEW: Keeps docs in sync
├── commands/
│   ├── plan.md                 # /plan command
│   ├── review.md               # /review command
│   ├── wrapup.md               # /wrapup command
│   ├── resume.md               # /resume command
│   └── update-docs.md          # NEW: /update-docs command
└── docs/
    └── context/
        └── current-session.md  # Improved initial context
```

---

## Installation

```bash
# From your project root
cd ndt-wifi7-mlo-security

# Create directories
mkdir -p .claude/agents
mkdir -p .claude/commands
mkdir -p .claude/docs/context
mkdir -p .claude/docs/plans
mkdir -p .claude/docs/reviews
mkdir -p .claude/docs/updates
mkdir -p .claude/docs/context/archive

# Copy files (adjust source path as needed)
cp improved-agents/CLAUDE.md .claude/
cp improved-agents/agents/* .claude/agents/
cp improved-agents/commands/* .claude/commands/
cp improved-agents/docs/context/current-session.md .claude/docs/context/

# Also ensure project docs are in place
# (The docs/ folder with CURRENT-STATE.md, BLUEPRINT.md, etc.)
```

---

## Usage

### Starting a Session
```
/resume
```
Loads context from previous session and project docs.

### Before Complex Work
```
/plan WP7 one-command pipeline
```
Creates implementation plan using project docs and ADRs.

### After Implementation
```
/review
```
Reviews code against project patterns and ADRs.

### After Completing Work
```
/update-docs WP7
```
Updates all relevant documentation.

### End of Session
```
/wrapup completed WP7
```
Saves comprehensive context for next session.

---

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     START SESSION                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │    /resume      │ ◄── Reads docs/CURRENT-STATE.md
                    │                 │     and session context
                    └────────┬────────┘
                             │
          ┌──────────────────┴──────────────────┐
          │                                      │
          ▼                                      ▼
   ┌──────────────┐                     ┌──────────────┐
   │ Simple task  │                     │ Complex task │
   │ (implement)  │                     │  /plan first │
   └──────┬───────┘                     └──────┬───────┘
          │                                     │
          │                                     ▼
          │                            ┌──────────────┐
          │                            │  @planner    │ ◄── Reads ADRs,
          │                            │              │     WP docs
          │                            └──────┬───────┘
          │                                    │
          │◄───────────────────────────────────┘
          │
          ▼
   ┌──────────────┐
   │  Implement   │ ◄── Parent agent does all implementation
   │              │
   └──────┬───────┘
          │
          ▼
   ┌──────────────┐
   │   /review    │ ◄── Checks against ADRs
   │  @reviewer   │
   └──────┬───────┘
          │
          ▼
   ┌──────────────┐
   │  Fix issues  │
   │  if needed   │
   └──────┬───────┘
          │
          ▼
   ┌──────────────┐
   │ /update-docs │ ◄── Updates WP docs, ADRs
   │ @documenter  │
   └──────┬───────┘
          │
          ▼
   ┌──────────────┐
   │   /wrapup    │ ◄── Saves session context
   │   @wrapper   │
   └──────┬───────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                      END SESSION                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Differences from Original

| Aspect | Original | Improved |
|--------|----------|----------|
| Doc awareness | Generic | Knows about all project docs |
| ADR checking | No | Planner and Reviewer check ADRs |
| Documentation | Manual | `@documenter` agent helps |
| Context file | Duplicates info | References docs |
| Project-specific | Generic rules | Knows common issues |
| Commands | 4 | 5 (added /update-docs) |

---

## Best Practices

### 1. Keep Docs in Sync
Run `/update-docs` after completing any significant work.

### 2. Create ADRs for Decisions
When making architectural decisions, note them for ADR creation.

### 3. Use Plans for Complex Work
Don't skip planning for WP-level work.

### 4. Always Wrapup
Even for short sessions, run `/wrapup` to preserve context.

### 5. Reference, Don't Duplicate
Context file should reference docs, not copy them.
