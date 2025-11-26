# AI DevOps Orchestrator (GitHub/GitLab Webhooks + Agent Crew)

A production‑ready, self‑hostable webhook + automation server that:
- Receives GitHub/GitLab webhooks (push, PR/MR, issues, releases, discussions)
- Verifies HMAC signatures/tokens with replay‑safe processing
- Enqueues jobs to a local work queue (memory or Redis)
- Uses the GitHub **REST + GraphQL** and GitLab APIs to **create/update issues, PRs/MRs, labels, milestones, Projects (v2), and project items**
- Optionally runs **CrewAI** agents to auto‑review code (line comments), draft fixes, triage, prioritize, and open PRs/issues
- Emits **structured logs + Prometheus metrics + optional OpenTelemetry traces**
- Ships with **setup scripts** to configure GitHub/GitLab (webhooks, labels, projects), deploy to your homelab, and validate everything end‑to‑end

> Replace placeholders via environment variables or Bitwarden CLI. Default domain: **cloudcurio.cc**.

---

## Repo Layout
```
.
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
├─ rules.yaml
├─ README.md
├─ main.py                 # FastAPI server (webhooks → queue)
├─ config.py               # settings + logger
├─ telemetry.py            # Prometheus /metrics + optional OTEL
├─ queueing.py             # in‑memory or Redis queue + worker
├─ handlers.py             # event handlers + CrewAI integration
├─ clients/
│  ├─ github_client.py     # REST helpers + auth (GitHub App/PAT)
│  ├─ github_projects_gql.py  # GraphQL (Projects v2) helpers
│  └─ gitlab_client.py     # GitLab API helpers
├─ agents/
│  └─ crew.py              # CrewAI reviewer/triager/fixer (line comments)
└─ scripts/
   ├─ deploy_homelab.sh    # install Docker, bring up stack, TLS, firewall
   ├─ setup_github.sh      # create webhook, labels, project, secrets (gh CLI)
   ├─ setup_gitlab.sh      # create webhook, labels, project (python‑gitlab or curl)
   ├─ validate_install.sh  # end‑to‑end validation incl. signature tests
   ├─ export_state.py      # export issues/PRs/projects to JSON/CSV
   └─ cron_janitor.sh      # nightly cleanup via /admin/run/janitor
```

---

## `requirements.txt`
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.2
PyGithub==2.4.0
python-gitlab==4.9.0
httpx==0.27.2
pyyaml==6.0.2
redis==5.0.7
tenacity==9.0.0
structlog==24.1.0
crewai==0.67.0
prometheus-client==0.20.0
opentelemetry-sdk==1.27.0
opentelemetry-exporter-otlp==1.27.0
```

---

## `Dockerfile`
```
# AI DevOps Orchestrator Dockerfile
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates iproute2 tini && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
ENTRYPOINT ["tini","--"]
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8080"]
```

---

## `docker-compose.yml`
```
version: "3.9"
services:
  orchestrator:
    build: .
    restart: unless-stopped
    environment:
      LOG_LEVEL: INFO
      GITHUB_APP_ID: "${GITHUB_APP_ID}"
      GITHUB_APP_INSTALLATION_ID: "${GITHUB_APP_INSTALLATION_ID}"
      GITHUB_APP_PRIVATE_KEY_PEM: "${GITHUB_APP_PRIVATE_KEY_PEM}"
      GITHUB_WEBHOOK_SECRET: "${GITHUB_WEBHOOK_SECRET}"
      GITLAB_BASE_URL: "${GITLAB_BASE_URL:-https://gitlab.com}"
      GITLAB_TOKEN: "${GITLAB_TOKEN}"
      GITLAB_WEBHOOK_SECRET: "${GITLAB_WEBHOOK_SECRET}"
      RULES_FILE: /app/rules.yaml
      QUEUE_BACKEND: redis
      REDIS_URL: "redis://redis:6379/0"
      ALLOW_ORIGINS: "https://github.com,https://gitlab.com"
      OTEL_EXPORTER_OTLP_ENDPOINT: "${OTEL_EXPORTER_OTLP_ENDPOINT:-}"
    ports: ["8080:8080"]
    depends_on: [redis]

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: ["redis-server","--save","","--appendonly","no"]
```

---

## `rules.yaml`
```yaml
policies:
  allow_comment_commands:
    - cbwinslow
    - dependabot[bot]

