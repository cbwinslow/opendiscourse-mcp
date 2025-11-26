/**
 * File: src/index.ts
 * Project: Cloudflare multi-source ingestor
 * Author: CBW + GPT-5.1 Thinking
 * Date: 2025-11-20
 *
 * Summary:
 *   Cloudflare Worker that coordinates ingestion from multiple public
 *   civic-data APIs (govinfo, Congress API, OpenStates) into a single
 *   Postgres warehouse running in your homelab, via Cloudflare Hyperdrive.
 *
 *   The design is intentionally generic:
 *     - One Worker binary, parameterized by `source` query param.
 *     - Shared library of helpers for Postgres access, sync state, and
 *       raw JSON storage.
 *     - Source-specific ingestion functions that fetch a batch of records
 *       and map them into the generic `raw_ingest` table.
 *
 *   This gives you a stable ingestion core you can re-use from many
 *   Workers or Cron triggers, and lets you add new sources later without
 *   rewriting plumbing.
 *
 * HTTP Interface:
 *   GET /ingest?source=govinfo|congress|openstates
 *              [&limit=200]
 *              [&cursorOverride=...]   (optional JSON string; mostly for testing)
 *
 *   Examples:
 *     - /ingest?source=govinfo&limit=100
 *     - /ingest?source=congress&limit=50
 *     - /ingest?source=openstates
 *
 *   Each call processes at most `limit` records per invocation to avoid
 *   long-running Workers. You can chain multiple calls with Cron or
 *   external orchestration.
 *
 * Env Bindings (wrangler.toml):
 *   HYPERDRIVE:   Hyperdrive binding with `connectionString` to homelab Postgres
 *   GOVINFO_API_KEY:  string
 *   CONGRESS_API_KEY: string
 *   OPENSTATES_API_KEY: string
 *
 * Database Schema (Postgres via Hyperdrive):
 *
 *   -- Generic raw ingestion store (per-source, per-record JSON)
 *   CREATE TABLE IF NOT EXISTS raw_ingest (
 *     source       TEXT NOT NULL,
 *     record_id    TEXT NOT NULL,
 *     fetched_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 *     payload      JSONB NOT NULL,
 *     PRIMARY KEY (source, record_id)
 *   );
 *
 *   -- Sync state per source (cursor can be arbitrary JSON)
 *   CREATE TABLE IF NOT EXISTS ingest_sync_state (
 *     source       TEXT PRIMARY KEY,
 *     cursor       JSONB,
 *     last_run_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
 *   );
 *
 *   This keeps ingestion plumbing unified and lets you build normalized
 *   tables and views downstream (in your OpenDiscourse stack) without
 *   coupling them to how the APIs paginate.
 */

import postgres from "postgres";

// ------------------------- Types & Env --------------------------------------

interface Env {
  HYPERDRIVE: {
    connectionString: string;
  };

  GOVINFO_API_KEY: string;
  CONGRESS_API_KEY: string;
  OPENSTATES_API_KEY: string;
}

/** Generic representation of a unit of data ingested from a source. */
interface IngestRecord {
  recordId: string;      // unique per-source ID (e.g., packageId, billId)
  payload: unknown;      // raw JSON from upstream API
}

/** Result from a single ingestion run for a source. */
interface IngestResult {
  processed: number;
  errors: number;
  newCursor: unknown | null;  // new cursor to store, or null if unchanged
}

// Cursor shapes for specific sources (kept loose on purpose)
interface GovinfoCursor {
  sinceIso: string;  // we use a since-timestamp model for govinfo
}

interface CongressCursor {
  page: number;
}

interface OpenStatesCursor {
  page: number;
}

// ------------------------- Postgres Helpers ---------------------------------

/**
 * Create a postgres.js client against the Hyperdrive connection string
 * and run a handler with it. Ensures clean shutdown and basic error
 * isolation.
 */
async function withPostgres<T>(env: Env, handler: (sql: postgres.Sql) => Promise<T>): Promise<T> {
  const sql = postgres(env.HYPERDRIVE.connectionString, {
    max: 5,
    fetch_types: false,
    prepare: true,
  });

  try {
    return await handler(sql);
  } finally {
    await sql.end({ timeout: 5_000 }).catch(() => {
      // swallow close errors so they don't mask ingestion issues
    });
  }
}

