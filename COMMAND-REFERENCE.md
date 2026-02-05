# Command Reference Card

Quick copy-paste reference for common development commands.

## Starting & Stopping

### Start Development with Logs
```bash
cd /Users/angelcorredor/Code/Wallet
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Start in Background
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Stop All Services
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
```

### Stop and Remove All Data
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

## Viewing Logs

### All Services
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f
```

### Frontend Only
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f frontend
```

### Backend Only
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend
```

### Database Only
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f db
```

### Last 100 Lines
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs --tail=100
```

## Service Management

### List Running Services
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps
```

### Restart All Services
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart
```

### Restart Specific Service
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart frontend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart backend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart db
```

### Rebuild Image (after dependency changes)
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build frontend --no-cache
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build backend --no-cache
```

### Rebuild and Restart
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build frontend
```

## Shell Access

### Backend Python Shell
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend sh
```

### Frontend Node Shell
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend sh
```

### Database SQL Shell (psql)
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec db psql -U wallet_user -d wallet_db
```

### Run Single Command in Backend
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -c "print('test')"
```

### Run Single Command in Frontend
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend npm list
```

## Database Operations

### Connect to Database
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec db psql -U wallet_user -d wallet_db
```

### List All Tables
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec db psql -U wallet_user -d wallet_db -c "\dt"
```

### View Migration Status
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend flask db current
```

### Run Pending Migrations
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend flask db upgrade
```

### Create New Migration
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend flask db migrate -m "Add user table"
```

### Downgrade to Previous Migration
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend flask db downgrade
```

### Backup Database
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec db pg_dump -U wallet_user wallet_db > backup.sql
```

### Restore Database
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T db psql -U wallet_user wallet_db < backup.sql
```

### Run SQL Query
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec db psql -U wallet_user -d wallet_db -c "SELECT * FROM users LIMIT 5;"
```

## Testing Connectivity

### Test Frontend
```bash
curl http://localhost:5173/
```

### Test Backend
```bash
curl http://localhost:5001/health
```

### Test Database
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T db pg_isready -U wallet_user
```

### Test All Services
```bash
curl http://localhost:5173/ && echo "✓ Frontend" || echo "✗ Frontend"
curl http://localhost:5001/health && echo "✓ Backend" || echo "✗ Backend"
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T db pg_isready -U wallet_user && echo "✓ Database" || echo "✗ Database"
```

## Docker Compose Configuration

### Validate Configuration
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml config > /dev/null && echo "✓ Valid"
```

### Show Merged Configuration
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml config
```

### Show Service Configuration Only
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml config --services
```

## Production Commands

### Start Production Environment
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Stop Production Environment
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
```

### View Production Logs
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

### Restart Production Services
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart
```

## Troubleshooting Commands

### Check Port Usage
```bash
lsof -i :5173  # Frontend
lsof -i :5001  # Backend
lsof -i :5432  # Database
lsof -i :5050  # pgAdmin
```

### Kill Process on Port
```bash
kill -9 $(lsof -t -i :5173)
kill -9 $(lsof -t -i :5001)
kill -9 $(lsof -t -i :5432)
```

### View Docker System Info
```bash
docker system df      # Disk usage
docker system prune   # Clean up unused resources
docker stats          # Real-time resource usage
```

### View Container Details
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend docker inspect
```

### Check Environment Variables
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend printenv
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend printenv | grep FLASK
```

### View Volume Mounts
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend sh -c 'mount | grep /app'
```

### Clear Docker Cache
```bash
docker builder prune   # Clear build cache
docker system prune -a # Remove all unused containers/images
```

## Package Management

### Install npm Package
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
cd frontend
npm install lodash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build frontend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Install pip Package
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
echo "requests==2.31.0" >> backend/requirements.txt
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build backend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### List npm Dependencies
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend npm list
```

### List pip Dependencies
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend pip list
```

## Useful Aliases (Add to ~/.bashrc or ~/.zshrc)

```bash
# Development shortcuts
alias walletdev='cd /Users/angelcorredor/Code/Wallet && docker-compose -f docker-compose.yml -f docker-compose.dev.yml'
alias walletprod='cd /Users/angelcorredor/Code/Wallet && docker-compose -f docker-compose.yml -f docker-compose.prod.yml'

# Common wallet commands
alias wstart='walletdev up -d'
alias wstop='walletdev down'
alias wlogs='walletdev logs -f'
alias wps='walletdev ps'
alias wdb='walletdev exec db psql -U wallet_user -d wallet_db'
alias wfrontend='walletdev exec frontend sh'
alias wbackend='walletdev exec backend sh'

# Then use:
# wstart          # Start dev
# wstop           # Stop dev
# wlogs           # View logs
# wdb             # Open database shell
# wfrontend       # Open frontend shell
# wbackend        # Open backend shell
```

## Advanced Docker Compose

### Execute in Running Container Without Interactive TTY
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python script.py
```

### Execute as Different User
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -u appuser backend sh
```

### Run One-Off Container
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml run --rm frontend npm install lodash
```

### Scale Service (if no port conflicts)
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --scale backend=2
```

## Health Check Verification

### Check Service Health
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps
# Look for "(healthy)" status in STATE column
```

### Manually Test Health Check
```bash
# Frontend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend wget -O- http://localhost:5173/

# Backend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

# Database
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T db pg_isready -U wallet_user
```

## Environment File Management

### Create .env from Example
```bash
cp /Users/angelcorredor/Code/Wallet/.env.example /Users/angelcorredor/Code/Wallet/.env
```

### View Current Environment Variables
```bash
cat /Users/angelcorredor/Code/Wallet/.env
```

### Update Environment Variable in Running Container
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
# Edit .env file
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Files Reference

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Base configuration (production defaults) |
| `docker-compose.dev.yml` | Development overrides (hot-reload) |
| `docker-compose.prod.yml` | Production overrides (optimization) |
| `frontend/Dockerfile` | Production frontend build |
| `frontend/Dockerfile.dev` | Development frontend (Vite) |
| `backend/Dockerfile` | Backend Python container |
| `.env` | Environment variables (gitignored) |
| `.env.example` | Environment template |

## Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | N/A |
| Frontend (Vite) | http://localhost:5173 | N/A |
| Backend API | http://localhost:5001 | N/A |
| pgAdmin | http://localhost:5050 | admin@wallet.local / admin |
| Database | localhost:5432 | wallet_user / wallet_password |

## Git Integration

### Check Git Status
```bash
cd /Users/angelcorredor/Code/Wallet
git status
```

### Commit Changes
```bash
git add .
git commit -m "Description of changes"
```

### View Recent Commits
```bash
git log --oneline -10
```

---

**Pro Tip:** Create a `.bash_aliases` file with these aliases for faster development!
