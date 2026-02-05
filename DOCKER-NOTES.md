# Docker Configuration - Important Notes

## Key Changes and Decisions

This document outlines the Docker configuration choices made for the Wallet application.

### 1. Multi-Stage Frontend Build

**What**: The frontend Dockerfile uses a two-stage build process.

**Why**:
- **Stage 1 (Builder)**: Node.js environment for compiling Vue.js with Vite
- **Stage 2 (Production)**: Minimal Nginx image serving static files
- **Benefit**: Final image is only ~40MB instead of 500MB+
- **Result**: Faster deployments, less bandwidth usage, smaller attack surface

**Implementation**:
```dockerfile
FROM node:20-alpine as builder
# Build Vue app here

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

### 2. Health Checks on All Services

**What**: Each service includes a health check endpoint.

**Why**:
- Docker can determine service readiness
- `depends_on: condition: service_healthy` ensures proper startup order
- Automatic container replacement if unhealthy
- Better observability and monitoring

**Checks**:
- **Database**: `pg_isready` command
- **Backend**: `/health` HTTP endpoint
- **Frontend**: `/health` HTTP endpoint

**Important**: If you modify backend routes, ensure `/health` endpoint remains available.

### 3. Non-Root User for Backend

**What**: Backend Flask application runs as `appuser` (UID 1000), not root.

**Why**:
- **Security**: If container is compromised, attacker has limited privileges
- **Best Practice**: Docker security documentation recommends this
- **Performance**: Minimal overhead

**Verification**:
```bash
docker-compose exec backend whoami  # Should output: appuser
```

### 4. Nginx SPA Routing Configuration

**What**: Nginx is configured to route all URLs to `index.html`.

**Why**:
- Vue Router handles client-side routing
- Direct URL access to SPA routes works (e.g., `/dashboard`)
- Proper fallback for non-existent files
- Cache headers prevent stale content

**Config Location**: `/Users/angelcorredor/Code/Wallet/frontend/nginx.conf`

**Key Lines**:
```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

**Important**: If you modify Vue Router configuration, this Nginx config should still work correctly.

### 5. API Proxy Through Frontend

**What**: Frontend Nginx proxies `/api/` requests to the backend service.

**Why**:
- **Single Origin**: Frontend and API appear as single domain to browser
- **CORS Simplification**: Eliminates most CORS issues in production
- **Convenience**: Developers can use relative paths: `/api/endpoint`

**Nginx Config**:
```nginx
location /api/ {
    proxy_pass http://backend:5000/;
}
```

**Implication**: Backend API is not directly exposed in production; access goes through Nginx.

### 6. Development Hot Reload Setup

**What**: `docker-compose.dev.yml` enables live code reloading for both backend and frontend.

**Why**:
- **Backend**: Flask `--reload` flag watches for Python file changes
- **Frontend**: Vite HMR (Hot Module Reload) updates components instantly
- **Productivity**: No need to restart containers during development

**Usage**:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

**Important**: The development setup uses different base images:
- Backend: Still Python, but with reload enabled
- Frontend: Node Alpine with Vite dev server (not Nginx)

### 7. Environment Variables Strategy

**What**: All configuration comes from environment variables, never hardcoded.

**Why**:
- **Security**: Secrets not in images or git
- **Flexibility**: Same image for dev, staging, production
- **12-Factor App**: Follows industry best practices

**Files**:
- `.env.example`: Template showing available variables
- `.env`: Your local overrides (never committed)
- `docker-compose.yml`: References variables with `${VAR_NAME:-default}`

**Important**: The `:-default` syntax provides a fallback value if variable not set.

### 8. Volume Mount Strategy

**Development**:
```yaml
volumes:
  - ./backend:/app          # Mount entire source directory
  - /app/venv              # Exclude virtual environment
```

**Why**:
- Live code changes reflected immediately
- No need to rebuild containers
- But venv is excluded to avoid host/container conflicts

**Production**: No volume mounts
- Static files baked into image
- No performance overhead
- Better security

### 9. Alembic Migrations on Startup

**What**: Backend startup includes `flask db upgrade` before starting the app.

**Why**:
- Automatic schema updates
- No manual migration steps required
- Safe for rolling deployments

**Command**:
```bash
sh -c "
  sleep 5 &&
  flask db upgrade &&
  flask run --host=0.0.0.0
"
```

**Important**:
- Ensure Alembic migrations are in version control
- Test migrations locally before deploying
- `flask db migrate -m "description"` creates new migrations

### 10. pgAdmin Disabled by Default in docker-compose.yml

**What**: pgAdmin service uses `profiles: [dev]`.

**Why**:
- Not needed in production
- Adds security surface area if exposed
- Developers can optionally enable it

