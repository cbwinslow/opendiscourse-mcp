# Continue.dev — CBW Setup & Ops Bundle

A single, versioned bundle to install **Continue** (CLI + IDE), configure models (Ollama / OpenRouter / Groq / LiteLLM proxy), wire up **MCP servers** safely, and standardize a **universal tools** directory for your AI agents.

> Everything here is idempotent, heavily commented, and designed for reuse across your machines (Red Hat/Ubuntu/Debian). Drop these files into a repo and iterate.

---

## 📦 Repository Layout
```
continue-setup/
├─ README.md
├─ install-continue.sh
├─ scripts/
│  ├─ install-ollama-models.sh
│  ├─ cbw-ctx-pack.sh
│  ├─ cbw-continue-guard.sh
│  └─ project-scan.py
├─ .env.example
├─ .envrc
├─ Makefile
├─ continue/
│  ├─ config.example.yaml
│  ├─ permissions.example.yaml
│  └─ per-repo.config.example.yaml
├─ ai-tools/
│  └─ cbw-net-info.sh
└─ .github/
   └─ workflows/
      └─ continue-pr-review.yml
```

---

## README.md
```markdown
# Continue.dev Setup Bundle (CBW Edition)

This bundle installs and configures **Continue** for terminal + IDE usage, wires safe **MCP servers**, and sets up a universal `~/ai-tools` directory for agent-usable utilities.

## Quick Start
```bash
bash ./install-continue.sh
cp -n ./continue/config.example.yaml ~/.continue/config.yaml
cp -n ./continue/permissions.example.yaml ~/.continue/permissions.yaml
# Optional: local LLMs
ollama serve &
bash ./scripts/install-ollama-models.sh
```

## DevOps Integrations
- **Headless CLI:** `git diff | cn -p "Conventional commit message; respond with only the message."`
- **PR review CI:** `.github/workflows/continue-pr-review.yml` posts a sticky PR comment.
- **Context packer:** `scripts/cbw-ctx-pack.sh` bundles repo context for targeted prompts.

## Security Notes
- Keep **MCP** scopes tight (allowlist paths and whitelisted commands).
- Use `permissions.yaml` and CLI `--allow/--ask/--exclude` for tool gating.
- Store secrets in environment (`.envrc`/direnv) or Bitwarden CLI; never hardcode keys.

## Next Steps
1. Enable Filesystem + Shell MCPs with strict scopes/whitelists.
2. Create per-repo overrides with `continue/per-repo.config.example.yaml`.
3. Add more curated tools under `~/ai-tools` (lint, test, build, deploy).
```
```

---

## install-continue.sh
```bash
#!/usr/bin/env bash
#===============================================================================
# Script Name   : install-continue.sh
# Author        : ChatGPT for cbwinslow (CBW)
# Date          : 2025-11-02
# Summary       : Idempotent installer for Continue (CLI + VS Code ext), config
#                 folders, universal AI tools dir, and optional LiteLLM proxy.
# Inputs        : Environment variables (see .env.example)
# Outputs       : Installs Node (nvm if needed), Continue CLI, creates ~/.continue,
#                 seeds ai-tools/, optionally installs VS Code extension.
# Parameters    : --no-vscode-ext   Skip VS Code extension install
#                 --no-nvm          Skip nvm bootstrap (requires Node >= 18)
#                 --force           Reinstall CLI even if detected
#                 --with-litellm    Install LiteLLM proxy locally (pipx)
#                 --verbose         Extra logging
#                 --dry-run         Print actions only
# Modification Log:
#   2025-10-30 - Initial version
#   2025-11-02 - Add LiteLLM proxy option, safer npm/pipx checks, direnv hint
#===============================================================================
set -Eeuo pipefail
IFS=$'\n\t'

LOG="/tmp/CBW-install-continue.log"
DRY=false
VERBOSE=false
INSTALL_VSCODE_EXT=true
USE_NVM=true
FORCE=false
WITH_LITELLM=false
REQUIRED_NODE_MAJOR=18

log(){ printf "%s\n" "$*" | tee -a "$LOG" >&2; }
vrb(){ $VERBOSE && log "[verbose] $*"; }
run(){ $DRY && { echo "[dry-run] $*"; return 0; }; eval "$@"; }
exists(){ command -v "$1" >/dev/null 2>&1; }
usage(){ sed -n '1,120p' "$0" >&2; exit 1; }

