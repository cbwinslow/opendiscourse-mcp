/**
 * Script name : cloudcurio-mcp-server
 * Author      : cbwinslow + ChatGPT (MCP buddy)
 * Date        : 2025-11-20
 * Summary     :
 *   HTTP-based MCP server using the official TypeScript SDK.
 *   Exposes:
 *     - Core homelab tools (system info, ping, Docker, HTTP fetch)
 *     - Cloudcurio registry views (agents, databases, SSH profiles,
 *       dotfiles, inference endpoints)
 *     - DB + SSH health checks (db_ping, ssh_can_connect)
 *   Deployable on Proxmox (Docker/VM) and reachable via Cloudflare
 *   Tunnel as a remote MCP server.
 *
 * Inputs      :
 *   - HTTP POST /mcp with MCP JSON-RPC payloads (from Claude / other MCP clients)
 *   - Optional Authorization: Bearer <MCP_AUTH_TOKEN>
 *
 * Outputs     :
 *   - MCP-compliant JSON-RPC responses over HTTP
 *
 * Env vars    :
 *   PORT                -> HTTP port to listen on (default: 3000)
 *   MCP_AUTH_TOKEN      -> If set, required Bearer token for /mcp
 *   ALLOWED_HTTP_BASES  -> Comma-separated list of URL prefixes the
 *                          http_get_json tool can call
 *   REGISTRY_ROOT       -> Path to cloudcurio registry config folder
 *                          (default: ../registry/cloudcurio)
 *   DB_PASS_*           -> Password env vars referenced in databases.yaml
 *
 * Notes       :
 *   - Uses Streamable HTTP transport from the official MCP TS SDK
 *   - Designed to be extended with more tools and resources over time
 *
 * Modification log:
 *   - 0.1.0 (2025-11-20): Initial version with core tools and HTTP transport
 *   - 0.2.0 (2025-11-20): Cloudcurio registry integration + db_ping +
 *                         ssh_can_connect tools
 */

import express from "express";
import cors from "cors";
import morgan from "morgan";
import os from "os";
import fs from "node:fs";
import path from "node:path";
import { execFile } from "child_process";
import { promisify } from "node:util";

import { McpServer, ResourceTemplate } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import * as z from "zod/v4";
import YAML from "yaml";
import { Client as PgClient } from "pg";

// ---------- Constants & helpers -------------------------------------------------

const execFileAsync = promisify(execFile);

const PORT = parseInt(process.env.PORT || "3000", 10);
const MCP_AUTH_TOKEN = process.env.MCP_AUTH_TOKEN || "";

// Comma-separated list of allowed URL prefixes, e.g.
// "https://api.github.com,https://stats.nba.com".
// This keeps http_get_json from becoming an open proxy.
const ALLOWED_HTTP_BASES: string[] = (process.env.ALLOWED_HTTP_BASES || "")
  .split(",")
  .map((s) => s.trim())
  .filter((s) => s.length > 0);

function isUrlAllowed(target: string): boolean {
  if (ALLOWED_HTTP_BASES.length === 0) {
    // If not configured, be conservative and deny.
    return false;
  }
  return ALLOWED_HTTP_BASES.some((prefix) => target.startsWith(prefix));
}

function validateHost(host: string): void {
  const hostPattern = /^[a-zA-Z0-9.-]+$/;
  if (!hostPattern.test(host) || host.length > 253) {
    throw new Error("Invalid host. Only letters, digits, dots and dashes are allowed.");
  }
}

function expandTilde(p?: string): string | undefined {
  if (!p) return undefined;
  if (p === "~") return os.homedir();
  if (p.startsWith("~/")) {
    return path.join(os.homedir(), p.slice(2));
  }
  return p;
}

// ---------- Cloudcurio registry config loaders ---------------------------------

const REGISTRY_ROOT = process.env.REGISTRY_ROOT || path.resolve("..", "registry", "cloudcurio");

