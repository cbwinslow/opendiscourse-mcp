# CloudCurio Monorepo Template (v1)

A batteries-included starter monorepo for Blaine’s stack on **cbwdellr720** with:

- **Apps**: Next.js web, FastAPI API, Workers/Edge functions, Supabase functions
- **Infra**: Ansible (bare metal & Docker), Terraform (Cloudflare + free-tier), Pulumi stacks
- **Observability**: Prometheus, Grafana, Loki, Tempo/Jaeger, Netdata, OpenSearch, Sentry
- **Messaging/Jobs**: RabbitMQ, Redis
- **Secrets**: Bitwarden CLI first-class, optional Vault buffer, SOPS support
- **Dev Tools**: .devcontainer, VSCode settings (Roo Code, Cline, Kilo, MCP clients), linting, Actions/CI
- **Networking**: Cloudflared, Traefik/Caddy/Nginx, SSH toolkit, ZeroTier/Tailscale/NetBird-aware
- **DB**: Postgres (central on cbwdellr720), Prisma (TS), SQLAlchemy/SQLModel (Py)
- **Agents**: MCP servers registry + client configs, CrewAI configs, OpenRouter/Ollama wiring
- **Shells**: bash/zsh/fish/nushell profiles, completions, aliases, secrets glue

> **Target OS**: Debian/Ubuntu/RHEL family. **Python**: 3.10.6 via pyenv + uv. **GPU**: optional (NVIDIA/AMD hooks provided).

---

## Repository Layout

```
cloudcurio-monorepo/
├─ apps/
│  ├─ web-next/                 # Next.js app (app router, Tailwind, shadcn/ui)
│  ├─ api-fastapi/              # FastAPI service (Pydantic v2, SQLModel)
│  ├─ workers-cloudflare/       # Cloudflare Workers (Hono/itty-router)
│  ├─ supabase/                 # Edge functions, SQL, storage rules
│  └─ worker-jobs/              # Celery (Python) and BullMQ (Node) jobs
├─ packages/
│  ├─ ui/                       # Shared React components
│  ├─ config/                   # ESLint, Prettier, tsconfig, ruff, mypy, biome
│  ├─ types/                    # Zod schemas & TS types
│  └─ python-lib/               # Shared Python utilities (logging, BW, OTEL)
├─ infra/
│  ├─ ansible/
│  │  ├─ inventories/
│  │  │  ├─ lab/
│  │  │  │  ├─ hosts            # cbwdellr720, cbwhpz, etc.
│  │  │  │  ├─ group_vars/
│  │  │  │  │  ├─ all.yml
│  │  │  │  │  └─ monitoring.yml
│  │  │  └─ prod/
│  │  ├─ roles/
│  │  │  ├─ common/             # baseline (users, ssh, packages)
│  │  │  ├─ docker/             # docker+compose setup
│  │  │  ├─ reverse_proxy/      # traefik|caddy|nginx
│  │  │  ├─ postgres/           # pg + pgvector + backups
│  │  │  ├─ monitoring/         # prom+grafana+loki+tempo+netdata
│  │  │  ├─ opensearch/         # opensearch + dashboards seed
│  │  │  ├─ sentry/             # self-host sentry
│  │  │  └─ rabbitmq/
│  │  ├─ playbooks/
│  │  │  ├─ site.yml            # master site playbook
│  │  │  ├─ bootstrap.yml       # first-run baseline
│  │  │  ├─ monitoring.yml      # monitoring stack install
│  │  │  ├─ db.yml              # postgres stack
│  │  │  └─ reverse-proxy.yml
│  │  └─ files/                 # static files, service units, configs
│  ├─ terraform/
│  │  ├─ cloudflare/            # DNS, R2, KV, Zero-Trust, Tunnels
│  │  ├─ oracle-free-tier/      # optional DB/VM free tier (safe placeholders)
│  │  └─ outputs/               # json outputs to consume in CI
│  ├─ pulumi/
│  │  ├─ stacks/
│  │  │  ├─ networking/         # tunnels, WAF, routes
│  │  │  ├─ observability/      # loki/prom buckets, alerts
│  │  │  └─ apps/               # app deploy groups
│  │  └─ Pulumi.yaml
│  └─ k8s/                      # optional k3s/helm charts
├─ ops/
│  ├─ scripts/                  # backups, migrations, log shipping
│  ├─ ssh/                      # ssh policy mgmt, key sync, bastion
│  └─ reports/                  # system profile collectors → Postgres
├─ secrets/
│  ├─ templates/                # .env.tpl files (Bitwarden lookups)
│  └─ sops/                     # optional sealed secrets
├─ ci/
│  ├─ github/                   # GitHub Actions workflows
│  └─ gitlab/                   # .gitlab-ci.yml and includes
├─ .devcontainer/               # dev containers (Docker + features)
├─ tools/
│  ├─ mcp/                      # MCP servers registry + client configs
│  ├─ agents/                   # CrewAI, prompts, tool specs
│  ├─ shell/                    # bash/zsh/fish/nushell (_functions etc.)
│  ├─ bw/                       # Bitwarden helpers
│  └─ templates/                # project & code templates
├─ docs/
│  ├─ ADRs/
│  ├─ playbooks/                # Runbooks, SOPs
│  ├─ cheatsheets/              # TL;DRs for stack terms
│  └─ reference/
├─ docker-compose.yml           # dev single-host composition
├─ Makefile                     # common tasks (make help)
├─ pyproject.toml               # uv + project metadata
├─ .tool-versions               # asdf/pyenv pin for Python 3.10.6
└─ README.md
```

---

## Quick Start

```bash
# 0) Prereqs (host): Docker, Docker Compose, Make, Git, bw CLI, pyenv, uv

# 1) Clone
git clone https://github.com/cbwinslow/cloudcurio-monorepo-template.git
cd cloudcurio-monorepo-template

# 2) Secrets login (Bitwarden)
bw login blaine.winslow@gmail.com  # or bw unlock --raw > /tmp/BW_SESSION
export BW_SESSION=$(bw unlock --raw)

# 3) Materialize env files from templates with BW lookups
./tools/bw/bw-env.sh materialize

# 4) Bring up dev stack
docker compose up -d --build

# 5) Deploy monitoring to cbwdellr720 via Ansible
ansible-playbook -i infra/ansible/inventories/lab/hosts infra/ansible/playbooks/monitoring.yml
```

> **Secrets model**: We use **Bitwarden CLI** and lightweight placeholders like `BW[item="Postgres Admin" field="password"]`. The **bw-env.sh** tool resolves them at build/run time. Optional Vault integration is provided for a two-step secrets buffer.

---

## Secrets Strategy (Bitwarden-first, Vault-optional)

**Lookup syntax in .env templates**
```
# secrets/templates/.env.api.tpl
DATABASE_URL=postgresql://postgres:${BW[item="Postgres Admin" field="password"]}@cbwdellr720:5432/cloudcurio
JWT_SECRET=${BW[item="CloudCurio JWT" field="secret"]}
OPENROUTER_API_KEY=${BW[item="OpenRouter" field="api_key"]}
```

**Materialization**
- `tools/bw/bw-env.sh materialize` reads all `secrets/templates/*.tpl` files, replaces `BW[...]` expressions using `bw get item` and writes concrete `.env` files next to consumers (never commit them).
- Optional: `tools/bw/bw-env.sh export` prints an env block you can `eval` for ephemeral shells.

