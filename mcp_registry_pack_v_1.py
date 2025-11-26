# =============================================
# MCP Registry Pack v1.1 — Cloudflare Pipeline
# =============================================
# This pack contains:
#   • mcpctl_v1_1.py  – unified CLI with R2 publish
#   • wrangler.toml    – Worker config (R2 + D1)
#   • src/schema.sql   – D1 schema for index/search
#   • src/worker.ts    – Worker API + registry proxy
#   • .github/workflows/registry-ci.yml – CI to validate, checksum & publish
#   • PAGES-README.md  – notes for a minimal Pages UI
#   • bw_askpass.sh    – (carried from v1) Bitwarden AskPass helper
#
# Note: Replace placeholders: YOUR_CF_ACCOUNT_ID, REPLACE_WITH_D1_ID, secrets in CI.


# ---------------------------------------------
# File: mcpctl_v1_1.py  (standalone)
# ---------------------------------------------
#!/usr/bin/env python3
"""
Script: mcpctl_v1_1.py
Author: CBW + GPT-5 Thinking
Date: 2025-11-02
Summary:
  Manage a local MCP server registry and publish to Cloudflare R2.
  Subcommands:
    list, add, validate, export-compose, export-clients, merge, publish-r2
Inputs:
  MCP_REGISTRY (env) or --registry path to YAML
  R2_BUCKET / R2_PREFIX envs for publish-r2 (optional)
Outputs:
  YAML/JSON files, compose fragments, client stanzas; uploads to R2
Security:
  No secrets stored. Uses wrangler CLI for R2 auth. Prefer Bitwarden CLI for secrets.
"""
import argparse, json, os, sys, textwrap, logging, subprocess, hashlib, tempfile, shutil
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml  # PyYAML
except Exception:
    print("[FATAL] PyYAML is required. Try: pip install pyyaml", file=sys.stderr)
    raise

LOG = logging.getLogger("mcpctl")

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "MCP Server Registry",
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
        "servers": {"type": "array"}
    },
    "required": ["version", "servers"]
}

def load_registry(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"version": "v0.1.0", "sources": [], "servers": []}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"version": "v0.1.0", "sources": [], "servers": []}


