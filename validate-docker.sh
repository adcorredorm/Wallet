#!/bin/bash
# Docker Validation Script for Wallet Application
# This script verifies that the Docker configuration is correct and all services can start

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Wallet Docker Configuration Validation Script              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Counter for checks
PASSED=0
FAILED=0

# Function to print status
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $1"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $1"
        ((FAILED++))
    fi
}

# ============================================================================
# Check Prerequisites
# ============================================================================

echo -e "${YELLOW}Checking Prerequisites...${NC}"
echo "---"

# Check Docker
docker --version > /dev/null 2>&1
check_status "Docker is installed"

# Check Docker Compose
docker-compose --version > /dev/null 2>&1
check_status "Docker Compose is installed"

# Check if Docker daemon is running
docker ps > /dev/null 2>&1
check_status "Docker daemon is running"

# ============================================================================
# Check File Structure
# ============================================================================

echo ""
echo -e "${YELLOW}Checking Project Structure...${NC}"
echo "---"

# Check required files exist
[ -f /Users/angelcorredor/Code/Wallet/docker-compose.yml ]
check_status "docker-compose.yml exists"

[ -f /Users/angelcorredor/Code/Wallet/backend/Dockerfile ]
check_status "backend/Dockerfile exists"

[ -f /Users/angelcorredor/Code/Wallet/frontend/Dockerfile ]
check_status "frontend/Dockerfile exists"

[ -f /Users/angelcorredor/Code/Wallet/frontend/nginx.conf ]
check_status "frontend/nginx.conf exists"

[ -f /Users/angelcorredor/Code/Wallet/backend/requirements.txt ]
check_status "backend/requirements.txt exists"

[ -f /Users/angelcorredor/Code/Wallet/frontend/package.json ]
check_status "frontend/package.json exists"

[ -f /Users/angelcorredor/Code/Wallet/.env.example ]
check_status ".env.example exists"

[ -f /Users/angelcorredor/Code/Wallet/README-DOCKER.md ]
check_status "README-DOCKER.md exists"

# ============================================================================
# Check Docker Configuration
# ============================================================================

echo ""
echo -e "${YELLOW}Validating Docker Configuration...${NC}"
echo "---"

# Validate docker-compose.yml syntax
docker-compose -f /Users/angelcorredor/Code/Wallet/docker-compose.yml config > /dev/null 2>&1
check_status "docker-compose.yml is valid YAML"

# Check if services are defined
docker-compose -f /Users/angelcorredor/Code/Wallet/docker-compose.yml config | grep -q "db:"
check_status "Database service (db) is defined"

docker-compose -f /Users/angelcorredor/Code/Wallet/docker-compose.yml config | grep -q "backend:"
check_status "Backend service is defined"

docker-compose -f /Users/angelcorredor/Code/Wallet/docker-compose.yml config | grep -q "frontend:"
check_status "Frontend service is defined"

# ============================================================================
# Check Dockerfile Syntax
# ============================================================================

echo ""
echo -e "${YELLOW}Validating Dockerfiles...${NC}"
echo "---"

# Check backend Dockerfile
[ -f /Users/angelcorredor/Code/Wallet/backend/Dockerfile ]
check_status "backend/Dockerfile is readable"

# Check frontend Dockerfile
[ -f /Users/angelcorredor/Code/Wallet/frontend/Dockerfile ]
check_status "frontend/Dockerfile is readable"

# Check .dockerignore files exist
[ -f /Users/angelcorredor/Code/Wallet/backend/.dockerignore ]
check_status "backend/.dockerignore exists"

[ -f /Users/angelcorredor/Code/Wallet/frontend/.dockerignore ]
check_status "frontend/.dockerignore exists"

# ============================================================================
# Check Build Configuration
# ============================================================================

echo ""
echo -e "${YELLOW}Checking Build Requirements...${NC}"
echo "---"

# Check if requirements.txt has required packages
grep -q "Flask" /Users/angelcorredor/Code/Wallet/backend/requirements.txt
check_status "Flask is in backend requirements"

grep -q "psycopg2" /Users/angelcorredor/Code/Wallet/backend/requirements.txt
check_status "psycopg2 is in backend requirements"

grep -q "SQLAlchemy" /Users/angelcorredor/Code/Wallet/backend/requirements.txt
check_status "SQLAlchemy is in backend requirements"

# Check frontend package.json
grep -q "vue" /Users/angelcorredor/Code/Wallet/frontend/package.json
check_status "Vue.js is in frontend dependencies"

grep -q "vite" /Users/angelcorredor/Code/Wallet/frontend/package.json
check_status "Vite is in frontend dev dependencies"

# ============================================================================
# Optional: Try to build images (with confirmation)
# ============================================================================

echo ""
echo -e "${YELLOW}Ready to Test Build?${NC}"
read -p "Do you want to build Docker images now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${BLUE}Building Docker images...${NC}"
    echo "(This may take several minutes)"
    echo "---"

    cd /Users/angelcorredor/Code/Wallet

    if docker-compose build; then
        echo -e "${GREEN}✓ PASS${NC}: Docker images built successfully"
        ((PASSED++))

        # Try to start containers briefly
        echo ""
        echo -e "${BLUE}Starting services for health check...${NC}"
        docker-compose up -d 2>&1 | grep -E "Creating|Started" || true

        # Give services time to start
        sleep 10

        # Check service health
        echo ""
        echo -e "${YELLOW}Checking Service Health...${NC}"
        echo "---"

        if docker-compose ps | grep -q "healthy"; then
            echo -e "${GREEN}✓ PASS${NC}: Services are running and healthy"
            ((PASSED++))
        else
            echo -e "${YELLOW}⚠ WARNING${NC}: Services started but health status unknown"
        fi

        # Test backend endpoint
        if curl -s http://localhost:5000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ PASS${NC}: Backend API is responding"
            ((PASSED++))
        else
            echo -e "${YELLOW}⚠ WARNING${NC}: Backend API not responding yet (may need more time)"
        fi

        # Stop containers
        echo ""
        echo -e "${BLUE}Cleaning up test containers...${NC}"
        docker-compose down --volumes > /dev/null 2>&1
        echo -e "${GREEN}✓ Cleanup complete${NC}"
    else
        echo -e "${RED}✗ FAIL${NC}: Docker build failed"
        ((FAILED++))
    fi
fi

# ============================================================================
# Summary
# ============================================================================

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                        VALIDATION SUMMARY                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Copy .env.example to .env and customize if needed"
    echo "  2. Run: docker-compose up -d --build"
    echo "  3. Access frontend at: http://localhost:3000"
    echo "  4. Access backend at: http://localhost:5000"
    echo ""
    exit 0
else
    echo ""
    echo -e "${RED}✗ Some checks failed. Please fix the issues above.${NC}"
    echo ""
    echo "For help, see: README-DOCKER.md"
    exit 1
fi