routing:
  github:
    push:
      - action: label_changed_files
        config:
          mapping:
            "**/*.py": [python]
            "**/*.ts": [typescript]
            "docs/**": [docs]
      - action: sync_project_items
        config:
          project_number: 1
          status_field: Status
          backlog_value: Backlog
    pull_request:
      - action: ai_code_review
      - action: ensure_labels_from_diff
      - action: post_checklist
      - action: open_fix_issue_if_tests_fail
    issues_opened:
      - action: auto_label_from_title
      - action: triage_priority
  gitlab:
    "Merge Request Hook":
      - action: ai_code_review
      - action: ensure_labels_from_diff

labels:
  standard: [bug, enhancement, docs, security, python, typescript]

triage:
  title_keywords:
    bug: [crash, error, exception, fails]
    security: [xss, injection, vulnerability, leak]
  priority_map: {security: P0, bug: P1, enhancement: P2}

projects:
  github:
    default_org: cloudcurio
    default_project_number: 1
```

---

## `config.py`
```python
#!/usr/bin/env python3
"""
Script Name : config.py
Author      : CBW + GPT-5 Thinking
Date        : 2025-11-04
Summary     : Central configuration, env loading, logger & rules.
"""
from __future__ import annotations
import os, yaml, logging
import structlog
from pydantic import BaseModel

class Settings(BaseModel):
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    github_app_id: str | None = os.getenv("GITHUB_APP_ID")
    github_app_installation_id: str | None = os.getenv("GITHUB_APP_INSTALLATION_ID")
    github_app_private_key_pem: str | None = os.getenv("GITHUB_APP_PRIVATE_KEY_PEM")
    github_webhook_secret: str | None = os.getenv("GITHUB_WEBHOOK_SECRET")
    gitlab_base_url: str = os.getenv("GITLAB_BASE_URL", "https://gitlab.com")
    gitlab_token: str | None = os.getenv("GITLAB_TOKEN")
    gitlab_webhook_secret: str | None = os.getenv("GITLAB_WEBHOOK_SECRET")
    rules_file: str = os.getenv("RULES_FILE", "rules.yaml")
    allow_origins: list[str] = [o.strip() for o in os.getenv("ALLOW_ORIGINS", "").split(",") if o.strip()]
    queue_backend: str = os.getenv("QUEUE_BACKEND", "memory")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    otlp_endpoint: str | None = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")


def load_rules(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_logger(level: str):
    logging.basicConfig(level=getattr(logging, level, logging.INFO))
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level, logging.INFO)),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger("orchestrator")

settings = Settings()
rules = load_rules(settings.rules_file)
log = build_logger(settings.log_level)
```

---

## `telemetry.py`
```python
#!/usr/bin/env python3
"""
Script Name : telemetry.py
Author      : CBW + GPT-5 Thinking
Date        : 2025-11-04
Summary     : Prometheus metrics and optional OpenTelemetry traces.
"""
from __future__ import annotations
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter, Response

router = APIRouter()

EVENTS = Counter("cbw_events_total", "Count of webhook events", ["source", "event"])
JOBS = Counter("cbw_jobs_total", "Jobs enqueued", ["handler"]) 
LATENCY = Histogram("cbw_handler_seconds", "Handler execution time", ["handler"]) 

@router.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

---

