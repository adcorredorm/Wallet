---
description: Full feature development lifecycle with Notion tracking
argument-hint: [feature description or Notion page URL]
model: sonnet
allowed-tools: Agent, mcp__notion__notion-create-pages, mcp__notion__notion-update-page, mcp__notion__notion-fetch, Bash(python -m pytest:*), Read, Glob, Grep
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
| `Frontend` | `vue-mobile-first-dev` | Vue.js components, mobile-first UI |
| `DevOps` | `docker-manager` | Docker, docker-compose, infra config |
| `User` | (human) | Decisions or tasks requiring user judgment |

---

## Phase 0: Resolve Notion entry

Check if the input is a Notion page URL or ID:
- **If yes**: fetch the existing page with `mcp__notion__notion-fetch`. Use that page as the main entry. Update its Status to `In Progress` and Tags to `["Architect"]` if not already set.
- **If no**: create a new entry in the Kanban with:
  - **Name**: concise feature name derived from the input
  - **Status**: `In Progress`
  - **Priority**: estimate based on scope (`High` if core, `Medium` otherwise, `Low` if enhancement)
  - **Tags**: `["Architect"]`
  - **Notes**: one-line summary of the feature

Save the page ID — you will update it throughout the flow.

---

## Phase 1: Architecture Design Document (ADD)

Launch `the-architect` agent with the following prompt:

> "You are responsible for designing the architecture for a new feature in the Wallet project.
>
> **Feature**: $ARGUMENTS
>
> Produce a complete Architecture Design Document (ADD) that includes:
> 1. **Overview**: what the feature does and why it's needed
> 2. **Scope**: what is in and out of scope
> 3. **Affected layers**: which parts of the system are touched (backend, frontend, DevOps)
> 4. **Design decisions**: key technical choices with rationale and trade-offs
> 5. **Data model changes**: new or modified entities, fields, relationships
> 6. **API changes**: new or modified endpoints (method, path, request/response shape)
> 7. **Sub-tasks per agent**: a task list broken down by agent (backend-architect, vue-mobile-first-dev, docker-manager), each with a clear description and acceptance criteria
> 8. **Clarifying questions**: any ambiguities or decisions that require user input before implementation
>
> Be specific. Reference existing patterns in the codebase where relevant."

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

Present the list of created sub-tickets to the user for review before proceeding.

---

## Phase 3: Agent implementation plans

For each sub-task that has an agent (not `User` tagged), launch the corresponding agent with:

> "Review the following ADD and your assigned sub-task. Produce a detailed implementation plan before writing any code:
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

For each sub-task, launch the corresponding agent referencing its approved plan:
- `Backend` → `backend-architect`
- `Frontend` → `vue-mobile-first-dev`
- `DevOps` → `docker-manager`
- `User` → pause, inform the user what needs to be done manually, and wait for confirmation before continuing

Run independent agents in parallel when there are no dependencies. When dependencies exist (e.g. frontend needs the API contract from backend first), run sequentially.

As each sub-task starts, update its Notion Status to `In Progress`. When it completes, update to `Done`.

---

## Phase 5: Testing

After all sub-tasks are complete:
1. Run: `python -m pytest`
2. If tests fail, identify which agent is responsible for the failing area and re-launch it with the full failure output and a reference to its approved plan
3. Repeat until the suite passes cleanly

---

## Phase 6: Close

1. Update the main Notion entry Status to `Done`
2. Present a final summary:
   - What was built
   - Sub-tasks completed per agent
   - Files modified
   - Test results
   - Any follow-up items or known limitations (suggest adding them to the backlog)
