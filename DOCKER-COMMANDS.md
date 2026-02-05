# Docker Commands Reference

Quick reference for commonly used Docker Compose commands for the Wallet application.

## Most Common Commands

### Start Everything

```bash
# Build images and start all services (background)
docker-compose up -d --build

# View realtime logs
docker-compose logs -f

# Stop viewing logs
Ctrl + C
```

### Stop Everything

```bash
# Stop all services (data preserved)
docker-compose stop

# Stop and remove containers (data persists in volumes)
docker-compose down

# Stop, remove, and delete data (WARNING: data loss!)
docker-compose down -v
```

### Check Status

```bash
# List all services and their status
docker-compose ps

# View logs from all services
docker-compose logs

# View logs from specific service
docker-compose logs backend
docker-compose logs frontend
docker-compose logs db

# Follow logs in real-time
docker-compose logs -f backend

# View last N lines
docker-compose logs backend --tail=50
```

---

## Development Workflow

### Start with Hot Reload

```bash
# Backend Python changes and frontend Vue changes auto-reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View development logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f
```

### Access Containers

```bash
# Backend shell
docker-compose exec backend sh

# Python interactive shell (with Flask context)
docker-compose exec backend flask shell

# Database shell (PostgreSQL CLI)
docker-compose exec db psql -U wallet_user -d wallet_db

# Frontend shell
docker-compose exec frontend sh

# Run commands in any service
docker-compose exec <service-name> <command>
```

### Run Tests

```bash
# Run all tests
docker-compose exec backend pytest

# Run specific test file
docker-compose exec backend pytest tests/test_auth.py

# Run with coverage report
docker-compose exec backend pytest --cov=app --cov-report=html

# Run with verbose output
docker-compose exec backend pytest -v

# Run tests in watch mode (if available)
docker-compose exec backend pytest-watch
```

### Code Quality

```bash
# Run linter
docker-compose exec backend ruff check app/

# Format code
docker-compose exec backend black app/

# Type checking (if available)
docker-compose exec backend mypy app/

# Frontend linting
docker-compose exec frontend npm run lint
```

---

## Database Operations

### Migrations

```bash
# Apply pending migrations
docker-compose exec backend flask db upgrade

# Create new migration after model changes
docker-compose exec backend flask db migrate -m "Add user roles table"

# Downgrade to previous migration
docker-compose exec backend flask db downgrade

# Show current migration version
docker-compose exec backend flask db current

# Show migration history
docker-compose exec backend flask db history

# View specific migration details
docker-compose exec backend flask db show <revision>
```

### Direct Database Access

```bash
# Connect to PostgreSQL CLI
docker-compose exec db psql -U wallet_user -d wallet_db

# Common PostgreSQL commands (in psql shell):
# \dt              - List all tables
# \du              - List users/roles
# \db              - List databases
# SELECT * FROM information_schema.tables WHERE table_schema='public';  - List all tables with schema
# \d <table_name>  - Show table structure
# \copy <table> TO 'file.csv' WITH CSV;  - Export table to CSV
```

### Database Backup and Restore

```bash
# Create backup (SQL format)
docker-compose exec db pg_dump -U wallet_user wallet_db > backup.sql

# Create backup (compressed)
docker-compose exec db pg_dump -U wallet_user wallet_db | gzip > backup.sql.gz

# List database backups
ls -lah backup*.sql*

# Restore from backup
docker-compose exec -T db psql -U wallet_user wallet_db < backup.sql

# Restore from compressed backup
gunzip < backup.sql.gz | docker-compose exec -T db psql -U wallet_user wallet_db
```

### Database Inspection

```bash
# Get table row counts
docker-compose exec db psql -U wallet_user -d wallet_db -c "SELECT tablename, rows FROM pg_stat_user_tables ORDER BY rows DESC;"

# Get database size
docker-compose exec db psql -U wallet_user -d wallet_db -c "SELECT pg_size_pretty(pg_database.datsize) AS size FROM pg_database WHERE datname = 'wallet_db';"

# Get table sizes
docker-compose exec db psql -U wallet_user -d wallet_db -c "SELECT tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema') ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

---

## Building and Rebuilding

### Build Images

```bash
# Build all images
docker-compose build

# Build specific service
docker-compose build backend
docker-compose build frontend

# Force rebuild without cache
docker-compose build --no-cache

# Build with custom parameters
docker-compose build --build-arg PYTHON_VERSION=3.11
```

### Clean Up and Rebuild

```bash
# Completely rebuild (remove containers, build new images)
docker-compose up -d --build