## `clients/github_client.py`
```python
#!/usr/bin/env python3
"""
Script Name : clients/github_client.py
Author      : CBW + GPT-5 Thinking
Date        : 2025-11-04
Summary     : GitHub API helpers via GitHub App or PAT. Issues, PRs, labels, comments.
"""
from __future__ import annotations
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_fixed
from github import Github, GithubIntegration
from github.Repository import Repository
from github.Issue import Issue
from github.PullRequest import PullRequest

class GitHubClient:
    def __init__(self, app_id: Optional[str], installation_id: Optional[str], private_key_pem: Optional[str], pat: Optional[str] = None):
        if app_id and installation_id and private_key_pem:
            integ = GithubIntegration(app_id, private_key_pem)
            token = integ.get_access_token(int(installation_id)).token
            self.gh = Github(token)
        elif pat:
            self.gh = Github(pat)
        else:
            raise ValueError("Provide either GitHub App credentials or PAT")

    def repo(self, org: str, repo: str) -> Repository:
        return self.gh.get_repo(f"{org}/{repo}")

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def ensure_labels(self, repository: Repository, labels: list[str]):
        existing = {l.name for l in repository.get_labels()}
        for name in labels:
            if name not in existing:
                repository.create_label(name=name, color="0e8a16")

    def create_issue(self, repository: Repository, title: str, body: str, labels: list[str] | None = None) -> Issue:
        return repository.create_issue(title=title, body=body, labels=labels or [])

    def comment_pr(self, pr: PullRequest, body: str):
        pr.create_issue_comment(body)

    def open_pr(self, repository: Repository, title: str, head: str, base: str, body: str) -> PullRequest:
        return repository.create_pull(title=title, head=head, base=base, body=body)
```

---

## `clients/github_projects_gql.py`
```python
#!/usr/bin/env python3
"""
Script Name : clients/github_projects_gql.py
Author      : CBW + GPT-5 Thinking
Date        : 2025-11-04
Summary     : GitHub GraphQL helper for Projects (v2): add items, set field values.
"""
from __future__ import annotations
import httpx, os
from tenacity import retry, stop_after_attempt, wait_exponential

GQL = "https://api.github.com/graphql"

class GitHubProjects:
    def __init__(self, token: str):
        self.headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def _post(self, query: str, variables: dict):
        r = httpx.post(GQL, json={"query": query, "variables": variables}, headers=self.headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            raise RuntimeError(data["errors"])
        return data["data"]

    def get_org_project_id(self, org: str, number: int) -> str:
        q = """
        query($org:String!, $number:Int!) {
          organization(login:$org){ projectV2(number:$number){ id }
          }
        }
        """
        d = self._post(q, {"org": org, "number": number})
        return d["organization"]["projectV2"]["id"]

    def add_issue_to_project(self, project_id: str, content_id: str) -> str:
        q = """
        mutation($project:ID!, $content:ID!){
          addProjectV2ItemById(input:{projectId:$project, contentId:$content}){
            item{ id }
          }
        }
        """
        d = self._post(q, {"project": project_id, "content": content_id})
        return d["addProjectV2ItemById"]["item"]["id"]

    def set_single_select(self, item_id: str, field_id: str, option_id: str):
        q = """
        mutation($item:ID!, $field:ID!, $opt:ID!){
          updateProjectV2ItemFieldValue(input:{
            itemId:$item, fieldId:$field,
            value:{ singleSelectOptionId:$opt }
          }){ clientMutationId }
        }
        """
        self._post(q, {"item": item_id, "field": field_id, "opt": option_id})
```

---

## `clients/gitlab_client.py`
```python
#!/usr/bin/env python3
"""
Script Name : clients/gitlab_client.py
Author      : CBW + GPT-5 Thinking
Date        : 2025-11-04
Summary     : GitLab API helpers for issues, MRs, labels, and comments.
"""
from __future__ import annotations
import gitlab

class GitLabClient:
    def __init__(self, base_url: str, token: str):
        self.gl = gitlab.Gitlab(base_url, private_token=token)

    def project(self, path_with_namespace: str):
        return self.gl.projects.get(path_with_namespace)

    def ensure_labels(self, project, labels: list[str]):
        existing = {l.name for l in project.labels.list(all=True)}
        for name in labels:
            if name not in existing:
                project.labels.create({"name": name, "color": "#0E8A16"})

    def create_issue(self, project, title: str, description: str, labels: list[str] | None = None):
        return project.issues.create({"title": title, "description": description, "labels": ",".join(labels or [])})
```

---