export type AgentConfig = {
  id: string;
  name: string;
  description?: string;
  type: string;
  mcp_server_url?: string;
  api_base_url?: string;
  tools?: string[];
  tags?: string[];
};

export type DatabaseConfig = {
  id: string;
  engine: "postgres" | "mysql" | "sqlite" | string;
  host: string;
  port: number;
  database: string;
  user: string;
  password_env?: string;
  tags?: string[];
};

export type SshProfile = {
  id: string;
  host: string;
  port: number;
  user: string;
  key_path?: string;
  tags?: string[];
};

export type DotfilesConfig = {
  dotfiles: {
    tool: string;
    repo: string;
    bootstrap_script?: string;
    tags?: string[];
  };
  profiles?: {
    id: string;
    host_pattern: string;
    branches?: string[];
  }[];
};

export type InferenceEndpoint = {
  id: string;
  provider: string;
  base_url: string;
  model: string;
  api_key_env?: string;
  tags?: string[];
};

function safeLoadYaml<T>(fileName: string): T | null {
  try {
    const fullPath = path.join(REGISTRY_ROOT, fileName);
    const raw = fs.readFileSync(fullPath, "utf8");
    return YAML.parse(raw) as T;
  } catch (err) {
    console.warn(`Failed to load ${fileName} from ${REGISTRY_ROOT}:`, err);
    return null;
  }
}

function loadAgents(): AgentConfig[] {
  const data = safeLoadYaml<{ agents?: AgentConfig[] }>("agents.yaml");
  return data?.agents ?? [];
}

function loadDatabases(): DatabaseConfig[] {
  const data = safeLoadYaml<{ databases?: DatabaseConfig[] }>("databases.yaml");
  return data?.databases ?? [];
}

function loadSshProfiles(): SshProfile[] {
  const data = safeLoadYaml<{ ssh_profiles?: SshProfile[] }>("ssh_profiles.yaml");
  return data?.ssh_profiles ?? [];
}

function loadDotfiles(): DotfilesConfig | null {
  return safeLoadYaml<DotfilesConfig>("dotfiles.yaml");
}

function loadInference(): InferenceEndpoint[] {
  const data = safeLoadYaml<{ endpoints?: InferenceEndpoint[] }>("inference.yaml");
  return data?.endpoints ?? [];
}

// ---------- MCP server setup ----------------------------------------------------

const server = new McpServer({
  name: "cloudcurio-mcp",
  version: "0.2.0",
});

// ----- Tool: system_info --------------------------------------------------------

server.registerTool(
  "system_info",
  {
    title: "System Info",
    description: "Get basic system information about the MCP host (OS, CPU, memory).",
    inputSchema: {},
    outputSchema: {
      hostname: z.string(),
      platform: z.string(),
      release: z.string(),
      cpus: z.array(
        z.object({
          model: z.string(),
          speedMHz: z.number(),
        })
      ),
      totalMemMB: z.number(),
      freeMemMB: z.number(),
      uptimeSeconds: z.number(),
    },
  },
  async () => {
    const cpus = os.cpus().map((cpu) => ({
      model: cpu.model,
      speedMHz: cpu.speed,
    }));

    const payload = {
      hostname: os.hostname(),
      platform: os.platform(),
      release: os.release(),
      cpus,
      totalMemMB: Math.round(os.totalmem() / (1024 * 1024)),
      freeMemMB: Math.round(os.freemem() / (1024 * 1024)),
      uptimeSeconds: os.uptime(),
    };

    const text = JSON.stringify(payload, null, 2);

    return {
      content: [{ type: "text", text }],
      structuredContent: payload,
    };
  }
);

// ----- Tool: ping_host ---------------------------------------------------------