# Force rebuild and restart all
docker-compose down && docker-compose up -d --build

# Remove dangling images and rebuild
docker image prune -f && docker-compose build --no-cache
```

---

## Monitoring and Troubleshooting

### Check Health

```bash
# Show all containers and their health status
docker-compose ps

# Test backend API health
curl http://localhost:5000/health

# Test frontend health
curl http://localhost:3000/health

# Test database connectivity
docker-compose exec backend psql -h db -U wallet_user -d wallet_db -c "SELECT 1"
```

### Monitor Resources

```bash
# Real-time resource usage
docker stats

# CPU and memory for specific services
docker stats wallet_backend wallet_frontend wallet_postgres

# Historical resource usage
docker stats --no-stream
```

### Inspect Services

```bash
# Detailed info about a service
docker inspect wallet_backend

# Get service IP address
docker inspect wallet_backend --format='{{.NetworkSettings.Networks.wallet_network.IPAddress}}'

# Get service environment variables
docker inspect wallet_backend --format='{{json .Config.Env}}' | jq

# Check if service is running
docker inspect wallet_backend --format='{{.State.Running}}'

# Check service health status
docker inspect wallet_backend --format='{{.State.Health.Status}}'
```

### View Detailed Logs

```bash
# Logs with timestamps
docker-compose logs --timestamps

# Show only errors
docker-compose logs | grep -i error

# Show last 100 lines
docker-compose logs --tail=100

# Follow logs for multiple services
docker-compose logs -f backend frontend

# Export logs to file
docker-compose logs > logfile.txt
```

---

## Network and Connectivity

### Check Network

```bash
# List Docker networks
docker network ls

# Inspect wallet network
docker network inspect wallet_network

# Test connectivity between services
docker-compose exec backend ping frontend
docker-compose exec backend ping db
docker-compose exec frontend curl http://backend:5000/health

# DNS resolution test
docker-compose exec backend nslookup db
docker-compose exec frontend nslookup backend
```

### Port Mapping

```bash
# Show port mappings
docker-compose port backend 5000
docker-compose port frontend 80

# Check if ports are available on host
lsof -i :5000      # Check port 5000
lsof -i :3000      # Check port 3000
lsof -i :5432      # Check port 5432
lsof -i :5050      # Check port 5050
```

---

## Volumes and Data

### Manage Volumes

```bash
# List all volumes
docker volume ls

# Inspect specific volume
docker volume inspect wallet_postgres_data

# Get volume mount path
docker volume inspect wallet_postgres_data --format='{{.Mountpoint}}'

# Backup volume data
docker run --rm -v wallet_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/db-backup.tar.gz -C /data .

# Restore volume data
docker run --rm -v wallet_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/db-backup.tar.gz -C /data
```

### Clean Up Storage

```bash
# Remove unused volumes
docker volume prune

# Remove specific volume (after docker-compose down -v)
docker volume rm wallet_postgres_data

# Clean up all unused Docker resources
docker system prune

# Aggressive cleanup (includes unused images)
docker system prune -a

# Show Docker disk usage
docker system df
```

---

## Advanced Operations

### Execute Complex Commands

```bash
# Run multiple commands
docker-compose exec backend sh -c "flask db upgrade && flask run"

# Execute with environment variables
docker-compose exec -e DEBUG=True backend flask shell

# Execute with working directory
docker-compose exec -w /app backend python script.py

# Run command without pseudo-TTY (for piping)
docker-compose exec -T db pg_dump -U wallet_user wallet_db > backup.sql
```

### Container Management

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart backend

# Pause all services (without stopping)
docker-compose pause

# Resume paused services
docker-compose unpause

# Rebuild and restart single service
docker-compose up -d --build backend
```

### View Configuration

```bash
# Show resolved docker-compose.yml (with variables substituted)
docker-compose config

# Show resolved file with all overrides
docker-compose -f docker-compose.yml -f docker-compose.dev.yml config

# Validate compose file syntax
docker-compose config --quiet

# Show service dependencies
docker-compose config | grep -A2 "depends_on"
```

---

## Production Commands

### Deploy Production Setup

```bash
# Build with production overrides
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Start production services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# View production logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Stop production services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
```

### Database Backup for Production