def save_registry(path: Path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp.yaml")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    tmp.replace(path)


def validate_registry(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["registry root must be an object"]
    if "version" not in data:
        errors.append("missing version")
    if "servers" not in data or not isinstance(data["servers"], list):
        errors.append("servers must be an array")
        return errors
    for i, s in enumerate(data["servers"]):
        for key in ["id", "name", "endpoints", "metadata"]:
            if key not in s:
                errors.append(f"server[{i}] missing {key}")
        eps = s.get("endpoints", {})
        if not any(eps.get(k) for k in ("sse", "ws", "http")):
            errors.append(f"server[{i}] must include at least one endpoint (sse/ws/http)")
    return errors


def cmd_list(args, reg, *_):
    for s in reg.get("servers", []):
        if args.query and args.query.lower() not in (" ".join([
            s.get("id", ""), s.get("name", ""), " ".join(s.get("tags", [])),
            s.get("category", "")
        ])).lower():
            continue
        print(f"- {s['name']} ({s['id']})\n  category: {s.get('category')}\n  tags: {', '.join(s.get('tags', []))}\n  repo: {s.get('repo_url')}\n  home: {s.get('home_url')}\n  endpoints: {json.dumps(s.get('endpoints'))}\n")


def cmd_add(args, reg, path):
    new = {
        "id": args.id,
        "name": args.name,
        "category": args.category,
        "tags": args.tags,
        "repo_url": args.repo,
        "home_url": args.home,
        "docker_image": args.image,
        "compose_service": args.service,
        "endpoints": {"sse": args.sse, "ws": args.ws, "http": args.http},
        "auth": {"method": args.auth, "env": args.auth_env},
        "metadata": {"description": args.desc, "license": args.license, "maintainers": args.maint or []}
    }
    reg.setdefault("servers", []).append(new)
    errs = validate_registry(reg)
    if errs:
        for e in errs:
            LOG.error(e)
        sys.exit(1)
    save_registry(path, reg)
    print(f"added: {args.id}")


def cmd_validate(args, reg, *_):
    errs = validate_registry(reg)
    if errs:
        print("INVALID registry:\n- " + "\n- ".join(errs), file=sys.stderr)
        sys.exit(1)
    print("OK: registry is valid")


def cmd_export_compose(args, reg, *_):
    selected = [s for s in reg["servers"] if (args.id and s["id"] in (args.id or [])) or (args.tag and set(args.tag or []).intersection(set(s.get("tags", [])))) or (not args.id and not args.tag)]
    print("version: '3.9'\nservices:")
    for s in selected:
        image = s.get("docker_image") or ""
        name = s.get("compose_service") or s["id"].replace('/', '-').replace('_','-')
        env = s.get("auth", {}).get("env", [])
        env_lines = "\n".join([f"      - {k}=${{{k}:-}}" for k in env])
        print(textwrap.dedent(f"""
          {name}:
            image: {image if image else 'REPLACE_WITH_IMAGE'}
            restart: unless-stopped
            environment:
{env_lines if env_lines else '      # - EXAMPLE_TOKEN=${EXAMPLE_TOKEN}'}
            ports:
              # - "0.0.0.0:8800:8800"  # if server exposes HTTP/SSE
            command: []  # add server-specific args if needed
        """))


def cmd_export_clients(args, reg, *_):
    for s in reg["servers"]:
        if args.id and s["id"] not in (args.id or []):
            continue
        eps = s.get("endpoints", {})
        print(f"# {s['name']} ({s['id']})\n# Gemini CLI extensions.yaml fragment:\n- name: {s['id']}\n  url: {eps.get('sse') or eps.get('http') or eps.get('ws','')}\n  description: {s.get('metadata',{}).get('description','').strip()}\n\n# Claude Desktop mcpServers fragment (settings.json):\n\"{s['id']}\": {{ \"command\": \"node\", \"args\": [\"/path/to/{s['id']}.js\"] }}\n")


def cmd_merge(args, reg, path):
    import urllib.request
    merged = 0
    for url in args.url:
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                data = yaml.safe_load(r.read().decode("utf-8"))
                if isinstance(data, dict) and "servers" in data:
                    reg["servers"].extend(data["servers"])  # naive merge; dedupe below
                    reg.setdefault("sources", []).append(url)
                    merged += 1
        except Exception as e:
            LOG.warning("failed to fetch %s: %s", url, e)
    # de-dupe by id
    seen = set(); unique = []
    for s in reg["servers"]:
        if s.get("id") in seen: continue
        seen.add(s.get("id")); unique.append(s)
    reg["servers"] = unique
    errs = validate_registry(reg)
    if errs:
        for e in errs: LOG.error(e)
        sys.exit(1)
    save_registry(path, reg)
    print(f"merged {merged} source(s)")


def put_r2_with_wrangler(bucket_key: str, local_file: str) -> None:
    """Publish a file to R2 using wrangler if available (no secrets in code)."""
    if not shutil.which("wrangler"):
        raise RuntimeError("wrangler CLI not found. Install: npm i -g wrangler")
    cmd = ["wrangler", "r2", "object", "put", bucket_key, f"--file={local_file}"]
    subprocess.check_call(cmd)


def cmd_publish_r2(args, reg, path):
    # 1) Build manifest with SHA256 of YAML-JSON 
    blob = json.dumps(reg, sort_keys=True).encode("utf-8")
    sha = hashlib.sha256(blob).hexdigest()
    manifest = {"files": [{"path": "mcp_registry.yaml", "sha256": sha}]}

    tmpdir = tempfile.mkdtemp()
    man_path = os.path.join(tmpdir, "manifest.json")
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    json_path = os.path.join(tmpdir, "mcp_registry.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2)

    bucket = args.r2_bucket or os.getenv("R2_BUCKET", "cloudcurio-mcp")
    prefix = args.prefix or os.getenv("R2_PREFIX", "registry")

    put_r2_with_wrangler(f"{bucket}/{prefix}/mcp_registry.yaml", str(path))
    put_r2_with_wrangler(f"{bucket}/{prefix}/mcp_registry.json", json_path)
    put_r2_with_wrangler(f"{bucket}/{prefix}/manifest.json", man_path)
    print(f"Published to r2://{bucket}/{prefix}/ (yaml/json/manifest)")


def build_parser():
    p = argparse.ArgumentParser(description="Manage a local MCP server registry")
    p.add_argument("--registry", default=os.getenv("MCP_REGISTRY", "./mcp_registry.yaml"), help="Path to the registry YAML")
    p.add_argument("--verbose", action="store_true")

    sub = p.add_subparsers(dest="cmd", required=True)

    s_list = sub.add_parser("list", help="List servers")
    s_list.add_argument("--query", help="Filter by substring across id/name/tags/category")
    s_list.set_defaults(func=cmd_list)

    s_add = sub.add_parser("add", help="Add a server entry")
    s_add.add_argument("--id", required=True)
    s_add.add_argument("--name", required=True)
    s_add.add_argument("--category", default="other")
    s_add.add_argument("--tags", nargs="*", default=[])
    s_add.add_argument("--repo")
    s_add.add_argument("--home")
    s_add.add_argument("--image")
    s_add.add_argument("--service")
    s_add.add_argument("--sse")
    s_add.add_argument("--ws")
    s_add.add_argument("--http")
    s_add.add_argument("--auth", default="none")
    s_add.add_argument("--auth-env", nargs="*", default=[])
    s_add.add_argument("--desc", default="")
    s_add.add_argument("--license", default="")
    s_add.add_argument("--maint", nargs="*")
    s_add.set_defaults(func=cmd_add)

    s_val = sub.add_parser("validate", help="Validate registry file")
    s_val.set_defaults(func=cmd_validate)

    s_cmp = sub.add_parser("export-compose", help="Emit docker compose blocks for servers")
    s_cmp.add_argument("--id", nargs="*")
    s_cmp.add_argument("--tag", nargs="*")
    s_cmp.set_defaults(func=cmd_export_compose)

    s_cli = sub.add_parser("export-clients", help="Emit Gemini/Claude config fragments")
    s_cli.add_argument("--id", nargs="*")
    s_cli.set_defaults(func=cmd_export_clients)

    s_merge = sub.add_parser("merge", help="Merge from remote registry URLs (YAML)")
    s_merge.add_argument("url", nargs="+")
    s_merge.set_defaults(func=cmd_merge)

    s_pub = sub.add_parser("publish-r2", help="Publish registry to Cloudflare R2 via wrangler")
    s_pub.add_argument("--r2-bucket", default=os.getenv("R2_BUCKET","cloudcurio-mcp"))
    s_pub.add_argument("--prefix", default=os.getenv("R2_PREFIX","registry"))
    s_pub.set_defaults(func=cmd_publish_r2)

    return p


def main():
    args = build_parser().parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")
    path = Path(args.registry).expanduser().resolve()
    reg = load_registry(path)
    try:
        args.func(args, reg, path)
    except Exception:
        LOG.exception("Unhandled error")
        sys.exit(1)

if __name__ == "__main__":
    main()


# ---------------------------------------------
# File: wrangler.toml
# ---------------------------------------------
name = "mcp-registry"
main = "src/worker.ts"
compatibility_date = "2024-11-21"
account_id = "YOUR_CF_ACCOUNT_ID"
workers_dev = true

[vars]
REGISTRY_PREFIX = "registry/"
PUBLIC_BASE_URL = "https://registry.cloudcurio.cc/"

[[r2_buckets]]
binding = "R2"
bucket_name = "cloudcurio-mcp"

[[d1_databases]]
binding = "DB"
database_name = "mcp-registry"
database_id = "REPLACE_WITH_D1_ID"

[observability]
enabled = true


# ---------------------------------------------
# File: src/schema.sql
# ---------------------------------------------
CREATE TABLE IF NOT EXISTS servers (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT,
  tags TEXT,
  repo_url TEXT,
  home_url TEXT,
  docker_image TEXT,
  has_sse INTEGER DEFAULT 0,
  has_ws  INTEGER DEFAULT 0,
  has_http INTEGER DEFAULT 0,
  description TEXT,
  license TEXT,
  maintainers TEXT,
  quality INTEGER DEFAULT 0,
  version TEXT,
  updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_servers_category ON servers(category);
CREATE INDEX IF NOT EXISTS idx_servers_quality ON servers(quality);


# ---------------------------------------------
# File: src/worker.ts
# ---------------------------------------------
export interface Env {
  R2: R2Bucket;
  DB: D1Database;
  REGISTRY_PREFIX: string;
  PUBLIC_BASE_URL: string;
  ADMIN_API_TOKEN: string;
}

const json = (data: unknown, init: ResponseInit = {}) =>
  new Response(JSON.stringify(data, null, 2), { headers: { "content-type": "application/json" }, ...init });

function requireAdmin(req: Request, env: Env) {
  const tok = req.headers.get("authorization")?.replace(/^Bearer\s+/i, "");
  if (!tok || tok !== env.ADMIN_API_TOKEN) return new Response("Unauthorized", { status: 401 });
  return null;
}

async function handleRegistry(req: Request, env: Env) {
  const url = new URL(req.url);
  const key = env.REGISTRY_PREFIX + url.pathname.replace(/^\/registry\//, "");
  const obj = await env.R2.get(key);
  if (!obj) return new Response("Not found", { status: 404 });
  const hdrs = new Headers();
  if (obj.httpMetadata?.contentType) hdrs.set("content-type", obj.httpMetadata.contentType);
  return new Response(obj.body, { headers: hdrs });
}

async function handleListServers(req: Request, env: Env) {
  const { searchParams } = new URL(req.url);
  const category = searchParams.get("category");
  const tag = searchParams.get("tag");
  const minQ = parseInt(searchParams.get("minQuality") || "0", 10);
  const q = searchParams.get("q");

  let sql = `SELECT * FROM servers WHERE quality >= ?`;
  const args: unknown[] = [minQ];
  if (category) { sql += ` AND category = ?`; args.push(category); }
  if (tag) { sql += ` AND (tags LIKE ?)`; args.push(`%${tag}%`); }
  if (q) { sql += ` AND (id LIKE ? OR name LIKE ? OR description LIKE ?)`; args.push(`%${q}%`, `%${q}%`, `%${q}%`); }
  sql += ` ORDER BY quality DESC, name ASC LIMIT 500`;

  const out = await env.DB.prepare(sql).bind(...args).all();
  return json({ count: out.results?.length || 0, results: out.results || [] });
}

async function handleAdminIngest(req: Request, env: Env) {
  const unauthorized = requireAdmin(req, env); if (unauthorized) return unauthorized;
  const body = await req.json<any>();
  const servers = body?.servers || [];
  const tx = env.DB.prepare("BEGIN TRANSACTION");
  await tx.run();
  try {
    for (const s of servers) {
      const tags = (s.tags || []).join(",");
      const has_sse = s.endpoints?.sse ? 1 : 0;
      const has_ws  = s.endpoints?.ws ? 1 : 0;
      const has_http= s.endpoints?.http ? 1 : 0;
      const quality = Number(s.metadata?.quality || 0);
      await env.DB.prepare(`
        INSERT INTO servers (id, name, category, tags, repo_url, home_url, docker_image,
                              has_sse, has_ws, has_http, description, license, maintainers, quality, version, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(id) DO UPDATE SET
          name=excluded.name,
          category=excluded.category,
          tags=excluded.tags,
          repo_url=excluded.repo_url,
          home_url=excluded.home_url,
          docker_image=excluded.docker_image,
          has_sse=excluded.has_sse,
          has_ws=excluded.has_ws,
          has_http=excluded.has_http,
          description=excluded.description,
          license=excluded.license,
          maintainers=excluded.maintainers,
          quality=excluded.quality,
          version=excluded.version,
          updated_at=datetime('now');
      `).bind(
        s.id, s.name, s.category || null, tags, s.repo_url || null, s.home_url || null, s.docker_image || null,
        has_sse, has_ws, has_http, s.metadata?.description || null, s.metadata?.license || null,
        (s.metadata?.maintainers || []).join(","), quality, s.metadata?.version || null
      ).run();
    }
    await env.DB.prepare("COMMIT").run();
    return json({ ingested: servers.length });
  } catch (e) {
    await env.DB.prepare("ROLLBACK").run();
    return json({ error: String(e) }, { status: 500 });
  }
}

async function handleAdminSign(req: Request, env: Env) {
  const unauthorized = requireAdmin(req, env); if (unauthorized) return unauthorized;
  const { path = "registry/manifest.json" } = await req.json().catch(() => ({ path: "registry/manifest.json" }));
  const obj = await env.R2.get(path);
  if (!obj) return new Response("Not found", { status: 404 });
  const data = await obj.arrayBuffer();
  const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", data)))
    .map(b => b.toString(16).padStart(2, "0")).join("");
  return json({ sha256: hash, note: "Replace with Sigstore signature in v1.2" });
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    if (url.pathname.startsWith("/registry/")) return handleRegistry(req, env);
    if (url.pathname === "/api/servers") return handleListServers(req, env);
    if (url.pathname === "/admin/ingest" && req.method === "POST") return handleAdminIngest(req, env);
    if (url.pathname === "/admin/sign"   && req.method === "POST") return handleAdminSign(req, env);
    return json({ ok: true, routes: ["/registry/*", "/api/servers", "/admin/ingest", "/admin/sign"] });
  }
} satisfies ExportedHandler<Env>;


# ---------------------------------------------
# File: .github/workflows/registry-ci.yml
# ---------------------------------------------
name: Registry CI
on:
  push:
    branches: [ main ]
    paths:
      - 'mcp_registry.yaml'
      - 'registry/**'
      - 'src/**'
      - '.github/workflows/registry-ci.yml'

jobs:
  validate-and-publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install deps
        run: |
          python -m pip install --upgrade pip pyyaml

      - name: Validate YAML schema (light)
        run: |
          python - <<'PY'
          import yaml, sys
          doc = yaml.safe_load(open('mcp_registry.yaml'))
          assert isinstance(doc, dict) and 'servers' in doc and isinstance(doc['servers'], list)
          for s in doc['servers']:
              assert 'id' in s and 'name' in s and 'endpoints' in s and 'metadata' in s
          print('OK: registry basic validation passed.')
          PY

      - name: Create manifest.json with SHA256
        run: |
          mkdir -p registry
          python - <<'PY'
          import yaml, json, hashlib
          data = yaml.safe_load(open('mcp_registry.yaml'))
          blob = json.dumps(data, sort_keys=True).encode()
          sha = hashlib.sha256(blob).hexdigest()
          open('registry/manifest.json','w').write(json.dumps({'files':[{'path':'mcp_registry.yaml','sha256':sha}]}, indent=2))
          print('Wrote registry/manifest.json')
          PY

      - name: Upload to R2 (wrangler)
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CF_API_TOKEN }}
          accountId: ${{ secrets.CF_ACCOUNT_ID }}
          command: r2 object put cloudcurio-mcp/registry/mcp_registry.yaml --file=./mcp_registry.yaml

      - name: Upload manifest.json
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CF_API_TOKEN }}
          accountId: ${{ secrets.CF_ACCOUNT_ID }}
          command: r2 object put cloudcurio-mcp/registry/manifest.json --file=./registry/manifest.json

      - name: Run DB migrations (D1)
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CF_API_TOKEN }}
          accountId: ${{ secrets.CF_ACCOUNT_ID }}
          command: d1 execute mcp-registry --file=src/schema.sql

      - name: Ingest into D1 via Worker
        env:
          ADMIN_API_TOKEN: ${{ secrets.ADMIN_API_TOKEN }}
          WORKER_ADMIN_INGEST_URL: ${{ secrets.WORKER_ADMIN_INGEST_URL }}
        run: |
          echo '{"servers": '$(python -c "import yaml, json; print(json.dumps(yaml.safe_load(open('mcp_registry.yaml'))['servers']))")'}' > payload.json
          curl -fsSL -X POST "$WORKER_ADMIN_INGEST_URL" \
               -H "authorization: Bearer $ADMIN_API_TOKEN" \
               -H 'content-type: application/json' \
               --data-binary @payload.json


