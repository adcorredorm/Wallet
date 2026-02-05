# Development Workflow Guide

This guide explains how to set up and use the Docker-based development environment with hot-reload for both frontend and backend services.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Development Setup](#development-setup)
3. [Frontend Hot Reload (Vite HMR)](#frontend-hot-reload-vite-hmr)
4. [Backend Hot Reload](#backend-hot-reload)
5. [Database Management](#database-management)
6. [Common Workflows](#common-workflows)
7. [Troubleshooting](#troubleshooting)
8. [Production vs Development](#production-vs-development)

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Node.js 20+ (for local development without Docker)
- Python 3.11+ (for local development without Docker)
- `.env` file created from `.env.example`

### Start Development Environment

```bash
# Navigate to project root
cd /Users/angelcorredor/Code/Wallet

# Create .env from example if not exists
cp .env.example .env

# Start all services with hot-reload enabled
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# In another terminal, to view logs from specific service:
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f frontend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend
```

### Access Development Environment

- **Frontend (Vite Dev Server)**: http://localhost:3000 or http://localhost:5173
- **Backend API**: http://localhost:5001 (proxied from port 5000)
- **pgAdmin Database UI**: http://localhost:5050
  - Email: admin@wallet.local
  - Password: admin

## Development Setup

### Initial Setup

1. **Clone and Install Dependencies**
   ```bash
   cd /Users/angelcorredor/Code/Wallet

   # Initialize development environment
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

   # Wait for database to initialize (watch logs)
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f db
   ```

2. **Environment Configuration**
   - Copy `.env.example` to `.env`
   - Adjust database credentials if needed
   - The `.env` file is automatically loaded by Docker Compose

3. **Database Initialization**
   - Backend service automatically runs migrations on startup: `flask db upgrade`
   - Database schema is created automatically
   - Initial seed data can be added through backend endpoints

### Docker Compose File Structure

The development setup uses **Docker Compose file merging**:

```bash
# Base configuration (all services definitions)
docker-compose.yml

# Development overrides (applies dev-specific changes)
-f docker-compose.dev.yml

# Production overrides (for production deployment)
-f docker-compose.prod.yml
```

**How it works:**
- `docker-compose.yml` defines all services with production-like defaults
- `docker-compose.dev.yml` overrides specific settings for development:
  - Exposes ports for debugging
  - Mounts source code as volumes
  - Enables auto-reload features
  - Enables pgAdmin by default

When using `-f docker-compose.yml -f docker-compose.dev.yml up`:
1. Base services are loaded from `docker-compose.yml`
2. Development settings override the base settings
3. The result is a merged configuration with development features

## Frontend Hot Reload (Vite HMR)

### How It Works

Vite's Hot Module Replacement (HMR) allows frontend changes to reflect instantly in the browser without full page reload:

1. **File Change Detection**: Vite detects changes to `.vue`, `.ts`, `.js`, `.css` files
2. **Module Update**: Modified modules are recompiled and sent to the browser
3. **Browser Update**: Browser applies changes to running application state

### Frontend Development

Make changes to any frontend file and see updates immediately:

```bash
# Frontend source files
/Users/angelcorredor/Code/Wallet/frontend/
├── src/
│   ├── components/     # Vue components (changes trigger HMR)
│   ├── pages/         # Page components
│   ├── stores/        # Pinia state management
│   ├── App.vue        # Root component
│   └── main.ts        # Entry point
├── index.html         # HTML template
└── vite.config.ts     # Vite configuration

# Changes to these files trigger instant reload:
src/components/**/*.vue    # Vue components
src/**/*.ts                # TypeScript files
src/**/*.css               # CSS/style files
src/**/*.js                # JavaScript files
```

### Frontend Development Example

1. **Edit a Component**
   ```bash
   # Open frontend/src/components/WalletCard.vue
   # Make any change (e.g., update text, change styling)
   # Save the file
   ```

2. **Observe Changes**
   - Browser automatically refreshes the component
   - Application state is preserved
   - Changes appear within 1-2 seconds

3. **Console Output**
   ```
   [vite] hmr update /src/components/WalletCard.vue
   [vite] page reload triggered
   ```

### Frontend Environment Variables

Development frontend uses these variables:

```env
# Vite HMR Configuration
VITE_HMR_HOST=localhost         # WebSocket host for HMR
VITE_HMR_PORT=5173             # HMR port
VITE_HMR_PROTOCOL=ws           # WebSocket protocol

# API Configuration
VITE_API_BASE_URL=http://localhost:5000

# Development flag
NODE_ENV=development
```

### Troubleshooting Frontend HMR

**Issue: Changes not reflecting in browser**
- Ensure `VITE_HMR_HOST=localhost` is set
- Clear browser cache (Cmd+Shift+Delete)
- Restart container: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart frontend`

**Issue: WebSocket connection errors**
- Check firewall allows port 5173
- Verify `VITE_HMR_PORT=5173` matches exposed port
- Use `docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs frontend` to check for errors

**Issue: node_modules permission errors**
- Volume mount excludes `/app/node_modules` to use container versions
- If needed, rebuild: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache frontend`

## Backend Hot Reload

### How It Works

Flask's development server in watch mode monitors Python files and automatically restarts when changes are detected:

1. **File Change Detection**: Flask watches `.py` files in `/app`
2. **Server Restart**: Application context is recreated
3. **Request Handling**: New code is used for subsequent requests

### Backend Development

Make changes to any Python file and Flask will auto-reload:

```bash
# Backend source files
/Users/angelcorredor/Code/Wallet/backend/
├── app/
│   ├── models/        # SQLAlchemy models
│   ├── routes/        # API endpoints
│   ├── services/      # Business logic
│   └── __init__.py    # Flask app factory
├── alembic/           # Database migrations
├── run.py             # Application entry point
└── requirements.txt   # Python dependencies

# Changes to these files trigger Flask reload:
app/**/*.py            # All Python files
run.py                 # Entry point
```

### Backend Development Example

1. **Edit an API Route**
   ```bash
   # Open backend/app/routes/wallet.py
   # Make any change (e.g., add endpoint, modify response)
   # Save the file
   ```

2. **Observe Changes**
   - Flask detects the file change
   - Server restarts automatically
   - Look for messages like: `[Restarting with stat]`
   - Next API call uses updated code

3. **Console Output**
   ```
   [timestamp] * Detected change in '/app/app/routes/wallet.py', restarting with stat
   [timestamp] * Debugger is active!
   [timestamp] * Debugger PIN: XXX-XXX-XXX
   ```

### Backend Debug Mode

Debug mode is enabled in development:

```python
# View Flask debug configuration
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend printenv | grep DEBUG
# Output: DEBUG=True
```

**Debug Features:**
- Interactive stack traces on errors
- Automatic reloader on file changes
- Pin-protected interactive debugger
- Detailed error pages

### Backend Environment Variables

Development backend uses these variables:

```env
FLASK_ENV=development           # Enable development features
DEBUG=True                       # Enable debug mode
FLASK_CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://frontend:80

# Database
DATABASE_URL=postgresql://wallet_user:wallet_password@db:5432/wallet_db
SQLALCHEMY_DATABASE_URI=postgresql://wallet_user:wallet_password@db:5432/wallet_db

# Application
SECRET_KEY=dev-secret-key-change-in-production
```

### Troubleshooting Backend Hot Reload

**Issue: Server not restarting on changes**
- Verify Flask running with `--reload` flag
- Check logs for errors: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend`
- Restart service: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart backend`

**Issue: Syntax errors causing crashes**
- Flask will log the error and keep the server running (recovers on fix)
- Fix the Python syntax error
- Refresh browser to trigger API call and reload

**Issue: Database migration failures**
- Migrations run automatically on startup
- Check database status: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f db`
- Manual migration: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend flask db upgrade`

## Database Management

### Using pgAdmin (Web UI)

pgAdmin is enabled by default in development at http://localhost:5050

**Login:**
- Email: admin@wallet.local
- Password: admin

**Features:**
- Browse database schema
- Run SQL queries
- Inspect tables and data
- Monitor database performance

**Adding Database Connection in pgAdmin:**
1. Click "Add New Server"
2. **General Tab:**
   - Name: `Wallet DB`
3. **Connection Tab:**
   - Hostname: `db` (Docker service name)
   - Port: `5432`
   - Username: `wallet_user`
   - Password: `wallet_password`
   - Database: `wallet_db`
4. Click "Save"

### Command Line Database Operations

```bash
# Connect to database with psql
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec db psql -U wallet_user -d wallet_db

# Run specific SQL query
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec db psql -U wallet_user -d wallet_db -c "SELECT version();"

# Backup database
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec db pg_dump -U wallet_user wallet_db > backup.sql

# Restore from backup
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T db psql -U wallet_user wallet_db < backup.sql
```

### Flask Database Commands

```bash
# View current database version
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend flask db current

# Run pending migrations
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend flask db upgrade

# Revert last migration
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend flask db downgrade

# Create new migration (after model changes)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend flask db migrate -m "Description of changes"
```

## Common Workflows

### Starting Development Session

```bash
# Terminal 1: Start all services
cd /Users/angelcorredor/Code/Wallet
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Wait for all services to be healthy (look for "healthy" status)
# Terminal 2: Tail logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f
```

### Adding a New Frontend Component

```bash
# 1. Create component file
cat > frontend/src/components/NewFeature.vue << 'EOF'
<template>
  <div>New Feature</div>
</template>

<script setup lang="ts">
// Component logic here
</script>

<style scoped>
/* Styles here */
</style>
EOF

# 2. Import in App.vue or target page
# 3. Save file
# 4. Changes automatically appear in browser via HMR
```

### Adding a New Backend API Endpoint

```bash
# 1. Edit or create backend/app/routes/new_feature.py
cat > backend/app/routes/new_feature.py << 'EOF'
from flask import Blueprint, jsonify
from app import db

bp = Blueprint('new_feature', __name__, url_prefix='/api/v1/features')

@bp.route('', methods=['GET'])
def get_features():
    return jsonify({'features': []})
EOF

# 2. Register in app/__init__.py
# 3. Save file
# 4. Flask auto-reloads
# 5. API endpoint immediately available
```

### Installing New Dependencies

**Frontend (npm packages):**
```bash
# 1. Stop containers
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# 2. Add dependency (from host machine)
cd frontend
npm install new-package

# 3. Rebuild frontend image with new dependencies
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build frontend

# 4. Restart services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

**Backend (Python packages):**
```bash
# 1. Edit backend/requirements.txt with new package

# 2. Stop containers
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# 3. Rebuild backend image
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build backend

# 4. Restart services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Inspecting Container State

```bash
# View running containers
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps

# Execute command in backend container
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -c "import app; print(app.__version__)"

# View environment variables in container
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend printenv

# SSH into container (requires sh in image)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend sh
```

## Troubleshooting

### Services Won't Start

**Check if port already in use:**
```bash
# Find process using port 5173 (frontend)
lsof -i :5173

# Find process using port 5001 (backend)
lsof -i :5001

# Kill the process if needed
kill -9 <PID>
```

**Check Docker resource limits:**
```bash
# View Docker stats
docker stats

# Restart Docker daemon if needed
# macOS: Click Docker icon > Restart
# Linux: sudo systemctl restart docker
```

### Database Connection Issues

**Test database connectivity:**
```bash
# From host machine
psql -h localhost -U wallet_user -d wallet_db

# From backend container
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend psql -h db -U wallet_user -d wallet_db
```

**Check database logs:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs db
```

### Frontend/Backend Not Communicating

**Test API connectivity:**
```bash
# From frontend container to backend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend wget -O- http://backend:5000/health

# From host to backend
curl http://localhost:5001/health
```

**Check CORS settings:**
```bash
# Verify FLASK_CORS_ORIGINS includes frontend origin
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend printenv | grep CORS
```

### View Detailed Logs

```bash
# All services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs --tail=100

# Single service with follow
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f frontend

# Specific service with timestamps
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs --timestamps backend
```

### Clean Up and Reset

```bash
# Stop all containers
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# Remove volumes (DELETES DATA)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v

# Remove unused Docker resources
docker system prune

# Rebuild images from scratch
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache
```

## Production vs Development

### Key Differences

| Aspect | Development | Production |
|--------|-------------|-----------|
| **Frontend Server** | Vite dev server (HMR) | Nginx (static files) |
| **Backend Server** | Flask dev (auto-reload) | Gunicorn (4 workers) |
| **Code Mounting** | Source mounted (live reload) | Code in image (immutable) |
| **Debug Mode** | Enabled | Disabled |
| **Database Ports** | Exposed (5432) | Closed |
| **pgAdmin** | Enabled | Disabled |
| **CORS** | Permissive | Restricted |
| **Health Checks** | Lenient | Strict |

### Switching to Production

```bash
# Stop development environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# Start production environment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

### Production Checklist

Before deploying to production:

- [ ] Remove all debug print statements
- [ ] Set `SECRET_KEY` to a strong random value
- [ ] Update `FLASK_CORS_ORIGINS` with actual domain
- [ ] Update `VITE_API_BASE_URL` to production API
- [ ] Verify database credentials are strong
- [ ] Check SSL/TLS certificates are configured
- [ ] Review environment variables in `.env`
- [ ] Run security audit: `docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec backend pip-audit`
- [ ] Test all features in staging environment first
- [ ] Set up monitoring and logging
- [ ] Document deployment procedures

---

For more information about Docker Compose, see: https://docs.docker.com/compose/
For Vite HMR documentation, see: https://vitejs.dev/guide/ssr.html#setting-up-the-dev-server