**Enable pgAdmin**:
```bash
# Include dev profile
docker-compose --profile dev up -d

# Or use dev compose file
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

---

## Critical Configuration Details

### Backend DATABASE_URL Connection String

**Format**:
```
postgresql://username:password@hostname:port/database
```

**In docker-compose.yml**:
```yaml
DATABASE_URL: postgresql://${DB_USER:-wallet_user}:${DB_PASSWORD:-wallet_password}@db:5432/${DB_NAME:-wallet_db}
```

**Important Considerations**:
- `@db:5432` uses Docker DNS to resolve `db` service
- If you rename the `db` service, update this URL
- Password must be URL-encoded if it contains special characters
- PostgreSQL connection timeout is 30 seconds (sufficient for development)

### CORS Configuration

**Current Default**:
```env
FLASK_CORS_ORIGINS=http://localhost:3000,http://localhost:80,http://frontend:80
```

**For Production**, update to your domain:
```env
FLASK_CORS_ORIGINS=https://yourdomain.com
```

**Why Multiple Origins in Dev**:
- `http://localhost:3000` - Direct frontend port
- `http://localhost:80` - Via host port mapping
- `http://frontend:80` - Via docker DNS inside containers

### Flask Debug Mode

**Development** (`FLASK_ENV=development`):
- `DEBUG=True` enables auto-reload
- Detailed error pages
- Less efficient

**Production** (`FLASK_ENV=production`):
- `DEBUG=False` disables auto-reload
- Generic error pages
- Better performance

**Never set DEBUG=True in production!**

---

## Port Mapping Reference

| Service | Internal Port | Host Port | Use Case |
|---------|---------------|-----------|----------|
| PostgreSQL | 5432 | 5432 | Database connections |
| Backend | 5000 | 5000 | API access, development |
| Frontend | 80 | 3000, 80 | Web interface |
| pgAdmin | 80 | 5050 | Database UI (dev only) |

**Why Port 3000 for Frontend**?
- Common convention for development servers
- Doesn't require root to bind to port 80
- Easy to remember

**Production Setup**:
- Remove direct port mappings
- Use reverse proxy (Nginx/HAProxy) on port 80/443
- Map only essential ports

---

## Container Naming Convention

All containers follow `wallet_*` prefix:
- `wallet_postgres` - Database container
- `wallet_backend` - Backend API container
- `wallet_frontend` - Frontend container
- `wallet_pgadmin` - Database UI container

**Purpose**:
- Easy to identify related containers
- Prevents naming conflicts with other projects
- Consistent with Docker conventions

**Verification**:
```bash
docker ps | grep wallet
```

---

## Network Behavior

### Service Discovery

Inside containers, services are accessible by name via Docker's embedded DNS:

```bash
# From backend container
curl http://db:5432        # Fails (postgres not HTTP)
curl http://frontend:80    # Works

# From frontend container
curl http://backend:5000   # Works
```

### External Access

From the host machine, use `localhost`:

```bash
curl http://localhost:5000        # Backend
curl http://localhost:3000        # Frontend
```

**Important**: Container-to-container communication uses DNS names, not `localhost`.

---

## Persistence and Data Management

### What Persists

```yaml
volumes:
  postgres_data:      # Database files - PERSISTS
  pgadmin_data:       # pgAdmin config - PERSISTS
```

After `docker-compose down`, volumes remain. Data is NOT deleted.

### What Doesn't Persist

Application code (mounted at development):
```yaml
./backend:/app    # Mounted from host, not a volume
./frontend:/app   # Mounted from host, not a volume
```

### Backup Strategy

```bash
# Backup PostgreSQL data
docker-compose exec db pg_dump -U wallet_user wallet_db > backup.sql

# Backup volumes (database files)
docker run --rm -v wallet_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/db-backup.tar.gz -C /data .
```

### Complete Reset

```bash
# Stop and remove everything
docker-compose down -v

# Remove images
docker-compose down -v --rmi all

# This will:
# - Stop all containers
# - Remove containers and networks
# - Remove volumes (DATA LOSS!)
# - Remove images (will rebuild next time)
```

---

## Production Deployment Considerations

### Use docker-compose.prod.yml

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**Changes from development**:
- Database port not exposed
- Frontend uses pre-built image (no node_modules)
- Read-only filesystem for frontend
- Resource limits applied
- Gunicorn WSGI server for backend
- Proper restart policies

### Secrets Management

Never store secrets in .env file in production:

**Options**:
1. **Docker Secrets** (Swarm mode):
   ```bash
   echo "production-password" | docker secret create db_password -
   ```

2. **Environment Variables** (from CI/CD):
   ```bash
   docker-compose up -d  # Reads from system environment
   ```

3. **Secret Management Services**:
   - HashiCorp Vault
   - AWS Secrets Manager
   - Azure Key Vault

### SSL/TLS Certificates

Frontend Nginx should terminate SSL:

```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
}
```

