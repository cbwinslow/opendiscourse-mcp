#!/usr/bin/env python3
"""govinfo_swarm_ingest_v2.py

Upgraded govinfo -> PostgreSQL ingestion pipeline with:
- Swarm-style multi-agent orchestration
- LLM-based normalization via OpenRouter (optional)
- Self-validating ValidationAgent with retry / human-review states

This script is designed to be a single, reusable entrypoint.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import logging
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

try:
    import psycopg2
    from psycopg2.extras import Json
except ImportError as exc:  # pragma: no cover - environment specific
    print("[FATAL] psycopg2 is required. pip install psycopg2-binary", file=sys.stderr)
    raise

try:
    # Optional: OpenRouter SDK for LLM-based normalization
    from openrouter import OpenRouter  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    OpenRouter = None  # type: ignore


# ---------------------------------------------------------------------------
# Embedded migrations (idempotent)
# ---------------------------------------------------------------------------

MIGRATION_SQL = """
-- Enable pgvector if available (optional; ignore failures at runtime).
DO $$
BEGIN
    BEGIN
        CREATE EXTENSION IF NOT EXISTS vector;
    EXCEPTION WHEN OTHERS THEN
        NULL;
    END;
END$$;

CREATE TABLE IF NOT EXISTS govinfo_collections (
    code            TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS govinfo_packages (
    id                   BIGSERIAL PRIMARY KEY,
    package_id           TEXT NOT NULL UNIQUE,
    collection_code      TEXT NOT NULL,
    doc_class            TEXT,
    title                TEXT,
    congress             INTEGER,
    date_issued          DATE,
    last_modified        TIMESTAMPTZ,
    package_link         TEXT,
    raw_json             JSONB,
    normalized_json      JSONB,
    embedding            vector(1536),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- validation fields added later (also ensured via ALTER TABLE below)
    validation_status    TEXT,
    validation_attempts  INTEGER NOT NULL DEFAULT 0,
    last_validation_at   TIMESTAMPTZ,
    last_validation_error TEXT
);

CREATE INDEX IF NOT EXISTS idx_govinfo_packages_collection_date
    ON govinfo_packages (collection_code, date_issued);

CREATE INDEX IF NOT EXISTS idx_govinfo_packages_congress
    ON govinfo_packages (congress);

CREATE INDEX IF NOT EXISTS idx_govinfo_packages_title_trgm
    ON govinfo_packages USING GIN (title gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_govinfo_packages_normalized_json
    ON govinfo_packages USING GIN (normalized_json);

CREATE TABLE IF NOT EXISTS govinfo_published_ingest_state (
    id               BIGSERIAL PRIMARY KEY,
    collection_code  TEXT NOT NULL,
    date_start       DATE NOT NULL,
    date_end         DATE NOT NULL,
    offset_mark      TEXT NOT NULL,
    last_run_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed        BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (collection_code, date_start, date_end)
);

CREATE TABLE IF NOT EXISTS govinfo_ingest_log (
    id               BIGSERIAL PRIMARY KEY,
    collection_code  TEXT NOT NULL,
    run_started_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    run_completed_at TIMESTAMPTZ,
    status           TEXT NOT NULL,
    message          TEXT
);

-- Safety ALTER to ensure newer columns exist when upgrading.
ALTER TABLE govinfo_packages
    ADD COLUMN IF NOT EXISTS validation_status TEXT,
    ADD COLUMN IF NOT EXISTS validation_attempts INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_validation_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_validation_error TEXT;
"""


# ---------------------------------------------------------------------------
# Config dataclasses
# ---------------------------------------------------------------------------


@dataclass
class DBConfig:
    host: str
    port: int
    database: str
    user: str
    password: str


@dataclass
class IngestConfig:
    start_date: dt.date
    end_date: dt.date
    collections: List[str]
    max_packages: Optional[int] = None
    use_llm_normalizer: bool = False
    dry_run: bool = False
    max_validation_retries: int = 3


@dataclass
class SwarmTask:
    kind: str
    payload: Dict[str, Any]


@dataclass
class SwarmContext:
    db_cfg: DBConfig
    http_session: requests.Session
    openrouter_client: Optional["OpenRouter"]
    ingest_cfg: IngestConfig


@dataclass
class ValidationReport:
    """Represents the result of validating a single package."""

    status: str  # "ok" | "retry" | "human_review"
    reasons: List[str] = dataclasses.field(default_factory=list)
    retryable: bool = False


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def get_db_connection(cfg: DBConfig):
    conn = psycopg2.connect(
        host=cfg.host,
        port=cfg.port,
        dbname=cfg.database,
        user=cfg.user,
        password=cfg.password,
    )
    conn.autocommit = False
    return conn


def run_migrations(db_cfg: DBConfig) -> None:
    logging.info("Running govinfo migrations ...")
    conn = get_db_connection(db_cfg)
    try:
        with conn.cursor() as cur:
            cur.execute(MIGRATION_SQL)
        conn.commit()
        logging.info("Migrations completed successfully.")
    except Exception:
        conn.rollback()
        logging.exception("Migration failed; rolled back.")
        raise
    finally:
        conn.close()


def upsert_package(conn, pkg: Dict[str, Any], collection_code: str) -> None:
    """Insert or update a govinfo package row.

    This is idempotent on package_id and safe to call repeatedly.
    """

    package_id = pkg.get("packageId")
    if not package_id:
        logging.warning("Skipping package without packageId: %s", pkg)
        return

    date_issued = None
    if pkg.get("dateIssued"):
        try:
            date_issued = dt.datetime.strptime(pkg["dateIssued"], "%Y-%m-%d").date()
        except ValueError:
            logging.warning("Could not parse dateIssued=%s", pkg.get("dateIssued"))

    last_modified = None
    if pkg.get("lastModified"):
        try:
            last_modified = dt.datetime.fromisoformat(
                pkg["lastModified"].replace("Z", "+00:00")
            )
        except ValueError:
            logging.warning("Could not parse lastModified=%s", pkg.get("lastModified"))

    congress = None
    if pkg.get("congress"):
        try:
            congress = int(pkg["congress"])
        except (ValueError, TypeError):
            logging.warning("Non-integer congress=%s", pkg.get("congress"))

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO govinfo_packages (
                package_id, collection_code, doc_class, title,
                congress, date_issued, last_modified, package_link, raw_json,
                created_at, updated_at
            ) VALUES (
                %(package_id)s, %(collection_code)s, %(doc_class)s, %(title)s,
                %(congress)s, %(date_issued)s, %(last_modified)s, %(package_link)s,
                %(raw_json)s, NOW(), NOW()
            )
            ON CONFLICT (package_id) DO UPDATE SET
                collection_code = EXCLUDED.collection_code,
                doc_class       = EXCLUDED.doc_class,
                title           = EXCLUDED.title,
                congress        = EXCLUDED.congress,
                date_issued     = EXCLUDED.date_issued,
                last_modified   = EXCLUDED.last_modified,
                package_link    = EXCLUDED.package_link,
                raw_json        = EXCLUDED.raw_json,
                updated_at      = NOW();
            """,
            {
                "package_id": package_id,
                "collection_code": collection_code,
                "doc_class": pkg.get("docClass"),
                "title": pkg.get("title"),
                "congress": congress,
                "date_issued": date_issued,
                "last_modified": last_modified,
                "package_link": pkg.get("packageLink"),
                "raw_json": Json(pkg),
            },
        )


def update_normalized_json(conn, package_id: str, normalized: Dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE govinfo_packages
               SET normalized_json = %(normalized)s,
                   updated_at      = NOW()
             WHERE package_id      = %(package_id)s;
            """,
            {"normalized": Json(normalized), "package_id": package_id},
        )


# ---------------------------------------------------------------------------
# Govinfo API helpers
# ---------------------------------------------------------------------------


GOVINFO_BASE_URL = "https://api.govinfo.gov"


def build_published_url(
    collection: str,
    start_date: dt.date,
    end_date: dt.date,
    offset_mark: str,
    page_size: int,
    api_key: str,
) -> str:
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    return (
        f"{GOVINFO_BASE_URL}/published/{start_str}/{end_str}"
        f"?offsetMark={requests.utils.quote(offset_mark)}"
        f"&pageSize={page_size}"
        f"&collection={collection}"
        f"&api_key={api_key}"
    )


def fetch_published_page(
    session: requests.Session,
    collection: str,
    start_date: dt.date,
    end_date: dt.date,
    offset_mark: str,
    page_size: int,
    api_key: str,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    url = build_published_url(collection, start_date, end_date, offset_mark, page_size, api_key)
    logging.debug("Fetching govinfo published page: %s", url)

    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    packages = data.get("packages", [])

    next_page_url = data.get("nextPage")
    next_offset: Optional[str] = None
    if next_page_url:
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(next_page_url)
        qs = parse_qs(parsed.query)
        marks = qs.get("offsetMark")
        if marks:
            next_offset = marks[0]

    return packages, next_offset


def fetch_package_summary(session: requests.Session, package_link: str, api_key: str) -> Dict[str, Any]:
    if "api_key=" not in package_link:
        sep = "&" if "?" in package_link else "?"
        url = f"{package_link}{sep}api_key={api_key}"
    else:
        url = package_link

    logging.debug("Fetching package summary: %s", url)
    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# OpenRouter client + LLM normalization helper
# ---------------------------------------------------------------------------


def build_openrouter_client() -> Optional["OpenRouter"]:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        logging.warning("OPENROUTER_API_KEY not set; LLM normalization disabled.")
        return None

    if OpenRouter is None:
        logging.warning("openrouter SDK not installed; pip install openrouter.")
        return None

    return OpenRouter(api_key=api_key)


def llm_normalize_package(
    client: "OpenRouter", package: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Use an OpenRouter model to normalize/enrich a package.

    Returns a dict to be stored in normalized_json, or None on failure.
    """

    prompt = {
        "role": "user",
        "content": (
            "You are an analyst for a legislative intelligence system. "
            "Given the following bill/package metadata from govinfo, "
            "return a concise JSON object with the keys: "
            "topics (list of strings), policy_domain (string), "
            "ideology_estimate (string from ['left','center-left','center',"
            "'center-right','right','unclear']), "
            "primary_branch (string, e.g., 'legislative', 'executive'), "
            "summary (1-2 sentence plain text description). "
            "Return ONLY valid JSON, no commentary.\n\n" +
            json.dumps(
                {
                    "title": package.get("title"),
                    "docClass": package.get("docClass"),
                    "congress": package.get("congress"),
                    "collection": package.get("collection_code"),
                    "dateIssued": package.get("dateIssued"),
                },
                ensure_ascii=False,
            )
        ),
    }

    try:
        res = client.chat.send(
            messages=[prompt],
            model="qwen/qwen2.5-72b-instruct",
            stream=False,
        )
        msg = res["choices"][0]["message"]["content"]  # type: ignore[index]
        if isinstance(msg, list):
            text_parts = [chunk.get("text", "") for chunk in msg]
            msg = "".join(text_parts)
        if not isinstance(msg, str):
            logging.warning("Unexpected LLM message format: %r", msg)
            return None

        normalized = json.loads(msg)
        if not isinstance(normalized, dict):
            logging.warning("LLM response is not a JSON object: %s", msg)
            return None
        return normalized
    except Exception:
        logging.exception("LLM normalization failed for package %s", package.get("packageId"))
        return None


# ---------------------------------------------------------------------------
# Swarm agents
# ---------------------------------------------------------------------------


class BaseAgent:
    def can_handle(self, task: SwarmTask) -> bool:
        raise NotImplementedError

    def handle(self, task: SwarmTask, ctx: SwarmContext) -> List[SwarmTask]:
        raise NotImplementedError


class GovinfoPublishedAgent(BaseAgent):
    """Agent that fetches pages from govinfo `/published` endpoint."""

    def __init__(self, api_key: str, page_size: int = 100):
        self.api_key = api_key
        self.page_size = page_size

    def can_handle(self, task: SwarmTask) -> bool:
        return task.kind == "fetch_published_page"

    def handle(self, task: SwarmTask, ctx: SwarmContext) -> List[SwarmTask]:
        payload = task.payload
        collection = payload["collection"]
        start_date = payload["start_date"]
        end_date = payload["end_date"]
        offset_mark = payload["offset_mark"]

        packages, next_offset = fetch_published_page(
            ctx.http_session,
            collection=collection,
            start_date=start_date,
            end_date=end_date,
            offset_mark=offset_mark,
            page_size=self.page_size,
            api_key=self.api_key,
        )

        logging.info(
            "Fetched %d packages from collection=%s offset_mark=%s",
            len(packages),
            collection,
            offset_mark,
        )

        new_tasks: List[SwarmTask] = []
        if packages:
            new_tasks.append(
                SwarmTask(
                    kind="upsert_packages",
                    payload={
                        "collection": collection,
                        "packages": packages,
                    },
                )
            )

        if next_offset:
            new_tasks.append(
                SwarmTask(
                    kind="fetch_published_page",
                    payload={
                        "collection": collection,
                        "start_date": start_date,
                        "end_date": end_date,
                        "offset_mark": next_offset,
                    },
                )
            )

        return new_tasks


class GovinfoUpsertAgent(BaseAgent):
    """Agent that writes raw govinfo packages into PostgreSQL."""

    def can_handle(self, task: SwarmTask) -> bool:
        return task.kind == "upsert_packages"

    def handle(self, task: SwarmTask, ctx: SwarmContext) -> List[SwarmTask]:
        payload = task.payload
        collection = payload["collection"]
        packages: List[Dict[str, Any]] = payload["packages"]

        if not packages:
            return []

        conn = get_db_connection(ctx.db_cfg)
        new_tasks: List[SwarmTask] = []
        try:
            for pkg in packages:
                if ctx.ingest_cfg.max_packages is not None and ctx.ingest_cfg.max_packages <= 0:
                    logging.info("Reached max_packages limit; stopping upserts.")
                    break

                if ctx.ingest_cfg.max_packages is not None:
                    ctx.ingest_cfg.max_packages -= 1

                if ctx.ingest_cfg.dry_run:
                    logging.debug("[DRY-RUN] Would upsert package %s", pkg.get("packageId"))
                else:
                    upsert_package(conn, pkg, collection_code=collection)

                pkg_with_collection = dict(pkg)
                pkg_with_collection["collection_code"] = collection

                if ctx.ingest_cfg.use_llm_normalizer and ctx.openrouter_client is not None:
                    new_tasks.append(
                        SwarmTask(
                            kind="normalize_with_llm",
                            payload={"package": pkg_with_collection},
                        )
                    )
                else:
                    # No LLM normalization; still validate basic invariants
                    new_tasks.append(
                        SwarmTask(
                            kind="validate_package",
                            payload={"package_id": pkg.get("packageId")},
                        )
                    )

            if not ctx.ingest_cfg.dry_run:
                conn.commit()
        except Exception:
            conn.rollback()
            logging.exception("Failed during package upsert; rolled back.")
            raise
        finally:
            conn.close()

        return new_tasks


class LLMNormalizerAgent(BaseAgent):
    """Agent that calls OpenRouter to normalize/enrich packages."""

    def can_handle(self, task: SwarmTask) -> bool:
        return task.kind == "normalize_with_llm"

    def handle(self, task: SwarmTask, ctx: SwarmContext) -> List[SwarmTask]:
        if ctx.openrouter_client is None:
            logging.debug("No OpenRouter client; skipping LLM normalization task.")
            return []

        package = task.payload["package"]
        package_id = package.get("packageId")
        if not package_id:
            logging.warning("normalize_with_llm task without packageId: %s", package)
            return []

        normalized = llm_normalize_package(ctx.openrouter_client, package)
        if normalized is None:
            # Failed normalization; let ValidationAgent / retry logic decide
            logging.warning("Normalization returned None for package %s", package_id)
            return [
                SwarmTask(
                    kind="validate_package",
                    payload={"package_id": package_id},
                )
            ]

        if ctx.ingest_cfg.dry_run:
            logging.debug(
                "[DRY-RUN] Would update normalized_json for %s with %s",
                package_id,
                normalized,
            )
            return [
                SwarmTask(
                    kind="validate_package",
                    payload={"package_id": package_id},
                )
            ]

        conn = get_db_connection(ctx.db_cfg)
        try:
            update_normalized_json(conn, package_id, normalized)
            conn.commit()
        except Exception:
            conn.rollback()
            logging.exception("Failed to update normalized_json for %s", package_id)
        finally:
            conn.close()

        return [
            SwarmTask(
                kind="validate_package",
                payload={"package_id": package_id},
            )
        ]


# ---------------------------------------------------------------------------
# Validation helpers & agent
# ---------------------------------------------------------------------------


def _collect_diagnostics(conn, package_id: str) -> Optional[Dict[str, Any]]:
    """Load diagnostics for a given package_id from the DB."""

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT package_id,
                   collection_code,
                   congress,
                   date_issued,
                   title,
                   normalized_json,
                   validation_status,
                   validation_attempts,
                   last_validation_at,
                   last_validation_error,
                   raw_json
              FROM govinfo_packages
             WHERE package_id = %s;
            """,
            (package_id,),
        )
        row = cur.fetchone()

    if not row:
        return None

    (
        package_id,
        collection_code,
        congress,
        date_issued,
        title,
        normalized_json,
        validation_status,
        validation_attempts,
        last_validation_at,
        last_validation_error,
        raw_json,
    ) = row

    today = dt.date.today()

    diag: Dict[str, Any] = {
        "package_id": package_id,
        "collection_code": collection_code,
        "congress": congress,
        "date_issued": date_issued,
        "title": title,
        "title_length": len(title or "") if title else 0,
        "has_normalized_json": normalized_json is not None,
        "normalized_json": normalized_json or {},
        "validation_status": validation_status,
        "validation_attempts": validation_attempts or 0,
        "last_validation_at": last_validation_at,
        "last_validation_error": last_validation_error,
        "raw_json": raw_json or {},
        "days_from_today": (today - date_issued).days if isinstance(date_issued, dt.date) else None,
    }
    return diag


def classify_package(diag: Dict[str, Any], max_retries: int) -> ValidationReport:
    """Apply rule-based validation to a package diagnostics object.

    Returns a ValidationReport indicating status + reasons.
    """

    attempts = int(diag.get("validation_attempts") or 0)

    if attempts >= max_retries:
        return ValidationReport(
            status="human_review",
            reasons=["max_retries_exceeded"],
            retryable=False,
        )

    reasons: List[str] = []

    if not diag.get("package_id"):
        reasons.append("missing_package_id")
        return ValidationReport(status="human_review", reasons=reasons, retryable=False)

    # Date sanity
    days_from_today = diag.get("days_from_today")
    if isinstance(days_from_today, int) and abs(days_from_today) > 365 * 10:
        reasons.append("date_issued_out_of_range")

    norm = diag.get("normalized_json") or {}
    has_norm = diag.get("has_normalized_json", False)

    if not has_norm:
        reasons.append("missing_normalized_json")
        return ValidationReport(status="retry", reasons=reasons, retryable=True)

    topics = norm.get("topics", [])
    if not isinstance(topics, list) or len(topics) == 0:
        reasons.append("empty_or_invalid_topics")

    ideology = norm.get("ideology_estimate")
    allowed_ideo = {"left", "center-left", "center", "center-right", "right", "unclear"}
    if ideology not in allowed_ideo:
        reasons.append("invalid_ideology_estimate")

    summary = norm.get("summary", "")
    if not isinstance(summary, str) or len(summary) < 20:
        reasons.append("summary_too_short")

    if len(reasons) == 0:
        return ValidationReport(status="ok", reasons=[], retryable=False)

    # If we have only soft issues and attempts < max_retries, mark retry
    if attempts < max_retries:
        return ValidationReport(status="retry", reasons=reasons, retryable=True)

    return ValidationReport(status="human_review", reasons=reasons, retryable=False)


class ValidationAgent(BaseAgent):
    """Agent that validates packages and enqueues retries if needed."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def can_handle(self, task: SwarmTask) -> bool:
        return task.kind == "validate_package"

    def handle(self, task: SwarmTask, ctx: SwarmContext) -> List[SwarmTask]:
        package_id = task.payload["package_id"]
        conn = get_db_connection(ctx.db_cfg)
        report: Optional[ValidationReport] = None
        diag: Optional[Dict[str, Any]] = None
        try:
            diag = _collect_diagnostics(conn, package_id)
            if diag is None:
                logging.warning("ValidationAgent: package %s not found", package_id)
                return []
            report = classify_package(diag, max_retries=self.max_retries)
            self._apply_report(conn, package_id, diag, report)
            conn.commit()
        except Exception:
            conn.rollback()
            logging.exception("Validation failed for %s", package_id)
            return []
        finally:
            conn.close()

        return self._next_tasks_for_report(diag, report, ctx)

    def _apply_report(
        self,
        conn,
        package_id: str,
        diag: Dict[str, Any],
        report: ValidationReport,
    ) -> None:
        attempts = int(diag.get("validation_attempts") or 0) + 1
        validation_json = {
            "status": report.status,
            "reasons": report.reasons,
            "attempt": attempts,
            "validated_at": dt.datetime.utcnow().isoformat() + "Z",
        }
        error_str = "; ".join(report.reasons) if report.reasons else None

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE govinfo_packages
                   SET validation_status      = %(status)s,
                       validation_attempts    = %(attempts)s,
                       last_validation_at    = NOW(),
                       last_validation_error = %(error)s,
                       normalized_json       = COALESCE(normalized_json, '{}'::jsonb) ||
                                                jsonb_build_object('validation', %(validation_json)s),
                       updated_at            = NOW()
                 WHERE package_id           = %(package_id)s;
                """,
                {
                    "status": report.status,
                    "attempts": attempts,
                    "error": error_str,
                    "validation_json": Json(validation_json),
                    "package_id": package_id,
                },
            )

    def _next_tasks_for_report(
        self,
        diag: Dict[str, Any],
        report: ValidationReport,
        ctx: SwarmContext,
    ) -> List[SwarmTask]:
        if report.status != "retry" or not report.retryable:
            return []

        if not ctx.ingest_cfg.use_llm_normalizer or ctx.openrouter_client is None:
            # Nothing we can do automatically
            return []

        raw = diag.get("raw_json") or {}
        package_id = diag["package_id"]
        # Enrich with collection_code for LLM prompt
        raw["collection_code"] = diag.get("collection_code")

        logging.info(
            "Enqueuing retry normalization for package %s (attempt %s)",
            package_id,
            diag.get("validation_attempts"),
        )

        return [
            SwarmTask(
                kind="normalize_with_llm",
                payload={"package": raw},
            )
        ]


# ---------------------------------------------------------------------------
# Swarm coordinator
# ---------------------------------------------------------------------------


class SwarmCoordinator:
    def __init__(self, agents: Iterable[BaseAgent], ctx: SwarmContext):
        self.agents = list(agents)
        self.ctx = ctx

    def run(self, initial_tasks: List[SwarmTask]) -> None:
        queue: List[SwarmTask] = list(initial_tasks)
        processed = 0

        while queue:
            task = queue.pop(0)
            handled = False

            for agent in self.agents:
                if agent.can_handle(task):
                    handled = True
                    new_tasks = agent.handle(task, self.ctx)
                    processed += 1
                    queue.extend(new_tasks)
                    break

            if not handled:
                logging.warning("No agent could handle task kind=%s", task.kind)

        logging.info("Swarm run complete. Processed %d tasks.", processed)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_ingestion(db_cfg: DBConfig, ingest_cfg: IngestConfig, api_key: str) -> None:
    session = requests.Session()
    openrouter_client = build_openrouter_client() if ingest_cfg.use_llm_normalizer else None

    ctx = SwarmContext(
        db_cfg=db_cfg,
        http_session=session,
        openrouter_client=openrouter_client,
        ingest_cfg=ingest_cfg,
    )

    agents: List[BaseAgent] = [
        GovinfoPublishedAgent(api_key=api_key, page_size=100),
        GovinfoUpsertAgent(),
        LLMNormalizerAgent(),
        ValidationAgent(max_retries=ingest_cfg.max_validation_retries),
    ]

    initial_tasks: List[SwarmTask] = []
    for collection in ingest_cfg.collections:
        initial_tasks.append(
            SwarmTask(
                kind="fetch_published_page",
                payload={
                    "collection": collection,
                    "start_date": ingest_cfg.start_date,
                    "end_date": ingest_cfg.end_date,
                    "offset_mark": "*",
                },
            )
        )

    coordinator = SwarmCoordinator(agents=agents, ctx=ctx)
    coordinator.run(initial_tasks)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="govinfo -> PostgreSQL ingestion + LLM normalization (swarm-style)",
    )

    parser.add_argument("--init-db", action="store_true", help="Run DB migrations and exit")
    parser.add_argument("--ingest", action="store_true", help="Run ingestion for given range")

    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--collections",
        type=str,
        default="BILLS",
        help="Comma-separated govinfo collection codes (e.g., BILLS, BILLSTATUS)",
    )
    parser.add_argument(
        "--max-packages",
        type=int,
        default=None,
        help="Optional cap on number of packages to ingest.",
    )
    parser.add_argument(
        "--use-llm-normalizer",
        action="store_true",
        help="Enable OpenRouter-based normalization tasks.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Log actions only; no writes")
    parser.add_argument(
        "--max-validation-retries",
        type=int,
        default=3,
        help="Maximum number of validation retries before human_review.",
    )

    parser.add_argument("--pg-host", type=str, default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--pg-port", type=int, default=int(os.getenv("PGPORT", "5432")))
    parser.add_argument(
        "--pg-db", type=str, default=os.getenv("PGDATABASE", "opendiscourse"),
    )
    parser.add_argument(
        "--pg-user", type=str, default=os.getenv("PGUSER", "opendiscourse"),
    )
    parser.add_argument(
        "--pg-password",
        type=str,
        default=os.getenv("PGPASSWORD", ""),
    )

    parser.add_argument(
        "--govinfo-api-key",
        type=str,
        default=os.getenv("GOVINFO_API_KEY", ""),
        help="govinfo API key (or set GOVINFO_API_KEY env var)",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    return parser.parse_args(argv)


def build_db_config(args: argparse.Namespace) -> DBConfig:
    if not args.pg_password:
        logging.warning(
            "No PostgreSQL password provided. Consider setting PGPASSWORD or --pg-password.",
        )
    return DBConfig(
        host=args.pg_host,
        port=args.pg_port,
        database=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
    )


def build_ingest_config(args: argparse.Namespace) -> IngestConfig:
    if not args.start_date or not args.end_date:
        raise ValueError("--start-date and --end-date are required when --ingest is set")

    start_date = dt.datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end_date = dt.datetime.strptime(args.end_date, "%Y-%m-%d").date()

    if end_date < start_date:
        raise ValueError("end_date must be >= start_date")

    collections = [c.strip().upper() for c in args.collections.split(",") if c.strip()]

    return IngestConfig(
        start_date=start_date,
        end_date=end_date,
        collections=collections,
        max_packages=args.max_packages,
        use_llm_normalizer=args.use_llm_normalizer,
        dry_run=args.dry_run,
        max_validation_retries=args.max_validation_retries,
    )


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
    )

    db_cfg = build_db_config(args)

    if not args.govinfo_api_key:
        logging.warning(
            "No GOVINFO_API_KEY provided. Set env or pass --govinfo-api-key; "
            "requests will fail without it.",
        )

    if args.init_db:
        run_migrations(db_cfg)
        if not args.ingest:
            return 0

    if args.ingest:
        ingest_cfg = build_ingest_config(args)
        run_ingestion(db_cfg, ingest_cfg, api_key=args.govinfo_api_key)

    if not args.init_db and not args.ingest:
        logging.error("Nothing to do. Use --init-db and/or --ingest.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
