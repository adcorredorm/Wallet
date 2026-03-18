# Docker Deployment Guide

## Quick Start

### Production Deployment

Deploy the entire application stack ready for production with a single command:

```bash
docker compose up -d
```

This command:
- Builds `wallet-backend:latest` and `wallet-frontend:latest` images
- Starts PostgreSQL, Flask API (gunicorn), Nginx, and the rates cron service
- Applies database migrations automatically
- Exposes the frontend on `http://localhost:3000`
- Backend API accessible through nginx at `http://localhost:3000/api/v1`

The application is production-ready: no debug mode, no code mounts, no development hot reload.

### Development Deployment

Start the application with hot reload and debug tools:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

This command:
- Uses Flask development server with auto-reload (`--reload`)
- Uses Vite dev server with Hot Module Replacement (HMR) for frontend
- Exposes Flask on `http://localhost:5001` (5000 is taken by macOS AirPlay)
- Exposes Vite dev server on `http://localhost:5173` (or legacy `http://localhost:3000`)
- Enables pgAdmin at `http://localhost:5050` for database management
- Enables Flask debug mode for detailed error pages
- Mounts source code volumes for auto-reload on file changes

**Important:** After installing new npm packages, rebuild the frontend image:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml build frontend
```

---

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and update with your values:

```bash
cp .env.example .env
```

**Required for production:**
- `GOOGLE_CLIENT_ID` — Google OAuth client ID
- `JWT_SECRET` — JWT signing secret
- `SECRET_KEY` — Flask session secret key

**Database:**
- `DB_NAME` — PostgreSQL database name (default: `wallet_db`)
- `DB_USER` — PostgreSQL user (default: `wallet_user`)
- `DB_PASSWORD` — PostgreSQL password (default: `wallet_password`)
- `DB_PORT` — PostgreSQL port exposed locally (default: `5432`, not exposed in production)

**Frontend:**
- `VITE_API_BASE_URL` — API endpoint for frontend (default: `/api/v1` for production, `/api/v1` for dev)
- `VITE_GOOGLE_CLIENT_ID` — Google OAuth client ID for frontend

---

## Architecture

### Services

#### **db** (PostgreSQL 15)
- Primary data store
- Named volume: `postgres_data` persists data across restarts
- Production: No exposed ports (backend-only access)
- Development: Port 5432 exposed for local database tools

#### **backend** (Flask API)
- RESTful API powered by Flask + SQLAlchemy
- Production: Gunicorn WSGI server, 4 workers, no source code mounts
- Development: Flask development server with auto-reload
- Runs database migrations (`flask db upgrade`) on startup
- Healthcheck: `/health` endpoint

#### **frontend** (Vue 3 SPA)
- Vue 3 + Vite compiled to static files
- Production: Nginx reverse proxy, read-only filesystem, port 3000
- Development: Vite dev server with HMR, port 5173 (or legacy 3000)
- Nginx routes `/api/*` and `/auth/*` to backend
- Healthcheck: `/health` endpoint

#### **rates_cron** (Exchange Rates)
- Sidecar container running daily exchange rate updates
- Reuses `wallet-backend:latest` image
- Runs `flask rates update` every 24 hours

#### **pgAdmin** (Development Only)
- Database management UI at `http://localhost:5050`
- Credentials: `admin@wallet.local` / `admin`
- Disabled by default in production (`profiles: [dev]`)
- Enable in dev with overlay: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`

---

## Common Tasks

### View logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
```

### Database operations

```bash
# Interactive psql shell
docker compose exec db psql -U wallet_user -d wallet_db

# Run migrations
docker compose exec backend flask db upgrade

# Seed test data (development only)
docker compose exec backend python dev_seed_test_data.py --email user@example.com
```

### Force resync frontend data

```bash
# Settings → Forzar sincronización completa in the app UI
# Or restart containers
docker compose restart backend
```

### Rebuild images

```bash
# Rebuild all images
docker compose build

# Rebuild specific service
docker compose build backend
docker compose build frontend
```

### Clean up and restart

```bash
# Stop all containers
docker compose down

# Remove containers and volumes (WARNING: deletes all data)
# docker compose down -v

# Start fresh
docker compose up -d
```

---

## Production Deployment Checklist

Before deploying to production:

- [ ] Set `FLASK_ENV=production` and `DEBUG=False` in `.env`
- [ ] Generate secure `SECRET_KEY` and `JWT_SECRET` (use `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- [ ] Set `GOOGLE_CLIENT_ID` and `VITE_GOOGLE_CLIENT_ID` from Google OAuth console
- [ ] Update `FLASK_CORS_ORIGINS` to your production domain
- [ ] Use a reverse proxy (Nginx/Apache) or cloud load balancer (AWS ALB, Azure LB) in front of the app
- [ ] Enable HTTPS/TLS on the reverse proxy
- [ ] Set up automated database backups
- [ ] Configure logging aggregation (ELK stack, CloudWatch, Datadog, etc.)
- [ ] Monitor resource usage and set up alerts
- [ ] Test database recovery procedure

---

## Troubleshooting

### "Waiting for database to be ready"

The backend may fail if PostgreSQL hasn't fully initialized. The compose file includes healthchecks that wait for the database to be ready before starting the backend.

If this happens repeatedly:
```bash
docker compose down
docker compose up -d
```

### "Port 5001 already in use" (macOS)

Port 5000 is reserved by macOS for AirPlay. The dev overlay maps Flask to 5001 by default.

If port 5001 is also in use, edit `docker-compose.dev.yml` and change:
```yaml
ports:
  - "5002:5000"  # Use 5002 instead
```

### "Module not found" errors in backend

After updating `backend/requirements.txt`:
```bash
docker compose down
docker compose build backend
docker compose up -d
```

### "Module not found" errors in frontend

After updating `frontend/package.json`:
```bash
# In development overlay
docker compose -f docker-compose.yml -f docker-compose.dev.yml build frontend
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### "CORS error" when accessing API from frontend

Ensure `FLASK_CORS_ORIGINS` environment variable includes your frontend URL:
```bash
# Development
FLASK_CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://frontend:80

# Production
FLASK_CORS_ORIGINS=https://yourdomain.com,http://frontend:80
```

---

## Docker Compose File Structure

### Base Configuration (`docker-compose.yml`)

Production-ready configuration:
- PostgreSQL (no exposed ports)
- Flask with gunicorn (no source code mounts)
- Nginx frontend (read-only filesystem)
- Resource limits and tight healthchecks
- Named volumes for data persistence

### Development Overlay (`docker-compose.dev.yml`)

Overrides base for development:
- Exposes all ports (5432, 5001, 5173, 5050)
- Flask with auto-reload and debug mode
- Vite dev server with HMR
- Source code mounts for hot reload
- Relaxed healthchecks
- pgAdmin enabled by default

**Usage:**
```bash
# Use base alone for production
docker compose up -d

# Use base + overlay for development
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

---

## Security Considerations

### Production Hardening

1. **Read-only filesystem**: Frontend uses `read_only: true` for filesystem immutability
2. **Non-root user**: Flask runs as `appuser` (UID 1000), Nginx as `nginx`
3. **No debug mode**: `DEBUG=False` in production
4. **No source code**: Production Dockerfiles copy code during build, not mounted at runtime
5. **Resource limits**: CPU and memory limits prevent runaway processes
6. **Network isolation**: Database not exposed externally in production
7. **Healthchecks**: Self-healing restart on unhealthy containers

### Development Considerations

- pgAdmin credentials should be changed in `.env`
- Development secrets (`SECRET_KEY`, `JWT_SECRET`) are for local testing only
- Source code mounts expose internals during development
- Debug mode enabled for detailed error pages

---

## Advanced Usage

### Using a custom reverse proxy

If you need SSL termination or additional routing:

```bash
# Create nginx.prod.conf with SSL and custom routing
# Update docker-compose.yml to add a reverse-proxy service
# docker-compose up -d
```

### Scaling gunicorn workers

Edit docker-compose.yml `backend.command` to adjust worker count:
```yaml
command: |
  gunicorn --bind 0.0.0.0:5000 --workers 8 --worker-class sync run:app
```

Higher worker count = more concurrent requests, higher memory usage.

### Database backup strategy

```bash
# Backup PostgreSQL data
docker compose exec db pg_dump -U wallet_user wallet_db > backup.sql

# Restore PostgreSQL data
docker compose exec db psql -U wallet_user wallet_db < backup.sql
```

Or use cloud-native backup solutions (AWS RDS backups, Azure Database for PostgreSQL, etc.).

---

## Support

For issues:
1. Check logs: `docker compose logs`
2. Verify `.env` configuration
3. Ensure Docker daemon is running
4. Rebuild images: `docker compose build`
5. Clean up and restart: `docker compose down && docker compose up -d`