while [[ "${1:-}" != "" ]]; do
  case "$1" in
    --no-vscode-ext) INSTALL_VSCODE_EXT=false ;;
    --no-nvm)        USE_NVM=false ;;
    --force)         FORCE=true ;;
    --with-litellm)  WITH_LITELLM=true ;;
    --verbose)       VERBOSE=true ;;
    --dry-run)       DRY=true ;;
    -h|--help)       usage ;;
    *) log "Unknown flag: $1"; usage ;;
  esac
  shift
done

ensure_node(){
  if exists node; then
    local major
    major=$(node -v | sed -E 's/^v([0-9]+).*/\1/')
    if [[ "$major" -ge "$REQUIRED_NODE_MAJOR" ]]; then
      vrb "Node ok: $(node -v)"; return 0
    fi
    log "Node $(node -v) too old (<$REQUIRED_NODE_MAJOR)."
  fi
  [[ "$USE_NVM" == true ]] || { log "Node missing/old and --no-nvm set."; return 1; }
  if [[ ! -d "$HOME/.nvm" ]]; then
    log "Installing nvm..."; run 'curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash'
  fi
  run 'export NVM_DIR="$HOME/.nvm"; [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"; nvm install --lts; nvm use --lts'
}

install_cli(){
  if exists cn && [[ "$FORCE" != true ]]; then
    vrb "Continue CLI present: $(cn --version 2>/dev/null || echo unknown)"; return 0
  fi
  log "Installing Continue CLI (@continuedev/cli)..."
  run "npm i -g @continuedev/cli"
  vrb "cn version: $(cn --version 2>/dev/null || echo unknown)"
}

install_vscode_ext(){
  $INSTALL_VSCODE_EXT || { vrb "Skip VS Code ext"; return 0; }
  if exists code; then
    log "Installing VS Code extension Continue.continue (idempotent)..."
    run "code --install-extension Continue.continue || true"
  else
    vrb "VS Code CLI not found; skipping"
  fi
}

bootstrap_dirs(){
  run "mkdir -p \"$HOME/.continue\""
  run "mkdir -p \"$HOME/ai-tools\""
  if [[ ! -f "$HOME/ai-tools/README.md" ]]; then
    run "cat > \"$HOME/ai-tools/README.md\" <<'EOF'\n# ~/ai-tools\nDrop agent-safe, idempotent utilities here. Keep inputs validated and outputs parseable.\nEOF"
  fi
}

install_litellm(){
  $WITH_LITELLM || return 0
  if ! exists pipx; then
    log "Installing pipx..."; run "python3 -m pip install --user pipx && python3 -m pipx ensurepath"
  fi
  log "Installing LiteLLM proxy via pipx..."
  run "pipx install litellm || true"
  log "You can run: 'litellm --port 4000 --config ~/.config/litellm/config.yaml' and point Continue at http://localhost:4000"
}

post_checks(){
  log "\nDone. Key locations:"
  log "  - CLI: $(command -v cn || echo 'not in PATH')"
  log "  - Config: $HOME/.continue/config.yaml"
  log "  - Permissions: $HOME/.continue/permissions.yaml"
  log "  - Tools dir: $HOME/ai-tools"
  log "  - Consider enabling direnv (see .envrc) for keys/models"
}

main(){
  : > "$LOG"
  log "Starting Continue installer (log: $LOG)"
  ensure_node
  install_cli
  install_vscode_ext
  bootstrap_dirs
  install_litellm
  post_checks
  log "Success."
}

main "$@"
```

---

## scripts/install-ollama-models.sh
```bash
#!/usr/bin/env bash
#===============================================================================
# Script Name   : install-ollama-models.sh
# Author        : CBW + ChatGPT
# Date          : 2025-11-02
# Summary       : Pull recommended local models for coding & reasoning.
# Parameters    : --fast-only (skip large models)
#===============================================================================
set -Eeuo pipefail
FAST=false
while [[ ${1:-} ]]; do case "$1" in --fast-only) FAST=true;; esac; shift; done
command -v ollama >/dev/null 2>&1 || { echo "ollama not installed" >&2; exit 1; }

