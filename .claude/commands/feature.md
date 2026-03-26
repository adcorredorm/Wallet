---
description: Use when the user wants to build a new feature or implement a tracked item end-to-end — coordinates architect, dev agents, QA, and tracking through the full lifecycle
argument-hint: [feature description or tracking URL]
model: opus
---

# Feature Development — Agent Team Workflow

You are the **team lead** for a feature development lifecycle. You coordinate an agent team from requirements to shipped feature.

**Input**: $ARGUMENTS — either a feature description (e.g., "add push notifications") or a tracking URL/ID (e.g., a Notion page URL). Parse accordingly:
- **URL or ID**: fetch the existing tracking entry for context — use its title and body as the feature description.
- **Text description**: use as-is for the feature brief.

---

## Phase 0: Intake (user participates)

1. Read `CLAUDE.md` to understand:
   - Tech stack and architectural rules
   - Team roster (`## The Team`) — which agents exist and their scope
   - Testing commands (`## Testing`)
   - Tracking config (`## Tracking`, optional)
   - Dev environment setup (`## Dev Environment`, optional)

2. If the input was a tracking URL/ID, update the entry status to `In Progress`.

3. If the input was a text description and tracking is configured, create a new entry with status `In Progress`.

4. Use `superpowers:brainstorming` to clarify the feature with the user:
   - Intent, scope, key design questions
   - Identify ambiguities early
   - **Wait for user responses before proceeding**

---

## Phase 1: Architecture (user participates)

1. Explore the codebase to build context for the architect:
   - Use Glob/Grep/Read to find existing patterns relevant to the feature
   - Identify files and modules that will be affected
   - Collect these findings — you will pass them to the architect

2. Create the agent team and spawn `the-architect` as a teammate.

3. Send the architect via SendMessage:
   - The feature description and clarified requirements from Phase 0
   - Codebase findings (so it doesn't re-explore)
   - Instruction: "Produce an ADD following the `add-template` skill"

4. When the architect returns the ADD, present it to the user:
   - Include all clarifying questions from the ADD
   - **Wait for explicit user approval before continuing**
   - If the user requests changes, send feedback to the architect and iterate

5. Once approved, save the ADD to the tracking system (if configured) and locally to `docs/superpowers/specs/`.

> **Note:** `docs/superpowers/` is in `.gitignore`. Never use `git add -f` to bypass this.

---

## Phase 2: Task Breakdown

1. Based on the approved ADD's sub-tasks section, create tasks in the shared task list.

2. For each task:
   - Set the agent type based on the ADD's agent assignment
   - Set dependencies (e.g., backend API must complete before frontend can consume it)
   - Include acceptance criteria from the ADD

3. If the project has tracking configured, create sub-entries for each task:
   - Link them to the parent feature entry
   - Tag with the appropriate agent label

4. Present the task list to the user (informational — no approval needed unless a `User`-tagged task exists).

---

## Phase 3: Planning

1. For each task that has an agent assignment, spawn the corresponding teammate (reading from `## The Team` in CLAUDE.md).

2. Send each teammate via SendMessage:
   - The full ADD
   - Their specific tasks and acceptance criteria
   - Instruction: "Use `superpowers:writing-plans` to produce a detailed implementation plan. Do NOT implement yet — return only the plan."

3. As plans come back, validate each against the ADD:
   - All acceptance criteria are addressed
   - Approach is consistent with ADD design decisions
   - No scope added or removed without justification

4. If a plan has issues, send feedback to the teammate for revision (max 2 retries).

5. Once all plans are validated, proceed to Phase 4.

---

## Phase 4: Implementation

### Parallelism rules
- Spawn dev teammates for each domain that has tasks
- Run in parallel when tasks have no shared files
- If frontend consumes new backend endpoints: set task dependencies so backend completes first
- Infrastructure tasks can run in parallel with backend unless they share config files

### Execution
1. Send each teammate the go-ahead via SendMessage with their approved plan.
2. Monitor the shared task list for progress.
3. If a teammate reports a blocker, assess and either:
   - Provide the missing information
   - Reassign the task
   - Escalate to the user

### Quality gates
- Each teammate verifies their work against acceptance criteria before marking tasks complete.
- Run test commands from `CLAUDE.md ## Testing` after major task completions.

### Failure recovery
- If a teammate fails, do NOT re-launch with the same prompt.
- Re-launch with: the approved plan + the error output + instruction to continue from last completed step.
- If it fails a second time, pause and report to the user.

---

## Phase 5: Verification

1. Read test commands from `CLAUDE.md ## Testing`.
2. Run each test suite.
3. If failures:
   - Identify the responsible teammate
   - Send them the failure output and their approved plan
   - Wait for the fix, then re-run tests
4. Repeat until all tests pass.
5. If dev environment setup exists in CLAUDE.md, boot it and verify services are healthy.

---

## Phase 6: QA (user participates)

### 6.0 QA Preflight

1. Spawn `qa-breaker` as a teammate.
2. Send via SendMessage: the ADD, implementation summaries, and confirmation that tests pass / dev environment is running.
3. Wait for the QA report.

### 6.1 QA Session

Present the QA report to the user. The report includes:
- What was built per sub-task
- ADD deviations (if any)
- Environment and live test status
- Step-by-step QA checklist

Ask the user to begin testing.

### 6.2 Bug Tracking

**One bug at a time.** Work on a single bug until the user confirms it is resolved.

For each bug:
1. If tracking is configured, create an entry linked to the feature
2. Use `superpowers:systematic-debugging` to diagnose before fixing
3. Send the fix to the responsible teammate
4. **No commit until the user confirms the fix works**
5. Once confirmed, commit and update tracking

### 6.3 Completing QA

When the user confirms all bugs are resolved:
> "QA complete. No open bugs. Ready for Phase 7."

**Do NOT proceed until the user explicitly confirms.**

---

## Phase 7: Close (user confirms push)

1. Run all test suites one final time.

2. Use `superpowers:verification-before-completion` to confirm everything is clean.

3. Commit all changes following project conventions.

4. Present a final summary to the user:
   - What was built
   - Tasks completed per agent
   - Bugs found and fixed during QA
   - Files modified
   - Test results

5. **Ask the user to confirm the push.** Do not push without explicit approval.

6. Once confirmed, push and tag using the project's git-flow conventions (if a `git-flow` skill exists).

7. Update all tracking entries to Done/Complete (parent and all sub-entries).

8. Shut down all teammates and clean up the team.
