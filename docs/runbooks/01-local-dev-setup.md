# Local Development Setup (WP1)

## Purpose
This runbook explains how to clone, authenticate, and work on the
`ndt-wifi7-mlo-security` repository.

## Prerequisites
- Kali Linux
- git
- SSH key added to GitHub
- GitHub CLI (`gh`) authenticate- GitHub CLI (`gh`) authenticated (optional; required only for repo creation)

## Repository Setup
```bash
git clone git@github.com:pradeep512/ndt-wifi7-mlo-security.git
cd ndt-wifi7-mlo-security

## Branching Workflow

Never work directly on `main`.

Create a feature branch before starting work:

```bash
git checkout -b feat/<area>-<short-name>

Example : git checkout -b feat/foundations-wp1

## Development Rules

- `main` must always remain runnable
- Each work package (WP) should map to one or more feature branches
- Every experiment must use a unique Experiment ID (EXP_ID)
- Generated artifacts (simulation outputs, results) must not be committed
- Major design decisions must be recorded as ADRs under `docs/adr/`

## Next Steps After Setup

1. Create a feature branch
2. Add or update documentation and tooling
3. Commit changes with clear messages
4. Push the branch and open a Pull Request

# Your standard workflow from now on
git checkout main
git pull
git checkout -b feat/<module>-<task>
# work
git commit
git push
# PR → review → merge