pull(){ echo "> pulling $1"; ollama pull "$1" || true; }
# Coder / reasoning picks (tune to taste)
pull qwen2.5-coder:7b
$FAST || pull qwen2.5-coder:14b
pull llama3.1:8b
$FAST || pull llama3.1:70b
echo "done"
```

---

## scripts/cbw-ctx-pack.sh
```bash
#!/usr/bin/env bash
#===============================================================================
# Script Name   : cbw-ctx-pack.sh
# Author        : CBW + ChatGPT
# Date          : 2025-11-02
# Summary       : Pack useful repo context and feed to Continue CLI prompt.
# Usage         : cbw-ctx-pack.sh | cn -p "Refactor plan"
#===============================================================================
set -Eeuo pipefail
ROOT=${1:-"."}
max(){ awk 'NR==1||length>$0{m=length;s=$0}END{print s}'; }

{
  echo "# GIT STATUS"; git -C "$ROOT" status -sb || true
  echo -e "\n# IMPORTANT FILES"; ls -lah "$ROOT" | head -n 200 || true
  echo -e "\n# PACKAGE MANIFEST"; for f in package.json pyproject.toml requirements.txt; do
    [[ -f "$ROOT/$f" ]] && { echo "## $f"; sed -n '1,200p' "$ROOT/$f"; }
  done
  echo -e "\n# RECENT DIFF"; git -C "$ROOT" diff --stat || true
} | sed -e 's/[\x00-\x1F\x7F]//g'
```

---

## scripts/cbw-continue-guard.sh
```bash
#!/usr/bin/env bash
#===============================================================================
# Script Name   : cbw-continue-guard.sh
# Author        : CBW + ChatGPT
# Date          : 2025-11-02
# Summary       : Sanity-check ~/.continue config & permissions for risky entries.
#===============================================================================
set -Eeuo pipefail
CFG="$HOME/.continue/config.yaml"
PERM="$HOME/.continue/permissions.yaml"
[[ -f "$CFG" ]] || { echo "missing $CFG"; exit 1; }
[[ -f "$PERM" ]] || { echo "missing $PERM"; exit 1; }

risk=0
if grep -E "server-filesystem|ALLOW|ROOTS" -n "$CFG" | grep -q "/"; then
  echo "[warn] filesystem MCP appears enabled; verify allowlist is narrow"; risk=1
fi
if grep -E "bash|shell|exec" -n "$CFG" | grep -qi "allow:.*\*"; then
  echo "[warn] shell MCP wildcard allowlist detected"; risk=1
fi
if grep -qi "decision: allow" "$PERM" | grep -q "Fetch"; then
  echo "[warn] Fetch globally allowed; consider 'ask' or 'deny'"; risk=1
fi
[[ $risk -eq 0 ]] && echo "OK" || echo "Review warnings above"
```

---

## scripts/project-scan.py
```python
#!/usr/bin/env python3
"""
Script Name : project-scan.py
Author      : CBW + ChatGPT
Date        : 2025-11-02
Summary     : Scans current repo for language and dependency signals; prints
              tips to tune Continue config (models, context providers, tools).
"""
from __future__ import annotations
import os, json, pathlib

ROOT = pathlib.Path.cwd()
insights = {"languages": set(), "manifests": []}
for name in ["package.json", "pyproject.toml", "requirements.txt", "go.mod", "Cargo.toml"]:
    p = ROOT / name
    if p.exists():
        insights["manifests"].append(name)
        if name in ("package.json",): insights["languages"].add("javascript/typescript")
        if name in ("pyproject.toml", "requirements.txt"): insights["languages"].add("python")
        if name == "go.mod": insights["languages"].add("go")
        if name == "Cargo.toml": insights["languages"].add("rust")

