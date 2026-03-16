#!/bin/bash

# Development Workflow Helper Script
# Provides shortcuts for common development tasks
# Usage: ./dev-commands.sh [command]

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_COMPOSE="-f docker-compose.yml"
DEV_COMPOSE="-f docker-compose.dev.yml"
PROD_COMPOSE="-f docker-compose.prod.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Main commands
start_dev() {
    info "Starting development environment with hot-reload..."
    cd "$PROJECT_DIR"
    docker-compose $BASE_COMPOSE $DEV_COMPOSE up
}

start_dev_detached() {
    info "Starting development environment in background..."
    cd "$PROJECT_DIR"
    docker-compose $BASE_COMPOSE $DEV_COMPOSE up -d
    success "Development environment started"
    echo ""
    info "Services running:"
    docker-compose $BASE_COMPOSE $DEV_COMPOSE ps
    echo ""
    info "Access points:"
    echo "  Frontend (Vite):  http://localhost:3000 or http://localhost:5173"
    echo "  Backend API:      http://localhost:5001"
    echo "  pgAdmin:          http://localhost:5050"
}

stop_dev() {
    info "Stopping development environment..."
    cd "$PROJECT_DIR"
    docker-compose $BASE_COMPOSE $DEV_COMPOSE down
    success "Development environment stopped"
}

start_prod() {
    info "Starting production environment..."
    cd "$PROJECT_DIR"
    docker-compose $BASE_COMPOSE $PROD_COMPOSE up -d
    success "Production environment started"
    docker-compose $BASE_COMPOSE $PROD_COMPOSE ps
}

stop_prod() {
    info "Stopping production environment..."
    cd "$PROJECT_DIR"
    docker-compose $BASE_COMPOSE $PROD_COMPOSE down
    success "Production environment stopped"
}

restart_service() {
    local service="$1"
    if [ -z "$service" ]; then
        error "Please specify service: frontend, backend, or db"
        exit 1
    fi
    info "Restarting $service..."
    cd "$PROJECT_DIR"
    docker-compose $BASE_COMPOSE $DEV_COMPOSE restart "$service"
    success "$service restarted"
}

logs_service() {
    local service="$1"
    if [ -z "$service" ]; then
        info "Showing logs from all services..."
        cd "$PROJECT_DIR"
        docker-compose $BASE_COMPOSE $DEV_COMPOSE logs -f
    else
        info "Showing logs from $service..."
        cd "$PROJECT_PROJECT"
        docker-compose $BASE_COMPOSE $DEV_COMPOSE logs -f "$service"
    fi
}

rebuild_image() {
    local service="$1"
    if [ -z "$service" ]; then
        error "Please specify service: frontend or backend"
        exit 1
    fi
    info "Rebuilding $service image..."
    cd "$PROJECT_DIR"
    docker-compose $BASE_COMPOSE $DEV_COMPOSE build --no-cache "$service"
    success "$service image rebuilt"
}

exec_backend() {
    local cmd="$1"
    if [ -z "$cmd" ]; then
        info "Opening bash shell in backend container..."
        cd "$PROJECT_DIR"
        docker-compose $BASE_COMPOSE $DEV_COMPOSE exec backend sh
    else
        cd "$PROJECT_DIR"
        docker-compose $BASE_COMPOSE $DEV_COMPOSE exec backend "$cmd"
    fi
}

exec_frontend() {
    local cmd="$1"
    if [ -z "$cmd" ]; then
        info "Opening bash shell in frontend container..."
        cd "$PROJECT_DIR"
        docker-compose $BASE_COMPOSE $DEV_COMPOSE exec frontend sh
    else
        cd "$PROJECT_DIR"
        docker-compose $BASE_COMPOSE $DEV_COMPOSE exec frontend "$cmd"
    fi
}

migrations_status() {
    info "Getting database migration status..."
    cd "$PROJECT_DIR"
    docker-compose $BASE_COMPOSE $DEV_COMPOSE exec backend flask db current
}

migrations_upgrade() {
    info "Running pending database migrations..."
    cd "$PROJECT_DIR"
    docker-compose $BASE_COMPOSE $DEV_COMPOSE exec backend flask db upgrade
    success "Migrations completed"
}

migrations_create() {
    local message="$1"
    if [ -z "$message" ]; then
        error "Please provide migration message"
        exit 1
    fi
    info "Creating new database migration: $message"
    cd "$PROJECT_DIR"
    docker-compose $BASE_COMPOSE $DEV_COMPOSE exec backend flask db migrate -m "$message"
    success "Migration created"
}