server.registerTool(
  "ping_host",
  {
    title: "Ping Host",
    description: "Run a short ping to a host from the MCP server (ICMP reachability check).",
    inputSchema: {
      host: z.string(),
      count: z.number().int().min(1).max(5).default(3),
    },
    outputSchema: {
      exitCode: z.number(),
      stdout: z.string(),
      stderr: z.string(),
    },
  },
  async ({ host, count }) => {
    validateHost(host);

    const args = ["-c", String(count ?? 3), host];

    try {
      const { stdout, stderr } = await execFileAsync("ping", args, {
        timeout: 15_000,
      });

      const payload = {
        exitCode: 0,
        stdout,
        stderr,
      };

      return {
        content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
        structuredContent: payload,
      };
    } catch (err: unknown) {
      const error = err as { code?: number; stdout?: string; stderr?: string };

      const payload = {
        exitCode: typeof error.code === "number" ? error.code : 1,
        stdout: error.stdout || "",
        stderr: error.stderr || String(err),
      };

      return {
        content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
        structuredContent: payload,
      };
    }
  }
);

// ----- Tool: docker_list_containers -------------------------------------------

server.registerTool(
  "docker_list_containers",
  {
    title: "Docker: List Containers",
    description:
      "List Docker containers on the MCP server host using `docker ps`. Requires Docker CLI and permissions.",
    inputSchema: {},
    outputSchema: {
      output: z.string(),
    },
  },
  async () => {
    try {
      const { stdout } = await execFileAsync("docker", [
        "ps",
        "--format",
        "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}",
      ]);

      const payload = { output: stdout };
      return {
        content: [
          {
            type: "text",
            text: stdout || "No containers or docker ps returned empty output.",
          },
        ],
        structuredContent: payload,
      };
    } catch (err) {
      const message = `Failed to run docker ps: ${String(err)}`;
      const payload = { output: message };
      return {
        content: [{ type: "text", text: message }],
        structuredContent: payload,
      };
    }
  }
);

// ----- Tool: http_get_json -----------------------------------------------------

