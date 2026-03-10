---
name: git-flow
description: Use when completing a feature, deciding how to commit, creating a tag, or asking about branching strategy for this project.
---

# Git Flow

## Overview

Solo developer. Trunk-based on `main`. Conventional commits. Tag every completed feature with semver + slug.

## Strategy

- **Branch:** Always work directly on `main`. No feature branches.
- **Commits:** Conventional commits throughout (`feat`, `fix`, `refactor`, `docs`, `chore`, `test`)
- **Tags:** Create one tag per completed feature — format: `vMAJOR.MINOR.PATCH-feature-slug`

## Commit Format

```
<type>(<scope>): <description>

[optional body]
```

Types: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `style`
Scope: module or area (`agents`, `backend`, `frontend`, `docker`, `auth`, etc.)

## Tagging a Completed Feature

**Before tagging — REQUIRED:**
1. Use `superpowers:verification-before-completion` — confirm tests pass and work is done
2. Use `superpowers:finishing-a-development-branch` if in doubt about next steps

**Tag format:** `vMAJOR.MINOR.PATCH-feature-slug`

```bash
# Example: completing offline sync
git tag -a v0.3.0-offline-sync -m "feat: offline-first architecture with balance integrity"
git push origin --tags
```

**Slug rules:** lowercase, hyphens, describes the feature (`offline-sync`, `auth`, `mvp`, `docker-setup`)

## Version Bump Rules

| Change type | Bump | Example |
|---|---|---|
| New user-facing feature | **MINOR** | `v0.2.0` → `v0.3.0` |
| Bug fix or small improvement | **PATCH** | `v0.3.0` → `v0.3.1` |
| Breaking change or major milestone | **MAJOR** | `v0.3.0` → `v1.0.0` |

Start at `v0.1.0`. Reserve `v1.0.0` for production-ready MVP.

## Common Mistakes

| Mistake | Correct approach |
|---|---|
| `npm version minor` | Manual `git tag -a` — no single root package.json |
| Tag without slug | Always include slug: `v0.3.0-offline-sync` |
| Tag before verification | Always verify first with `superpowers:verification-before-completion` |
| Feature branch | Stay on `main` — trunk-based |
| Push tag separately | `git push origin --tags` after tagging |

## Quick Reference

```bash
# 1. Verify work is complete
# → use superpowers:verification-before-completion

# 2. Tag the feature
git tag -a vX.Y.Z-feature-slug -m "feat(scope): short description"

# 3. Push tag
git push origin --tags

# 4. Check tags
git tag --sort=-version:refname | head -5
```
