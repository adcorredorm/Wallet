# Docker Compose Architecture Guide

This document explains how the Docker Compose setup works, the file merging strategy, and the architecture of the development and production environments.

## Table of Contents

1. [Compose File Structure](#compose-file-structure)
2. [File Merging Behavior](#file-merging-behavior)
3. [Development Environment](#development-environment)
4. [Production Environment](#production-environment)
5. [Network Architecture](#network-architecture)
6. [Volume Architecture](#volume-architecture)
7. [Service Dependencies](#service-dependencies)

## Compose File Structure

### Three Main Configuration Files

```
docker-compose.yml          ← Base configuration (production-like defaults)
├── Defines all 4 services
├── Default ports and volumes
└── Health checks and restart policies

docker-compose.dev.yml      ← Development overrides (applies on top of base)
├── Mounts source code volumes
├── Enables auto-reload/HMR
├── Exposes debug ports
└── Enables pgAdmin

docker-compose.prod.yml     ← Production overrides (applies on top of base)
├── Removes volume mounts
├── Disables debug features
├── Tightens security
└── Optimizes resources
```

### File Loading Behavior

**Docker Compose file merging works like this:**

1. First file loaded completely: `docker-compose.yml`
2. Second file merged on top: `-f docker-compose.dev.yml` or `-f docker-compose.prod.yml`
3. Matching service names have their settings merged/overridden

```bash
# Example: Development command
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# File merge order:
# 1. Load docker-compose.yml (base)
# 2. Merge docker-compose.dev.yml (overrides)
# Result: Combined configuration with dev settings
```

## File Merging Behavior

### How Services Merge

When a service appears in both files:

```yaml
# docker-compose.yml (base)
services:
  frontend:
    image: node:20-alpine
    ports:
      - "3000:80"
    volumes:
      - ./frontend:/app

# docker-compose.dev.yml (overlay)
services:
  frontend:
    ports:
      - "5173:5173"  # REPLACES the base ports
    volumes:
      - ./frontend:/app  # REPLACES base volumes
      - /app/node_modules

# Result: Merged configuration
services:
  frontend:
    image: node:20-alpine  # from base (not in dev)
    ports:
      - "5173:5173"  # from dev (OVERRIDES base)
    volumes:
      - ./frontend:/app  # from dev (OVERRIDES base)
      - /app/node_modules  # from dev (added)
```

### Key Merging Rules

- **Arrays**: Completely replaced (not merged)
- **Objects**: Merged (nested keys combined)
- **Scalar values**: Overridden
- **Top-level keys**: Combined (networks, volumes, etc.)

## Development Environment

### Command
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEVELOPMENT ENVIRONMENT                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────┐      ┌────────────────────┐            │
│  │  Frontend Service  │      │  Backend Service   │            │
│  ├────────────────────┤      ├────────────────────┤            │
│  │ Container: Node 20 │      │ Container: Python  │            │
│  │ Port: 5173 (HMR)   │      │ Port: 5000 (Flask) │            │
│  │ Port: 3000 (compat)│      │                    │            │
│  │                    │      │ Auto-reload: ON    │            │
│  │ Vite Dev Server    │      │ Debug: ON          │            │
│  │ HMR: ENABLED       │      │ CORS: Permissive   │            │
│  │                    │      │                    │            │
│  │ ┌──────────────┐   │      │ ┌──────────────┐   │            │
│  │ │ Volume Mount │   │      │ │ Volume Mount │   │            │
│  │ │ ./frontend   │   │      │ │ ./backend    │   │            │
│  │ │ ↓            │   │      │ │ ↓            │   │            │
│  │ │ /app (live)  │   │      │ │ /app (live)  │   │            │
│  │ └──────────────┘   │      │ └──────────────┘   │            │
│  └────────────────────┘      └────────────────────┘            │
│         ↓ Hot Reload                 ↓ Auto-reload             │
│      Instant HMR              Flask restarts on .py change     │
│                                                                 │
│  ┌─────────────────────────────┐  ┌──────────────────┐        │
│  │  Database Service (PostgreSQL) │ pgAdmin (Web UI) │        │
│  ├─────────────────────────────┤  ├──────────────────┤        │
│  │ Container: PostgreSQL 15    │  │ Port: 5050       │        │
│  │ Port: 5432 (EXPOSED)        │  │ Debug UI         │        │
│  │ Volume: postgres_data       │  │                  │        │
│  │ Healthcheck: Active         │  │ Browse schema    │        │
│  └─────────────────────────────┘  │ Run queries      │        │
│                                     │ Monitor perf     │        │
│                                     └──────────────────┘        │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Development Network (bridge)                 │  │
│  │  Services communicate via DNS: frontend, backend, db     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Host Access (Port Forwarding)                 │  │
│  │  http://localhost:5173  → Frontend (Vite HMR)          │  │
│  │  http://localhost:3000  → Frontend (compat)             │  │
│  │  http://localhost:5001  → Backend API                   │  │
│  │  http://localhost:5050  → pgAdmin                       │  │
│  │  http://localhost:5432  → Database (direct access)      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Development Features

| Feature | Frontend | Backend | Database |
|---------|----------|---------|----------|
| **Server** | Vite (5173) | Flask (5000) | PostgreSQL (5432) |
| **Hot Reload** | ✓ HMR | ✓ Auto-reload | N/A |
| **Source Mount** | ✓ /frontend→/app | ✓ /backend→/app | N/A |
| **Debug Mode** | ✓ Vite debug | ✓ Flask debug | ✓ Query logs optional |
| **Ports Exposed** | ✓ Yes | ✓ Yes | ✓ Yes (5432) |
| **Health Checks** | ✓ Lenient (15s) | ✓ Lenient (15s) | ✓ Active |
| **Extra Tools** | npm console | Python shell | pgAdmin UI |
| **Rebuild needed** | ✗ No | ✗ No | N/A |

### Development Data Flow

```
┌─────────────┐
│  Developer  │ edits frontend/src/components/Card.vue
└──────┬──────┘
       │
       ↓
┌─────────────────────────────────────┐
│ Host file system detects change     │
│ (file watcher via bind mount)       │
└──────┬──────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────┐
│ Container sees file change          │
│ (synchronized via bind volume)      │
└──────┬──────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────┐
│ Vite dev server detects change      │
│ (uses chokidar file watcher)        │
└──────┬──────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────┐
│ Vite compiles module                │
│ Sends HMR update to browser         │
└──────┬──────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────┐
│ Browser receives HMR via WebSocket  │
│ (ws://localhost:5173)               │
└──────┬──────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────┐
│ Browser applies module update       │
│ UI changes without full reload      │
└─────────────────────────────────────┘
```

## Production Environment

### Command
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   PRODUCTION ENVIRONMENT                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────┐      ┌────────────────────┐            │
│  │  Frontend Service  │      │  Backend Service   │            │
│  ├────────────────────┤      ├────────────────────┤            │
│  │ Container: Nginx   │      │ Container: Python  │            │
│  │ Port: 80 (internal)│      │ Port: 5000 (inter.)│            │
│  │                    │      │                    │            │
│  │ Static files built │      │ Gunicorn (4x)      │            │
│  │ in container       │      │ Optimized config   │            │
│  │                    │      │                    │            │
│  │ ┌──────────────┐   │      │ ┌──────────────┐   │            │
│  │ │ Built Image  │   │      │ │ Built Image  │   │            │
│  │ │ dist/ baked  │   │      │ │ All deps in  │   │            │
│  │ │ in layer     │   │      │ │ container    │   │            │
│  │ └──────────────┘   │      │ └──────────────┘   │            │
│  │ (NO volumes)       │      │ (NO volumes)       │            │
│  └────────────────────┘      └────────────────────┘            │
│         ↓ Static                  ↓ Optimized WSGI             │
│      Fast serving            Concurrent requests               │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Database Service (PostgreSQL)                          │  │
│  ├─────────────────────────────────────────────────────────┤  │
│  │ Container: PostgreSQL 15                                │  │
│  │ Port: 5432 (NOT exposed to host)                       │  │
│  │ Volume: postgres_data (persistent)                     │  │
│  │ Resource Limits: 1 CPU, 512MB RAM                      │  │
│  │ Restart: always                                        │  │
│  │ Healthcheck: Strict (60s intervals)                    │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          Production Network (bridge)                    │  │
│  │  Services isolated: only inter-service communication   │  │
│  │  No port exposure on host                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │     External Access (via reverse proxy)                 │  │
│  │  https://yourdomain.com  → Reverse Proxy                │  │
│  │                               ↓                          │  │
│  │                           (Optional)                     │  │
│  │                         Load Balancer                    │  │
│  │                               ↓                          │  │
│  │                    Frontend + Backend                    │  │
│  │         (Docker containers on same network)             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Production Features

| Feature | Frontend | Backend | Database |
|---------|----------|---------|----------|
| **Server** | Nginx | Gunicorn (4) | PostgreSQL |
| **Hot Reload** | ✗ Static built | ✗ No | N/A |
| **Source Mount** | ✗ No volumes | ✗ No volumes | N/A |
| **Debug Mode** | ✗ Disabled | ✗ Disabled | N/A |
| **Ports Exposed** | ✗ Internal only | ✗ Internal only | ✗ Closed |
| **Health Checks** | ✓ Strict (60s) | ✓ Strict (60s) | ✓ Strict |
| **Resource Limits** | 0.5 CPU, 256M | 1 CPU, 512M | 1 CPU, 512M |
| **Read-only FS** | ✓ Enabled | N/A | N/A |
| **Restart Policy** | always | always | always |

## Network Architecture

### Docker Network Configuration

Both dev and prod use the same network strategy:

```yaml
networks:
  wallet_network:
    driver: bridge
```

### Service Discovery

Containers communicate via DNS names (no IP addresses needed):

```bash
# From frontend container → Backend
curl http://backend:5000/api/v1/users

# From backend container → Database
psql -h db -U wallet_user -d wallet_db

# From external (host machine)
curl http://localhost:5001/api/v1/users  # Port forwarding
```

### Port Mapping

**Development:**
```
Host (localhost) ↔ Docker Port Mapping ↔ Container
─────────────────────────────────────────────────────
5173:5173        ← Frontend Vite (HMR)
5001:5000        ← Backend Flask API
5432:5432        ← Database PostgreSQL
5050:80          ← pgAdmin UI
```

**Production:**
```
Host (localhost)          ← No port mappings
Internal Docker Network
─────────────────────────────────────────────────────
frontend:80  ← Internal only
backend:5000 ← Internal only
db:5432      ← Internal only

External Access via Reverse Proxy
reverse-proxy:443 ↔ reverse-proxy:80 → frontend:80
```

## Volume Architecture

### Development Volumes

**Bind Mounts** (source code syncing):
```
Host Machine                Docker Container
───────────────────────────────────────────────
/Users/.../frontend/    ↔  /app (in frontend container)
/Users/.../backend/     ↔  /app (in backend container)
```

Benefits:
- Source code changes immediately visible in container
- Hot-reload features can detect file changes
- Easy to edit files with host editor

**Named Volumes** (data persistence):
```
Container File System     Docker Volume        Host Storage
─────────────────────────────────────────────────────────────
/var/lib/postgresql/data  ↔  postgres_data     ~= /var/lib/docker/volumes/
/var/lib/pgadmin          ↔  pgadmin_data      (managed by Docker)
```

### Production Volumes

**No Bind Mounts** - Code is immutable in container:
```
Container has complete application
app/ = frozen at build time
No host synchronization
```

**Persistent Volumes** for data:
```
Container File System     Docker Volume        Host Storage
─────────────────────────────────────────────────────────────
/var/lib/postgresql/data  ↔  postgres_data     /var/lib/wallet/data
(specified mount point)
```

## Service Dependencies

### Startup Order

Docker Compose ensures services start in correct order:

```yaml
depends_on:
  db:
    condition: service_healthy  # Wait for health check
```

### Startup Sequence

1. **Database (db)** starts first
   - PostgreSQL initializes
   - Health check validates availability
   - Waits up to 10s (dev) / 30s (prod)

2. **Backend** starts after db is healthy
   - Python environment loads
   - Flask application initializes
   - Database migrations run (`flask db upgrade`)
   - Server becomes ready
   - Health check validates API is responding

3. **Frontend** starts after backend
   - Node dependencies loaded
   - Vite dev server starts (dev) or Nginx starts (prod)
   - Ready for connections

4. **pgAdmin** (dev only) starts after db is healthy
   - Web UI becomes available

### Health Check Strategy

```
Frontend    Backend      Database
  ↓           ↓            ↓
 HMR        Flask        postgres
 check      health        pg_isready
   ↑           ↑            ↑
   └───────────┴────────────┘
   Periodic validation
```

## Configuration Comparison Table

### Base Configuration (docker-compose.yml)

```yaml
db:
  image: postgres:15-alpine
  ports: ["5432:5432"]              # Exposed for flexibility
  environment: production-like
  healthcheck: active
  restart: unless-stopped

backend:
  volumes: [./backend:/app]         # Allow development
  environment: FLASK_ENV=development
  command: flask run --host=0.0.0.0

frontend:
  build: ./frontend (Dockerfile)    # Multi-stage build
  ports: ["3000:80"]
```

### Development Overlay (docker-compose.dev.yml)

```yaml
backend:
  command: flask run --host=0.0.0.0 --reload  # Add reload
  environment:
    DEBUG: "True"                             # Add debug

frontend:
  build: ./frontend (Dockerfile.dev)          # Override build
  ports: ["5173:5173", "3000:5173"]          # Vite ports
  volumes: [./frontend:/app, /app/node_modules]
  environment:
    VITE_HMR_HOST: localhost
    VITE_HMR_PORT: 5173
```

### Production Overlay (docker-compose.prod.yml)

```yaml
db:
  ports: []                          # Remove port exposure
  restart: always

backend:
  image: wallet-backend:latest       # Use pre-built image
  ports: []                          # Remove port mapping
  volumes: []                        # Remove source mount
  command: gunicorn ...             # Use WSGI server

frontend:
  image: wallet-frontend:latest
  ports: []
  volumes: []
  read_only: true                    # Immutable filesystem
```

## Practical Examples

### Example 1: Edit Frontend Component

```bash
# 1. Start with dev config
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 2. Edit component
nano frontend/src/components/Card.vue

# 3. Docker Compose merges files:
#    - Base config: Frontend service defined
#    - Dev overlay: Volumes and HMR settings applied
#    - Result: Vite watches files, HMR enabled

# 4. Changes appear instantly in browser
# (no rebuild, no container restart needed)
```

### Example 2: Switch to Production

```bash
# 1. Stop development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# 2. Start production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 3. Docker Compose merges files:
#    - Base config: All services defined
#    - Prod overlay: Optimized settings applied
#    - Result: Production-grade setup with no volumes

# 4. Application runs from built images
# (fast, secure, scalable)
```

### Example 3: Add New Backend Dependency

```bash
# With dev config active
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 1. Edit requirements.txt
# 2. Rebuild image (file mount allows you to edit requirements, then rebuild)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build backend

# 3. Restart service
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up backend

# The dev overlay ensures source is mounted so you can edit requirements.txt
```

---

**Key Takeaway:** Docker Compose file merging allows a single base configuration that can be optimized for either development (with hot-reload) or production (with optimization and security) using simple overlay files.