server.registerTool(
  "http_get_json",
  {
    title: "HTTP GET (JSON)",
    description:
      "Fetch JSON from an allow-listed HTTP(S) endpoint. Configure ALLOWED_HTTP_BASES env var to control targets.",
    inputSchema: {
      url: z.string().url(),
    },
    outputSchema: {
      status: z.number(),
      data: z.unknown(),
    },
  },
  async ({ url }) => {
    if (!isUrlAllowed(url)) {
      const message =
        "Requested URL is not in ALLOWED_HTTP_BASES. Update env config to permit this endpoint.";
      return {
        content: [{ type: "text", text: message }],
        structuredContent: { status: 0, data: { error: message } },
      };
    }

    const res = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json, text/plain;q=0.8, */*;q=0.1",
      },
    });

    let data: unknown;
    const text = await res.text();

    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }

    const payload = {
      status: res.status,
      data,
    };

    return {
      content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
      structuredContent: payload,
    };
  }
);

// ----- Tool: registry_list -----------------------------------------------------

server.registerTool(
  "registry_list",
  {
    title: "Registry: List items",
    description:
      "List items from the cloudcurio registry (agents, databases, ssh_profiles, inference, dotfiles).",
    inputSchema: {
      section: z.enum(["agents", "databases", "ssh_profiles", "inference", "dotfiles"]),
    },
    outputSchema: {
      items: z.array(z.unknown()),
    },
  },
  async ({ section }) => {
    let items: unknown[] = [];

    switch (section) {
      case "agents":
        items = loadAgents();
        break;
      case "databases":
        items = loadDatabases();
        break;
      case "ssh_profiles":
        items = loadSshProfiles();
        break;
      case "inference":
        items = loadInference();
        break;
      case "dotfiles": {
        const cfg = loadDotfiles();
        items = cfg ? [cfg] : [];
        break;
      }
    }

    const text = JSON.stringify({ section, items }, null, 2);
    return {
      content: [{ type: "text", text }],
      structuredContent: { items },
    };
  }
);

// ----- Tool: registry_get ------------------------------------------------------

server.registerTool(
  "registry_get",
  {
    title: "Registry: Get single item",
    description:
      "Get a specific item from the cloudcurio registry by section and id (where applicable).",
    inputSchema: {
      section: z.enum(["agents", "databases", "ssh_profiles", "inference"]),
      id: z.string(),
    },
    outputSchema: {
      item: z.unknown().nullable(),
    },
  },
  async ({ section, id }) => {
    let item: unknown | null = null;

    switch (section) {
      case "agents":
        item = loadAgents().find((a) => a.id === id) ?? null;
        break;
      case "databases":
        item = loadDatabases().find((d) => d.id === id) ?? null;
        break;
      case "ssh_profiles":
        item = loadSshProfiles().find((s) => s.id === id) ?? null;
        break;
      case "inference":
        item = loadInference().find((e) => e.id === id) ?? null;
        break;
    }

    const text = JSON.stringify({ section, id, item }, null, 2);
    return {
      content: [{ type: "text", text }],
      structuredContent: { item },
    };
  }
);

// ----- Tool: db_ping -----------------------------------------------------------

server.registerTool(
  "db_ping",
  {
    title: "Database: Ping",
    description:
      "Run a simple SELECT 1 against a configured database (from databases.yaml) to verify connectivity.",
    inputSchema: {
      databaseId: z.string(),
    },
    outputSchema: {
      databaseId: z.string(),
      success: z.boolean(),
      latencyMs: z.number().nullable(),
      error: z.string().nullable(),
    },
  },
  async ({ databaseId }) => {
    const db = loadDatabases().find((d) => d.id === databaseId);
    if (!db) {
      const message = `Database with id '${databaseId}' not found in registry.`;
      return {
        content: [{ type: "text", text: message }],
        structuredContent: {
          databaseId,
          success: false,
          latencyMs: null,
          error: message,
        },
      };
    }

    const password = db.password_env ? process.env[db.password_env] : undefined;

    const client = new PgClient({
      host: db.host,
      port: db.port,
      database: db.database,
      user: db.user,
      password,
    });

    const start = Date.now();
    try {
      await client.connect();
      await client.query("SELECT 1 AS ok");
      const latencyMs = Date.now() - start;

      const payload = {
        databaseId,
        success: true,
        latencyMs,
        error: null,
      };

      return {
        content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
        structuredContent: payload,
      };
    } catch (err) {
      const latencyMs = Date.now() - start;
      const message = `db_ping failed for '${databaseId}': ${String(err)}`;
      const payload = {
        databaseId,
        success: false,
        latencyMs,
        error: message,
      };

      return {
        content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
        structuredContent: payload,
      };
    } finally {
      try {
        await client.end();
      } catch (err) {
        console.warn("Error closing PG client:", err);
      }
    }
  }
);

// ----- Tool: ssh_can_connect ---------------------------------------------------

server.registerTool(
  "ssh_can_connect",
  {
    title: "SSH: Connectivity check",
    description:
      "Check whether SSH can connect to a configured profile (from ssh_profiles.yaml) using BatchMode.",
    inputSchema: {
      profileId: z.string(),
    },
    outputSchema: {
      profileId: z.string(),
      success: z.boolean(),
      exitCode: z.number(),
      stdout: z.string(),
      stderr: z.string(),
    },
  },
  async ({ profileId }) => {
    const profile = loadSshProfiles().find((p) => p.id === profileId);
    if (!profile) {
      const message = `SSH profile with id '${profileId}' not found in registry.`;
      const payload = {
        profileId,
        success: false,
        exitCode: 1,
        stdout: "",
        stderr: message,
      };
      return {
        content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
        structuredContent: payload,
      };
    }

    const keyPath = expandTilde(profile.key_path);

    const args: string[] = [
      "-o",
      "BatchMode=yes",
      "-o",
      "ConnectTimeout=5",
      "-p",
      String(profile.port),
    ];

    if (keyPath) {
      args.push("-i", keyPath);
    }

    const destination = `${profile.user}@${profile.host}`;
    args.push(destination, "echo", "ok");

    try {
      const { stdout, stderr } = await execFileAsync("ssh", args, {
        timeout: 15_000,
      });

      const payload = {
        profileId,
        success: true,
        exitCode: 0,
        stdout,
        stderr,
      };

      return {
        content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
        structuredContent: payload,
      };
    } catch (err: unknown) {
      const error = err as { code?: number; stdout?: string; stderr?: string };
      const payload = {
        profileId,
        success: false,
        exitCode: typeof error.code === "number" ? error.code : 1,
        stdout: error.stdout || "",
        stderr: error.stderr || String(err),
      };

      return {
        content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
        structuredContent: payload,
      };
    }
  }
);

// ----- Resource: /cloudcurio/mcp/manifest -------------------------------------

server.registerResource(
  "cloudcurio-manifest",
  new ResourceTemplate("cloudcurio://manifest", { list: undefined }),
  {
    title: "Cloudcurio MCP Manifest",
    description: "High-level description of this MCP server and its tools.",
  },
  async (uri) => ({
    contents: [
      {
        uri: uri.href,
        text: `cloudcurio-mcp-server v0.2.0

Tools:
  - system_info: report OS, CPU, memory and uptime
  - ping_host: ICMP ping from server to target host
  - docker_list_containers: list Docker containers (if Docker is present)
  - http_get_json: safe HTTP GET for JSON from allow-listed APIs
  - registry_list: list items from the cloudcurio registry
  - registry_get: get a specific registry item
  - db_ping: check connectivity to configured databases
  - ssh_can_connect: verify SSH connectivity for configured profiles

Deployment:
  - Intended to run on homelab servers (Proxmox / bare metal / VMs)
  - Typically exposed to the internet via Cloudflare Tunnel
  - Used as a remote MCP server for Claude and other clients
`,
      },
    ],
  })
);

// ---------- HTTP server + MCP transport ----------------------------------------

const app = express();

// Basic middleware
app.use(express.json({ limit: "1mb" }));
app.use(cors());
app.use(morgan("combined"));

// Health / info endpoints
app.get("/", (_req, res) => {
  res.json({
    ok: true,
    name: "cloudcurio-mcp-server",
    version: "0.2.0",
    mcpEndpoint: "/mcp",
  });
});

app.get("/healthz", (_req, res) => {
  res.status(200).json({ status: "ok" });
});

// Simple bearer-token auth for /mcp if MCP_AUTH_TOKEN is set.
app.use("/mcp", (req, res, next) => {
  if (!MCP_AUTH_TOKEN) {
    return next();
  }

  const authHeader = req.header("authorization") || "";
  const expected = `Bearer ${MCP_AUTH_TOKEN}`;

  if (authHeader !== expected) {
    return res.status(401).json({ error: "Unauthorized MCP request" });
  }

  return next();
});

// Main MCP endpoint
app.post("/mcp", async (req, res) => {
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
    enableJsonResponse: true,
  });

  // Ensure we close the transport if the client disconnects.
  res.on("close", () => {
    transport.close().catch((err) => {
      console.error("Transport close error:", err);
    });
  });

  try {
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (err) {
    console.error("Error handling MCP request:", err);
    if (!res.headersSent) {
      res.status(500).json({ error: "Internal MCP server error" });
    }
  }
});

// Fallback 404
app.use((req, res) => {
  res.status(404).json({ error: "Not found", path: req.path });
});

// Start the HTTP server
app
  .listen(PORT, () => {
    console.log(`cloudcurio-mcp-server listening on http://0.0.0.0:${PORT}`);
    if (ALLOWED_HTTP_BASES.length === 0) {
      console.warn(
        "WARNING: ALLOWED_HTTP_BASES is empty. http_get_json will reject all requests until configured."
      );
    }
    console.log(`Using REGISTRY_ROOT=${REGISTRY_ROOT}`);
  })
  .on("error", (err) => {
    console.error("Fatal HTTP server error:", err);
    process.exit(1);
  });

// End of src/server.ts
