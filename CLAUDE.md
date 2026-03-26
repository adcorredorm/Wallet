# Wallet

Personal finance tracker for managing accounts, transactions, transfers, and categories. Operated entirely by AI agents with minimal human intervention.

## Philosophy

- **Offline-first**: Frontend IndexedDB (Dexie) is the source of truth. The backend is a sync backup, not the primary data layer.
- **AI-operated**: This codebase is written and maintained by AI agents. All documentation is for agents, not humans.

## Tech Stack

| Layer | Stack |
|-------|-------|
| Backend | Python 3.11+, Flask 3.x, SQLAlchemy 2.0, Pydantic v2, PostgreSQL 15, Alembic |
| Frontend | Vue 3 (Composition API + `<script setup>`), TypeScript, Pinia, Vue Router, Axios, Tailwind CSS, Vite |
| Offline | Dexie (IndexedDB) |
| Infra | Docker Compose, Makefile.docker |
| Testing | pytest, Vitest, vue-tsc, ESLint |

## Architectural Rules

- Balances are always computed dynamically — never stored in the database
- Frontend IndexedDB is the source of truth; backend is a sync backup
- Amounts are always positive — transaction `type` (income/expense) determines the sign
- All primary keys are UUIDs
- Exchange rates are seeded into Dexie on first launch (`BASE_RATES` in `src/stores/exchangeRates.ts`). The backend upserts fresh rates on every sync. **On every minor version release, ask the user if they want to update `BASE_RATES` with the current rates from the DB** so offline cold-start accuracy stays acceptable.

## Testing

```bash
cd backend && python -m pytest
cd frontend && npm run type-check
cd frontend && npm run lint
```

## Hooks Setup

Run once per clone to activate the pre-push migration hook:

```bash
git config core.hooksPath .githooks
```

The hook runs `flask db upgrade` against production (Neon) before every push to `main`. If migrations fail, the push is aborted. Uses `backend/migrations/` (Flask-Migrate), which matches the production DB revision history.

**Escape hatch** (emergencies only — manual rollback, hotfix bypass):

```bash
git push --no-verify
```

## Dev-Only Utilities

> DEV ONLY — never run against production.

**Seed test data** (`backend/dev_seed_test_data.py`) — injects 15 months of fake multi-currency data into a user account. Deletes and recreates all `offline_id LIKE 'test-%'` records on every run. After running, do a force full sync in the app (Settings → Forzar sincronización completa).

```bash
docker compose exec backend python dev_seed_test_data.py --email <email>
```

## The Team (Agents)

| Agent | Role | Scope |
|-------|------|-------|
| `the-architect` | Architecture, ADD generation | Read-only. No code. |
| `backend-dev` | Flask API, models, services, migrations, tests | `backend/` only |
| `frontend-dev` | Vue components, mobile-first UI, dark mode | `frontend/` only |
| `infra-dev` | Docker, compose, Makefiles, CI/CD | Infrastructure files only |
| `qa-breaker` | QA testing, bug reporting | Read-only. No fixes. |

Agent definitions: `.claude/agents/`
Workflow: `/feature` command

## Tracking

This project uses Notion for feature tracking.

- **Kanban data source ID**: `4a998974-915d-463f-b599-4d1a6a475032`
- **Status values**: `Backlog`, `TODO`, `In Progress`, `Done`
- **Priority values**: `Low`, `Medium`, `High`, `Critical`, `Blocker`
- **Tags**: `User`, `Architect`, `Backend`, `Frontend`, `DevOps`
- **Parent relation**: link sub-tickets to parent feature via `["<page-url>"]`
- **MCP tools**: use `mcp__notion__*` for all tracking operations

## Dev Environment

```bash
make -f Makefile.docker up-dev
```

Verify health: `docker compose logs --tail=20 db backend frontend`
