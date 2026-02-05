# Docker Services Reference

This document provides a detailed reference for each Docker service in the Wallet application.

## Service Inventory

| Service | Image | Port (Host) | Port (Container) | Purpose |
|---------|-------|-------------|------------------|---------|
| db | postgres:15-alpine | 5432 | 5432 | PostgreSQL Database |
| backend | Custom (Flask) | 5000 | 5000 | Flask API Backend |
| frontend | Custom (Nginx) | 3000, 80 | 80 | Vue.js Web Frontend |
| pgadmin | dpage/pgadmin4 | 5050 | 80 | Database Management UI (Optional) |

## Database Service (db)

### Configuration

```yaml
service_name: db
container_name: wallet_postgres
image: postgres:15-alpine
ports: 5432:5432
```

### Purpose

- Persistent data storage using PostgreSQL 15
- Supports all database operations for the Wallet application
- Alpine Linux base image for minimal footprint

### Environment Variables

```env
POSTGRES_DB=wallet_db              # Database name
POSTGRES_USER=wallet_user          # Database user
POSTGRES_PASSWORD=wallet_password  # Database password (change in production)
PGTZ=UTC                          # Timezone
```

### Volumes

| Volume | Mount Point | Purpose |
|--------|------------|---------|
| postgres_data | /var/lib/postgresql/data | Data persistence |

### Health Check

```bash
pg_isready -U wallet_user -d wallet_db
```

### Useful Commands

```bash
# Connect to database
docker-compose exec db psql -U wallet_user -d wallet_db

# List tables
docker-compose exec db psql -U wallet_user -d wallet_db -c "\dt"

# Create backup
docker-compose exec db pg_dump -U wallet_user wallet_db > backup.sql

# View logs
docker-compose logs db
```

### Performance Tuning (Production)

For production deployments, adjust PostgreSQL parameters:

```yaml
environment:
  POSTGRES_INITDB_ARGS: "-c shared_buffers=256MB -c effective_cache_size=1GB"
```

### Resource Limits (Production)

```yaml
deploy:
  resources:
    limits:
      cpus: '1'
      memory: 512M
    reservations:
      cpus: '0.5'
      memory: 256M
```

---

## Backend Service (backend)

### Configuration

```yaml
service_name: backend
container_name: wallet_backend
image: wallet-backend:latest (built from ./backend/Dockerfile)
ports: 5000:5000
```

### Purpose

- Flask REST API server
- Business logic implementation
- Database queries and transactions
- Authentication and authorization

### Base Image Details

- **Image**: python:3.11-slim
- **Reasoning**: Official Python image with minimal footprint, suitable for server applications
- **Size**: ~150MB (vs 1GB+ for python:3.11)

### Dockerfile Layers

1. **Base**: `python:3.11-slim`
2. **System deps**: gcc, postgresql-client
3. **Non-root user**: appuser (security best practice)
4. **Python deps**: Installed from requirements.txt
5. **Application**: Flask application code

### Environment Variables

```env
# Flask configuration
FLASK_APP=run.py                  # Flask entry point
FLASK_ENV=development|production  # Environment mode
DEBUG=True|False                  # Debug mode (production: False)
SECRET_KEY=...                    # Session/CSRF protection key

# Database connection
DATABASE_URL=postgresql://wallet_user:wallet_password@db:5432/wallet_db
SQLALCHEMY_DATABASE_URI=postgresql://wallet_user:wallet_password@db:5432/wallet_db

# CORS settings
FLASK_CORS_ORIGINS=http://localhost:3000,http://frontend:80
```

### Volumes (Development)

```yaml
volumes:
  - ./backend:/app           # Mount source code (hot reload)
  - /app/venv               # Exclude virtual environment
```

### Ports

| Port | Use |
|------|-----|
| 5000 | Flask development server |

### Health Check

```bash
curl -f http://localhost:5000/health
```

Response:
```json
{
  "status": "healthy",
  "service": "wallet-api"
}
```