db_backup() {
    local backup_file="${1:-backup_$(date +%Y%m%d_%H%M%S).sql}"
    info "Backing up database to $backup_file..."
    cd "$PROJECT_DIR"
    docker-compose $BASE_COMPOSE $DEV_COMPOSE exec db pg_dump -U wallet_user wallet_db > "$backup_file"
    success "Database backed up to $backup_file"
}

db_shell() {
    info "Opening psql shell to database..."
    cd "$PROJECT_DIR"
    docker-compose $BASE_COMPOSE $DEV_COMPOSE exec db psql -U wallet_user -d wallet_db
}

health_check() {
    info "Checking service health..."
    cd "$PROJECT_DIR"
    echo ""
    docker-compose $BASE_COMPOSE $DEV_COMPOSE ps
    echo ""
    info "Testing connectivity:"

    # Test frontend
    if curl -s http://localhost:5173/ > /dev/null; then
        success "Frontend (Vite):   ✓ http://localhost:5173"
    else
        error "Frontend (Vite):   ✗ Not responding"
    fi

    # Test backend
    if curl -s http://localhost:5001/health > /dev/null; then
        success "Backend API:      ✓ http://localhost:5001/health"
    else
        error "Backend API:      ✗ Not responding"
    fi

    # Test database
    if docker-compose $BASE_COMPOSE $DEV_COMPOSE exec -T db pg_isready -U wallet_user > /dev/null 2>&1; then
        success "Database (PgSQL): ✓ localhost:5432"
    else
        error "Database (PgSQL): ✗ Not responding"
    fi
}

clean() {
    warning "This will remove all containers and volumes. Continue? (y/N)"
    read -r response
    if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
        info "Cleaning up Docker resources..."
        cd "$PROJECT_DIR"
        docker-compose $BASE_COMPOSE $DEV_COMPOSE down -v
        success "Cleanup completed"
    else
        info "Cleanup cancelled"
    fi
}

show_help() {
    cat << EOF
${BLUE}Development Workflow Helper${NC}

Usage: ./dev-commands.sh [command] [args]

${GREEN}Development Environment${NC}
  start              Start dev environment with logs visible
  start-bg           Start dev environment in background
  stop               Stop dev environment
  restart [service]  Restart specific service (frontend/backend/db)
  logs [service]     View logs from service or all if none specified

${GREEN}Production Environment${NC}
  prod-start         Start production environment
  prod-stop          Stop production environment

${GREEN}Building & Rebuilding${NC}
  rebuild [service]  Rebuild Docker image (frontend/backend)

${GREEN}Shell Access${NC}
  backend [cmd]      Execute command in backend or open shell
  frontend [cmd]     Execute command in frontend or open shell

${GREEN}Database Management${NC}
  db-status          Check database migration status
  db-upgrade         Run pending database migrations
  db-migrate [msg]   Create new database migration
  db-backup [file]   Backup database (defaults to backup_TIMESTAMP.sql)
  db-shell           Open psql shell to database

${GREEN}System${NC}
  health             Check health of all services
  clean              Remove all containers and volumes (WARNING)
  help               Show this help message

${GREEN}Examples${NC}
  ./dev-commands.sh start              # Start with logs
  ./dev-commands.sh start-bg           # Start in background
  ./dev-commands.sh logs frontend      # View frontend logs
  ./dev-commands.sh rebuild backend    # Rebuild backend image
  ./dev-commands.sh db-migrate "Add user table"
  ./dev-commands.sh backend python --version

EOF
}

# Main command dispatcher
case "${1:-help}" in
    start)
        start_dev
        ;;
    start-bg|start-detached)
        start_dev_detached
        ;;
    stop)
        stop_dev
        ;;
    restart)
        restart_service "$2"
        ;;
    logs)
        logs_service "$2"
        ;;
    prod-start)
        start_prod
        ;;
    prod-stop)
        stop_prod
        ;;
    rebuild)
        rebuild_image "$2"
        ;;
    backend)
        exec_backend "$2"
        ;;
    frontend)
        exec_frontend "$2"
        ;;
    db-status)
        migrations_status
        ;;
    db-upgrade)
        migrations_upgrade
        ;;
    db-migrate)
        migrations_create "$2"
        ;;
    db-backup)
        db_backup "$2"
        ;;
    db-shell)
        db_shell
        ;;
    health)
        health_check
        ;;
    clean)
        clean
        ;;
    help)
        show_help
        ;;
    *)
        error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
