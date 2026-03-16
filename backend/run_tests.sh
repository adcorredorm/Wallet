#!/usr/bin/env bash
# Run pytest in the worktree using the Docker backend image.
# Usage: ./run_tests.sh [pytest args...]
docker run --rm \
  --network wallet_wallet_network \
  -v "$(pwd)":/app \
  -e FLASK_ENV=testing \
  -e FLASK_APP=run.py \
  -e TEST_DATABASE_URL=postgresql://wallet_user:wallet_password@db:5432/wallet_test_db \
  -e DATABASE_URL=postgresql://wallet_user:wallet_password@db:5432/wallet_test_db \
  -e SECRET_KEY=test-secret \
  -e JWT_SECRET=test-jwt-secret \
  -e GOOGLE_CLIENT_ID=test-client-id \
  wallet-backend \
  pytest "$@"
