# Docker Configuration Guide - Wallet Application

This document provides comprehensive instructions for building, running, and managing the Wallet application using Docker and Docker Compose.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Running Services](#running-services)
6. [Database Management](#database-management)
7. [Development Workflow](#development-workflow)
8. [Troubleshooting](#troubleshooting)
9. [Production Deployment](#production-deployment)
10. [Architecture Overview](#architecture-overview)

## Overview

The Wallet application consists of three main services:

- **PostgreSQL Database** (port 5432): Data persistence layer
- **Flask Backend API** (port 5000): Business logic and REST API
- **Vue.js Frontend** (port 3000/80): User interface served via Nginx
- **pgAdmin** (port 5050): Optional database management tool

### Service Architecture

```
┌─────────────────┐
│    Frontend     │ (Nginx SPA)
│   Port 3000/80  │
└────────┬────────┘
         │
    ┌────▼────────┬──────────────┐
    │             │              │
    ▼             ▼              ▼
┌────────┐  ┌──────────┐  ┌───────────┐
│Backend │  │pgAdmin   │  │  Database │
│ Flask  │  │Optional  │  │PostgreSQL │
│ 5000   │  │  5050    │  │   5432    │
└────────┘  └──────────┘  └───────────┘
```

## Prerequisites

### Required

- Docker 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose 2.0+ (included with Docker Desktop)
- Git (for cloning the repository)

### Optional

- Make (for convenient command shortcuts)
- curl or wget (for testing API endpoints)
- DBeaver or pgAdmin (for database inspection)

### System Requirements

- Minimum 2GB RAM available
- At least 5GB free disk space
- Linux, macOS, or Windows with WSL2

### Verify Installation

```bash
docker --version          # Docker version 20.10.0 or higher
docker-compose --version  # Docker Compose version 2.0.0 or higher
```

## Quick Start

### 1. Clone and Navigate to Project

```bash
cd /Users/angelcorredor/Code/Wallet
```

### 2. Create Environment File

```bash
cp .env.example .env
# Edit .env with your configuration (optional for development)
```

### 3. Build and Start Services

```bash
# Build images and start all services
docker-compose up --build

# Or use detached mode (run in background)
docker-compose up -d --build

# View logs
docker-compose logs -f
```

### 4. Access Applications

Once all services are healthy (check with `docker-compose ps`):

- **Frontend**: http://localhost:3000 or http://localhost
- **Backend API**: http://localhost:5000
- **pgAdmin** (optional): http://localhost:5050
  - Email: admin@wallet.local
  - Password: admin

### 5. Verify Setup

```bash
# Check service health
docker-compose ps

# Test backend API
curl http://localhost:5000/health

# Check database connection
docker-compose exec db psql -U wallet_user -d wallet_db -c "\dt"

# View logs
docker-compose logs backend
```

## Configuration

### Environment Variables

The application uses environment variables from `.env` file. Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

### Key Configuration Variables

#### Database Configuration

```env
DB_NAME=wallet_db              # PostgreSQL database name
DB_USER=wallet_user            # PostgreSQL user
DB_PASSWORD=wallet_password    # PostgreSQL password (change in production!)
DB_PORT=5432                   # PostgreSQL port
```

#### Flask Application

```env
FLASK_ENV=development          # development, staging, or production
DEBUG=True                      # Enable Flask debug mode (development only)
SECRET_KEY=dev-secret-key...   # Session and CSRF protection key
FLASK_CORS_ORIGINS=...         # Comma-separated allowed origins
```

#### Frontend

```env
VITE_API_BASE_URL=http://localhost:5000  # Backend API URL for frontend
```

### Generating Secure Secrets

For production, generate secure keys:

```bash
# Generate a secure SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"

# Generate a secure database password
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Running Services

### Start Services

```bash
# Start all services in background
docker-compose up -d

# Start specific service
docker-compose up -d db

# Start with verbose output
docker-compose up --build
```

### Stop Services

```bash
# Stop all services (data persists)
docker-compose stop

# Stop and remove containers (data persists in volumes)
docker-compose down

# Stop and remove containers, volumes, and networks
docker-compose down -v

# Completely remove everything including images
docker-compose down -v --rmi all
```

### View Logs

```bash
# View all logs
docker-compose logs

# View backend logs only
docker-compose logs backend

# Follow logs in real-time
docker-compose logs -f

# View last 50 lines of frontend logs
docker-compose logs frontend --tail=50
```

### Access Container Shell

```bash
# Access backend (Flask) shell
docker-compose exec backend sh

# Access backend Python shell
docker-compose exec backend flask shell

# Access database shell
docker-compose exec db psql -U wallet_user -d wallet_db

# Access frontend container
docker-compose exec frontend sh
```

### Check Service Health

```bash
# List all services and their status
docker-compose ps

# Inspect specific service health
docker inspect wallet_backend --format='{{.State.Health.Status}}'

# Get detailed service information
docker-compose stats
```

## Database Management

### Running Migrations

Migrations are automatically applied when the backend starts. To manually run migrations:

```bash
# Apply all pending migrations
docker-compose exec backend flask db upgrade

# Create a new migration (after model changes)
docker-compose exec backend flask db migrate -m "Description of changes"

# Downgrade to previous migration
docker-compose exec backend flask db downgrade

# View migration history
docker-compose exec backend flask db history
```

### Database Operations

```bash
# Connect to database shell
docker-compose exec db psql -U wallet_user -d wallet_db

# Common PostgreSQL commands:
# \dt                 - List all tables
# \du                 - List users/roles
# \db                 - List databases
# \df                 - List functions
# SELECT version();   - Check PostgreSQL version
```

### Backup Database

```bash
# Create backup
docker-compose exec db pg_dump -U wallet_user wallet_db > backup.sql

# Restore from backup
docker-compose exec -T db psql -U wallet_user wallet_db < backup.sql

# Backup with verbose output
docker-compose exec db pg_dump -U wallet_user -v wallet_db > backup.sql
```

### Reset Database

```bash
# WARNING: This deletes all data!
# Stop services
docker-compose stop

# Remove database volume
docker volume rm wallet_postgres_data

# Start services (creates fresh database)
docker-compose up -d

# Confirm fresh database
docker-compose exec db psql -U wallet_user -d wallet_db -c "\dt"
```

## Development Workflow

### Using Development Compose File

The `docker-compose.dev.yml` file enables hot reload for rapid development:

```bash
# Start with development configuration
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View development logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f
```

### Backend Development

With the development setup, Python file changes automatically reload:

```bash
# Make changes to backend code
vim backend/app/routes.py

# Changes apply automatically (Flask debug mode enabled)
# Check logs for errors
docker-compose logs backend

# Run tests
docker-compose exec backend pytest

# Run linting
docker-compose exec backend ruff check app/
docker-compose exec backend black --check app/
```

### Frontend Development

With the development setup, Vue component changes enable hot module reload:

```bash
# Make changes to Vue components
vim frontend/src/components/MyComponent.vue

# HMR applies changes instantly in browser
# Check console for errors
docker-compose logs frontend

# Run linting
docker-compose exec frontend npm run lint
```

### Testing

```bash
# Run backend tests
docker-compose exec backend pytest

# Run with coverage
docker-compose exec backend pytest --cov

# Run specific test file
docker-compose exec backend pytest tests/test_auth.py

# Run with verbose output
docker-compose exec backend pytest -v

# Run frontend tests (if configured)
docker-compose exec frontend npm test
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Database Connection Failed

**Error**: `psycopg2.OperationalError: could not connect to server`

**Solution**:
```bash
# Check if database is running
docker-compose ps

# Check database logs
docker-compose logs db

# Ensure database is healthy
docker-compose exec db pg_isready -U wallet_user

# Wait longer for database to initialize
sleep 10
docker-compose exec backend flask db upgrade
```

#### 2. Port Already in Use

**Error**: `Bind for 0.0.0.0:5000 failed: port is already allocated`

**Solution**:
```bash
# Find process using port
lsof -i :5000

# Kill process using port
kill -9 <PID>

# Or change port in docker-compose.yml
# Change "5000:5000" to "5001:5000"
```

#### 3. Migrations Not Running

**Error**: Backend starts but database tables don't exist

**Solution**:
```bash
# Check backend logs
docker-compose logs backend

# Manually run migrations
docker-compose exec backend flask db upgrade

# Check migration status
docker-compose exec backend flask db current
docker-compose exec backend flask db history
```

#### 4. Frontend Cannot Reach Backend

**Error**: CORS errors or API 404 in browser console

**Solution**:
```bash
# Check CORS configuration
docker-compose logs backend | grep -i cors

# Verify backend is running
curl http://localhost:5000/health

# Check frontend environment
docker-compose exec frontend env | grep VITE

# Update VITE_API_BASE_URL if needed in .env
VITE_API_BASE_URL=http://localhost:5000
```

#### 5. Docker Daemon Not Running

**Error**: `Cannot connect to Docker daemon`

**Solution**:
```bash
# macOS
open -a Docker

# Linux
sudo systemctl start docker

# Windows (Docker Desktop)
# Launch Docker Desktop application
```

#### 6. Out of Disk Space

**Error**: `no space left on device`

**Solution**:
```bash
# Clean up Docker
docker system prune -a

# Remove unused volumes
docker volume prune

# Check disk usage
docker system df
```

#### 7. Container Exiting Immediately

**Error**: `container exited with code 1`

**Solution**:
```bash
# Check service logs
docker-compose logs <service-name>

# Increase verbosity
docker-compose --verbose up

# Check if dependencies are healthy
docker-compose ps

# Review Dockerfile and entrypoint script
```

### Useful Debug Commands

```bash
# View exact environment variables passed to container
docker-compose exec backend env | sort

# Test connectivity between services
docker-compose exec frontend ping backend

# Check DNS resolution
docker-compose exec frontend nslookup db

# Monitor container resource usage
docker stats

# View container inspect details
docker inspect wallet_backend

# Check network connectivity
docker-compose exec backend curl -v http://db:5432

# Verify volume mounts
docker inspect wallet_backend | grep -A 20 Mounts
```

## Production Deployment

### Pre-Deployment Checklist

- [ ] All tests passing locally
- [ ] Generated secure SECRET_KEY
- [ ] Database password changed from default
- [ ] CORS origins configured correctly
- [ ] SSL/TLS certificates obtained
- [ ] Database backup strategy implemented
- [ ] Logging and monitoring configured
- [ ] Health checks verified

### Production Configuration

Create `.env.production`:

```env
FLASK_ENV=production
DEBUG=False
SECRET_KEY=<generate-secure-random-key>
DB_PASSWORD=<strong-production-password>
FLASK_CORS_ORIGINS=https://yourdomain.com
```

### Production Docker Compose

```bash
# Use production override file
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or set environment explicitly
FLASK_ENV=production docker-compose up -d
```

### Security Best Practices

1. **Secrets Management**
   - Never commit `.env` file with real credentials
   - Use Docker secrets for orchestration (Swarm/Kubernetes)
   - Rotate passwords regularly

2. **Network Security**
   - Don't expose database port to internet
   - Use nginx as reverse proxy with SSL
   - Implement rate limiting
   - Enable HTTPS only

3. **Container Security**
   - Run containers as non-root users (implemented)
   - Use read-only filesystems where possible
   - Regularly update base images
   - Scan images for vulnerabilities

4. **Monitoring and Logging**
   - Forward logs to centralized system
   - Monitor container resource usage
   - Set up alerting for failures
   - Keep audit logs

### Reverse Proxy Setup (Nginx)

```nginx
upstream backend {
    server backend:5000;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Redirect HTTP to HTTPS
    if ($scheme != "https") {
        return 301 https://$server_name$request_uri;
    }

    location / {
        proxy_pass http://frontend;
    }

    location /api/ {
        proxy_pass http://backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Database Persistence

```bash
# Weekly backup
0 2 * * 0 docker-compose exec -T db pg_dump -U wallet_user wallet_db > /backups/wallet_$(date +\%Y\%m\%d).sql

# Verify backup
docker-compose exec db psql -U wallet_user -f /backups/wallet_20240131.sql
```

## Architecture Overview

### Directory Structure

```
/Users/angelcorredor/Code/Wallet/
├── docker-compose.yml          # Main production configuration
├── docker-compose.dev.yml      # Development overrides with hot reload
├── .env.example                # Environment variables template
├── .dockerignore                # Files to exclude from build context
├── README-DOCKER.md            # This file
│
├── backend/
│   ├── Dockerfile              # Flask application image definition
│   ├── .dockerignore           # Backend build context exclusions
│   ├── docker-entrypoint.sh    # Initialization script
│   ├── requirements.txt        # Python dependencies
│   ├── app/                    # Flask application code
│   ├── alembic/                # Database migrations
│   ├── tests/                  # Unit tests
│   └── run.py                  # Flask entry point
│
├── frontend/
│   ├── Dockerfile              # Production image (multi-stage)
│   ├── Dockerfile.dev          # Development image with HMR
│   ├── .dockerignore           # Frontend build context exclusions
│   ├── nginx.conf              # Nginx SPA configuration
│   ├── package.json            # Node.js dependencies
│   ├── src/                    # Vue.js application code
│   ├── vite.config.ts          # Vite build configuration
│   └── tsconfig.json           # TypeScript configuration
```

### Network Architecture

```
Docker Host
├─ wallet_network (bridge)
│  ├─ db (postgres:15-alpine)
│  │  └─ Port 5432 (internal) → 5432 (host)
│  │
│  ├─ backend (custom Flask image)
│  │  └─ Port 5000 (internal) → 5000 (host)
│  │
│  └─ frontend (custom Nginx image)
│     └─ Port 80 (internal) → 3000/80 (host)
```

### Volume Management

| Volume | Purpose | Persistence |
|--------|---------|-------------|
| postgres_data | Database storage | Persists until deleted |
| pgadmin_data | pgAdmin configuration | Persists until deleted |
| ./backend (mount) | Development hot reload | Live changes |
| ./frontend (mount) | Development hot reload | Live changes |

### Health Checks

Each service includes health checks:

```yaml
db:
  pg_isready -U wallet_user -d wallet_db

backend:
  curl -f http://localhost:5000/health

frontend:
  wget --quiet --spider http://localhost/health
```

Health checks are used by `depends_on` to ensure proper startup order.

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Specification](https://compose-spec.io/)
- [Flask with Docker](https://flask.palletsprojects.com/en/3.0.x/deploying/docker/)
- [Vue.js Docker Guide](https://v3.vuejs.org/guide/ssr/build-image.html)
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres)
- [Nginx Docker Guide](https://hub.docker.com/_/nginx)

## Support and Contribution

For issues or questions:

1. Check [Troubleshooting](#troubleshooting) section
2. Review Docker Compose logs: `docker-compose logs`
3. Verify all prerequisites are installed
4. Open an issue with:
   - Error messages and logs
   - Output of `docker --version` and `docker-compose --version`
   - Steps to reproduce the issue