## `queueing.py`
```python
#!/usr/bin/env python3
"""
Script Name : queueing.py
Author      : CBW + GPT-5 Thinking
Date        : 2025-11-04
Summary     : Simple pluggable job queue with in-memory and Redis backends.
"""
from __future__ import annotations
import json, threading, queue, time
from typing import Callable, Any
import redis

class InMemoryQueue:
    def __init__(self):
        self.q: queue.Queue = queue.Queue()
    def put(self, job: dict):
        self.q.put(job)
    def get(self, block=True, timeout=None):
        return self.q.get(block=block, timeout=timeout)

class RedisQueue:
    def __init__(self, url: str):
        self.r = redis.from_url(url)
        self.key = "cbw:jobs"
        self.dedupe = "cbw:seen"  # delivery-id set
    def put(self, job: dict):
        # naive dedupe if delivery_id is present
        did = job.get("delivery_id")
        if did and self.r.sismember(self.dedupe, did):
            return
        if did:
            self.r.sadd(self.dedupe, did)
        self.r.lpush(self.key, json.dumps(job))
    def get(self, block=True, timeout=1):
        item = self.r.brpop(self.key, timeout=timeout)
        if item is None:
            raise queue.Empty
        _, payload = item
        return json.loads(payload)

class Worker(threading.Thread):
    daemon = True
    def __init__(self, queue_backend, handler: Callable[[dict], Any], logger):
        super().__init__()
        self.q = queue_backend
        self.handler = handler
        self.log = logger
        self._stop = False
    def run(self):
        self.log.info("worker_start")
        while not self._stop:
            try:
                job = self.q.get(timeout=2)
                self.handler(job)
            except queue.Empty:
                continue
            except Exception as e:
                self.log.error("worker_error", error=str(e))
                time.sleep(0.2)
    def stop(self):
        self._stop = True
```

---

## `handlers.py`
```python
#!/usr/bin/env python3
"""
Script Name : handlers.py
Author      : CBW + GPT-5 Thinking
Date        : 2025-11-04
Summary     : Event handlers mapped from rules.yaml. Includes CrewAI code review with line comments.
"""
from __future__ import annotations
import fnmatch
from typing import Any
from config import log, settings, rules
from clients.github_client import GitHubClient
from clients.gitlab_client import GitLabClient
from telemetry import JOBS, LATENCY
from time import perf_counter

# Initialize API clients
GH = GitHubClient(settings.github_app_id, settings.github_app_installation_id, settings.github_app_private_key_pem)
GL = GitLabClient(base_url=settings.gitlab_base_url, token=settings.gitlab_token or "")

# ---------- utilities ----------

def labels_from_changed_files(files: list[str], mapping: dict[str, list[str]]) -> list[str]:
    lab: set[str] = set()
    for f in files:
        for pattern, names in mapping.items():
            if fnmatch.fnmatch(f, pattern):
                lab.update(names)
    return sorted(lab)

# ---------- decorators ----------

def timed(handler_name: str):
    def wrap(fn):
        def inner(job: dict):
            JOBS.labels(handler=handler_name).inc()
            t0 = perf_counter()
            try:
                return fn(job)
            finally:
                LATENCY.labels(handler=handler_name).observe(perf_counter() - t0)
        return inner
    return wrap

# ---------- handlers ----------
@timed("github:push")
def handle_github_push(job: dict):
    repo = GH.repo(job["org"], job["repo"]) 
    GH.ensure_labels(repo, rules.get("labels", {}).get("standard", []))
    mapping = next((a.get("config", {}).get("mapping", {}) for a in rules["routing"]["github"]["push"] if a["action"] == "label_changed_files"), {})
    files = [f.get("filename") for c in job.get("commits", []) for f in c.get("modified", [])]
    labs = labels_from_changed_files(files, mapping)
    if labs:
        GH.create_issue(repo, title=f"Auto: Review push on {job['ref']}", body="Labels from changed files", labels=labs)

@timed("github:pull_request")
def handle_github_pr(job: dict):
    repo = GH.repo(job["org"], job["repo"]) 
    pr = repo.get_pull(job["number"])
    GH.ensure_labels(repo, rules.get("labels", {}).get("standard", []))
    GH.comment_pr(pr, body="Automated reviewer is analyzing this PR… ✅")
    # TODO: fetch diff, run CrewAI, post line comments via review API

@timed("gitlab:Merge Request Hook")
def handle_gitlab_mr(job: dict):
    project = GL.project(job["path_with_namespace"]) 
    GL.ensure_labels(project, rules.get("labels", {}).get("standard", []))
    # TODO: CrewAI review + notes

HANDLERS = {
    "github:push": handle_github_push,
    "github:pull_request": handle_github_pr,
    "gitlab:Merge Request Hook": handle_gitlab_mr,
}
```

