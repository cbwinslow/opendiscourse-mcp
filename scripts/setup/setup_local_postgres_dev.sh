#!/usr/bin/env bash
# Local PostgreSQL developer helper for opendiscourse-mcp
set -euo pipefail
NAME="opendiscourse-dev-postgres"
IMAGE="postgres:15-alpine"
DB_USER="opendiscourse"
DB_PASS="opendiscourse123"
DB_NAME="opendiscourse"
HOST_PORT=5432

echo "[dev] Starting local PostgreSQL container (if not running) ..."
if [ "$(docker ps -aq -f name=^/${NAME}$)" != "" ]; then
  echo "[dev] Reusing existing container: $NAME"
else
  # Clean up any stopped container with the same name
  if [ "$(docker ps -aq -f name=^/${NAME}$ -f status=exited)" != "" ]; then
    docker rm "$NAME" >/dev/null 2>&1 || true
  fi
  docker run -d \
    --name "$NAME" \
    -e POSTGRES_USER="$DB_USER" \
    -e POSTGRES_PASSWORD="$DB_PASS" \
    -e POSTGRES_DB="$DB_NAME" \
    -p ${HOST_PORT}:5432 \
    "$IMAGE" >/dev/null
fi

echo "[dev] Waiting for PostgreSQL to become ready..."
# Wait until pg_isready reports ready inside the container
until docker exec "$NAME" pg_isready -U "$DB_USER" >/dev/null 2>&1; do
  sleep 1
  echo -n "."
done

echo "\n[dev] PostgreSQL is ready. Connection details:"
echo "DATABASE_URL=postgresql://$DB_USER:$DB_PASS@localhost:$HOST_PORT/$DB_NAME"

echo "[dev] Optional: export the URL for your shell session"
echo "export DATABASE_URL='postgresql://$DB_USER:$DB_PASS@localhost:$HOST_PORT/$DB_NAME'"
