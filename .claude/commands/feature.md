---
description: Full feature development lifecycle with Notion tracking
argument-hint: [feature description or Notion page URL]
model: sonnet
allowed-tools: Agent, Skill, mcp__notion__notion-create-pages, mcp__notion__notion-update-page, mcp__notion__notion-fetch, Bash(cd backend && python -m pytest:*), Bash(cd frontend && npm run type-check:*), Bash(cd frontend && npm run lint:*), Read, Glob, Grep
---

# Wallet Feature Development

You are orchestrating the full development lifecycle for a new feature in the Wallet project. Follow each phase strictly and never skip or reorder steps.

Input: $ARGUMENTS

---

## Notion Schema

- **Kanban data source ID**: `4a998974-915d-463f-b599-4d1a6a475032`
- **Status**: `TODO` | `In Progress` | `Done`
- **Priority**: `High` | `Medium` | `Low`
- **Tags**: `User` | `Architect` | `Backend` | `Frontend` | `DevOps`
- **Notes**: short summary — use for one-line context or links
- **Parent**: relation to another entry in the same DB — used to link sub-tickets to their parent feature (pass the parent page URL as a JSON array: `["<page-url>"]`)
- **Page body**: use for the ADD, agent plans, and decisions (rich content)

## Tag → Agent mapping

| Tag | Agent | Scope |
|---|---|---|
| `Architect` | `the-architect` | ADD generation, architectural oversight |
| `Backend` | `backend-architect` | Flask API, models, DB, business logic |
| `Frontend` | `nico-front` | Vue.js components, mobile-first UI |
| `DevOps` | `docker-manager` | Docker, docker-compose, infra config |
| `User` | (human) | Decisions or tasks requiring user judgment |

---

## Phase 0: Resolve Notion entry

Check if the input is a Notion page URL or ID:
- **If yes**: fetch the existing page with `mcp__notion__notion-fetch`.
  - If the fetch fails or the page does not exist, inform the user and ask them to confirm whether to create a new entry or provide a valid URL. Do not continue until resolved.
  - If successful, use that page as the main entry. Update its Status to `In Progress` and Tags to `["Architect"]` if not already set.
- **If no**: create a new entry in the Kanban with:
  - **Name**: concise feature name derived from the input
  - **Status**: `In Progress`
  - **Priority**: estimate based on scope (`High` if core, `Medium` otherwise, `Low` if enhancement)
  - **Tags**: `["Architect"]`
  - **Notes**: one-line summary of the feature

Save the page ID — you will update it throughout the flow.

---

## Phase 1: Architecture Design Document (ADD)

Before launching the architect, explore the codebase to build context:
- Backend: `backend/models/`, `backend/routes/`, `backend/services/`
- Frontend: `frontend/src/components/`, `frontend/src/views/`, `frontend/src/stores/`
- Look for existing patterns similar to what the feature requires

Collect those findings — you will pass them to the architect so it doesn't re-explore.

Then launch `the-architect` agent with the following prompt:

> "You are responsible for designing the architecture for a new feature in the Wallet project.
>
> **Feature**: $ARGUMENTS
>
> **Codebase findings** (already explored — do not re-explore):
> [paste the full findings from your exploration here]
>
> Produce a complete Architecture Design Document (ADD) that includes:
> 1. **Overview**: what the feature does and why it's needed
> 2. **Scope**: what is in and out of scope
> 3. **Affected layers**: which parts of the system are touched (backend, frontend, DevOps)
> 4. **Design decisions**: key technical choices with rationale and trade-offs — reference existing patterns where applicable
> 5. **Data model changes**: new or modified entities, fields, relationships
> 6. **API changes**: new or modified endpoints (method, path, request/response shape)
> 7. **Sub-tasks per agent**: a task list broken down by agent (backend-architect, nico-front, docker-manager), each with a clear description and acceptance criteria
> 8. **API contract**: if frontend consumes new backend endpoints, define the full contract here so both agents can work from the same spec
> 9. **Clarifying questions**: any ambiguities or decisions that require user input before implementation
>
> Be specific. Reference existing files and patterns from the codebase findings above."

