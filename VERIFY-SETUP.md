# Verify Development Setup

Complete this checklist to ensure your development environment is properly configured for hot-reload development.

## Pre-Flight Checks

### 1. Prerequisites Installed

```bash
# Check Docker version (need 20.10+)
docker --version
# Expected: Docker version 20.10.x or higher

# Check Docker Compose version (need 1.29+)
docker-compose --version
# Expected: Docker Compose version 1.29.x or higher

# Check .env file exists
ls -la /Users/angelcorredor/Code/Wallet/.env
# Should exist (copy from .env.example if missing)
```

### 2. Project Files Present

```bash
cd /Users/angelcorredor/Code/Wallet

# Verify all required files exist
ls -la docker-compose.yml docker-compose.dev.yml docker-compose.prod.yml
ls -la frontend/Dockerfile frontend/Dockerfile.dev
ls -la backend/Dockerfile
ls -la DEVELOPMENT-WORKFLOW.md DEV-QUICK-START.md
ls -la DOCKER-COMPOSE-ARCHITECTURE.md
```

## Setup Verification

### 3. Docker Compose Configuration Valid

```bash
cd /Users/angelcorredor/Code/Wallet

# Validate development configuration
docker-compose -f docker-compose.yml -f docker-compose.dev.yml config > /dev/null
echo $?  # Should return 0 (success)

# Validate production configuration
docker-compose -f docker-compose.yml -f docker-compose.prod.yml config > /dev/null
echo $?  # Should return 0 (success)
```

### 4. Images Build Successfully

```bash
cd /Users/angelcorredor/Code/Wallet

# Build frontend development image
echo "Building frontend..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build frontend
# Should complete without errors

# Build backend image
echo "Building backend..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build backend
# Should complete without errors

# Build database image (just verify it's available)
echo "Checking database image..."
docker pull postgres:15-alpine
# Should pull without errors
```

### 5. Network and Ports Available

```bash
# Check if ports are available
for port in 3000 5001 5050 5173 5432; do
    if ! lsof -i :$port >/dev/null 2>&1; then
        echo "✓ Port $port is available"
    else
        echo "✗ Port $port is in use:"
        lsof -i :$port
    fi
done

# Expected: All ports available (no processes listening)
```

## Startup Verification

### 6. Services Start Successfully

```bash
cd /Users/angelcorredor/Code/Wallet

# Start services
echo "Starting services..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Wait 30 seconds for services to initialize
sleep 30

# Check status
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps
```

Expected output should show:
```
NAME                COMMAND             STATUS              PORTS
wallet_frontend     npm run dev ...     Up (healthy)        0.0.0.0:5173->5173/tcp, 0.0.0.0:3000->5173/tcp
wallet_backend      flask run ...       Up (healthy)        0.0.0.0:5001->5000/tcp
wallet_db           postgres           Up (healthy)        0.0.0.0:5432->5432/tcp
wallet_pgadmin      /entrypoint.sh     Up (healthy)        0.0.0.0:5050->80/tcp
```

### 7. Service Health Checks

```bash
cd /Users/angelcorredor/Code/Wallet

# Frontend Vite dev server
echo "Testing Frontend..."
curl -v http://localhost:5173/ 2>&1 | grep -E "HTTP|200|301"
# Expected: HTTP/1.1 200 OK (or 301 redirect)

# Backend Flask API
echo "Testing Backend..."
curl -v http://localhost:5001/health 2>&1 | grep -E "HTTP|200"
# Expected: HTTP/1.1 200 OK

# Database
echo "Testing Database..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T db pg_isready -U wallet_user
# Expected: accepting connections

# pgAdmin
echo "Testing pgAdmin..."
curl -v http://localhost:5050/ 2>&1 | grep -E "HTTP|200|301|302"
# Expected: HTTP/1.1 200 OK (or redirect)
```

### 8. Volume Mounts Verified

```bash
cd /Users/angelcorredor/Code/Wallet

# Check frontend volume mount
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend sh -c 'ls /app/src' | head -5
# Expected: Lists frontend source files

# Check backend volume mount
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend sh -c 'ls /app/app' | head -5
# Expected: Lists backend source files

# Verify node_modules excluded from frontend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend sh -c 'ls /app/node_modules' | head -3
# Expected: Lists node_modules (not mounted but in container)
```

### 9. Hot Reload Capabilities

```bash
cd /Users/angelcorredor/Code/Wallet

# Check frontend HMR configuration
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend printenv | grep VITE_HMR
# Expected:
# VITE_HMR_HOST=localhost
# VITE_HMR_PORT=5173
# VITE_HMR_PROTOCOL=ws

# Check backend auto-reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs backend | grep -i "reload"
# Expected: Output showing Flask is in reloader mode
```

### 10. Environment Variables Correct

```bash
cd /Users/angelcorredor/Code/Wallet

# Check database environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec db printenv | grep "POSTGRES"
# Expected:
# POSTGRES_DB=wallet_db
# POSTGRES_USER=wallet_user
# POSTGRES_PASSWORD=wallet_password

# Check backend environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend printenv | grep "FLASK\|DEBUG"
# Expected:
# FLASK_ENV=development
# DEBUG=True

# Check frontend environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend printenv | grep "VITE"
# Expected:
# VITE_API_BASE_URL=http://localhost:5000
# VITE_HMR_HOST=localhost
# VITE_HMR_PORT=5173
```

