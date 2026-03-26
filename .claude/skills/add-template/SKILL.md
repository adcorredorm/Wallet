---
name: add-template
description: Use when producing, reviewing, or validating an Architecture Design Document (ADD) for a new feature — includes required sections, agent task breakdown format, and API contract structure
---

# Architecture Design Document (ADD)

## Overview

An ADD is the single source of truth for a feature's design. **Core principle: every implementation decision must be made in the ADD before any code is written.** The ADD is produced by the architect and approved by the user before implementation begins.

## Structure

Every ADD must include these sections in order:

### 1. Overview
What the feature does and why it's needed. 2-3 sentences max.

### 2. Scope
- **In scope**: what this feature covers
- **Out of scope**: what it explicitly does NOT cover (prevents scope creep)

### 3. Affected Layers
Which parts of the system are touched. For each layer, state whether it's a new addition or a modification.

### 4. Design Decisions
Key technical choices with:
- **Decision**: what was chosen
- **Rationale**: why this approach
- **Trade-offs**: what was sacrificed
- **Alternatives considered**: what else was evaluated (brief)

Reference existing patterns in the codebase where applicable.

### 5. Data Model Changes
New or modified entities, fields, relationships. Use a table:

| Entity | Field | Type | Notes |
|--------|-------|------|-------|
| ... | ... | ... | new/modified/removed |

If no data model changes: state "No data model changes."

### 6. API Changes
New or modified endpoints:

| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| POST | /api/... | `{ field: type }` | `{ field: type }` | new/modified |

If no API changes: state "No API changes."

### 7. Sub-tasks per Agent
A task list broken down by agent role. Each task must have:
- **Agent**: which agent owns it (e.g., backend-dev, frontend-dev, infra-dev)
- **Task**: clear description of what to implement
- **Acceptance criteria**: specific, verifiable conditions for completion
- **Dependencies**: which other tasks must complete first (if any)
- **Independent**: whether this task can run in parallel with other tasks of the same agent (helps the team lead decide if spawning multiple instances is worthwhile)

### 8. API Contract
If frontend consumes new backend endpoints, define the full request/response contract here so both agents work from the same spec. Include:
- Exact request body shape with types
- Exact response body shape with types
- Error response shape
- Authentication requirements

If no cross-layer API contract: state "No cross-layer API contract needed."

### 9. Decisions Made
Key decisions resolved during requirements clarification. For each:
- **Decision**: what was decided
- **Context**: the question or ambiguity that prompted it

If no significant decisions were made: state "No notable decisions — requirements were clear from the start."

## Guidelines

- Be specific. Reference existing files and patterns from the codebase.
- Keep it concise. An ADD is a decision document, not a tutorial.
- Every sub-task must map to exactly one agent. If a task spans agents, split it.
- Acceptance criteria must be verifiable without subjective judgment.
- The ADD is immutable after approval. Changes require a new revision with user consent.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Vague acceptance criteria ("works correctly") | Make it verifiable: "POST /api/x returns 201 with `{ id, name }`" |
| Sub-task spans multiple agents | Split it — one task, one agent, always |
| Missing API contract when frontend consumes backend | If both layers touch the same endpoint, section 8 is mandatory |
| ADD modified after approval without user consent | Treat as immutable — create a revision and get explicit approval |
| Scope section missing "out of scope" | Always state what is NOT included — prevents creep during implementation |
| Design decisions without alternatives | Even if the choice is obvious, state what else was considered and why it was rejected |
| Data model section omitted when "no changes" | Always include the section — state "No data model changes" explicitly so QA knows it was considered |