# ---------------------------------------------
# File: PAGES-README.md
# ---------------------------------------------
Minimal Pages site plan:
1) Static index.html fetches /registry/mcp_registry.json and renders a searchable table.
2) Optional: call /api/servers for tag/category filters.
3) Secure admin views with Cloudflare Access (optional).


# ---------------------------------------------
# File: bw_askpass.sh  (from v1)
# ---------------------------------------------
#!/usr/bin/env bash
set -euo pipefail
: "${BW_ITEM:=}"; : "${BW_FIELD:=password}"; : "${BW_QUERY:=}"; : "${BW_SESSION:=}"
log() { printf "[bw_askpass] %s\n" "$*" >&2; }
err() { printf "[bw_askpass:ERROR] %s\n" "$*" >&2; exit 1; }
command -v bw >/dev/null 2>&1 || err "Bitwarden CLI (bw) not installed"
[[ -n "${BW_SESSION}" ]] || err "BW_SESSION not set. Run: bw unlock --raw"
set +e
if [[ -n "${BW_ITEM}" ]]; then
  out=$(bw get item --session "$BW_SESSION" "$BW_ITEM" 2>/dev/null)
else
  [[ -n "${BW_QUERY}" ]] || err "Specify BW_ITEM or BW_QUERY"
  match=$(bw list items --search "$BW_QUERY" --session "$BW_SESSION" | jq -r '.[0].id // empty')
  [[ -n "$match" ]] || err "No items match query: $BW_QUERY"
  out=$(bw get item --session "$BW_SESSION" "$match" 2>/dev/null)
fi
rc=$?; set -e
[[ $rc -eq 0 ]] || err "bw get item failed"
secret=$(printf '%s' "$out" | jq -r --arg field "$BW_FIELD" 'if $field == "password" then .login.password // empty else (.fields // []) | map(select(.name==$field)) | .[0].value // empty end')
[[ -n "$secret" ]] || err "field not found: $BW_FIELD"
printf '%s' "$secret"