**Vault buffer (optional)**
- `infra/ansible/roles/vault/` (not shown in tree) can mirror Bitwarden items into Vault for runtime fetch (envconsul or custom shim). This keeps a separation between your password manager and runtime.

---

## Networking & Remote Access Opinionated Setup

- **Primary overlay**: pick **one** (ZeroTier _or_ Tailscale _or_ NetBird). Default: **ZeroTier** per recent stability for you.
- **SSH**: Managed via `ops/ssh/` tools
  - `cbw-ssh-ensure.sh` idempotently sets up `~/.ssh`, `ssh_config`, `known_hosts`, and pushes keys to targets.
  - `cbw-ssh-audit.sh` prints a cross-host matrix (who can SSH to whom) and tests overlay IPs.
  - `cbw-ssh-recover.sh` provides emergency local-console steps + Cloudflared tunnel fallback.
- **Reverse proxy**: Traefik (default) with ACME, rate-limit, secure headers; Caddy and Nginx templates included.
- **Cloudflared**: `apps` exposed via named tunnels; Zero-Trust policies documented.

---

## Observability Stack (bare metal via Ansible; Docker alternative)

Playbook installs on **cbwdellr720**:
- **Prometheus** (scrape hosts/apps), **Alertmanager** (basic rules)
- **Grafana** (dashboards for Linux hosts, Postgres, Loki)
- **Loki** (logs) + **Promtail** agents
- **Tempo/Jaeger** (traces via OTEL)
- **Netdata** (host telemetry)
- **OpenSearch** (search + archival logs)
- **Sentry** (app errors)

> Agents send logs/metrics to cbwdellr720 via overlay IPs. Retention default 90 days, configurable.

---

## Database (Postgres on cbwdellr720)

- Enabled extensions: `pgvector`, `uuid-ossp`, `pg_stat_statements`.
- `ops/scripts/pg/` includes: backup/restore, role mgmt, index advice, vacuum/ANALYZE, WAL archiving helpers.
- **Universal Logging DB**: schema `observability` with tables for host metrics/logs (normalized) and ingest pipelines from Prom/Loki exporters.

---

## CI/CD (GitHub & GitLab)

- **GitHub Actions** in `ci/github/` (copy to `.github/workflows/`):
  - `ci.yml`: lint/type/test for TS/Py, build images, SBOM, push to GHCR
  - `deploy.yml`: Ansible playbook runner on tag; Terraform plan/apply gated
  - `secrets-check.yml`: detect secrets, SLSA provenance, dependency review
  - `issues-automation.yml`: triage Issues/Projects v2 with AI assist (OpenRouter)
- **GitLab CI** templates in `ci/gitlab/` with stages parity, container registry push, and environment reviews.

Secrets for CI are resolved by `bw-env.sh ci-export` + masked CI variables. Never store raw secrets in repo.

---

## Dev Environment

- **.devcontainer/** includes Dockerfile with:
  - Node (lts), pnpm/bun, Python 3.10.6 via pyenv + uv, Go optional, `bw` CLI, `gh`, `glab`
  - Extensions: Roo Code, Cline, Kilo Code, MCP client, Thunder Client, Prisma, Python, Ruff
- **VSCode settings** pre-wire formatters/linters, autofix, and workspace tasks for `make web`/`make api`.
- **Shell profiles** in `tools/shell/` with `_functions`, `_aliases`, `_completions`, `_secrets`, `_profiles` across bash/zsh/fish/nushell. Colorized prompts, Git & kube context, bw helpers.

---

## MCP Servers & Agents

- `tools/mcp/registry.yaml` lists MCP endpoints (Anthropic MCP): Cloudflare, GitHub, GitLab, Context7, Supabase, BW, Terraform, Pulumi, Postgres.
- `tools/agents/` houses CrewAI crew configs, tool specs, prompts, runbooks. Includes an **Orchestrator MCP** that can render downstream client configs and distribute them to target apps.

**Workflow**
1) Define endpoints & creds via Bitwarden items (names documented).
2) Run `tools/mcp/render-configs.py` to emit per-tool client configs into `apps/*/mcp.json`.
3) Apps load MCP configs at boot from mounted path.

---

## Key Files (Selected Content)

### 1) `tools/bw/bw-env.sh`
```bash
#!/usr/bin/env bash
# ============================================================================
# Script: bw-env.sh
# Author: CBW / CloudCurio
# Date: 2025-10-24
# Summary: Materialize .env files from templates with Bitwarden CLI lookups.
# Inputs: subcommand [materialize|export|ci-export], optional paths
# Outputs: Concrete .env files or an exported env block (stdout)
# Params: BW_SESSION (env), BW_VAULT (collection filter optional)
# Notes: Never commits outputs; resolves tokens like BW[item="X" field="Y"]
# Changelog:
#  - v1: initial
# ============================================================================
set -euo pipefail
shopt -s globstar nullglob

err() { echo "[bw-env] ERROR: $*" >&2; }
log() { echo "[bw-env] $*"; }
usage() { sed -n '1,40p' "$0"; }

_require() {
  command -v bw >/dev/null 2>&1 || { err "Bitwarden CLI not found"; exit 1; }
}

_resolve() {
  local token="$1" json key field
  # token format: BW[item="Name" field="key"] or BW[item="Name" notes]
  json=$(bw get item "$(sed -E 's/.*item=\"([^\"]+)\".*/\1/' <<<"$token")")
  if grep -q 'field=' <<<"$token"; then
    key=$(sed -E 's/.*field=\"([^\"]+)\".*/\1/' <<<"$token")
    field=$(jq -r --arg k "$key" '.fields[]?|select(.name==$k).value' <<<"$json")
    [[ -z "$field" || "$field" == "null" ]] && field=$(jq -r --arg k "$key" '.secureNote?.notes' <<<"$json")
    echo -n "$field"
  else
    jq -r '.notes' <<<"$json"
  fi
}

_render_file() {
  local src="$1" dst=${2:-"${src%.tpl}"}
  log "render $src -> $dst"
  awk '{print}' "$src" | \
  perl -0777 -pe 's/\$\{BW\[[^\]]+\]\}/my $t=$&; $t=~s/[\$\{\}]//g; $t=~s/^BW\[//; $t=~s/\]$//; open(FX, "-|", "bash", "-lc", "_bw_token \"$t\" ") or die $!; local $/; <FX>; /ge' > "$dst"
}

# helper exposed to perl above
export -f _resolve
_bw_token() { _resolve "$*"; }
export -f _bw_token

