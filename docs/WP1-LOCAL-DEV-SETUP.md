# WP1: Local Development Setup and GitHub Access

## Status: ✅ COMPLETED

## Overview
WP1 established the foundational development environment and GitHub repository access for the NDT Wi-Fi 7 MLO Security project.

---

## What Was Implemented

### 1. SSH Key Generation (ed25519)
- Created SSH key pair at `~/.ssh/id_ed25519` and `~/.ssh/id_ed25519.pub`
- Added key to ssh-agent:
  ```bash
  eval "$(ssh-agent -s)"
  ssh-add ~/.ssh/id_ed25519
  ```

### 2. GitHub SSH Trust and Verification
- Initial connection prompted for host authenticity confirmation
- Answered "yes" to add GitHub host key to `~/.ssh/known_hosts`
- Resolved "Permission denied (publickey)" by ensuring key was added to GitHub
- Verified with verbose test:
  ```bash
  ssh -vT -i ~/.ssh/id_ed25519 git@github.com
  ```
- Success message: `Hi <user>! You've successfully authenticated, but GitHub does not provide shell access.`

### 3. GitHub CLI (gh) Installation
- `apt install gh` failed on Kali (not in apt source)
- Installed using snap: `snap install gh`
- Logged in using device code flow in browser
- Created repo and pushed successfully

### 4. Repository Created
- **Repo:** `pradeep512/ndt-wifi7-mlo-security`
- **Remote:** SSH URL (`git@github.com:...`)
- **Branch:** `main` tracking `origin/main`

---

## Acceptance Criteria (All Met)

| Criteria | Status |
|----------|--------|
| `git status` clean | ✅ |
| `gh repo create ... --push` succeeded | ✅ |
| Repo accessible via SSH | ✅ |
| Can clone on fresh machine | ✅ |

---

## Key Commands

```bash
# SSH key setup
ssh-keygen -t ed25519 -C "your_email@example.com"
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Test GitHub SSH
ssh -T git@github.com

# GitHub CLI
snap install gh
gh auth login
gh repo create pradeep512/ndt-wifi7-mlo-security --public --push
```

---

## Problems Solved

### Problem 1: Permission Denied (publickey)
**Cause:** SSH key not yet added to GitHub account
**Solution:** Added public key to GitHub SSH settings

### Problem 2: gh not available via apt on Kali
**Cause:** Package not in Kali apt repositories
**Solution:** Installed via snap instead

---

## Files Created/Modified
- `~/.ssh/id_ed25519` (private key)
- `~/.ssh/id_ed25519.pub` (public key)
- `~/.ssh/known_hosts` (GitHub host entry)
- Repository initialized with basic structure

---

## Lessons Learned

1. **Use SSH (ed25519) for GitHub access** - cleaner for CLI workflows, avoids token leakage
2. **Kali Linux quirks** - some packages need alternative install methods (snap, manual)
3. **Always verify SSH with `-vT` flag** when debugging auth issues

---

## Related ADRs
- ADR-0001: Use GitHub SSH (ed25519) for repo access
- ADR-0002: Use gh CLI for repo creation

---

## Next Steps (→ WP2)
- Create Containerlab topology
- Set up service containers (DB, Grafana)
- Establish Makefile targets