Backend API can run behind SSL-terminating proxy.

### Database Backups

Set up automated backups:

```bash
# Daily backup cron job
0 2 * * * docker-compose exec -T db pg_dump -U wallet_user wallet_db | gzip > /backups/wallet_$(date +\%Y\%m\%d).sql.gz
```

### Monitoring and Logging

**Options**:
1. Docker logs: `docker-compose logs -f`
2. ELK Stack: Elasticsearch, Logstash, Kibana
3. DataDog, New Relic, Splunk
4. Prometheus + Grafana for metrics

---

## Troubleshooting Common Docker Issues

### Issue: "postgres is not ready"

**Cause**: Backend tries to connect before database accepts connections

**Solution**:
```bash
# Increase sleep time in backend command
sh -c "sleep 10 && flask db upgrade && flask run ..."

# Or check database directly
docker-compose exec db pg_isready -U wallet_user
```

### Issue: "Address already in use"

**Cause**: Port 5000, 3000, or 5432 already in use

**Solution**:
```bash
# Find what's using the port
lsof -i :5000

# Change docker-compose.yml port mapping
# "5000:5000" → "5001:5000"

# Or kill the conflicting process
kill -9 <PID>
```

### Issue: "Frontend can't reach backend"

**Cause**: CORS or network configuration issue

**Solution**:
```bash
# Check backend is running
curl http://localhost:5000/health

# Check CORS headers
curl -i http://localhost:5000/health

# Verify network connectivity
docker-compose exec frontend curl http://backend:5000/health

# Check environment variables
docker-compose exec frontend env | grep API
```

### Issue: "Docker daemon not running"

**Solution**:
```bash
# macOS
open -a Docker

# Linux
sudo systemctl start docker

# Windows
# Launch Docker Desktop application
```

---

## Useful Docker Commands Cheat Sheet

```bash
# View what's running
docker-compose ps
docker-compose ps --all

# View logs
docker-compose logs
docker-compose logs backend
docker-compose logs -f  # Follow

# Execute commands in containers
docker-compose exec backend sh
docker-compose exec backend flask shell
docker-compose exec db psql -U wallet_user

# View resource usage
docker stats

# Inspect container details
docker inspect wallet_backend
docker inspect wallet_backend --format='{{.State.Health.Status}}'

# Build images
docker-compose build
docker-compose build --no-cache

# Start/stop services
docker-compose up -d
docker-compose down
docker-compose restart

# Remove everything
docker system prune -a --volumes

# View network info
docker network ls
docker network inspect wallet_network
```

---

## File Locations Reference

| File | Path | Purpose |
|------|------|---------|
| Main Config | `/Users/angelcorredor/Code/Wallet/docker-compose.yml` | Production/dev base |
| Dev Overrides | `/Users/angelcorredor/Code/Wallet/docker-compose.dev.yml` | Development settings |
| Prod Overrides | `/Users/angelcorredor/Code/Wallet/docker-compose.prod.yml` | Production settings |
| Backend Dockerfile | `/Users/angelcorredor/Code/Wallet/backend/Dockerfile` | Flask image |
| Frontend Dockerfile | `/Users/angelcorredor/Code/Wallet/frontend/Dockerfile` | Nginx production |
| Frontend Dev Dockerfile | `/Users/angelcorredor/Code/Wallet/frontend/Dockerfile.dev` | Vite dev server |
| Nginx Config | `/Users/angelcorredor/Code/Wallet/frontend/nginx.conf` | SPA routing |
| Environment Template | `/Users/angelcorredor/Code/Wallet/.env.example` | Variable reference |
| Documentation | `/Users/angelcorredor/Code/Wallet/README-DOCKER.md` | Complete guide |
| Services Reference | `/Users/angelcorredor/Code/Wallet/DOCKER-SERVICES.md` | Service details |
| Quick Start | `/Users/angelcorredor/Code/Wallet/DOCKER-QUICKSTART.md` | 5-minute setup |
| Validation Script | `/Users/angelcorredor/Code/Wallet/validate-docker.sh` | Check configuration |
| Make Commands | `/Users/angelcorredor/Code/Wallet/Makefile.docker` | Convenience commands |

---

## Next Steps

1. **Try the Quick Start**: Run `docker-compose up -d --build` and access http://localhost:3000
2. **Review Documentation**: Read `README-DOCKER.md` for comprehensive guide
3. **Explore Services**: See `DOCKER-SERVICES.md` for detailed service information
4. **Test Locally**: Use `docker-compose.dev.yml` for hot reload development
5. **Plan Production**: Review `docker-compose.prod.yml` for production settings

---

## Support

For issues or questions:

1. Check the troubleshooting section in `README-DOCKER.md`
2. Run validation: `bash validate-docker.sh`
3. Check logs: `docker-compose logs`
4. Review this document for context