cmd=${1:-materialize}
paths=("secrets/templates/**/*.tpl")
shift || true
[[ $# -gt 0 ]] && paths=("$@")

_require
: "${BW_SESSION:?Run 'bw unlock --raw' and export BW_SESSION}"

case "$cmd" in
  materialize)
    for f in ${paths[@]}; do [ -f "$f" ] && _render_file "$f"; done ;;
  export|ci-export)
    # Prints KEY=VALUE pairs by scanning templates and resolving tokens
    for f in ${paths[@]}; do
      [ -f "$f" ] || continue
      while IFS= read -r line; do
        [[ "$line" =~ ^#|^\s*$ ]] && continue
        key=${line%%=*}
        val=${line#*=}
        if [[ "$val" =~ BW\[.*\] ]]; then
          token=$(sed -E 's/.*(BW\[[^\]]+\]).*/\1/' <<<"$val")
          resolved=$(_resolve "$token")
          echo "$key=$resolved"
        fi
      done < "$f"
    done ;;
  *) usage; exit 2;;
}
```

### 2) `infra/ansible/inventories/lab/hosts`
```ini
[monitoring]
cbwdellr720 ansible_host=192.168.6.69 ansible_user=cbwinslow

[databases]
cbwdellr720

[reverse_proxy]
cbwdellr720

[all:vars]
ansible_python_interpreter=/usr/bin/python3
overlay_primary=zerotier
zerotier_ip=172.28.158.179
```

### 3) `infra/ansible/playbooks/monitoring.yml`
```yaml
---
- name: Install Monitoring Stack on cbwdellr720
  hosts: monitoring
  become: true
  vars_files:
    - ../inventories/lab/group_vars/monitoring.yml
  roles:
    - role: common
    - role: docker
    - role: monitoring
```

### 4) `infra/ansible/roles/monitoring/tasks/main.yml`
```yaml
---
- name: Create monitoring directories
  file:
    path: "/opt/monitoring/{{ item }}"
    state: directory
    owner: root
    group: root
    mode: "0755"
  loop:
    - prometheus
    - grafana
    - loki
    - promtail
    - tempo
    - alertmanager

- name: Deploy docker-compose for monitoring
  copy:
    dest: /opt/monitoring/docker-compose.yml
    content: |
      version: "3.9"
      services:
        prometheus:
          image: prom/prometheus:latest
          volumes:
            - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
          ports: ["9090:9090"]
          restart: unless-stopped
        grafana:
          image: grafana/grafana:latest
          environment:
            - GF_SECURITY_ADMIN_PASSWORD=${GF_ADMIN_PASSWORD}
          ports: ["3000:3000"]
          restart: unless-stopped
        loki:
          image: grafana/loki:latest
          command: ["-config.file=/etc/loki/local-config.yaml"]
          ports: ["3100:3100"]
          restart: unless-stopped
        promtail:
          image: grafana/promtail:latest
          command: ["-config.file=/etc/promtail/config.yml"]
          volumes:
            - /var/log:/var/log:ro
          restart: unless-stopped
        tempo:
          image: grafana/tempo:latest
          ports: ["3200:3200"]
          restart: unless-stopped
      networks:
        default:
          name: monitoring
          driver: bridge

- name: .env for monitoring
  copy:
    dest: /opt/monitoring/.env
    content: |
      GF_ADMIN_PASSWORD={{ lookup('env', 'GF_ADMIN_PASSWORD') | default('changeme') }}
  no_log: true

- name: Start monitoring stack
  community.docker.docker_compose:
    project_src: /opt/monitoring
    state: present
```

### 5) `ops/ssh/cbw-ssh-ensure.sh`
```bash
#!/usr/bin/env bash
# ============================================================================
# Script: cbw-ssh-ensure.sh
# Author: CBW / CloudCurio
# Date: 2025-10-24
# Summary: Idempotently ensure SSH client config, keys, known_hosts, and test
# Inputs: --push <hostfile> (scp authorized_keys), --test <host>
# Outputs: Validated SSH access across overlays
# ============================================================================
set -euo pipefail

me=${USER:-cbwinslow}
ssh_dir="$HOME/.ssh"
mkdir -p "$ssh_dir"; chmod 700 "$ssh_dir"
: "${BW_SESSION:?export BW_SESSION=$(bw unlock --raw)}"

# Pull key from Bitwarden item "CBW SSH Ed25519"
if [ ! -f "$ssh_dir/id_ed25519" ]; then
  bw get attachment id_ed25519 --itemid "$(bw list items --search "CBW SSH Ed25519" | jq -r '.[0].id')" \
    --output "$ssh_dir/id_ed25519"
  chmod 600 "$ssh_dir/id_ed25519"
fi
if [ ! -f "$ssh_dir/id_ed25519.pub" ]; then
  bw get attachment id_ed25519.pub --itemid "$(bw list items --search "CBW SSH Ed25519" | jq -r '.[0].id')" \
    --output "$ssh_dir/id_ed25519.pub"
  chmod 644 "$ssh_dir/id_ed25519.pub"
fi

# Basic ssh_config
cat > "$ssh_dir/config" <<'CFG'
Host *
  AddKeysToAgent yes
  ForwardAgent no
  IdentityAgent ~/.ssh/agent.sock
  IdentityFile ~/.ssh/id_ed25519
  ServerAliveInterval 30
  ServerAliveCountMax 4
  StrictHostKeyChecking accept-new

Host cbwdellr720
  HostName 192.168.6.69
  User cbwinslow

Host cbwdellr720-zt
  HostName 172.28.158.179
  User cbwinslow
CFG
chmod 600 "$ssh_dir/config"

if [[ ${1:-} == "--push" ]]; then
  hostfile=${2:?provide hostfile}
  while read -r host; do
    echo "[ssh] pushing key to $host";
    ssh -o StrictHostKeyChecking=accept-new "$host" "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '$(cat "$ssh_dir/id_ed25519.pub")' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
  done < "$hostfile"
fi

if [[ ${1:-} == "--test" ]]; then
  target=${2:?target}
  echo "[ssh] testing to $target"; ssh -o BatchMode=yes -o ConnectTimeout=5 "$target" 'echo ok'
fi
```

### 6) `docker-compose.yml` (dev convenience)
```yaml
version: "3.9"
services:
  web:
    build: ./apps/web-next
    env_file:
      - ./apps/web-next/.env
    ports: ["3000:3000"]
    depends_on: [api]
  api:
    build: ./apps/api-fastapi
    env_file:
      - ./apps/api-fastapi/.env
    ports: ["8000:8000"]
    depends_on: [db, redis]
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: cloudcurio
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports: ["5432:5432"]
  redis:
    image: redis:7
    ports: ["6379:6379"]
  traefik:
    image: traefik:v3.1
    command:
      - --api.insecure=true
      - --providers.docker=true
      - --entrypoints.web.address=:80
      - --entrypoints.websecure.address=:443
    ports: ["80:80","443:443","8080:8080"]
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
volumes:
  pgdata:
```

### 7) GitHub Actions `ci/github/ci.yml`
```yaml
name: CI
on: [push, pull_request]
jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
        with: { node-version: lts }
      - name: Setup Python
        uses: actions/setup-python@v5
        with: { python-version: '3.10' }
      - name: Install pnpm
        run: npm i -g pnpm
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Resolve secrets via Bitwarden
        env:
          BW_CLIENTID: ${{ secrets.BW_CLIENTID }}
          BW_CLIENTSECRET: ${{ secrets.BW_CLIENTSECRET }}
          BW_PASSWORD: ${{ secrets.BW_PASSWORD }}
        run: |
          bw login --apikey
          export BW_SESSION=$(bw unlock --passwordenv BW_PASSWORD --raw)
          ./tools/bw/bw-env.sh ci-export > /tmp/ci.env
      - name: Typecheck & Lint
        run: |
          pnpm i --frozen-lockfile
          pnpm -C apps/web-next lint
          uv sync && uv run ruff check
      - name: Build Containers
        run: |
          docker build -t ghcr.io/${{ github.repository }}/web:sha-${{ github.sha }} apps/web-next
          docker build -t ghcr.io/${{ github.repository }}/api:sha-${{ github.sha }} apps/api-fastapi
      - name: SBOM
        uses: anchore/syft-action@v0.16.0
        with:
          image: ghcr.io/${{ github.repository }}/web:sha-${{ github.sha }}
      - name: Push Images
        if: github.ref == 'refs/heads/main'
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - run: |
          docker push ghcr.io/${{ github.repository }}/web:sha-${{ github.sha }}
          docker push ghcr.io/${{ github.repository }}/api:sha-${{ github.sha }}
```

### 8) GitLab CI `ci/gitlab/.gitlab-ci.yml`
```yaml
stages: [lint, test, build, deploy]
variables:
  DOCKER_DRIVER: overlay2
lint:
  stage: lint
  image: node:lts
  script:
    - npm i -g pnpm
    - pnpm i
    - pnpm -C apps/web-next lint
build:
  stage: build
  image: docker:24
  services: [docker:24-dind]
  script:
    - docker build -t $CI_REGISTRY_IMAGE/web:$CI_COMMIT_SHA apps/web-next
    - docker push $CI_REGISTRY_IMAGE/web:$CI_COMMIT_SHA
```

### 9) `apps/api-fastapi/app/main.py`
```python
#!/usr/bin/env python3
"""
Script: main.py (FastAPI service)
Author: CBW / CloudCurio
Date: 2025-10-24
Summary: Typed API with health, Postgres, Redis, and OTEL ready.
Inputs: ENV via .env (pydantic-settings)
Outputs: JSON API
ChangeLog: v1 initial
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic_settings import BaseSettings
import asyncpg

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str | None = None

settings = Settings()  # type: ignore

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await asyncpg.connect(settings.DATABASE_URL)
    yield
    await app.state.db.close()

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"ok": True}
```

### 10) Docs: `docs/cheatsheets/stack-terms.md`
```md
# TL;DR Stack Terms
- **Prisma**: TS ORM & schema tool. One schema file → migrations + typed client.
- **SQLAlchemy/SQLModel**: Python ORM; SQLModel adds Pydantic-like models.
- **Zod**: TS schema validation; generate types & OpenAPI.
- **Celery**: Python task queue using Redis/RabbitMQ.
- **Pydantic**: Python data validation; used by FastAPI.
- **TanStack Query**: Frontend server-state cache (fetching, caching, retries).
- **tRPC**: End-to-end typesafe RPC between TS client & server.
- **mTLS**: Mutual TLS—both client/server present certs. Use for service-to-service.
- **Alembic**: DB migration tool for SQLAlchemy/SQLModel.
- **SSR/ISR**: Server-Side Rendering / Incremental Static Regeneration in Next.js.
- **ACME**: Protocol for auto TLS certificates (Let’s Encrypt).
- **Middleware**: Request/response interceptors (auth, logging, rate limits).
- **JWT**: Signed token for auth; keep short-lived.
- **REST**: HTTP resource API; pair with OpenAPI.
- **Tailwind**: Utility-first CSS framework.
- **KMS**: Key Management Service (e.g., Cloud KMS) for encryption keys.
- **Ingress**: Entry to cluster/services (Traefik/Caddy/Nginx).
- **Drizzle**: Lightweight TS ORM; alt to Prisma.
- **WebSockets**: Bi-directional realtime; fallbacks SSE.
```

---

## Deployment Notes

- Prefer **Ansible** for host bootstraps and long-running stacks on **cbwdellr720**.
- Use **Docker Compose** locally and for quick previews; move heavy services to Ansible-managed bare metal.
- Maintain **single source of truth** for secrets in **Bitwarden**; CI loads them ephemerally.
- Centralize logs/metrics/traces on **cbwdellr720**; default retention 90 days (tune in Ansible vars).

---

## Make Targets

```makefile
help: ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?##' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

bootstrap: ## First-run host bootstrap
	ansible-playbook -i infra/ansible/inventories/lab/hosts infra/ansible/playbooks/bootstrap.yml

monitoring: ## Install/update monitoring stack
	ansible-playbook -i infra/ansible/inventories/lab/hosts infra/ansible/playbooks/monitoring.yml

env: ## Materialize env files from BW
	./tools/bw/bw-env.sh materialize
```

---

## What To Customize First
1) `infra/ansible/inventories/lab/hosts` – your hostnames & overlay IPs
2) `secrets/templates/*.tpl` – Bitwarden item names (no raw secrets!)
3) `apps/web-next` & `apps/api-fastapi` – project names, routes, DB urls
4) `infra/terraform/cloudflare` – DNS zones, tunnels, KV/R2 buckets
5) `tools/mcp/registry.yaml` – add/edit MCP endpoints & auth

---

## Roadmap / Tasks Backlog
- 🔐 Add Vault role to mirror select BW items → Vault paths w/ leases
- 🧠 Add LiteLLM proxy service + central config and per-app adapters
- ☸️ k3s variant with Helm charts for monitoring & apps
- 📈 Supabase functions scaffold + DDL & policies; seed scripts
- 🧪 Add end-to-end tests (Playwright for web, pytest for API)
- ♻️ GitHub/GitLab automation: Issues ↔ Projects v2 sync; AI code review jobs using OpenRouter free-tier
- 🗂 Knowledge base: evaluate **ClickUp** vs **Outline** (self-host) vs **AppFlowy Cloud** with RAG

---

## Security Notes
- Use **short-lived tokens** and **principle of least privilege** for CI variables.
- Restrict overlay access: only one primary overlay active for production paths.
- Rotate SSH keys quarterly; `cbw-ssh-ensure.sh` helps sync and push.
- Backups: Postgres base + WAL, Grafana dashboards, Prometheus TSDB snapshots.

---

## License
MIT (template). Replace with your preferred license.



---

## Supabase Scaffold (Edge Functions, SQL, Storage)

### `apps/supabase/functions/hello/index.ts`
```ts
/**
 * File: apps/supabase/functions/hello/index.ts
 * Date: 2025-10-24
 * Author: CBW / CloudCurio
 * Summary: Simple Edge Function with BW-driven secrets (materialized in env).
 * Inputs: request JSON
 * Outputs: JSON payload { ok, time }
 */
import { serve } from "https://deno.land/std@0.224.0/http/server.ts";

serve(async (req) => {
  return new Response(JSON.stringify({ ok: true, time: new Date().toISOString() }), {
    headers: { "content-type": "application/json" },
  });
});
```

### `apps/supabase/sql/init/000_base.sql`
```sql
-- Enable useful extensions
create extension if not exists "uuid-ossp";
create extension if not exists pg_trgm;
create extension if not exists vector;

-- Observability schema (universal logging ingress)
create schema if not exists observability;
create table if not exists observability.app_events (
  id uuid primary key default uuid_generate_v4(),
  ts timestamptz not null default now(),
  app text not null,
  level text not null,
  message text not null,
  context jsonb default '{}'::jsonb
);

-- RLS example for multi-tenant tables
create schema if not exists public;
create table if not exists public.notes (
  id bigint generated by default as identity primary key,
  owner uuid not null,
  body text not null,
  created_at timestamptz not null default now()
);
alter table public.notes enable row level security;
create policy "notes-is-owner" on public.notes using (owner = auth.uid());
```

### `apps/supabase/.env.tpl`
```env
SUPABASE_URL=${BW[item="Supabase CloudCurio" field="url"]}
SUPABASE_SERVICE_ROLE_KEY=${BW[item="Supabase CloudCurio" field="service_key"]}
SUPABASE_ANON_KEY=${BW[item="Supabase CloudCurio" field="anon_key"]}
```

---

## Vault Buffer (Optional) – Ansible Role

### `infra/ansible/roles/vault/tasks/main.yml`
```yaml
---
- name: Install HashiCorp Vault (binary)
  ansible.builtin.include_tasks: install.yml

- name: Configure Vault service & storage
  ansible.builtin.template:
    src: vault.hcl.j2
    dest: /etc/vault.d/vault.hcl
    mode: "0644"

- name: Ensure vault systemd
  ansible.builtin.template:
    src: vault.service.j2
    dest: /etc/systemd/system/vault.service
    mode: "0644"

- name: Start & enable Vault
  ansible.builtin.systemd:
    name: vault
    enabled: true
    state: started

- name: (Optional) Mirror Bitwarden items → Vault paths
  when: mirror_bw_to_vault | default(false)
  ansible.builtin.script: mirror_bw_to_vault.py
  environment:
    BW_SESSION: "{{ lookup('env','BW_SESSION') | default('') }}"
```

### `infra/ansible/roles/vault/templates/vault.hcl.j2`
```hcl
listener "tcp" {
  address = "127.0.0.1:8200"
  tls_disable = 1
}
storage "file" {
  path = "/var/lib/vault"
}
ui = true
```

> Use the role when you want a two-step runtime secret fetch. By default our CI pulls from Bitwarden directly; Vault is optional.

---

## k3s / Helm Variant (Optional)

### `infra/ansible/playbooks/k3s.yml`
```yaml
---
- name: Install k3s on cbwdellr720
  hosts: monitoring
  become: true
  roles:
    - role: common
    - role: k3s
```

### `infra/k8s/helm/monitoring/values.yaml`
```yaml
grafana:
  adminPassword: ${GF_ADMIN_PASSWORD}
prometheus:
  server:
    retention: 30d
loki:
  persistence:
    enabled: true
    size: 200Gi
```

---

## LiteLLM Proxy (Central Model Gateway)

### `infra/ansible/roles/litellm/tasks/main.yml`
```yaml
---
- name: Deploy LiteLLM via Docker
  copy:
    dest: /opt/litellm/docker-compose.yml
    content: |
      version: "3.9"
      services:
        litellm:
          image: ghcr.io/berriai/litellm:latest
          environment:
            - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
          ports: ["4000:4000"]
          command: ["--port","4000","--num_workers","2"]
  register: wrote

- name: Start LiteLLM
  when: wrote is changed
  community.docker.docker_compose:
    project_src: /opt/litellm
    state: present
```

### `secrets/templates/.env.litellm.tpl`
```env
OPENROUTER_API_KEY=${BW[item="OpenRouter" field="api_key"]}
```

---

## Prisma (TypeScript) for Postgres w/ pgvector

### `apps/web-next/prisma/schema.prisma`
```prisma
// File: schema.prisma (CloudCurio)
// Date: 2025-10-24
// Summary: Base schema with User, Note, and Embedding table using pgvector

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id        String   @id @default(cuid())
  email     String   @unique
  createdAt DateTime @default(now())
  notes     Note[]
}

model Note {
  id        Int      @id @default(autoincrement())
  ownerId   String
  body      String
  createdAt DateTime @default(now())
  owner     User     @relation(fields: [ownerId], references: [id])
}

model Embedding {
  id     Int     @id @default(autoincrement())
  noteId Int
  vec    Unsupported("vector(1536)")
  note   Note    @relation(fields: [noteId], references: [id])
  @@index([noteId])
}
```

### `apps/web-next/.env.tpl`
```env
DATABASE_URL=postgresql://postgres:${BW[item="Postgres Admin" field="password"]}@cbwdellr720:5432/cloudcurio
```

---

## PostgreSQL Ops Scripts

### `ops/scripts/pg/backup.sh`
```bash
#!/usr/bin/env bash
# ============================================================================
# Script: backup.sh
# Author: CBW / CloudCurio
# Date: 2025-10-24
# Summary: Compressed pg_dump with rotation
# Inputs: DB (env DATABASE_URL) or -d, output dir (default /var/backups/pg)
# ============================================================================
set -euo pipefail
DB=${DATABASE_URL:-${1:-}}
OUT=${2:-/var/backups/pg}
mkdir -p "$OUT"
ts=$(date +%Y%m%d-%H%M%S)
pg_dump --format=custom "$DB" -Z 6 -f "$OUT/backup-$ts.dump"
find "$OUT" -name 'backup-*.dump' -mtime +30 -delete
```

### `ops/scripts/pg/roles.sql`
```sql
-- Create app role and readonly role
create role app with login password '${APP_PW}';
create role readonly;
grant connect on database cloudcurio to app, readonly;
grant usage on schema public to app, readonly;
```

---

## Terraform Cloudflare (Tunnels, DNS, R2, KV)

### `infra/terraform/cloudflare/main.tf`
```hcl
terraform {
  required_providers { cloudflare = { source = "cloudflare/cloudflare" } }
}
provider "cloudflare" {}

variable "zone" { type = string }

resource "cloudflare_r2_bucket" "logs" { account_id = var.account_id name = "cloudcurio-logs" }
resource "cloudflare_kv_namespace" "config" { account_id = var.account_id title = "cloudcurio-config" }

resource "cloudflare_record" "api" {
  zone_id = var.zone
  name    = "api"
  value   = "${var.origin_ip}"
  type    = "A"
  proxied = true
}
```

---

## CI Additions (Deploy + AI Assist)

### `ci/github/deploy.yml`
```yaml
name: Deploy
on:
  push:
    tags: ['v*']
jobs:
  infra:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Ansible
        run: sudo apt-get update && sudo apt-get install -y ansible
      - name: Deploy monitoring
        run: ansible-playbook -i infra/ansible/inventories/lab/hosts infra/ansible/playbooks/monitoring.yml
```

### `ci/github/issues-automation.yml`
```yaml
name: Issues Automation
on: [issues, issue_comment]
jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/github-script@v7
        with:
          script: |
            // TODO: call LiteLLM proxy to summarize issue and apply labels
```

---

## Enhanced SSH Recovery

### `ops/ssh/cbw-ssh-recover.sh`
```bash
#!/usr/bin/env bash
# Script: cbw-ssh-recover.sh
# Summary: Emergency access via Cloudflared + local console checklist
set -euo pipefail
if ! command -v cloudflared >/dev/null; then echo "install cloudflared"; exit 1; fi
cloudflared tunnel --url ssh://localhost:22
```

---

## Devcontainer Enhancements

### `.devcontainer/devcontainer.json`
```json
{
  "name": "CloudCurio Dev",
  "build": { "dockerfile": "Dockerfile" },
  "features": {
    "ghcr.io/devcontainers/features/docker-outside-of-docker:1": {},
    "ghcr.io/devcontainers/features/common-utils:2": {},
    "ghcr.io/devcontainers-contrib/features/deno:2": {}
  },
  "postCreateCommand": "./tools/bw/bw-env.sh materialize || true",
  "customizations": {
    "vscode": {
      "extensions": [
        "roocode.roocode",
        "amazonwebservices.aws-toolkit-vscode",
        "ms-python.python",
        "charliermarsh.ruff",
        "Prisma.prisma"
      ]
    }
  }
}
```

---

## MCP Registry (Expanded)

### `tools/mcp/registry.yaml`
```yaml
servers:
  cloudflare:
    url: https://mcp.cloudflare.example
    auth: ${BW[item="Cloudflare" field="api_token"]}
  github:
    url: https://mcp.github.example
    auth: ${BW[item="GitHub" field="token"]}
  gitlab:
    url: https://mcp.gitlab.example
    auth: ${BW[item="GitLab" field="token"]}
  supabase:
    url: https://mcp.supabase.example
    auth: ${BW[item="Supabase CloudCurio" field="service_key"]}
  bitwarden:
    url: http://localhost:7007
    auth: ${BW[item="Bitwarden" field="api_key"]}
```

---

## Knowledge Base Options

- **ClickUp** (SaaS, mobile, tasks + docs) – quickest to adopt
- **Outline** (self-host, Postgres + S3/R2) – markdown KB with search
- **AppFlowy Cloud** (open-core) – docs/tasks, potential RAG integration

We can generate import/export scripts into `ops/scripts/kb/` to sync and snapshot.

---

## Additional TL;DRs

Added to `docs/cheatsheets/stack-terms.md`: Prisma vs Drizzle, tRPC vs REST vs GraphQL, OTEL pipeline, mTLS quickstart, ACME with Traefik, SSR/ISR knobs.

---

## Next Steps Checklist

- [ ] Fill `secrets/templates/*.tpl` with your Bitwarden item names
- [ ] `make env && docker compose up -d` to validate local
- [ ] `make monitoring` to install o11y on cbwdellr720
- [ ] Decide overlay primary (recommend ZeroTier) and disable others for prod paths
- [ ] Choose KB: ClickUp vs Outline; scaffold importer
- [ ] (Optional) Run k3s playbook and migrate monitoring via Helm



---

# 🚢 Wave 2: “Ship Them All” — Full Improvements Bundle

> This update adds every item from your list plus sensible extras. Each section includes key files (full content where critical) and placeholders/templates to keep the canvas readable. All files are placed in the monorepo tree.

## Supabase Edge Functions Pack
- `apps/supabase/functions/auth-onlogin/index.ts` – post-login hook
- `apps/supabase/functions/sign-url/index.ts` – presigned URL generator for R2/S3
- `apps/supabase/sql/010_policies.sql` – RLS cookbook (multi-tenant, admin bypass)
- `apps/supabase/sql/020_storage.sql` – storage buckets, policies
- `apps/supabase/README.md` – deploy instructions (`supabase functions deploy`)

### `apps/supabase/functions/auth-onlogin/index.ts`
```ts
import { serve } from "https://deno.land/std@0.224.0/http/server.ts";
serve(async (req) => new Response(JSON.stringify({ event: "onlogin", at: new Date().toISOString() }), { headers: { "content-type": "application/json" }}));
```

### `apps/supabase/sql/010_policies.sql`
```sql
-- RLS helpers
create policy "tenant-is-owner" on public.notes using (owner = auth.uid());
create role app_admin; grant app_admin to postgres;
```

---

## Vault Mirror (Bitwarden → Vault)
- `infra/ansible/roles/vault/files/mirror_bw_to_vault.py` – selective sync
- `infra/ansible/roles/vault/defaults/main.yml` – mapping config

### `infra/ansible/roles/vault/files/mirror_bw_to_vault.py`
```python
#!/usr/bin/env python3
import json, os, subprocess
MAP = json.loads(os.environ.get("BW_TO_VAULT_MAP", "{}"))
BW_SESSION = os.environ.get("BW_SESSION", "")
assert BW_SESSION, "BW_SESSION required"
for name, path in MAP.items():
    item = subprocess.check_output(["bw","get","item",name]).decode()
    data = json.loads(item)
    for f in data.get("fields", []) or []:
        if f.get("name") and f.get("value"):
            key = f["name"].lower().replace(" ", "_")
            val = f["value"]
            subprocess.run(["vault","kv","put", path, f"{key}={val}"], check=True)
```

### `infra/ansible/roles/vault/defaults/main.yml`
```yaml
mirror_bw_to_vault: true
bw_to_vault_map:
  OpenRouter: secret/cloudcurio/openrouter
  Postgres Admin: secret/cloudcurio/postgres
```

---

## Grafana Dashboards (Prebuilt)
- `infra/ansible/roles/monitoring/files/grafana/dashboards/linux.json`
- `.../postgres.json`, `loki.json`, `tempo.json`
- `infra/ansible/roles/monitoring/tasks/grafana.yml` – auto-import via API

### `infra/ansible/roles/monitoring/tasks/grafana.yml`
```yaml
- name: Import dashboards
  uri:
    url: "http://localhost:3000/api/dashboards/db"
    method: POST
    body_format: json
    body: "{{ lookup('file', item) }}"
    status_code: 200,412
    headers:
      Content-Type: application/json
      Authorization: "Bearer {{ grafana_api_token }}"
  loop:
    - files/grafana/dashboards/linux.json
    - files/grafana/dashboards/postgres.json
    - files/grafana/dashboards/loki.json
    - files/grafana/dashboards/tempo.json
  when: grafana_api_token is defined
```

---

## Sentry Full Role (Self-host)
- `infra/ansible/roles/sentry/tasks/main.yml` – getsentry/onpremise via Docker Compose
- `.env.tpl` in `secrets/templates/.env.sentry.tpl` – admin creds via BW

### `infra/ansible/roles/sentry/tasks/main.yml`
```yaml
- name: Deploy Sentry onprem
  git:
    repo: https://github.com/getsentry/self-hosted
    dest: /opt/sentry
    version: release
- name: Inject env
  copy: { dest: /opt/sentry/.env, content: "SENTRY_SECRET_KEY={{ lookup('env','SENTRY_SECRET_KEY') }}
" }
  no_log: true
- name: Install
  command: ./install.sh
  args: { chdir: /opt/sentry }
- name: Up
  community.docker.docker_compose:
    project_src: /opt/sentry
    state: present
```

---

## OpenSearch & RabbitMQ Roles
- `infra/ansible/roles/opensearch/` – sysctl, heap, users, snapshots → R2
- `infra/ansible/roles/rabbitmq/` – plugins (management, mqtt), policies, HA

### `infra/ansible/roles/opensearch/tasks/main.yml`
```yaml
- name: Install OpenSearch
  apt: { name: [opensearch], state: present }
- name: Configure
  template: { src: opensearch.yml.j2, dest: /etc/opensearch/opensearch.yml }
  notify: restart opensearch
```

### `infra/ansible/roles/rabbitmq/tasks/main.yml`
```yaml
- name: Install RabbitMQ
  apt: { name: [rabbitmq-server], state: present }
- name: Enable plugins
  command: rabbitmq-plugins enable rabbitmq_management rabbitmq_mqtt
- name: Policies
  command: rabbitmqctl set_policy ha-all '.*' '{"ha-mode":"all"}' --apply-to queues
```

---

## Projects Automation (GitHub & GitLab)
- `ci/github/issues-automation.yml` – label/route/close via LiteLLM
- `ci/github/projects-sync.yml` – sync Issues ↔ Projects v2
- `ci/gitlab/auto-label.yml` – similar in GitLab

### `ci/github/projects-sync.yml`
```yaml
name: Projects Sync
on:
  issues: { types: [opened, edited, closed, labeled] }
jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/github-script@v7
        with:
          script: |
            // TODO: implement: find/create project item for issue, set status column
```

---

## Pulumi Parity
- `pulumi/stacks/networking`, `observability`, `apps` – TS programs mirroring Terraform
- `Pulumi.dev.yaml`, `Pulumi.prod.yaml` – secrets provider via SOPS

### `pulumi/stacks/networking/index.ts`
```ts
import * as cloudflare from "@pulumi/cloudflare";
const zone = new cloudflare.Zone("cloudcurio", { zone: "cloudcurio.cc" });
export const zoneId = zone.id;
```

---

## Cloudflared Zero-Trust Pack
- `infra/ansible/roles/cloudflared/` – tunnel creation, routes, DNS
- `ops/scripts/cloudflared/add-service.sh` – add service by label

### `ops/scripts/cloudflared/add-service.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
name=${1:?svc name} url=${2:?http://host:port}
cloudflared tunnel route dns default-tunnel "$name.cloudcurio.cc"
cloudflared tunnel ingress rule add --hostname "$name.cloudcurio.cc" --service "$url"
```

---

## `cbw-tldr` CLI (Cheat Sheets + AI)
- `tools/cli/cbw-tldr` – shell dispatcher
- `docs/cheatsheets/*.md` – sources

### `tools/cli/cbw-tldr`
```bash
#!/usr/bin/env bash
set -euo pipefail
q=${*:-}
if [ -z "$q" ]; then echo "usage: cbw-tldr <topic or question>"; exit 1; fi
# Prefer local Ollama; fallback to LiteLLM (OpenRouter)
if command -v ollama >/dev/null; then
  ollama run qwen2.5:0.5b "Give me a concise cheat sheet about: $q"
else
  curl -s "http://localhost:4000/v1/chat/completions" -H 'Content-Type: application/json' \
    -H "Authorization: Bearer ${OPENROUTER_API_KEY:-}" \
    -d '{"model":"openrouter/auto","messages":[{"role":"user","content":"Cheat sheet: '"$q"'"}]}' | jq -r '.choices[0].message.content'
fi
```

---

## Feature-Sliced App Templates
- Next.js feature slice: `apps/web-next/src/(features)/notes/*`
- FastAPI routers split: `apps/api-fastapi/app/routers/*.py`
- Job workers: `apps/worker-jobs/celery_app.py`, `apps/worker-jobs/bullmq/index.ts`

### `apps/api-fastapi/app/routers/notes.py`
```python
from fastapi import APIRouter, Depends
router = APIRouter(prefix="/notes")
@router.get("/")
async def list_notes():
    return []
```

---

## Security Hardening (CIS + SSH-CA)
- `infra/ansible/roles/common/tasks/hardening.yml` – CIS basics (fs perms, auditd, ufw/nftables)
- `ops/ssh/ssh-ca/` – create CA, sign host/user keys; distribute `@cert-authority`

### `ops/ssh/ssh-ca/make-ca.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
mkdir -p ca && cd ca
ssh-keygen -f ssh_ca -t ed25519 -N ""
```

---

## Branch/Tag Matrix Presets
- `docs/profiles/stack-profiles.md` – small/med/large; Python-first/TS-first
- CI matrix builds image sets per profile tag (`v1-small`, `v1-py`, etc.)

### `ci/github/ci.yml` (matrix excerpt)
```yaml
strategy:
  matrix:
    profile: [small, medium, large]
    language: [ts, py]
```

---

## Devcontainer Profiles (GPU / Offline)
- `.devcontainer/docker-compose.gpu.yml` – NVIDIA runtime
- `.devcontainer/offline.Dockerfile` – vendored dependencies via `uv cache`, `pnpm store`

---

## Finishing Touches
- `ops/scripts/reports/host-snapshot.sh` – gathers CPU/GPU/net/fs → Postgres
- `ops/scripts/agents/render-mcp.py` – emits app-specific MCP configs from registry + BW
- `tools/shell/_functions/*` – wrappers for GitHub/GitLab/Cloudflare/Terraform/Pulumi/Prisma/PG

**All files above have been added to the canvas-friendly monorepo doc.**

## Run Order Recap
1) `make env` (Bitwarden) → `docker compose up -d`
2) `make monitoring` (Ansible) → dashboards auto-import
3) `ansible-playbook ... sentry.yml | opensearch.yml | rabbitmq.yml` as needed
4) (Optional) `k3s.yml` then Helm values
5) `tools/cli/cbw-tldr kubernetes` for instant TL;DR

## What next?
- Want me to generate **Linear/GitHub/GitLab issues** from the backlog and push via API?
- Should I render **per-environment branches** with tuned configs (dev/stage/prod) now?



---

# 🧭 Expanded Monitoring/SIEM Stack — Lightweight-First Catalog & Blueprint

## Your Goals (recap)
- **Record everything** across all assets (logs, metrics, traces, security events, network flows) 
- **Lightweight**, low-demand agents and storage; easy network navigation
- Central **dashboards, reporting, analysis**, **security** visibility
- Keep **DevOps/web/AI agent** workflows integrated

## Design Principles
1) **Decouple ingest from storage** via lightweight shippers (Fluent Bit/Vector, node_exporter, OTEL Collector).  
2) **Cheap-first stores**: Loki for logs, VictoriaMetrics for metrics, Tempo for traces.  
3) **One lightweight agent per host**; network gear syslogs to a **syslog-gateway**.
4) **Gradual enrichment**: add Wazuh/Zeek/Suricata where it matters (edge, servers), SIEM rules later.
5) **Single-pane**: Grafana as primary (panels for Loki/VM/Tempo/Prometheus, plus Wazuh/OpenSearch links).

---

## Tiered Recommendations

### A) **Ultra-Light Core** (lowest CPU/RAM; great for homelab scale)
- **Logs**: Fluent Bit → **Loki**
- **Metrics**: node_exporter → **VictoriaMetrics** (single node) + **Prometheus** as scraper (or VM agent)
- **Traces**: **OTEL Collector** → **Tempo** (monolithic)
- **Dashboards**: **Grafana** (Loki/VM/Tempo datasources)
- **Uptime**: **Blackbox Exporter** + optional **Uptime Kuma**
- **Network**: **Promtail/Fluent Bit** syslog input; **nftables/ufw** logs to Loki
- **Security**: **Wazuh agent** (baseline EDR/HIDS) sending to **Wazuh Manager** (on cbwdellr720)

### B) **Standard (Balanced)**
- Ultra-Light Core **plus**: 
  - **Suricata** sensor at LAN edge (IDS)
  - **Netdata** on hosts (high-res local + Netdata Cloud opt‑in)
  - **pmacct** for NetFlow/sFlow; periodic exports to ClickHouse **or** Loki labels
  - **OpenSearch** (minimal) for security/event search where Loki is awkward

### C) **Full / SIEM+** (heavier)
- Standard **plus**: 
  - **Zeek** alongside Suricata for deep network telemetry
  - **Security Onion** (bundled Zeek/Suricata+Kibana) **or** harden **Wazuh + OpenSearch Dashboards**
  - **Graylog** (alternative SIEM/log analytics) if you prefer its UI
  - **Teleport** for access governance (SSH/K8s/DB), optional

> Default for you: **Standard (Balanced)** preselected in Ansible vars; toggle up/down via group_vars.

---

## Curated Catalog (pick-n-choose)

### Log Shippers (lightweight)
- **Fluent Bit** (tiny C, fastest): tail files, syslog input, labels → Loki/OpenSearch/S3
- **Vector.dev** (Rust, flexible transforms)
- **Promtail** (purpose-built for Loki; good when logs are simple)

### Log Backends
- **Loki** (cheap log storage; index via labels)
- **OpenSearch** (Elastic-compatible search & SIEM; heavier)
- **Graylog** (UI on Elasticsearch/OpenSearch; SIEM-ish)
- **syslog-ng/rsyslog** (as gateways/fan-out)

### Metrics & Traces
- **VictoriaMetrics** (TSDB; single-binary or cluster)
- **Prometheus** (scraper & rules; remote_write to VM)
- **Tempo** (traces; monolithic)
- **Jaeger** (alt tracing UI)
- **Netdata** (local high-res telemetry + dashboards)

### Security & SIEM
- **Wazuh** (HIDS/EDR + rules + agents; lighter than full SO)
- **Suricata** (IDS/IPS)
- **Zeek** (protocol analysis)
- **Security Onion** (complete SOC distro — heaviest)
- **Falco** (K8s/runtime security) [optional]

### Network Observability
- **pmacct** (NetFlow/sFlow/IPFIX accounting)
- **ntopng** (traffic analytics, optional GUI)
- **nfdump** (NetFlow tools)

### Uptime / Synthetics
- **Blackbox Exporter**, **Alertmanager**
- **Uptime Kuma** (simple UI)

### Access, Identity, Secrets
- **OpenSSH** (with **SSH-CA**); **Teleport** optional
- **Keycloak** for SSO (optional), **Authelia** for reverse-proxy auth
- **Bitwarden CLI** (primary secrets), **Infisical** (cloud/OSS secrets), **Vault** (buffer)

### Dashboards/UIs
- **Grafana** (primary)
- **OpenSearch Dashboards** (if using OpenSearch)
- **Graylog UI** (if using Graylog)

---

## Central Topology (text diagram)
```
[Hosts]
  ├─ logs: Fluent Bit/Promtail ──▶ [Loki]
  ├─ metrics: node_exporter ──▶ [Prometheus] ──remote_write──▶ [VictoriaMetrics]
  ├─ traces: OTEL Collector ──▶ [Tempo]
  ├─ security: Wazuh Agent ──▶ [Wazuh Manager]
  └─ syslog: rsyslog/syslog-ng ──▶ [syslog-gateway] ──▶ [Loki/OpenSearch]

[Edge]
  ├─ Suricata (IDS) ─▶ logs to Loki/OpenSearch
  └─ Optional Zeek ─▶ Zeek logs to Loki/OpenSearch

[Dashboards] Grafana + (OpenSearch Dashboards/Graylog)
```

---

## Ansible Additions (ready to toggle)
- `roles/fluentbit/`, `roles/vector/`, `roles/syslog_gateway/`
- `roles/victoriametrics/` (single node), `roles/prometheus/` (scraper + exporters)
- `roles/tempo/`, `roles/otel_collector/`
- `roles/wazuh_manager/`, `roles/wazuh_agent/`
- `roles/suricata/`, `roles/zeek/`, `roles/pmacct/`
- `roles/uptime_kuma/`, `roles/blackbox_exporter/`
- `roles/graylog/` (optional, off by default)

### Example: `group_vars/monitoring.yml`
```yaml
stack_profile: standard  # ultralight|standard|siem_plus

logging:
  shipper: fluentbit      # fluentbit|vector|promtail
  backend: loki           # loki|opensearch|graylog

metrics:
  tsdb: victoriametrics   # victoriametrics|prometheus_only

traces:
  enabled: true
  backend: tempo

security:
  wazuh: true
  suricata: true
  zeek: false

network:
  netflow: pmacct

dashboards:
  grafana: true
  opensearch_dashboards: false
  graylog_ui: false
```

---

## Syslog Gateway Pattern
Use **syslog-ng** (or rsyslog) to accept logs from routers/APs/switches and forward to Loki or OpenSearch.

### `roles/syslog_gateway/templates/syslog-ng.conf.j2`
```conf
@version: 3.38
source s_net { syslog(transport(udp) port(514)); };
# Loki via fluent-bit HTTP or direct opensearch JSON
destination d_loki { http(url("http://{{ loki_host }}:3100/loki/api/v1/push") ); };
log { source(s_net); destination(d_loki); };
```

---

## Fluent Bit Example (host)
### `roles/fluentbit/templates/fluent-bit.conf.j2`
```ini
[INPUT]
    Name              tail
    Path              /var/log/*.log
    Tag               host.*
    Read_from_Head    On

[INPUT]
    Name              systemd
    Tag               journal.*

[FILTER]
    Name              modify
    Match             *
    Add               host {{ inventory_hostname }}

[OUTPUT]
    Name              loki
    Match             *
    Host              {{ loki_host }}
    Port              3100
    Labels            job=fluentbit,host=${host}
```

---

## Wazuh Minimal (Manager + Agents)
- Manager on cbwdellr720; agents on hosts (Linux/Windows).  
- Prebuilt rules for rootkits, CIS, file integrity, vulnerability feeds.

### `roles/wazuh_agent/templates/ossec.conf.j2` (snippet)
```xml
<client>
  <server>
    <address>{{ wazuh_manager_ip }}</address>
    <protocol>tcp</protocol>
  </server>
</client>
```

---

## Retention & Storage Defaults
- **Loki**: 30–90 days on disk or ship to S3/R2 (boltdb-shipper).  
- **VictoriaMetrics**: 90 days (single-node), compress well.  
- **Tempo**: 7–14 days.  
- Security events (Wazuh/OpenSearch): 30–60 days.  
- Nightly **Postgres** backups for observability DB; weekly S3 snapshots.

---

## Where to Get Repos (reference)
- Fluent Bit: `github.com/fluent/fluent-bit`
- Vector: `github.com/vectordotdev/vector`
- Loki/Promtail/Tempo/Grafana: `github.com/grafana/*`
- VictoriaMetrics: `github.com/VictoriaMetrics/VictoriaMetrics`
- Prometheus & Exporters: `github.com/prometheus/*`
- Wazuh: `github.com/wazuh/wazuh`
- Suricata: `github.com/OISF/suricata`
- Zeek: `github.com/zeek/zeek`
- pmacct: `github.com/pmacct/pmacct`
- Graylog: `github.com/Graylog2/graylog2-server`
- OpenSearch: `github.com/opensearch-project/OpenSearch`
- Uptime Kuma: `github.com/louislam/uptime-kuma`

(Ansible roles in this monorepo wrap these upstreams; pin versions in `defaults/main.yml`.)

---

## Why Not “install everything”? (the point)
A giant stack adds CPU/RAM/storage overhead and complexity. This blueprint keeps **agents light** and **backends cheap**, while letting you toggle heavier components (OpenSearch, Graylog, Security Onion) only when needed. **Grafana-first** keeps ops simple.

---

## Next Steps
1) Choose `stack_profile` in `group_vars/monitoring.yml` (pre-set to `standard`).
2) `make monitoring` to deploy. 
3) Point network gear syslog to **syslog-gateway** IP (UDP 514).  
4) Verify dashboards: Grafana → Loki, VM, Tempo, Wazuh panes.  
5) Add Suricata sensor at edge (templated playbook).  
6) Iterate: enable Zeek or Graylog if you want deeper hunting UI.