print(json.dumps({
    "recommendations": {
        "models": [
            "Use fast local Ollama for autocomplete; Claude/Groq for deep refactors.",
        ],
        "context": [
            "Enable 'code', 'diff', 'folder', 'problems'",
        ],
        "mcp": [
            "Filesystem MCP scoped to ~/ai-tools and repo root",
            "Shell MCP with whitelist: git,npm,pnpm,pytest,ruff,black,make",
        ]
    },
    "detected": {
        "languages": sorted(list(insights["languages"])),
        "manifests": insights["manifests"],
    }
}, indent=2))
```

---

## .env.example
```dotenv
# Continue cloud providers
OPENROUTER_API_KEY=
GROQ_API_KEY=
# Optional LiteLLM proxy endpoint
LITELLM_BASE_URL=http://localhost:4000
# Telemetry/observability flags
OTEL_SERVICE_NAME=continue-cli
OTEL_EXPORTER_OTLP_ENDPOINT=
```

---

## .envrc
```bash
# direnv: auto-load dev env for Continue
export OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-$(bw get item openrouter | jq -r .login.password 2>/dev/null || true)}
export GROQ_API_KEY=${GROQ_API_KEY:-$(bw get item groq | jq -r .login.password 2>/dev/null || true)}
# Optional LiteLLM base
export LITELLM_BASE_URL=${LITELLM_BASE_URL:-http://localhost:4000}
```

---

## Makefile
```makefile
.PHONY: install check models guard ctx ci
install:
	bash ./install-continue.sh --with-litellm
check:
	cn --version || echo "cn missing"
models:
	bash ./scripts/install-ollama-models.sh
guard:
	bash ./scripts/cbw-continue-guard.sh || true
ctx:
	bash ./scripts/cbw-ctx-pack.sh | cn -p "Give me a prioritized refactor plan."
ci:
	@echo "See .github/workflows/continue-pr-review.yml"
```

---

## continue/config.example.yaml
```yaml
name: CBW Local + Cloud
version: 1.1.0
schema: v1

# Default model strategy
defaultModel: Ollama (Autodetect)
# Keep autocomplete snappy (local small model)
tabAutocompleteModel: Ollama (Autodetect)
allowAnonymousTelemetry: false

models:
  # Local via Ollama (auto-detect present models)
  - name: Ollama (Autodetect)
    provider: ollama
    model: AUTODETECT
    roles: [chat, edit, apply, autocomplete]

  # OpenRouter (Claude Sonnet)
  - name: Claude (OpenRouter)
    provider: openrouter
    apiBase: https://openrouter.ai/api/v1
    apiKey: ${OPENROUTER_API_KEY}
    model: anthropic/claude-3.5-sonnet
    capabilities: [tool_use]
    roles: [chat, edit, apply]

  # Groq for speed drafts
  - name: Llama 3.1 70B (Groq)
    provider: groq
    apiKey: ${GROQ_API_KEY}
    model: llama-3.1-70b-versatile
    roles: [chat, edit]

  # Optional LiteLLM proxy (fan-out/routing)
  - name: LiteLLM (Proxy)
    provider: openai-compatible
    apiBase: ${LITELLM_BASE_URL}
    apiKey: "none"
    model: gpt-4o-mini  # ignored; server routes
    roles: [chat, edit]

context:
  - provider: code
  - provider: docs
  - provider: diff
  - provider: terminal
  - provider: problems
  - provider: folder
  - provider: codebase

# Minimal, scoped MCP servers (enable as needed)
mcpServers:
  - name: Filesystem (scoped)
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem"]
    env:
      # Restrict read roots to curated paths only
      ALLOW: "${HOME}/ai-tools,${PWD}"

  - name: Shell (whitelist)
    command: npx
    args: ["-y", "@mcp-cli/shell-server"]
    env:
      ALLOW_CMDS: "git,npm,pnpm,pytest,ruff,black,make"

# You can add DB/HTTP/etc MCPs here once vetted and scoped.
```

---

## continue/permissions.example.yaml
```yaml
# Tool permission policy; the CLI also supports --allow/--ask/--exclude
policies:
  - tool: Write
    decision: allow
  - tool: Bash(curl*)
    decision: ask
  - tool: Fetch
    decision: deny
```

---

## continue/per-repo.config.example.yaml
```yaml
# Drop this as .continue/config.yaml in a specific repo to override defaults
name: Per-Repo Overrides (CBW)
version: 1.0.0
schema: v1

# Pin a faster model for this repo's autocomplete if codebase is large
tabAutocompleteModel: Ollama (Autodetect)

# Extra context for monorepos
context:
  - provider: folder
  - provider: diff
  - provider: problems

# Example: whitelist only test/lint/build commands for Shell MCP here
```

---

## ai-tools/cbw-net-info.sh
```bash
#!/usr/bin/env bash
#===============================================================================
# Script Name   : cbw-net-info.sh
# Author        : CBW + ChatGPT
# Date          : 2025-11-02
# Summary       : Fast network context (IP, routes, DNS, open ports).
# Parameters    : --json | --quiet
#===============================================================================
set -Eeuo pipefail
QUIET=false; JSON=false
while [[ ${1:-} ]]; do case "$1" in --quiet) QUIET=true;; --json) JSON=true;; -h|--help) sed -n '1,80p' "$0"; exit 0;; *) echo "bad arg: $1"; exit 2;; esac; shift; done
exists(){ command -v "$1" >/dev/null 2>&1; }
_ip(){ exists ip && (ip -brief address || ip address) || ifconfig -a || true; }
_rt(){ exists ip && ip route || route -n || true; }
_dns(){ [[ -f /etc/resolv.conf ]] && cat /etc/resolv.conf || true; }
_prt(){ exists ss && ss -tulpn || netstat -tulpn || true; }
if $JSON; then python3 - <<'PY'
import json, subprocess, os
sh=lambda c: subprocess.getoutput(c)
print(json.dumps({
  "ip": sh("ip -brief address || ip address || ifconfig -a"),
  "routes": sh("ip route || route -n"),
  "dns": open("/etc/resolv.conf").read() if os.path.exists("/etc/resolv.conf") else "",
  "ports": sh("ss -tulpn || netstat -tulpn"),
}, indent=2))
PY
  exit 0; fi