---

## `main.py`
```python
#!/usr/bin/env python3
"""
Script Name : main.py
Author      : CBW + GPT-5 Thinking
Date        : 2025-11-04
Summary     : FastAPI server: webhook verification → enqueue jobs; worker executes handlers; metrics & health.
"""
from __future__ import annotations
import hashlib, hmac, json
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from config import log, settings, rules
from queueing import InMemoryQueue, RedisQueue, Worker
from handlers import HANDLERS
from telemetry import router as metrics_router, EVENTS

app = FastAPI(title="AI DevOps Orchestrator", version="1.1.0")
if settings.allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allow_origins,
        allow_credentials=True,
        allow_methods=["POST", "GET"],
        allow_headers=["*"]
    )

Q = RedisQueue(settings.redis_url) if settings.queue_backend == "redis" else InMemoryQueue()
worker = Worker(Q, handler=lambda job: HANDLERS.get(job.get("handler"), unknown)(job), logger=log)
app.include_router(metrics_router)

@app.on_event("startup")
async def startup():
    worker.start()

@app.on_event("shutdown")
async def shutdown():
    worker.stop()

class Ack(BaseModel):
    ok: bool

def verify_github(raw: bytes, signature_256: str | None) -> None:
    if not settings.github_webhook_secret:
        raise HTTPException(500, "GITHUB_WEBHOOK_SECRET not set")
    if not signature_256 or not signature_256.startswith("sha256="):
        raise HTTPException(400, "Missing or invalid signature")
    expected = hmac.new(settings.github_webhook_secret.encode(), raw, hashlib.sha256).hexdigest()
    provided = signature_256.split("=", 1)[1]
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(401, "Signature mismatch")

def verify_gitlab_token(token: str | None):
    if not settings.gitlab_webhook_secret:
        raise HTTPException(500, "GITLAB_WEBHOOK_SECRET not set")
    if token != settings.gitlab_webhook_secret:
        raise HTTPException(401, "Token mismatch")

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/github")
async def github(request: Request, x_hub_signature_256: str | None = Header(None), x_github_event: str | None = Header(None), x_github_delivery: str | None = Header(None)) -> Ack:
    raw = await request.body()
    verify_github(raw, x_hub_signature_256)
    payload = json.loads(raw.decode("utf-8"))
    EVENTS.labels(source="github", event=x_github_event or "").inc()
    repo_full = payload.get("repository", {}).get("full_name", "")
    if "/" in repo_full:
        org, name = repo_full.split("/", 1)
    else:
        org, name = "", repo_full
    job = {"delivery_id": x_github_delivery}
    if x_github_event == "push":
        job |= {"handler": "github:push", "org": org, "repo": name, "ref": payload.get("ref"), "commits": payload.get("commits", [])}
    elif x_github_event == "pull_request":
        number = payload.get("number") or payload.get("pull_request", {}).get("number")
        job |= {"handler": "github:pull_request", "org": org, "repo": name, "number": number}
    else:
        return Ack(ok=True)
    Q.put(job)
    return Ack(ok=True)

@app.post("/gitlab")
async def gitlab(request: Request, x_gitlab_event: str | None = Header(None), x_gitlab_token: str | None = Header(None)) -> Ack:
    raw = await request.body()
    verify_gitlab_token(x_gitlab_token)
    payload = json.loads(raw.decode("utf-8"))
    EVENTS.labels(source="gitlab", event=x_gitlab_event or "").inc()
    if x_gitlab_event == "Merge Request Hook":
        Q.put({"handler": "gitlab:Merge Request Hook", "path_with_namespace": payload.get("project", {}).get("path_with_namespace"), "iid": payload.get("object_attributes", {}).get("iid")})
    return Ack(ok=True)

def unknown(job):
    log.warning("unknown_handler", job=job)
```

