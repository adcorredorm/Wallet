#!/bin/bash

# Validation script for Docker Compose configuration
# Ensures all required files exist and configuration is correct

set -e

echo "Validating Docker Compose configuration..."
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Helper functions
error() {
  echo -e "${RED}✗ ERROR: $1${NC}"
  ((ERRORS++))
}

warning() {
  echo -e "${YELLOW}⚠ WARNING: $1${NC}"
  ((WARNINGS++))
}

success() {
  echo -e "${GREEN}✓ $1${NC}"
}

# Check required files
echo "Checking required files..."
[ -f docker-compose.yml ] && success "docker-compose.yml exists" || error "docker-compose.yml not found"
[ -f docker-compose.dev.yml ] && success "docker-compose.dev.yml exists" || error "docker-compose.dev.yml not found"
[ -f backend/Dockerfile ] && success "backend/Dockerfile exists" || error "backend/Dockerfile not found"
[ -f frontend/Dockerfile ] && success "frontend/Dockerfile exists" || error "frontend/Dockerfile not found"
[ -f frontend/nginx.conf ] && success "frontend/nginx.conf exists" || error "frontend/nginx.conf not found"

echo ""
echo "Checking for deprecated files..."
[ ! -f docker-compose.prod.yml ] && success "docker-compose.prod.yml removed (no longer needed)" || warning "docker-compose.prod.yml still exists (should be removed)"
[ ! -f docker-compose.ports.yml ] && success "docker-compose.ports.yml removed (no longer needed)" || warning "docker-compose.ports.yml still exists (should be removed)"

echo ""
echo "Validating Docker Compose YAML syntax..."
if command -v docker-compose &> /dev/null; then
  if docker-compose config > /dev/null 2>&1; then
    success "docker-compose.yml is valid YAML"
  else
    error "docker-compose.yml has syntax errors"
  fi

  if docker-compose -f docker-compose.yml -f docker-compose.dev.yml config > /dev/null 2>&1; then
    success "docker-compose.yml + docker-compose.dev.yml is valid YAML"
  else
    error "docker-compose development overlay has syntax errors"
  fi
elif command -v docker &> /dev/null; then
  warning "docker-compose not found, docker compose (v2) syntax may differ - install docker-compose or use 'docker compose'"
else
  warning "Docker not found, skipping YAML validation"
fi

echo ""
echo "Checking environment configuration..."
if [ -f .env ]; then
  success ".env file exists"

  # Check required production environment variables
  if grep -q "^GOOGLE_CLIENT_ID=" .env && [ ! "$(grep '^GOOGLE_CLIENT_ID=' .env | cut -d= -f2)" = "" ]; then
    success "GOOGLE_CLIENT_ID is configured"
  else
    warning "GOOGLE_CLIENT_ID is not configured (required for production)"
  fi

  if grep -q "^JWT_SECRET=" .env && [ ! "$(grep '^JWT_SECRET=' .env | cut -d= -f2)" = "" ]; then
    success "JWT_SECRET is configured"
  else
    warning "JWT_SECRET is not configured (required for production)"
  fi

  if grep -q "^SECRET_KEY=" .env && [ ! "$(grep '^SECRET_KEY=' .env | cut -d= -f2)" = "" ]; then
    success "SECRET_KEY is configured"
  else
    warning "SECRET_KEY is not configured (required for production)"
  fi
else
  error ".env file not found - copy from .env.example and update with your values"
fi

echo ""
echo "Checking Docker configuration..."
if [ -f .dockerignore ]; then
  success ".dockerignore exists"
else
  warning ".dockerignore not found (optional but recommended)"
fi

echo ""
echo "Configuration Summary:"
echo "====================="
echo "Production deployment: docker compose up -d"
echo "Development deployment: docker compose -f docker-compose.yml -f docker-compose.dev.yml up"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
  echo -e "${GREEN}All checks passed! Configuration is ready.${NC}"
  exit 0
elif [ $ERRORS -eq 0 ]; then
  echo -e "${YELLOW}Configuration is valid but has $WARNINGS warning(s).${NC}"
  exit 0
else
  echo -e "${RED}Configuration has $ERRORS error(s) and $WARNINGS warning(s).${NC}"
  exit 1
fi