$QUIET || echo "=== IP INFO ==="; _ip
$QUIET || echo -e "\n=== ROUTES ==="; _rt
$QUIET || echo -e "\n=== DNS ==="; _dns
$QUIET || echo -e "\n=== LISTENING PORTS ==="; _prt
```

---

## .github/workflows/continue-pr-review.yml
```yaml
name: Continue CLI Review
on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
permissions:
  contents: read
  pull-requests: write
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Install Continue CLI
        run: npm i -g @continuedev/cli
      - name: Generate PR Review (headless)
        run: |
          git fetch --depth=2 origin +refs/pull/*:refs/remotes/origin/pr/* || true
          DIFF=$(git diff HEAD~1..HEAD || git diff)
          printf "%s\n" "$DIFF" | cn -p "Review this PR diff. Provide a short summary, major issues, and actionable suggestions." > review.md
      - name: Post review comment
        uses: marocchino/sticky-pull-request-comment@v2
        with:
          recreate: true
          path: review.md
```

---

## How to Use This Bundle (Step-by-step)

1. **Install**
   ```bash
   bash ./install-continue.sh --with-litellm
   ```
2. **Copy configs**
   ```bash
   mkdir -p ~/.continue
   cp -n ./continue/config.example.yaml ~/.continue/config.yaml
   cp -n ./continue/permissions.example.yaml ~/.continue/permissions.yaml
   ```
3. **Start local models (optional)**
   ```bash
   ollama serve &
   bash ./scripts/install-ollama-models.sh
   ```
4. **Lock down MCP scopes**
   - In `config.yaml`, keep Filesystem roots small (e.g., `~/ai-tools, $PWD`).
   - In Shell MCP, keep `ALLOW_CMDS` short and audited.
5. **Load env**
   - Fill `.env.example` → `.envrc` values; run `direnv allow` in the repo.
6. **Run**
   ```bash
   cn
   git diff | cn -p "Conventional commit message; respond with only the message."
   ```
7. **Guard** your config
   ```bash
   bash ./scripts/cbw-continue-guard.sh
   ```

---

## Suggested Improvements / Next Steps
- Add **Bitwarden CLI** helper scripts to fetch provider keys on demand (no local storage).
- Add a **Shell MCP** that maps to a tiny wrapper per command (e.g., `cbw-git.sh`, `cbw-test.sh`) for clearer audit trails.
- Introduce **OpenTelemetry** exporter (OTLP) to ship `cn` run metadata to Grafana Tempo/Loki via a tiny sidecar script.

---

*End of bundle.*

