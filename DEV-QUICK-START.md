# Development Quick Start

Get your development environment running in 5 minutes with hot-reload for both frontend and backend.

## Prerequisites

- Docker and Docker Compose installed
- `.env` file (copy from `.env.example`)
- Terminal/Command prompt

## 5-Minute Setup

### Step 1: Prepare Environment
```bash
cd /Users/angelcorredor/Code/Wallet

# Create .env file if not exists
cp .env.example .env
```

### Step 2: Start Services
```bash
# Start all services with hot-reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Wait for "healthy" status on all services (2-3 minutes)
```

### Step 3: Access Development Environment
- **Frontend**: http://localhost:3000 (or http://localhost:5173)
- **Backend API**: http://localhost:5001
- **Database UI**: http://localhost:5050 (pgAdmin)

## What Works Out of the Box

### Frontend Hot Reload (Vite HMR)
- Edit `.vue` files → Changes appear instantly in browser
- Edit TypeScript/CSS → No page reload needed
- Edit components in `src/components/`

### Backend Hot Reload
- Edit Python files in `backend/app/` → Flask auto-restarts
- Edit API routes → Available on next request
- Debug errors show in Flask server logs

### Database
- PostgreSQL running and accessible
- Migrations auto-run on startup
- Database persists between restarts

## Common Development Commands

### Start/Stop

```bash
# Start development (show all logs)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Start in background
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Stop all services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# View logs from frontend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f frontend

# View logs from backend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend

# Restart specific service
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart frontend
```

### Database

```bash
# Open database shell
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec db psql -U wallet_user -d wallet_db

# View migration status
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend flask db current

# Run pending migrations
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend flask db upgrade

# Create new migration after model changes
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend flask db migrate -m "Describe changes"
```

### Shell Access

```bash
# Backend Python shell
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend sh

# Frontend Node shell
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend sh

# Run single command in backend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -c "print('hello')"
```

### Rebuild

```bash
# Rebuild frontend (after npm dependency changes)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build frontend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up frontend

# Rebuild backend (after pip dependency changes)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build backend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up backend
```

## File Structure for Development

```
/Users/angelcorredor/Code/Wallet/
├── frontend/
│   ├── src/
│   │   ├── components/      ← Edit Vue components here (hot-reload)
│   │   ├── pages/          ← Edit pages (hot-reload)
│   │   ├── stores/         ← Edit Pinia stores (hot-reload)
│   │   └── App.vue         ← Root component
│   ├── package.json
│   ├── Dockerfile          ← Production build
│   └── Dockerfile.dev       ← Development with Vite
│
├── backend/
│   ├── app/
│   │   ├── routes/         ← Edit API endpoints here (auto-reload)
│   │   ├── models/         ← Edit models (auto-reload)
│   │   └── services/       ← Edit business logic (auto-reload)
│   ├── alembic/            ← Database migrations
│   ├── run.py              ← Entry point
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml       ← Base configuration (production defaults)
├── docker-compose.dev.yml   ← Development overrides (hot-reload)
├── docker-compose.prod.yml  ← Production overrides
├── .env                     ← Your environment variables
└── DEVELOPMENT-WORKFLOW.md  ← Detailed guide
```

## Typical Development Workflow

### Adding a New Frontend Feature

1. Create new component or edit existing: `frontend/src/components/MyFeature.vue`
2. Save the file
3. See changes instantly in browser at http://localhost:3000
4. No rebuild needed, no page reload wait

### Adding a New API Endpoint

1. Edit backend route: `backend/app/routes/my_route.py`
2. Save the file
3. Flask auto-restarts (watch terminal for `[Restarting with stat]`)
4. Test endpoint immediately: `curl http://localhost:5001/api/v1/my-endpoint`

### Adding Frontend Dependency

```bash
# 1. Stop services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# 2. Add dependency (local machine)
cd frontend
npm install lodash

# 3. Rebuild container
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build frontend

# 4. Start services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Adding Backend Dependency

```bash
# 1. Stop services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# 2. Add dependency to backend/requirements.txt manually
echo "requests==2.31.0" >> backend/requirements.txt

# 3. Rebuild container
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build backend

# 4. Start services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Switching Between Environments

### Development (with hot-reload)
```bash
# Use both files - dev overlays changes on top of base
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Production (static builds, no hot-reload)
```bash
# Stop dev first
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# Run production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Quick Troubleshooting

### Port Already in Use
```bash
# Find what's using port 5173
lsof -i :5173

# Kill the process
kill -9 <PID>
```

### Changes Not Appearing
```bash
# Clear browser cache: Cmd+Shift+Delete

# Restart the service
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart frontend

# Check logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs frontend
```

### Database Connection Error
```bash
# Check if database is healthy
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps

# View database logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs db

# Restart database
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart db
```

### API Not Responding
```bash
# Check backend health
curl http://localhost:5001/health

# View backend logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend
```

## Next Steps

- Read [DEVELOPMENT-WORKFLOW.md](./DEVELOPMENT-WORKFLOW.md) for detailed documentation
- Check [README-DOCKER.md](./README-DOCKER.md) for Docker architecture overview
- Review `.env.example` for all available environment variables

## Environment Variables Reference

Key development variables in `.env`:

```env
# Database
DB_NAME=wallet_db              # Database name
DB_USER=wallet_user            # DB username
DB_PASSWORD=wallet_password    # DB password
DB_PORT=5432                   # PostgreSQL port (exposed in dev)

# Flask
FLASK_ENV=development          # Enable dev features
DEBUG=True                      # Enable debug mode (hot-reload)
SECRET_KEY=dev-secret-key-...  # Session secret (dev-only)

# Frontend
VITE_API_BASE_URL=http://localhost:5000  # Backend URL for API calls

# pgAdmin (optional database UI)
PGADMIN_EMAIL=admin@wallet.local
PGADMIN_PASSWORD=admin
```

## Architecture Overview

**How Hot-Reload Works:**

```
┌─────────────────────────────────────────────────────────┐
│                   Your Development Machine              │
├──────────────────────┬──────────────────────────────────┤
│    docker-compose    │        Docker Containers         │
│   (manages services) ├──────────────────────────────────┤
│                      │  Frontend Container              │
│                      │  ├─ Node.js 20 Alpine           │
│                      │  ├─ npm installed dependencies  │
│                      │  ├─ Vite dev server (5173)      │
│                      │  └─ HMR WebSocket listener      │
│                      ├──────────────────────────────────┤
│                      │  Backend Container               │
│                      │  ├─ Python 3.11 Slim            │
│                      │  ├─ pip dependencies            │
│                      │  ├─ Flask dev server (5000)     │
│                      │  └─ Auto-reload on .py changes  │
│                      ├──────────────────────────────────┤
│                      │  Database Container              │
│                      │  ├─ PostgreSQL 15 Alpine        │
│                      │  ├─ Port 5432 exposed           │
│                      │  └─ Volume persists data        │
│                      └──────────────────────────────────┘
│                                 ↑↑
│      ┌──────────────────────────┘└───────────────────┐
│      │                                                │
│   Volumes Mount                                   Port Forwarding
│   (source code                                    (access services
│    sync for                                        from host)
│    hot-reload)
└──────────────────────────────────────────────────────────┘

When you edit:
1. frontend/src/components/MyComponent.vue
   └─ File changes detected by Vite
      └─ HMR sends module update to browser
         └─ Component updates without full page reload

2. backend/app/routes/api.py
   └─ File changes detected by Flask
      └─ Auto-reloader restarts Flask process
         └─ New code runs on next request
```

---

**Happy coding! Your environment is ready for rapid development.**