After the agent responds:
1. Present the ADD and clarifying questions to the user
2. **Wait for user approval of the ADD before continuing** — if the user requests changes, re-launch the architect with the feedback
3. Once approved, write the ADD into the body of the main Notion page

---

## Phase 2: Create sub-tickets

Based on the approved ADD, create one Notion entry per sub-task:
- **Name**: descriptive sub-task name
- **Status**: `TODO`
- **Priority**: inherit from main feature or adjust per complexity
- **Tags**: single agent tag (`Backend`, `Frontend`, `DevOps`); use `User` for tasks requiring human decision
- **Notes**: acceptance criteria from the ADD (concise, one or two lines)
- **Parent**: set to `["<main-feature-page-url>"]` to link each sub-ticket to the parent feature entry

Only present the sub-tickets to the user if at least one of the following is true:
- There is a ticket tagged `User` (requires human action)
- A ticket introduces scope not clearly derived from the approved ADD

Otherwise, proceed directly to Phase 3.

---

## Phase 3: Agent implementation plans

For each sub-task that has an agent (not `User` tagged), launch the corresponding agent with:

> "Review the following ADD and your assigned sub-task. Use `superpowers:writing-plans` to produce a detailed implementation plan before writing any code:
>
> **ADD**: [paste relevant sections of the ADD]
> **Your sub-task**: [sub-task description and acceptance criteria]
>
> Your plan must include:
> 1. Files to create or modify (with brief reason for each)
> 2. Step-by-step implementation approach
> 3. Edge cases and error handling strategy
> 4. How you will verify your work is complete
>
> Do NOT implement yet. Return only the plan."

After all agents respond, present all plans to the user. **Wait for explicit approval of each plan before starting implementation.** If the user requests changes to a plan, re-launch the relevant agent with the feedback.

Write each approved plan into the body of the corresponding Notion sub-ticket.

---

## Phase 4: Implementation

**DO NOT START WITHOUT USER CONFIRMATION OF ALL PLANS.**

Use `superpowers:using-git-worktrees` to set up an isolated workspace before starting implementation.

For each sub-task, launch the corresponding agent referencing its approved plan:
- `Backend` → `backend-architect`
- `Frontend` → `nico-front`
- `DevOps` → `docker-manager`
- `User` → pause, inform the user what needs to be done manually, and wait for confirmation before continuing

### Parallelism rules

Run agents in parallel **only when** both conditions are true:
1. Their sub-tasks have no shared files or state
2. Frontend does NOT consume new backend endpoints introduced by this feature

If frontend consumes new backend endpoints: run `backend-architect` first, wait for it to complete and confirm the API contract, then start `nico-front`.

DevOps tasks can always run in parallel with backend unless they modify the same config files.

### Agent failure recovery

If an agent fails, returns incomplete work, or gets blocked:
1. Do not re-launch with the same prompt — that will repeat the same failure
2. Re-launch with: the original approved plan + the full error or incomplete output + explicit instruction: "Continue from [last completed step]. Do not redo previous steps."
3. If the agent fails a second time, pause and report to the user with a clear description of what failed and what was attempted

As each sub-task starts, update its Notion Status to `In Progress`. When it completes, update to `Done`. **Do not rely on the agent to update Notion — always update from the orchestrator** using the page IDs saved in Phase 2.

---

## Phase 5: Testing

Use `superpowers:verification-before-completion` before declaring this phase complete.

After all sub-tasks are complete, run both suites:

**Backend:**
```
cd backend && python -m pytest
```

**Frontend:**
```
cd frontend && npm run type-check
cd frontend && npm run lint
```

If any check fails:
- Identify which agent is responsible for the failing area
- Re-launch it with the full failure output and a reference to its approved plan
- Repeat until all checks pass cleanly

---

## Phase 6: Close

Use `superpowers:requesting-code-review` before closing.

1. Update the main Notion entry Status to `Done`
2. Use `git-flow` skill to tag the completed feature with the appropriate semver tag
3. Present a final summary:
   - What was built
   - Sub-tasks completed per agent
   - Files modified
   - Test results (backend pytest + frontend type-check + lint)
   - Any follow-up items or known limitations (suggest adding them to the backlog)