### Startup Command

```bash
sh -c "
  sleep 5 &&
  flask db upgrade &&
  flask run --host=0.0.0.0
"
```

Process:
1. Wait for database to be ready
2. Run database migrations with Alembic
3. Start Flask development server

### Dependencies

- **PostgreSQL**: Required to be healthy before backend starts
- **Environment**: Depends on .env configuration

### Useful Commands

```bash
# Connect to backend shell
docker-compose exec backend sh

# Access Flask shell (Python REPL with app context)
docker-compose exec backend flask shell

# Run database migrations
docker-compose exec backend flask db upgrade

# Create new migration
docker-compose exec backend flask db migrate -m "description"

# Run tests
docker-compose exec backend pytest

# Run specific test file
docker-compose exec backend pytest tests/test_auth.py

# Run with coverage
docker-compose exec backend pytest --cov=app

# Code linting
docker-compose exec backend ruff check app/
docker-compose exec backend black app/

# View logs
docker-compose logs backend
```

### Production Configuration

```yaml
# Use gunicorn WSGI server
command: >
  gunicorn
  --bind 0.0.0.0:5000
  --workers 4
  --worker-class sync
  --timeout 60
  --access-logfile -
  --error-logfile -
  run:app

# Remove volume mounts
volumes: []

# Add resource limits
deploy:
  resources:
    limits:
      cpus: '1'
      memory: 512M
```

### API Endpoints

**Health Check**
```
GET /health
Response: {"status": "healthy", "service": "wallet-api"}
```

See `/Users/angelcorredor/Code/Wallet/backend/API_EXAMPLES.md` for complete API documentation.

---

## Frontend Service (frontend)

### Configuration

```yaml
service_name: frontend
container_name: wallet_frontend
image: wallet-frontend:latest (built from ./frontend/Dockerfile)
ports: 3000:80
```

### Purpose

- Vue.js 3 single-page application (SPA)
- User interface for the Wallet application
- Nginx web server for static file serving

### Architecture: Multi-Stage Build

**Stage 1: Builder** (Node 20 Alpine)
- Installs dependencies with npm/yarn
- Builds Vue.js application using Vite
- Creates optimized production bundle in `dist/`

**Stage 2: Production** (Nginx Alpine)
- Copies built files from builder stage
- Serves files with Nginx
- Minimal final image size

### Base Image Details

| Stage | Image | Size | Purpose |
|-------|-------|------|---------|
| Builder | node:20-alpine | ~180MB | Build tools |
| Production | nginx:alpine | ~40MB | Web server |
| Final | ~ | ~40MB | Production image |

### Dockerfile Layers (Production Stage)

1. **Base**: `nginx:alpine`
2. **Nginx config**: Custom SPA routing configuration
3. **Built files**: Copy from builder stage
4. **Permissions**: Set proper file ownership
5. **Health check**: HTTP health endpoint

### Nginx Configuration Features

Located in `/Users/angelcorredor/Code/Wallet/frontend/nginx.conf`:

- **SPA Routing**: All routes redirect to index.html (Vue Router compatible)
- **Gzip Compression**: Enabled for .js, .css, .json files
- **Cache Headers**: Static assets cached for 1 year
- **API Proxy**: `/api/` routes proxy to backend service
- **Health Endpoint**: `/health` for Docker health checks
- **Security**: Deny access to hidden files (`.git`, `.env`, etc.)

### Environment Variables

```env
VITE_API_BASE_URL=http://localhost:5000  # Backend API URL
VITE_HMR_HOST=localhost                  # Vite HMR host (dev)
VITE_HMR_PORT=5173                       # Vite HMR port (dev)
```

### Ports

| Port | Use | Environment |
|------|-----|-------------|
| 3000 | Primary access port | All |
| 80 | Direct Nginx port | All (alternative) |
| 5173 | Vite dev server | Development only |

### Health Check

```bash
wget --quiet --tries=1 --spider http://localhost/health
```

### Volumes (Development)