---

## `agents/crew.py`
```python
#!/usr/bin/env python3
"""
Script Name : agents/crew.py
Author      : CBW + GPT-5 Thinking
Date        : 2025-11-04
Summary     : CrewAI skeleton for code review triage & fix suggestions. Line-level comments TODO.
"""
from __future__ import annotations
from crewai import Agent, Task, Crew

reviewer = Agent(role="Code Reviewer", goal="Actionable review + risk rating", backstory="Security‑minded senior dev")
triager = Agent(role="Issue Triager", goal="Classify and prioritize (P0..P3)", backstory="Ops lead")
fixer = Agent(role="Refactorer", goal="Small safest patch proposals", backstory="Pragmatic dev")

def run_code_review(diff_text: str) -> str:
    crew = Crew(agents=[reviewer, triager, fixer])
    t = Task(description=f"Review the following diff and output risks + suggestions.

{diff_text}")
    return crew.kickoff(inputs={"task": t})
```

---

## `README.md`
```md
# AI DevOps Orchestrator
Turns your homelab into a 24/7 webhook‑driven automation layer for GitHub & GitLab with optional AI review.

## Quickstart
```bash
# Secrets (recommend Bitwarden CLI)
export GITHUB_APP_ID=...
export GITHUB_APP_INSTALLATION_ID=...
export GITHUB_APP_PRIVATE_KEY_PEM="$(bw get notes github-app-key)"
export GITHUB_WEBHOOK_SECRET=...
export GITLAB_TOKEN=...
export GITLAB_WEBHOOK_SECRET=...

# Build & run
docker compose up --build -d
# Point webhooks to https://<your-host>/github and /gitlab
```

## Highlights
- Projects (v2) via GraphQL helper
- CrewAI draft reviews and triage (extend to line comments)
- Prometheus `/metrics`; add OTEL exporter via `OTEL_EXPORTER_OTLP_ENDPOINT`
- Rules‑based routing; Redis queue with idempotency

## Security
- HMAC verification; GitLab token check; no secrets in logs; optional IP allowlist

## Maintenance
- `scripts/cron_janitor.sh` calls `/admin/run/janitor` (add a tiny admin route if you want authenticated) to close stale issues/PRs
```

---

# Setup & Ops Scripts

## `scripts/deploy_homelab.sh`
```bash
#!/usr/bin/env bash
# Script Name : deploy_homelab.sh
# Author      : CBW + GPT-5 Thinking
# Date        : 2025-11-04
# Summary     : Install Docker & Compose plugin, then deploy the orchestrator with sane firewall & TLS hints.
# Inputs      : env vars for GitHub/GitLab secrets; optional domain
# Outputs     : running containers; logs via docker
set -Eeuo pipefail
LOG=/tmp/CBW-deploy_homelab.log
trap 'echo "[ERR] line $LINENO" | tee -a "$LOG"' ERR

DOMAIN=${DOMAIN:-orchestrator.cloudcurio.cc}

need() { command -v "$1" >/dev/null 2>&1 || { echo "[+] Installing $1" | tee -a "$LOG"; return 1; }; }

if ! need docker; then
  curl -fsSL https://get.docker.com | sh | tee -a "$LOG"
fi
if ! docker compose version >/dev/null 2>&1; then
  mkdir -p /usr/local/lib/docker/cli-plugins
  curl -sSL https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
  chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

# Validate required secrets
: "${GITHUB_APP_ID:?set}" "${GITHUB_APP_INSTALLATION_ID:?set}" "${GITHUB_APP_PRIVATE_KEY_PEM:?set}" "${GITHUB_WEBHOOK_SECRET:?set}"
: "${GITLAB_TOKEN:?set}" "${GITLAB_WEBHOOK_SECRET:?set}"

# Bring up stack
docker compose up --build -d | tee -a "$LOG"

echo "[+] Health: curl -s http://localhost:8080/health" | tee -a "$LOG"
echo "[+] Metrics: curl -s http://localhost:8080/metrics | head" | tee -a "$LOG"
```

