# the-architect Agent Improvements — Design

**Date:** 2026-03-09
**Status:** Approved

---

## Overview

Improve the existing `the-architect` agent to:
1. Proactively explore project context on startup
2. Maintain and update persistent architectural memory
3. Offer `writing-plans` invocation only after user approval

---

## Section 1: Startup Exploration

On every invocation, before any analysis, the agent executes:

1. Read `docs/architecture/ARCHITECTURE.md` if it exists
2. Read all files under `docs/superpowers/specs/` if the directory exists
3. List top-level folder structure + key config files (docker-compose, settings, etc.)
4. Read last 10 git commits (`git log --oneline -10`)

If no prior documentation exists, the agent declares this explicitly and proceeds from code structure alone.

---

## Section 2: Architectural Memory Management

The agent maintains `docs/architecture/ARCHITECTURE.md` as a living document.

**Document structure:**
- `## Decision Log` — dated entries of architectural decisions made
- `## Active Patterns` — patterns currently in use across the codebase
- `## Known Drift` — detected deviations from architectural intent
- `## Last Updated` — date and context of last update

**Update triggers** (agent updates the doc after analysis if any of these occurred):
- A new architectural decision was made
- An existing pattern was validated or rejected
- Architectural drift was detected and a correction was agreed upon
- A significant structural change was approved

**Commit message format:** `docs(architecture): update architectural decisions - <topic>`

If nothing relevant occurred, the agent notes this in "Next Steps" and does not modify the file.

---

## Section 3: writing-plans Invocation

The agent **never invokes `writing-plans` autonomously**.

At the end of every response, if actionable recommendations exist, the agent includes in "Next Steps":
> "If you approve these recommendations, I can generate an implementation plan — just say the word."

When the user confirms, the agent invokes the `writing-plans` skill with:
- Current architectural analysis
- Approved recommendations
- Current state of `ARCHITECTURE.md`

---

## Implementation Scope

- **File to modify:** `.claude/agents/the-architect.md`
- **File to create:** `docs/architecture/ARCHITECTURE.md` (on first update)
- **No new skills or agents required**

---

## Trade-offs

| Concern | Decision |
|---|---|
| Auto-invoking writing-plans | Rejected — user reviews first |
| Separate memory skill | Rejected — inline is simpler |
| Shared CLAUDE.md memory | Rejected — too coupled |
| Fixed 5-section output | Kept — predictable and clear |
