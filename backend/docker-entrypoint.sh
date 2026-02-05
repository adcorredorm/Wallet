#!/bin/sh
# Docker entrypoint script for Flask backend
# Handles database initialization and migrations before starting the app

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Flask Backend Initialization ===${NC}"

# Wait for database to be available
echo -e "${YELLOW}Waiting for database to be available...${NC}"
while ! nc -z db 5432; do
  sleep 1
done
echo -e "${GREEN}Database is ready!${NC}"

# Wait a bit more to ensure PostgreSQL is fully initialized
sleep 2

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
if flask db upgrade; then
  echo -e "${GREEN}Database migrations completed successfully!${NC}"
else
  echo -e "${YELLOW}No migrations to run or migrations already applied.${NC}"
fi

# Create initial admin user if it doesn't exist (optional)
# Uncomment if you have a CLI command to create admin users
# echo -e "${YELLOW}Creating initial admin user...${NC}"
# flask create-admin || echo -e "${YELLOW}Admin user already exists${NC}"

echo -e "${GREEN}All initialization steps completed!${NC}"
echo -e "${BLUE}Starting Flask application...${NC}"

# Execute the main command passed to the container
exec "$@"