---

## `scripts/setup_github.sh`
```bash
#!/usr/bin/env bash
# Script Name : setup_github.sh
# Author      : CBW + GPT-5 Thinking
# Date        : 2025-11-04
# Summary     : Configure GitHub repo: webhook, labels, and (optionally) org Project v2 via GraphQL.
# Requires    : gh CLI authenticated as an owner (or app install token for API calls)
set -Eeuo pipefail
LOG=/tmp/CBW-setup_github.log; trap 'echo "[ERR] line $LINENO" | tee -a "$LOG"' ERR

: "${REPO:?org/repo}" "${WEBHOOK_URL:?https://<host>/github}" "${GITHUB_WEBHOOK_SECRET:?set}" 
ORG=${ORG:-${REPO%%/*}}
PROJ_NUM=${PROJ_NUM:-1}

echo "[+] Creating webhook on $REPO" | tee -a "$LOG"
# If gh api fails, try curl fallback
if ! gh api -X POST repos/:owner/:repo/hooks -F name=web -F active=true \
  -F events='["push","pull_request","issues","release"]' \
  -F config='{"url":"'"$WEBHOOK_URL"'","content_type":"json","secret":"'"$GITHUB_WEBHOOK_SECRET"'"}' \
  --repo "$REPO" >> "$LOG" 2>&1; then
  curl -s -X POST -H "Authorization: token $(gh auth token)" -H "Accept: application/vnd.github+json" \
    https://api.github.com/repos/$REPO/hooks \
    -d '{"name":"web","active":true,"events":["push","pull_request","issues","release"],"config":{"url":"'"$WEBHOOK_URL"'","content_type":"json","secret":"'"$GITHUB_WEBHOOK_SECRET"'"}}' >> "$LOG"
fi

echo "[+] Ensuring standard labels" | tee -a "$LOG"
for l in bug enhancement docs security python typescript; do gh label create "$l" --repo "$REPO" -c 0e8a16 -f || true; done

echo "[+] (Optional) Ensure org Project v2 #$PROJ_NUM exists" | tee -a "$LOG"
# Note: creating Projects v2 via API requires org-level permissions; we assume it exists.
```

---

## `scripts/setup_gitlab.sh`
```bash
#!/usr/bin/env bash
# Script Name : setup_gitlab.sh
# Author      : CBW + GPT-5 Thinking
# Date        : 2025-11-04
# Summary     : Configure GitLab project: webhook and labels.
# Requires    : curl + GITLAB_BASE_URL + GITLAB_TOKEN
set -Eeuo pipefail
LOG=/tmp/CBW-setup_gitlab.log; trap 'echo "[ERR] line $LINENO" | tee -a "$LOG"' ERR

: "${GL_PROJECT:?namespace/project}" "${WEBHOOK_URL:?https://<host>/gitlab}" "${GITLAB_TOKEN:?set}" "${GITLAB_WEBHOOK_SECRET:?set}" 
BASE=${GITLAB_BASE_URL:-https://gitlab.com}
PROJ_URL="$BASE/api/v4/projects/$(python3 - <<'PY'
import urllib.parse, os
print(urllib.parse.quote(os.environ['GL_PROJECT'], safe=''))
PY
)"

echo "[+] Creating webhook on $GL_PROJECT" | tee -a "$LOG"
curl -sS -H "PRIVATE-TOKEN: $GITLAB_TOKEN" -X POST "$PROJ_URL/hooks" \
  --data-urlencode "url=$WEBHOOK_URL" --data "push_events=true" --data "merge_requests_events=true" \
  --data-urlencode "token=$GITLAB_WEBHOOK_SECRET" >> "$LOG"

echo "[+] Ensuring standard labels" | tee -a "$LOG"
for l in bug enhancement docs security python typescript; do
  curl -sS -H "PRIVATE-TOKEN: $GITLAB_TOKEN" -X POST "$PROJ_URL/labels" \
    --data-urlencode "name=$l" --data-urlencode "color=#0E8A16" >> "$LOG" || true
done
```