```bash
# Schedule daily backups (add to crontab)
# 0 2 * * * cd /home/wallet && docker-compose exec -T db pg_dump -U wallet_user wallet_db | gzip > /backups/wallet_$(date +\%Y\%m\%d).sql.gz

# Verify backups exist
ls -lah /backups/wallet_*.sql.gz

# Check backup size
du -sh /backups/wallet_*.sql.gz

# Test restore on backup
gunzip < /backups/wallet_20240131.sql.gz | docker-compose exec -T db psql -U wallet_user wallet_db_test
```

---

## Make Commands (Alternative)

If Make is installed, use `Makefile.docker` for convenience:

```bash
# Show all available commands
make -f Makefile.docker help

# Common shortcuts
make -f Makefile.docker up              # Start services
make -f Makefile.docker up-dev          # Start with hot reload
make -f Makefile.docker down            # Stop services
make -f Makefile.docker logs            # View logs
make -f Makefile.docker logs-backend    # Backend logs only
make -f Makefile.docker test            # Run tests
make -f Makefile.docker migrate         # Run migrations
make -f Makefile.docker shell-backend   # Backend shell
make -f Makefile.docker db-shell        # Database shell
make -f Makefile.docker db-backup       # Backup database
make -f Makefile.docker health          # Check service health
```

---

## Troubleshooting Commands

### Diagnose Issues

```bash
# Complete system check
docker-compose ps
docker-compose logs
docker-compose exec backend curl http://db:5432

# Check specific service
docker-compose logs backend --tail=50
docker inspect wallet_backend --format='{{.State}}'

# Verify connectivity
docker-compose exec backend ping db
docker-compose exec frontend curl http://backend:5000

# List open ports
lsof -i :5000
lsof -i :3000
lsof -i :5432
```

### Reset and Recover

```bash
# Soft reset (keep data)
docker-compose restart

# Hard reset (remove containers, keep volumes)
docker-compose down && docker-compose up -d

# Complete reset (remove everything)
docker-compose down -v

# Rebuild and start fresh
docker-compose down -v --rmi all && docker-compose up -d --build
```

### Debug Container

```bash
# Check why container exited
docker-compose logs backend
docker inspect wallet_backend --format='{{.State.ExitCode}}'

# Review environment
docker-compose exec backend env | sort

# Check file permissions
docker-compose exec backend ls -la /app

# Verify mount points
docker inspect wallet_backend --format='{{json .Mounts}}' | jq
```

---

## One-Liners for Common Tasks

```bash
# Get backend container ID
BACKEND_ID=$(docker-compose ps -q backend)

# Copy file from container
docker cp wallet_backend:/app/file.txt ./file.txt

# Copy file to container
docker cp ./file.txt wallet_backend:/app/file.txt

# Run one-off container
docker-compose run --rm backend pytest

# Show all environment variables in backend
docker-compose exec backend printenv | sort

# Check total database size
docker-compose exec db du -sh /var/lib/postgresql/data

# Count tables in database
docker-compose exec db psql -U wallet_user -d wallet_db -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"

# List all migration files
docker-compose exec backend find alembic/versions -name "*.py" | sort

# Show backend startup time
docker inspect wallet_backend --format='{{.State.StartedAt}}'

# Test full stack connectivity
docker-compose exec backend sh -c 'curl http://db:5432 2>&1 | head -1 && curl http://frontend:80/health'
```

---

## Finding Help

```bash
# Docker Compose help
docker-compose --help

# Specific command help
docker-compose up --help
docker-compose exec --help

# View documentation
# Main guide: /Users/angelcorredor/Code/Wallet/README-DOCKER.md
# Quick start: /Users/angelcorredor/Code/Wallet/DOCKER-QUICKSTART.md
# Services: /Users/angelcorredor/Code/Wallet/DOCKER-SERVICES.md
```

---

## Command Organization by Use Case

### I want to...

**Start the application**
```bash
docker-compose up -d --build
```

**Develop with hot reload**
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

**Run tests**
```bash
docker-compose exec backend pytest
```

**Run database migrations**
```bash
docker-compose exec backend flask db upgrade
```

**Access the database**
```bash
docker-compose exec db psql -U wallet_user -d wallet_db
```

**Backup the database**
```bash
docker-compose exec db pg_dump -U wallet_user wallet_db > backup.sql
```

**View error logs**
```bash
docker-compose logs backend | grep -i error
```

**Restart everything**
```bash
docker-compose restart
```

**Delete all data**
```bash
docker-compose down -v
```

**Deploy to production**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

**For complete documentation**, see `/Users/angelcorredor/Code/Wallet/README-DOCKER.md`