```yaml
volumes:
  - ./frontend:/app        # Mount source code (HMR)
  - /app/node_modules     # Use container's node_modules
```

### Development Setup

```bash
# Start with Vite dev server (hot module reload)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Access at http://localhost:5173
# Changes to Vue components reload instantly
```

### Build Process

```bash
# Build for production
npm run build          # Creates optimized dist/ folder
npm run preview        # Preview production build locally
npm run lint          # ESLint checks
npm run type-check    # TypeScript validation
```

### Useful Commands

```bash
# Connect to frontend container
docker-compose exec frontend sh

# View Nginx configuration
docker-compose exec frontend cat /etc/nginx/conf.d/default.conf

# View logs
docker-compose logs frontend

# Verify Nginx syntax (inside container)
docker-compose exec frontend nginx -t

# Reload Nginx configuration
docker-compose exec frontend nginx -s reload
```

### Production Configuration

```yaml
# Pre-built image
image: wallet-frontend:latest

# Remove ports for reverse proxy setup
ports: []

# Remove volume mounts (static files in image)
volumes: []

# Enable read-only filesystem for security
read_only: true

# Writable tmpfs for Nginx
tmpfs:
  - /var/cache/nginx
  - /var/run
```

### Static Assets Caching

| File Type | Cache Duration | Max-Age |
|-----------|-----------------|---------|
| .js, .css, .svg, .woff* | 1 year | 31536000 |
| index.html | Never | no-cache |
| Other files | Default | - |

---

## pgAdmin Service (Optional)

### Configuration

```yaml
service_name: pgadmin
container_name: wallet_pgadmin
image: dpage/pgadmin4:latest
ports: 5050:80
profiles: [dev]  # Only enabled in development
```

### Purpose

- Web-based PostgreSQL database management tool
- Useful for inspecting data, running queries, creating backups
- Optional - not required for application functionality

### Access

- **URL**: http://localhost:5050
- **Email**: admin@wallet.local
- **Password**: admin

### First Login

1. Open http://localhost:5050
2. Log in with credentials above
3. Add new server:
   - Hostname: `db`
   - Port: `5432`
   - Username: `wallet_user`
   - Password: (from .env)

### Features

- View database structure
- Run SQL queries
- Create backups
- Manage users and permissions
- Monitor activity

### Disable in Production

pgAdmin is configured with `profiles: [dev]`, so it only starts with:

```bash
docker-compose up  # Does NOT start pgAdmin

# To enable (development):
docker-compose --profile dev up
```

To completely disable, remove the service from docker-compose.yml.

### Alternative Tools

- **DBeaver**: Desktop application for database management
- **psql**: Command-line PostgreSQL client
- **DataGrip**: JetBrains database IDE

---

## Network Architecture

All services communicate via Docker bridge network `wallet_network`:

```
Container DNS Resolution:
- db.wallet_network → 172.xx.xx.xx:5432
- backend.wallet_network → 172.xx.xx.xx:5000
- frontend.wallet_network → 172.xx.xx.xx:80
```

### Service-to-Service Communication

| From | To | Protocol | Port |
|------|-----|----------|------|
| backend | db | TCP | 5432 |
| frontend | backend | HTTP | 5000 |
| frontend | API proxy | HTTP | 5000 |
| External | frontend | HTTP | 3000/80 |
| External | backend | HTTP | 5000 |

### DNS Names Available Inside Containers

```bash
# From backend container
curl http://db:5432      # PostgreSQL
curl http://frontend:80  # Nginx

# From frontend container
curl http://backend:5000 # Flask API
curl http://db:5432     # PostgreSQL (not normally accessed from frontend)
```

---

## Volume Management

### Defined Volumes

| Volume | Service | Mount Path | Purpose | Persistence |
|--------|---------|------------|---------|-------------|
| postgres_data | db | /var/lib/postgresql/data | Database files | Persistent |
| pgadmin_data | pgadmin | /var/lib/pgadmin | pgAdmin config | Persistent |