## Hot Reload Testing

### 11. Frontend Hot Reload Test

```bash
cd /Users/angelcorredor/Code/Wallet

# Open browser to http://localhost:3000
# You should see the application loaded

# Make a test change to a component:
echo "<!-- TEST COMMENT -->" >> frontend/src/App.vue

# Watch the terminal running docker-compose up
# You should see:
# [vite] hmr update

# Refresh browser - you should see the component update

# Clean up test change
git checkout frontend/src/App.vue
```

### 12. Backend Hot Reload Test

```bash
cd /Users/angelcorredor/Code/Wallet

# Make a temporary change to test Flask reload
# Edit a simple route like /health in backend/app/routes/__init__.py
# Add a comment or print statement

# Watch the terminal for output like:
# * Detected change in 'app/routes/__init__.py', restarting with stat
# * Debugger is active

# Test the API:
curl http://localhost:5001/health

# You should see the updated version running

# Clean up test change
git checkout backend/app/routes/__init__.py
```

### 13. Database Persistence Test

```bash
cd /Users/angelcorredor/Code/Wallet

# Create a test record via pgAdmin or CLI
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec db psql -U wallet_user -d wallet_db -c "CREATE TABLE test (id SERIAL PRIMARY KEY, name TEXT);"
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec db psql -U wallet_user -d wallet_db -c "INSERT INTO test (name) VALUES ('persistent_data');"

# Restart backend (source code changes trigger this automatically)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart backend

# Check data is still there
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec db psql -U wallet_user -d wallet_db -c "SELECT * FROM test;"
# Expected: Shows the inserted row

# Clean up
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec db psql -U wallet_user -d wallet_db -c "DROP TABLE test;"
```

## Production Configuration Check

### 14. Production Configuration Valid

```bash
cd /Users/angelcorredor/Code/Wallet

# Validate production configuration
docker-compose -f docker-compose.yml -f docker-compose.prod.yml config > /dev/null
echo $?  # Should return 0

# Check production image references
docker-compose -f docker-compose.yml -f docker-compose.prod.yml config | grep -A 2 "backend:\|frontend:"
# Expected: Should reference wallet-backend:latest and wallet-frontend:latest or build contexts
```

### 15. Production Build Test

```bash
cd /Users/angelcorredor/Code/Wallet

# Build production images
echo "Building frontend for production..."
docker build -t wallet-frontend:test ./frontend

# Should complete without errors, showing multi-stage build progress
# Stage 1: builder (node build)
# Stage 2: runtime (nginx)

echo "Building backend for production..."
docker build -t wallet-backend:test ./backend

# Should complete without errors
```

## Cleanup

### 16. Stop Services

```bash
cd /Users/angelcorredor/Code/Wallet

# Stop development services (preserve volumes)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
echo "✓ Development services stopped"

# Clean up test images
docker rmi wallet-frontend:test wallet-backend:test 2>/dev/null
echo "✓ Test images cleaned up"
```

## Verification Summary Checklist

```
Setup Verification:
  ✓ Docker and Docker Compose installed
  ✓ .env file exists
  ✓ Docker Compose configuration valid (dev and prod)
  ✓ Images build successfully
  ✓ Ports available
  ✓ All services start and show healthy status
  ✓ All services respond to health checks
  ✓ Volume mounts working correctly
  ✓ HMR configuration present and correct
  ✓ Environment variables set correctly

Hot Reload Testing:
  ✓ Frontend changes trigger HMR
  ✓ Backend changes trigger auto-reload
  ✓ Database persists across restarts

Production Verification:
  ✓ Production configuration valid
  ✓ Production images build correctly

Cleanup:
  ✓ Services stopped cleanly
  ✓ Test artifacts removed
```

## Next Steps

If all checks pass:

1. **Start Development**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
   ```

2. **Access Services**
   - Frontend: http://localhost:3000
   - Backend: http://localhost:5001
   - pgAdmin: http://localhost:5050

3. **Begin Development**
   - Edit frontend files and see changes instantly (HMR)
   - Edit backend files and see changes on next request (auto-reload)
   - Use pgAdmin to inspect database if needed

4. **Read Documentation**
   - [DEV-QUICK-START.md](./DEV-QUICK-START.md) - 5-minute setup overview
   - [DEVELOPMENT-WORKFLOW.md](./DEVELOPMENT-WORKFLOW.md) - Complete development guide
   - [DOCKER-COMPOSE-ARCHITECTURE.md](./DOCKER-COMPOSE-ARCHITECTURE.md) - Technical deep dive

## Troubleshooting

If any checks fail:

### Services won't start
```bash
# Check logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs

# Verify ports are free
lsof -i :5173
lsof -i :5001
lsof -i :5432
lsof -i :5050
```

### Health checks failing
```bash
# View detailed logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f db
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f frontend

# Try rebuilding images
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache
```

### Hot reload not working
```bash
# Verify HMR configuration
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend printenv | grep HMR

# Check file watching
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend sh -c 'npm ls vite'

# Restart container
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart frontend
```

### Volume mounts not syncing
```bash
# Check volume configuration
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend sh -c 'mount | grep /app'

# Verify Docker Desktop settings (macOS/Windows)
# Ensure /Users/angelcorredor/Code/Wallet is in Docker Desktop file sharing settings
```

---

**Once all checks pass, your development environment is ready for productive development with hot-reload!**
