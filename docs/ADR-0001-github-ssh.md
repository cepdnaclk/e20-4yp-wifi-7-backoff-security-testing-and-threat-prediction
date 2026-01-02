# ADR-0001: Use GitHub SSH (ed25519) for Repo Access

## Status
Accepted

## Date
2025-12-22

## Context
Need to decide authentication method for GitHub repository access in development workflow.

## Decision
Use SSH authentication with an ed25519 key instead of HTTPS tokens.

## Rationale
- Cleaner for CLI workflows (git + gh)
- Works well in Kali/Linux and CI later
- Avoids token leakage risk in shells/scripts
- No need to manage token expiration

## Implementation
- Key lives at `~/.ssh/id_ed25519`
- SSH trust established via `ssh -T git@github.com`
- Verified with verbose auth test: `ssh -vT -i ~/.ssh/id_ed25519 git@github.com`

## Consequences

### Positive
- Secure authentication without token management
- Works consistently across team members
- Compatible with CI/CD systems

### Negative
- Every teammate must add their own SSH key to GitHub
- Repository clone URLs should be SSH (`git@github.com:...`)
- Need to document SSH setup process for onboarding

## Related
- WP1: Local Development Setup
