# Local PostgreSQL Development Setup

Problem: The production DB at 100.90.251.120:5432 may be unreachable in development. This guide provides a quick way to run a local Postgres instance for development.

Prerequisites
- Docker is installed and running.
- You have permission to run containers on the host.

Start a local Postgres container
- Run:
  - `bash scripts/setup/setup_local_postgres_dev.sh`
- The script will:
  - Start a Postgres 15-alpine container named `opendiscourse-dev-postgres` (if not already running).
  - Expose port 5432 on localhost.
  - Create user `opendiscourse` with password `opendiscourse123` and database `opendiscourse`.
  - Wait for readiness and print the connection string.
- Example URL:
  - `DATABASE_URL=postgresql://opendiscourse:opendiscourse123@localhost:5432/opendiscourse`

Using the local DB in MCP or scripts
- In your environment, export the URL before running MCP:
  - `export DATABASE_URL="postgresql://opendiscourse:opendiscourse123@localhost:5432/opendiscourse"`
- Run your ingestion or API logic as usual. The local DB will be used instead of the remote host if you point `DATABASE_URL` to localhost.

Notes
- This is for development/testing. Do not use the local DB in production or with real data without proper data governance.
- If you need to stop the local DB:
  - `docker rm -f opendiscourse-dev-postgres`