### Bind Mounts (Development)

| Host Path | Container Path | Service | Purpose |
|-----------|----------------|---------|---------|
| ./backend | /app | backend | Source code hot reload |
| ./frontend | /app | frontend | Source code HMR |

### Excluded from Mounts

```
/app/venv          # Backend virtual environment
/app/node_modules  # Frontend node modules
```

This prevents overwriting container's dependencies with host's version.

---

## Startup Order and Dependencies

Services start in this order due to `depends_on: condition: service_healthy`:

```
1. PostgreSQL (db)
   ↓ (waits to be healthy)
2. Backend (backend)
   ↓ (waits for backend to be healthy)
3. Frontend (frontend)

4. pgAdmin (optional, depends on db)
```

### Health Check Strategy

Each service has health checks that docker-compose waits for:

```yaml
db:
  interval: 10s
  timeout: 5s
  retries: 5

backend:
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s

frontend:
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

---

## Resource Limits (Production)

### Applied Limits

**Database**
- CPU: 1 core max, 0.5 core reserved
- Memory: 512MB max, 256MB reserved

**Backend**
- CPU: 1 core max, 0.5 core reserved
- Memory: 512MB max, 256MB reserved

**Frontend**
- CPU: 0.5 core max, 0.25 core reserved
- Memory: 256MB max, 128MB reserved

### Enable Resource Limits

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Security Features

### Implemented

1. **Non-root User**: Backend runs as `appuser` (UID 1000)
2. **Read-only Filesystem**: Frontend can use read-only root (production)
3. **Minimal Base Images**: Alpine/slim variants reduce attack surface
4. **No Hardcoded Secrets**: All sensitive values in environment variables
5. **Network Isolation**: Services communicate via internal network
6. **Health Checks**: Detect unhealthy services automatically

### Additional Hardening (Production)

1. Use secrets management for credentials
2. Enable Nginx SSL/TLS
3. Implement rate limiting
4. Set resource limits (CPU, memory)
5. Regular image updates for base images
6. Vulnerability scanning with Trivy/Snyk
7. Network policies (if using Kubernetes)

---

## Monitoring and Observability

### View Logs

```bash
docker-compose logs           # All services
docker-compose logs backend   # Specific service
docker-compose logs -f        # Follow mode
docker-compose logs --tail=50 # Last 50 lines
```

### Monitor Resources

```bash
docker stats                  # Live resource usage
docker inspect <container>   # Detailed container info
```

### Health Status

```bash
docker-compose ps             # Show health status
docker inspect <container> --format='{{.State.Health.Status}}'
```

### Useful Metrics

- CPU usage per container
- Memory usage and limits
- Network I/O
- Disk usage for volumes
- Exit codes and restart count

---

## Updating and Rebuilding

### Rebuild Images

```bash
# Rebuild all images
docker-compose build

# Force rebuild without cache
docker-compose build --no-cache

# Rebuild specific service
docker-compose build backend
```

### Update Base Images

```bash
# Check for image updates
docker pull python:3.11-slim
docker pull node:20-alpine
docker pull nginx:alpine
docker pull postgres:15-alpine

# Rebuild with new base images
docker-compose build --no-cache
```

### Version Pinning

Current versions in Dockerfiles:
- Python: 3.11-slim
- Node: 20-alpine
- Nginx: alpine (latest)
- PostgreSQL: 15-alpine

For production, pin nginx and PostgreSQL to specific versions:
```dockerfile
FROM nginx:1.25-alpine        # Instead of nginx:alpine
FROM postgres:15.2-alpine     # Instead of postgres:15-alpine
```

---

## References

- Docker Compose Specification: https://compose-spec.io/
- Flask Deployment: https://flask.palletsprojects.com/deploying/
- Vue.js Docker: https://v3.vuejs.org/guide/
- PostgreSQL Docker: https://hub.docker.com/_/postgres
- Nginx Documentation: https://nginx.org/en/docs/