/** Ensure the generic raw_ingest + ingest_sync_state tables exist. */
async function ensureCoreSchema(env: Env): Promise<void> {
  await withPostgres(env, async (sql) => {
    await sql.begin(async (trx) => {
      await trx`
        CREATE TABLE IF NOT EXISTS raw_ingest (
          source      TEXT NOT NULL,
          record_id   TEXT NOT NULL,
          fetched_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          payload     JSONB NOT NULL,
          PRIMARY KEY (source, record_id)
        );
      `;

      await trx`
        CREATE TABLE IF NOT EXISTS ingest_sync_state (
          source      TEXT PRIMARY KEY,
          cursor      JSONB,
          last_run_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
      `;
    });
  });
}

/** Retrieve the last stored cursor for a given source, if any. */
async function getCursor(env: Env, source: string): Promise<unknown | null> {
  return await withPostgres(env, async (sql) => {
    const rows = await sql<{ cursor: unknown }[]>`
      SELECT cursor FROM ingest_sync_state WHERE source = ${source} LIMIT 1;
    `;
    if (rows.length === 0) return null;
    return rows[0].cursor ?? null;
  });
}

/** Upsert the cursor for a given source. */
async function setCursor(env: Env, source: string, cursor: unknown | null): Promise<void> {
  await withPostgres(env, async (sql) => {
    await sql`
      INSERT INTO ingest_sync_state (source, cursor, last_run_at)
      VALUES (${source}, ${cursor as any}, NOW())
      ON CONFLICT (source) DO UPDATE
      SET cursor = EXCLUDED.cursor,
          last_run_at = EXCLUDED.last_run_at;
    `;
  });
}

/**
 * Persist a batch of records for a given source into raw_ingest with
 * upsert semantics.
 */
async function upsertRawBatch(env: Env, source: string, records: IngestRecord[]): Promise<void> {
  if (records.length === 0) return;

  await withPostgres(env, async (sql) => {
    await sql.begin(async (trx) => {
      for (const rec of records) {
        await trx`
          INSERT INTO raw_ingest (source, record_id, payload)
          VALUES (${source}, ${rec.recordId}, ${trx.json(rec.payload)})
          ON CONFLICT (source, record_id) DO UPDATE
          SET payload = EXCLUDED.payload,
              fetched_at = NOW();
        `;
      }
    });
  });
}