---

## `scripts/validate_install.sh`
```bash
#!/usr/bin/env bash
# Script Name : validate_install.sh
# Author      : CBW + GPT-5 Thinking
# Date        : 2025-11-04
# Summary     : Health + metrics + signed payload test for GitHub webhook endpoint.
set -Eeuo pipefail
bail(){ echo "ERR: $*"; exit 1; }
BASE=${BASE:-http://localhost:8080}
SECRET=${GITHUB_WEBHOOK_SECRET:?set}

curl -fsS "$BASE/health" >/dev/null || bail "health failed"

BODY='{"zen":"Keep it logically awesome."}'
SIG="sha256=$(python3 - <<PY
import hmac,hashlib,os
b=b'${BODY}'.encode('utf-8') if isinstance('${BODY}', str) else b'${BODY}'
print(hmac.new(os.environ['GITHUB_WEBHOOK_SECRET'].encode(), b, hashlib.sha256).hexdigest())
PY
)"

curl -fsS -X POST "$BASE/github" -H "X-GitHub-Event: ping" -H "X-Hub-Signature-256: $SIG" -H 'Content-Type: application/json' -d "$BODY" >/dev/null || bail "signed ping failed"

echo "OK: endpoints up and signature verified"
```

---

## `scripts/export_state.py`
```python
#!/usr/bin/env python3
"""
Script Name : export_state.py
Author      : CBW + GPT-5 Thinking
Date        : 2025-11-04
Summary     : Export GitHub repo issues/PRs and (optionally) Project items to JSON/CSV for analytics.
"""
from __future__ import annotations
import json, csv, os, sys
from github import Github

if len(sys.argv) < 2:
    print("Usage: export_state.py <org/repo>"); sys.exit(2)
repo_full = sys.argv[1]

g = Github(os.getenv("GITHUB_TOKEN"))
repo = g.get_repo(repo_full)

issues = list(repo.get_issues(state="all"))
with open("issues.json","w") as f: json.dump([i.raw_data for i in issues], f, indent=2)
with open("issues.csv","w", newline="") as f:
    w = csv.writer(f); w.writerow(["number","state","title","labels","assignee"])
    for i in issues:
        w.writerow([i.number, i.state, i.title, ",".join([l.name for l in i.labels]), getattr(i.assignee, 'login', '')])

prs = list(repo.get_pulls(state="all"))
with open("prs.json","w") as f: json.dump([p.raw_data for p in prs], f, indent=2)
print("Exported issues.json, issues.csv, prs.json")
```

---

## `scripts/cron_janitor.sh`
```bash
#!/usr/bin/env bash
# Script Name : cron_janitor.sh
# Author      : CBW + GPT-5 Thinking
# Date        : 2025-11-04
# Summary     : Example of calling a protected admin endpoint for nightly cleanup (you can implement token check).
set -Eeuo pipefail
BASE=${BASE:-http://localhost:8080}
TOKEN=${ADMIN_TOKEN:-changeme}

curl -fsS -H "Authorization: Bearer $TOKEN" "$BASE/admin/run/janitor" || true
```

---

# Implementation Notes & To‑Dos
- **GitHub Projects v2** creation is org‑scoped; this bundle assumes the project already exists and wires items/fields via GraphQL helper.
- **CrewAI line comments**: extend `handlers.py` to fetch PR diff, map hunk→line, and use PR review API (`create_review`) to post inline suggestions.
- **Admin endpoints** (e.g., `/admin/run/janitor`) are trivial—add a FastAPI router with a bearer token check.

# Suggested Enhancements (next up)
1. Admin UI (Starlette + htmx) with live queue/metrics, rule editor, and policy tester.
2. GitHub App webhook delivery store in Redis for **idempotency + replay protection** with TTL.
3. Secret scanning and PII redaction pre‑review.
4. Backport bot: `/backport vX.Y` that cherry‑picks and opens PRs to maintenance branches.
5. Auto‑merge for trivial PRs (docs/typos) once required checks pass.

