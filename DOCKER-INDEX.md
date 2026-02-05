# Docker Configuration Index

Complete reference guide to all Docker-related files in the Wallet project.

## Quick Navigation

**New here?** Start with [DOCKER-QUICKSTART.md](#docker-quickstartmd)

**Looking for specific help?** Use the table below to find what you need.

## File Reference

### Configuration Files

| File | Location | Size | Purpose | Read When |
|------|----------|------|---------|-----------|
| **docker-compose.yml** | `/Wallet/` | 5.2 KB | Main service orchestration | Setting up services, understanding architecture |
| **docker-compose.dev.yml** | `/Wallet/` | 1.5 KB | Development overrides (hot reload) | Developing features locally |
| **docker-compose.prod.yml** | `/Wallet/` | 4.0 KB | Production optimizations | Deploying to production |
| **.env.example** | `/Wallet/` | 1.0 KB | Environment variables template | Configuring your environment |
| **.dockerignore** | `/Wallet/` | 0.5 KB | Root-level build context exclusions | Understanding what gets built |
| **backend/Dockerfile** | `/Wallet/backend/` | 1.3 KB | Flask application image | Understanding backend setup |
| **backend/.dockerignore** | `/Wallet/backend/` | 2.0 KB | Backend build exclusions | Understanding build efficiency |
| **frontend/Dockerfile** | `/Wallet/frontend/` | 1.3 KB | Nginx SPA production image | Understanding frontend optimization |
| **frontend/Dockerfile.dev** | `/Wallet/frontend/` | 0.6 KB | Vite dev server image | Understanding hot reload setup |
| **frontend/.dockerignore** | `/Wallet/frontend/` | 1.5 KB | Frontend build exclusions | Understanding build efficiency |
| **frontend/nginx.conf** | `/Wallet/frontend/` | 2.5 KB | Nginx configuration for SPA | Understanding frontend routing |

### Documentation Files

| File | Location | Pages | Read Time | Purpose | Best For |
|------|----------|-------|-----------|---------|----------|
| **DOCKER-QUICKSTART.md** | `/Wallet/` | ~150 lines | 5 min | Fast setup guide | Getting started immediately |
| **README-DOCKER.md** | `/Wallet/` | ~500 lines | 30 min | Complete Docker guide | Comprehensive reference |
| **DOCKER-SERVICES.md** | `/Wallet/` | ~600 lines | 45 min | Detailed service reference | Understanding each service |
| **DOCKER-NOTES.md** | `/Wallet/` | ~500 lines | 30 min | Configuration decisions | Understanding WHY choices were made |
| **DOCKER-COMMANDS.md** | `/Wallet/` | ~400 lines | 15 min | Command reference | Looking up specific commands |
| **DOCKER-SUMMARY.md** | `/Wallet/` | ~300 lines | 15 min | Overview of entire setup | Understanding what was created |
| **DOCKER-INDEX.md** | `/Wallet/` | This file | 10 min | Navigation guide | Finding what you need |

### Scripts and Utilities

| File | Location | Type | Purpose | Run When |
|------|----------|------|---------|----------|
| **validate-docker.sh** | `/Wallet/` | Bash | Configuration validation | After installation, before first run |
| **backend/docker-entrypoint.sh** | `/Wallet/backend/` | Bash | Database initialization | Automatically on backend startup |
| **Makefile.docker** | `/Wallet/` | Make | Convenient commands | As shortcut for docker-compose |

## Total Files Created: 21

```
Docker Configuration Files:     7
  - 3 docker-compose files
  - 3 Dockerfiles
  - 1 Nginx config

.dockerignore Files:           3

Documentation Files:           6

Environment Templates:         1

Scripts:                       3

Infrastructure Total:          20 files
                               ~3500 lines of configuration & docs
                               ~500 KB of documentation
```

## Reading Guide by Use Case

### I want to...

**Get started in 5 minutes**
→ Read: [DOCKER-QUICKSTART.md](./DOCKER-QUICKSTART.md)

**Understand the complete architecture**
→ Read: [README-DOCKER.md](./README-DOCKER.md) → [DOCKER-SERVICES.md](./DOCKER-SERVICES.md)

**Know what commands to use**
→ Read: [DOCKER-COMMANDS.md](./DOCKER-COMMANDS.md)

**Understand why things were configured this way**
→ Read: [DOCKER-NOTES.md](./DOCKER-NOTES.md)

**Look up a specific service**
→ Read: [DOCKER-SERVICES.md](./DOCKER-SERVICES.md)

**Deploy to production**
→ Read: [README-DOCKER.md](./README-DOCKER.md) → "Production Deployment" section

**Troubleshoot issues**
→ Read: [README-DOCKER.md](./README-DOCKER.md) → "Troubleshooting" section

**Understand the database setup**
→ Read: [DOCKER-SERVICES.md](./DOCKER-SERVICES.md) → "Database Service" section

**Configure development environment**
→ Read: [DOCKER-QUICKSTART.md](./DOCKER-QUICKSTART.md) → "Development with Hot Reload" section

**Find a specific command**
→ Read: [DOCKER-COMMANDS.md](./DOCKER-COMMANDS.md)

## Services Overview

| Service | Image | Purpose | Port | Health Check |
|---------|-------|---------|------|--------------|
| **db** | postgres:15-alpine | Database | 5432 | pg_isready |
| **backend** | python:3.11-slim | Flask API | 5000 | GET /health |
| **frontend** | nginx:alpine | Web UI | 3000/80 | GET /health |
| **pgadmin** | dpage/pgadmin4 | DB UI (optional) | 5050 | HTTP |

## Command Quick Reference

```bash
# Start everything
docker-compose up -d --build

# Start with hot reload (development)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View logs
docker-compose logs -f

# Access database
docker-compose exec db psql -U wallet_user -d wallet_db

# Run tests
docker-compose exec backend pytest

# Run migrations
docker-compose exec backend flask db upgrade

# Stop everything
docker-compose down

# Delete all data
docker-compose down -v
```

For more commands, see [DOCKER-COMMANDS.md](./DOCKER-COMMANDS.md).

## Configuration Hierarchy

```
docker-compose.yml (base)
├── Production: + docker-compose.prod.yml
└── Development: + docker-compose.dev.yml
```

**Usage**:
```bash
# Development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Default (production-like)
docker-compose up -d
```

## Documentation Relationship Map

```
DOCKER-QUICKSTART.md (5 min start)
    ↓
    ├→ DOCKER-COMMANDS.md (command reference)
    │
    ├→ README-DOCKER.md (complete guide)
    │   ├→ DOCKER-SERVICES.md (service details)
    │   ├→ DOCKER-NOTES.md (decision rationale)
    │   └→ Troubleshooting section
    │
    └→ Production section
        └→ DOCKER-SUMMARY.md (overview)
```

## Important Directories

```
/Users/angelcorredor/Code/Wallet/

All configuration files:
├── docker-compose*.yml              # 3 files
├── .env.example
├── .dockerignore
├── validate-docker.sh
├── Makefile.docker
└── DOCKER-*.md                      # 6 documentation files

Backend specific:
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── docker-entrypoint.sh
│   ├── requirements.txt
│   ├── app/
│   ├── alembic/
│   └── tests/

Frontend specific:
└── frontend/
    ├── Dockerfile
    ├── Dockerfile.dev
    ├── .dockerignore
    ├── nginx.conf
    ├── package.json
    ├── src/
    └── vite.config.ts
```

## Key Features Summary

### Security
- Non-root user execution (backend)
- No hardcoded secrets
- Minimal base images
- Network isolation

### Development
- Hot reload for Python changes
- Vite HMR for Vue component changes
- Database included (no external deps)
- pgAdmin for database inspection

### Production
- Multi-stage frontend build (40MB image)
- Gunicorn WSGI server
- Resource limits
- Automated migrations
- Health checks

### Operations
- Comprehensive logging
- Health status monitoring
- Volume persistence
- Backup/restore utilities
- Make command shortcuts

## Environment Variables Quick Reference

```env
# Database
DB_NAME=wallet_db
DB_USER=wallet_user
DB_PASSWORD=wallet_password
DB_PORT=5432

# Flask
FLASK_ENV=development
DEBUG=True
SECRET_KEY=dev-key

# CORS
FLASK_CORS_ORIGINS=http://localhost:3000

# Frontend API
VITE_API_BASE_URL=http://localhost:5000
```

See `.env.example` for complete list.

## Validation Checklist

Before first run:

- [ ] Docker installed (`docker --version`)
- [ ] Docker Compose 2.0+ (`docker-compose --version`)
- [ ] Visited `/Users/angelcorredor/Code/Wallet/`
- [ ] Read `DOCKER-QUICKSTART.md` (5 minutes)
- [ ] Optionally run `validate-docker.sh`
- [ ] Created `.env` from `.env.example` (optional for dev)
- [ ] Run `docker-compose up -d --build`
- [ ] Access http://localhost:3000

## Troubleshooting Navigation

Issue | See | Page |
-------|-----|------|
Port in use | README-DOCKER.md | Port Already in Use |
DB connection error | README-DOCKER.md | Database Connection Failed |
Frontend can't reach backend | README-DOCKER.md | Frontend Cannot Reach Backend |
Container won't start | README-DOCKER.md | Container Exiting Immediately |
Need a specific command | DOCKER-COMMANDS.md | Command section |
Don't understand a choice | DOCKER-NOTES.md | Key Features |

## Next Steps

1. **Read**: Start with [DOCKER-QUICKSTART.md](./DOCKER-QUICKSTART.md) (5 minutes)
2. **Validate**: Run `bash validate-docker.sh` (optional)
3. **Start**: Execute `docker-compose up -d --build`
4. **Access**: Visit http://localhost:3000
5. **Reference**: Use [DOCKER-COMMANDS.md](./DOCKER-COMMANDS.md) for common tasks
6. **Learn**: Read [README-DOCKER.md](./README-DOCKER.md) for complete guide

## File Sizes and Statistics

Total Docker configuration: **~500 KB**
- Configuration files: ~15 KB
- Dockerfiles: ~5 KB
- Documentation: ~450 KB
- Scripts: ~10 KB

Documentation content: **~1700 lines**
- README-DOCKER.md: ~500 lines
- DOCKER-SERVICES.md: ~600 lines
- DOCKER-NOTES.md: ~500 lines
- Other docs: ~100 lines

Configuration content: **~50 lines each**
- docker-compose.yml: ~170 lines (well-commented)
- backend/Dockerfile: ~47 lines (well-commented)
- frontend/Dockerfile: ~48 lines (multi-stage)

## Contact and Support

For questions about specific topics:

| Topic | File |
|-------|------|
| Getting started | DOCKER-QUICKSTART.md |
| Complete reference | README-DOCKER.md |
| Service architecture | DOCKER-SERVICES.md |
| Configuration choices | DOCKER-NOTES.md |
| Common commands | DOCKER-COMMANDS.md |
| Project overview | DOCKER-SUMMARY.md |

All files are in: `/Users/angelcorredor/Code/Wallet/`

---

**Last updated**: January 31, 2026
**Configuration version**: 1.0
**Docker Compose version**: 3.8+
**Docker version**: 20.10+
