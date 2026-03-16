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

## Dev-Only Utilities

> DEV ONLY — never run against production.

**Seed test data** (`backend/dev_seed_test_data.py`) — injects 15 months of fake multi-currency data into a user account. Deletes and recreates all `offline_id LIKE 'test-%'` records on every run. After running, do a force full sync in the app (Settings → Forzar sincronización completa).

```bash
docker compose exec backend python dev_seed_test_data.py --email <email>
```

## The Team (Agents)

| Agent | Scope |
|-------|-------|
| `the-architect` | Architectural decisions, cross-cutting reviews, ADD generation |
| `backend-architect` | Flask API, models, services, migrations, backend tests |
| `nico-front` | Vue components, mobile-first UI, dark mode, frontend patterns |
| `docker-manager` | Docker, docker-compose, infrastructure config |

Agent definitions: `.claude/agents/`
