# the-architect Agent Improvements Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve `the-architect` agent with proactive context exploration, persistent architectural memory, and user-gated `writing-plans` invocation.

**Architecture:** All changes are inline in `.claude/agents/the-architect.md`. No new files, skills, or agents. Memory lives in `docs/architecture/ARCHITECTURE.md` and is read/updated by the agent itself.

**Tech Stack:** Claude Code agent markdown, git CLI

---

## Chunk 1: Startup Exploration

**Files:**
- Modify: `.claude/agents/the-architect.md`

- [ ] **Step 1: Open and read the current agent file**

  Read `.claude/agents/the-architect.md` in full to understand current structure before editing.

- [ ] **Step 2: Add a new `# Startup Protocol` section after the frontmatter intro paragraph**

  Insert after line 8 (the intro paragraph), before `# Core Responsibilities`:

  ```markdown
  # Startup Protocol

  **Every time you are invoked, before any analysis, execute these steps in order:**

  1. **Read architectural memory** — check if `docs/architecture/ARCHITECTURE.md` exists and read it fully. If it doesn't exist, note this and proceed.
  2. **Read prior specs** — check if `docs/superpowers/specs/` exists and list its files. Read any spec relevant to the current task.
  3. **Explore project structure** — list top-level directories and identify key config files (docker-compose.yml, settings.json, .env.example, pyproject.toml, package.json, etc.).
  4. **Review recent history** — run `git log --oneline -10` to understand recent changes.

  Summarize your findings in 2-3 sentences at the start of your response before proceeding to analysis.
  ```

- [ ] **Step 3: Verify the edit looks correct**

  Re-read the file and confirm the section is properly placed and formatted.

- [ ] **Step 4: Commit**

  ```bash
  git add .claude/agents/the-architect.md
  git commit -m "feat(agents): add startup exploration protocol to the-architect"
  ```

---

## Chunk 2: Architectural Memory Management

**Files:**
- Modify: `.claude/agents/the-architect.md`

- [ ] **Step 1: Add `# Architectural Memory` section after `# Quality Control`**

  Insert before `# Output Format`:

  ```markdown
  # Architectural Memory

  The file `docs/architecture/ARCHITECTURE.md` is the single source of architectural truth for this project. You are responsible for keeping it up to date.

  **Document structure** (create if it doesn't exist):

  ```markdown
  # Architecture

  ## Decision Log
  <!-- Dated entries: YYYY-MM-DD — Decision made and rationale -->

  ## Active Patterns
  <!-- Patterns currently in use across the codebase -->

  ## Known Drift
  <!-- Detected deviations from architectural intent, with status -->

  ## Last Updated
  <!-- Date and context of last update -->
  ```

  **Update the document when any of these occur:**
  - A new architectural decision was made or confirmed
  - An existing pattern was validated or explicitly rejected
  - Architectural drift was detected and a correction was agreed upon
  - A significant structural change was approved by the user

  **After updating**, commit with:
  ```bash
  git add docs/architecture/ARCHITECTURE.md
  git commit -m "docs(architecture): update architectural decisions - <topic>"
  ```

  **If nothing relevant occurred**, do NOT modify the file. Note this in "Next Steps" instead.
  ```

- [ ] **Step 2: Verify the section is correctly placed**

  Re-read the file and confirm it appears between `# Quality Control` and `# Output Format`.

- [ ] **Step 3: Commit**

  ```bash
  git add .claude/agents/the-architect.md
  git commit -m "feat(agents): add architectural memory management to the-architect"
  ```

---

## Chunk 3: writing-plans Gated Invocation

**Files:**
- Modify: `.claude/agents/the-architect.md`

- [ ] **Step 1: Update the `# Output Format` section**

  Find the current Output Format section and add a rule to the "Next Steps" item:

  Replace:
  ```markdown
  5. **Next Steps**: Proposed actions or questions for clarification
  ```

  With:
  ```markdown
  5. **Next Steps**: Proposed actions or questions for clarification. If there are actionable recommendations, always end this section with:
     > "If you approve these recommendations, I can generate an implementation plan — just say the word."
  ```

- [ ] **Step 2: Add `# Invoking writing-plans` section after `# Output Format`**

  Append at the end of the file:

  ```markdown
  # Invoking writing-plans

  You NEVER invoke `writing-plans` on your own initiative.

  When the user explicitly approves your recommendations and asks for a plan (e.g. "generate the plan", "yes go ahead", "let's do it"), invoke the `writing-plans` skill and pass it:
  - A summary of the current architectural analysis
  - The list of approved recommendations
  - The current state of `docs/architecture/ARCHITECTURE.md`
  ```

- [ ] **Step 3: Verify the full file reads correctly end-to-end**

  Read the complete file and confirm all three new sections (Startup Protocol, Architectural Memory, Invoking writing-plans) are present and well-formed.

- [ ] **Step 4: Commit**

  ```bash
  git add .claude/agents/the-architect.md
  git commit -m "feat(agents): add gated writing-plans invocation to the-architect"
  ```

---

## Verification

- [ ] **Manual smoke test:** Trigger the architect agent on a small change and verify it:
  1. Reads `docs/architecture/ARCHITECTURE.md` (or notes it doesn't exist)
  2. Lists project structure in its opening summary
  3. Ends "Next Steps" with the writing-plans offer
  4. Does NOT auto-invoke writing-plans
