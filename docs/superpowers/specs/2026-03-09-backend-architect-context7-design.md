# backend-architect Agent: context7 Integration — Design

**Date:** 2026-03-09
**Status:** Approved

---

## Overview

Add context7 MCP usage to the `backend-architect` agent so it consults up-to-date, version-accurate documentation before writing code.

---

## Section 1: Context7 Protocol

**New section:** `# Context7 Protocol` inserted before `## Output Quality Standards`.

### When to activate

Only before writing new code or modifying existing code. Not during:
- Analysis or architectural discussions
- Code reviews
- Conversational/clarifying responses

### How to use

1. Read `backend/requirements.txt` to get exact versions of relevant libraries
2. Identify which libraries from the stack are relevant to the current task
3. For each relevant library: call `resolve-library-id` with the library name and version, then `query-docs` with a task-specific query
4. If `requirements.txt` doesn't exist or a library isn't listed, use the latest version available in context7

### Libraries to consider (task-dependent)

- Flask
- Flask-SQLAlchemy
- SQLAlchemy
- Pydantic
- Alembic
- Flask-Migrate
- Any other library from requirements.txt relevant to the task

### When to report findings

Only if context7 reveals something that changes the approach:
- A deprecation in the version being used
- A version-specific API or pattern different from the expected
- A known bug or breaking change in the version

Format: one brief line — e.g., `"SQLAlchemy 2.0 removed legacy Query API — using select() instead."`

### Fallback

If context7 MCP is unavailable, proceed using internal knowledge. Never block a task waiting for context7.

---

## Implementation Scope

- **File to modify:** `.claude/agents/backend-architect.md`
- **No new files, skills, or agents required**

---

## Trade-offs

| Concern | Decision |
|---|---|
| Always querying all libraries | Rejected — only query what's relevant to the task |
| Hardcoded versions | Rejected — read dynamically from requirements.txt |
| Reporting every context7 result | Rejected — only report when it changes the approach |
| Blocking on context7 unavailability | Rejected — graceful fallback to internal knowledge |
