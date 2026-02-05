# Docker Quick Start Guide

Get the Wallet application running in 5 minutes.

## Prerequisites

- Docker installed ([Download](https://docs.docker.com/get-docker/))
- Docker Compose 2.0+ (included with Docker Desktop)

## Start in 3 Steps

### Step 1: Navigate to Project

```bash
cd /Users/angelcorredor/Code/Wallet
```

### Step 2: Create Environment File (Optional)

```bash
cp .env.example .env
# Edit .env if you want to customize settings
# For development, defaults are fine
```

### Step 3: Start All Services

```bash
docker-compose up -d --build
```

That's it! Services will start in the background.

## Access Applications

Open in your browser:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **Database UI** (pgAdmin): http://localhost:5050
  - Email: `admin@wallet.local`
  - Password: `admin`

## Check Status

```bash
# See all running containers
docker-compose ps

# View logs
docker-compose logs -f

# Check specific service
docker-compose logs backend
```

## Common Commands

```bash
# Stop services (data is preserved)
docker-compose down

# Stop and remove all data
docker-compose down -v

# Restart all services
docker-compose restart

# Access database shell
docker-compose exec db psql -U wallet_user -d wallet_db

# Run tests
docker-compose exec backend pytest

# Access backend shell
docker-compose exec backend flask shell
```

## Development with Hot Reload

```bash
# Start with auto-reload for Python and Vue changes
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Frontend runs on http://localhost:5173 with HMR
# Backend runs on http://localhost:5000 with auto-reload
```

## Troubleshooting

### Services won't start

```bash
# Check for port conflicts
lsof -i :5000
lsof -i :3000
lsof -i :5432

# View detailed error logs
docker-compose logs
```

### Can't connect to database

```bash
# Check database health
docker-compose exec db pg_isready -U wallet_user

# View database logs
docker-compose logs db
```

### API responds but frontend can't reach it

```bash
# Check CORS configuration
docker-compose logs backend | grep -i cors

# Verify backend is running
curl http://localhost:5000/health
```

## Database Commands

```bash
# Apply migrations
docker-compose exec backend flask db upgrade

# See migration status
docker-compose exec backend flask db current

# Backup database
docker-compose exec db pg_dump -U wallet_user wallet_db > backup.sql

# Access database directly
docker-compose exec db psql -U wallet_user -d wallet_db
```

## Advanced

See **README-DOCKER.md** for:

- Detailed configuration options
- Production deployment guide
- Health checks and monitoring
- Volume and network architecture
- Advanced troubleshooting

## Using Make (Optional)

If you have Make installed:

```bash
# View all commands
make -f Makefile.docker help

# Examples
make -f Makefile.docker up
make -f Makefile.docker up-dev
make -f Makefile.docker logs
make -f Makefile.docker migrate
make -f Makefile.docker test
```

## Validate Setup

Run the validation script:

```bash
bash validate-docker.sh
```

This checks Docker installation, configuration files, and optionally builds the images.

## Next Steps

1. Check the API documentation: Backend at `/Users/angelcorredor/Code/Wallet/backend/API_EXAMPLES.md`
2. Review backend implementation: `/Users/angelcorredor/Code/Wallet/backend/README.md`
3. Explore frontend code: `/Users/angelcorredor/Code/Wallet/frontend/` (Vue.js components in `src/`)

---

**For detailed documentation**, see `/Users/angelcorredor/Code/Wallet/README-DOCKER.md`