// ------------------------- HTTP fetch helpers -------------------------------

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} from ${url}`);
  }
  return (await res.json()) as T;
}

// ------------------------- govinfo ingestion --------------------------------

interface GovinfoCollectionPage {
  count: number;
  message: string | null;
  nextPage: string | null;
  previousPage: string | null;
  packages: Array<{
    packageId: string;
    lastModified: string;
    packageLink: string;
  }>;
}

interface GovinfoPackageSummary {
  packageId: string;
  title?: string;
  collectionCode?: string;
  collectionName?: string;
  dateIssued?: string;
  lastModified?: string;
  branch?: string;
  congress?: string;
  session?: string;
  documentType?: string;
  category?: string;
  download?: Record<string, unknown>;
  [key: string]: unknown;
}

function defaultGovinfoCursor(): GovinfoCursor {
  const d = new Date();
  d.setDate(d.getDate() - 7); // default: last 7 days
  return { sinceIso: d.toISOString() };
}

function normalizeGovinfoCursor(cursor: unknown | null): GovinfoCursor {
  if (!cursor || typeof cursor !== "object") return defaultGovinfoCursor();
  const c = cursor as Partial<GovinfoCursor>;
  if (!c.sinceIso) return defaultGovinfoCursor();
  return { sinceIso: c.sinceIso };
}

function buildGovinfoCollectionsUrl(
  collection: string,
  sinceIso: string,
  apiKey: string,
  pageSize = 50,
  offsetMark: string | null = "*",
): string {
  const base = new URL(
    `https://api.govinfo.gov/collections/${encodeURIComponent(collection)}/${encodeURIComponent(
      sinceIso,
    )}`,
  );
  base.searchParams.set("pageSize", String(pageSize));
  base.searchParams.set("api_key", apiKey);
  if (offsetMark) {
    base.searchParams.set("offsetMark", offsetMark);
  }
  return base.toString();
}

async function fetchGovinfoPackageSummary(
  packageId: string,
  apiKey: string,
): Promise<GovinfoPackageSummary> {
  const url = `https://api.govinfo.gov/packages/${encodeURIComponent(
    packageId,
  )}/summary?api_key=${encodeURIComponent(apiKey)}`;
  return await fetchJson<GovinfoPackageSummary>(url);
}

/**
 * Ingest a batch of govinfo packages as raw JSON.
 *
 * Strategy:
 *   - Use `sinceIso` from cursor (or default to last 7 days).
 *   - Fetch one collections page at a time, up to `limit` package summaries.
 *   - Store each summary into raw_ingest with source = 'govinfo'.
 *   - Return an updated cursor that bumps `sinceIso` to now.
 */
async function ingestGovinfoBatch(
  env: Env,
  cursor: GovinfoCursor,
  limit: number,
): Promise<IngestResult> {
  if (!env.GOVINFO_API_KEY) {
    throw new Error("Missing GOVINFO_API_KEY env binding");
  }

  const collection = "BILLS"; // you can parameterize this later if desired

  let processed = 0;
  let errors = 0;

  let nextUrl: string | null = buildGovinfoCollectionsUrl(
    collection,
    cursor.sinceIso,
    env.GOVINFO_API_KEY,
    Math.min(limit, 50),
    "*",
  );

  const batch: IngestRecord[] = [];

  while (nextUrl && processed < limit) {
    const page = await fetchJson<GovinfoCollectionPage>(nextUrl);

    for (const pkg of page.packages ?? []) {
      if (processed >= limit) break;
      try {
        const summary = await fetchGovinfoPackageSummary(
          pkg.packageId,
          env.GOVINFO_API_KEY,
        );
        batch.push({ recordId: summary.packageId, payload: summary });
        processed += 1;
      } catch (err) {
        errors += 1;
        console.error("govinfo ingest error", pkg.packageId, (err as Error).message);
      }
    }

    if (processed >= limit) break;
    nextUrl = page.nextPage ? `${page.nextPage}&api_key=${env.GOVINFO_API_KEY}` : null;
  }

  await upsertRawBatch(env, "govinfo", batch);

  const newCursor: GovinfoCursor = { sinceIso: new Date().toISOString() };

  return { processed, errors, newCursor };
}

// ------------------------- Congress API ingestion ---------------------------

/**
 * NOTE: This is a deliberately generic / minimal ingestion for Congress API.
 * It uses a simple paging model and stores bill JSON blobs into raw_ingest
 * with source = 'congress'. You can expand this to handle more resources
 * (amendments, summaries, votes) using the same pattern.
 */

interface CongressBillPage<T = unknown> {
  pagination?: {
    count?: number;
    page?: number;
    per_page?: number;
    pages?: number;
    next?: string | null;
  };
  bills?: T[];
  results?: T[]; // some endpoints use `results`
  [key: string]: unknown;
}

function defaultCongressCursor(): CongressCursor {
  return { page: 1 };
}

function normalizeCongressCursor(cursor: unknown | null): CongressCursor {
  if (!cursor || typeof cursor !== "object") return defaultCongressCursor();
  const c = cursor as Partial<CongressCursor>;
  if (!c.page || c.page < 1) return defaultCongressCursor();
  return { page: c.page };
}

async function ingestCongressBatch(
  env: Env,
  cursor: CongressCursor,
  limit: number,
): Promise<IngestResult> {
  if (!env.CONGRESS_API_KEY) {
    throw new Error("Missing CONGRESS_API_KEY env binding");
  }

  const perPage = Math.min(50, limit);

  let processed = 0;
  let errors = 0;
  let page = cursor.page;

  const batch: IngestRecord[] = [];

  while (processed < limit) {
    const url = new URL("https://api.congress.gov/v3/bill");
    url.searchParams.set("api_key", env.CONGRESS_API_KEY);
    url.searchParams.set("page", String(page));
    url.searchParams.set("pageSize", String(perPage));

    const data = await fetchJson<CongressBillPage>(url.toString());
    const billsArray = (data.bills ?? data.results ?? []) as any[];

    if (!billsArray.length) break;

    for (const bill of billsArray) {
      if (processed >= limit) break;
      try {
        const recordId = String(
          bill.billNumber ?? bill.bill_id ?? bill.number ?? `${page}-${processed}`,
        );
        batch.push({ recordId, payload: bill });
        processed += 1;
      } catch (err) {
        errors += 1;
        console.error("congress ingest error", (err as Error).message);
      }
    }

    if (processed >= limit) break;

    const totalPages = data.pagination?.pages ?? page;
    if (page >= totalPages) break;
    page += 1;
  }

  await upsertRawBatch(env, "congress", batch);

  const newCursor: CongressCursor = { page };
  return { processed, errors, newCursor };
}

// ------------------------- OpenStates ingestion -----------------------------

/**
 * Minimal OpenStates v3 ingestion for bills. This follows a simple `page`
 * cursor and stores each bill JSON into raw_ingest with source = 'openstates'.
 */

interface OpenStatesBillPage<T = unknown> {
  pagination?: {
    page?: number;
    max_page?: number;
    per_page?: number;
  };
  results?: T[];
  [key: string]: unknown;
}

function defaultOpenStatesCursor(): OpenStatesCursor {
  return { page: 1 };
}

function normalizeOpenStatesCursor(cursor: unknown | null): OpenStatesCursor {
  if (!cursor || typeof cursor !== "object") return defaultOpenStatesCursor();
  const c = cursor as Partial<OpenStatesCursor>;
  if (!c.page || c.page < 1) return defaultOpenStatesCursor();
  return { page: c.page };
}

async function ingestOpenStatesBatch(
  env: Env,
  cursor: OpenStatesCursor,
  limit: number,
): Promise<IngestResult> {
  if (!env.OPENSTATES_API_KEY) {
    throw new Error("Missing OPENSTATES_API_KEY env binding");
  }

  const perPage = Math.min(50, limit);

  let processed = 0;
  let errors = 0;
  let page = cursor.page;

  const batch: IngestRecord[] = [];

  while (processed < limit) {
    const url = new URL("https://v3.openstates.org/bills");
    url.searchParams.set("apikey", env.OPENSTATES_API_KEY);
    url.searchParams.set("page", String(page));
    url.searchParams.set("per_page", String(perPage));

    const data = await fetchJson<OpenStatesBillPage>(url.toString());
    const billsArray = (data.results ?? []) as any[];

    if (!billsArray.length) break;

    for (const bill of billsArray) {
      if (processed >= limit) break;
      try {
        const recordId = String(
          bill.id ?? bill.openstates_bill_id ?? `${page}-${processed}`,
        );
        batch.push({ recordId, payload: bill });
        processed += 1;
      } catch (err) {
        errors += 1;
        console.error("openstates ingest error", (err as Error).message);
      }
    }

    if (processed >= limit) break;

    const maxPage = data.pagination?.max_page ?? page;
    if (page >= maxPage) break;
    page += 1;
  }

  await upsertRawBatch(env, "openstates", batch);

  const newCursor: OpenStatesCursor = { page };
  return { processed, errors, newCursor };
}

// ------------------------- Dispatcher & Worker -------------------------------

async function runSourceIngest(
  env: Env,
  source: string,
  limit: number,
  cursorOverride?: unknown,
): Promise<IngestResult & { source: string } > {
  await ensureCoreSchema(env);

  const existingCursor = cursorOverride ?? (await getCursor(env, source));

  let result: IngestResult;

  switch (source) {
    case "govinfo": {
      const cur = normalizeGovinfoCursor(existingCursor);
      result = await ingestGovinfoBatch(env, cur, limit);
      break;
    }
    case "congress": {
      const cur = normalizeCongressCursor(existingCursor);
      result = await ingestCongressBatch(env, cur, limit);
      break;
    }
    case "openstates": {
      const cur = normalizeOpenStatesCursor(existingCursor);
      result = await ingestOpenStatesBatch(env, cur, limit);
      break;
    }
    default:
      throw new Error(`Unknown source: ${source}`);
  }

  // Persist cursor if changed
  if (result.newCursor !== null) {
    await setCursor(env, source, result.newCursor);
  }

  return { ...result, source };
}

export default {
  async fetch(request: Request, env: Env, _ctx: ExecutionContext): Promise<Response> {
    try {
      const url = new URL(request.url);
      if (url.pathname !== "/ingest") {
        return new Response("Not found", { status: 404 });
      }

      const source = (url.searchParams.get("source") ?? "govinfo").toLowerCase();
      const limitRaw = url.searchParams.get("limit");
      const limit = (() => {
        const n = Number(limitRaw ?? "100");
        if (!Number.isFinite(n) || n <= 0) return 100;
        return Math.min(500, Math.floor(n)); // hard cap to keep runs fast
      })();

      const cursorOverrideParam = url.searchParams.get("cursorOverride");
      let cursorOverride: unknown | undefined;
      if (cursorOverrideParam) {
        try {
          cursorOverride = JSON.parse(cursorOverrideParam);
        } catch (err) {
          return new Response("Invalid cursorOverride JSON", { status: 400 });
        }
      }

      const result = await runSourceIngest(env, source, limit, cursorOverride);

      return new Response(JSON.stringify(result, null, 2), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    } catch (err) {
      console.error("Fatal worker error", (err as Error).message);
      return new Response("Internal error", { status: 500 });
    }
  },
};
