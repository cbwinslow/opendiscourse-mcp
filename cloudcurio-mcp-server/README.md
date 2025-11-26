# cloudcurio-mcp-server

Reusable MCP server exposing homelab + Cloudcurio registry tools over HTTP.

## Quickstart

```bash
npm install
npm run dev   # or: npm run build && npm start
```

Environment variables:

- `PORT` (default `3000`)
- `MCP_AUTH_TOKEN` (optional bearer token for `/mcp`)
- `ALLOWED_HTTP_BASES` (comma-separated URL prefixes for `http_get_json`)
- `REGISTRY_ROOT` (path to the `cloudcurio` registry folder)
- `DB_PASS_*` env vars for any databases in `databases.yaml`.

Then point your MCP client at:

```text
http://<host>:3000/mcp
```

with `Authorization: Bearer $MCP_AUTH_TOKEN` if set.
