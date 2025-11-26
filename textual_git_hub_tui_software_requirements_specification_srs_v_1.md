# Textual GitHub TUI — Software Requirements Specification (SRS) v1.0

**Project Codename:** `repobot-tui`

**Author:** ChatGPT (with Blaine)

**Last Updated:** 2025-10-14

---

## 1. Purpose & Scope
Build a terminal-based TUI (using **Textual**) that serves as a powerful yet elegant wrapper over **GitHub**. It enables search/browse across GitHub entities, bulk queue-and-download of repositories, gist operations, issue/PR triage, and an embedded **AI side-pane** that ingests the currently focused repository (files + metadata), vectorizes it, and supports RAG-style Q&A.

The application prioritizes:
- A clean **OOP** design with **Pydantic** models for schemas.
- **Parallel**/async job orchestration that respects GitHub **rate limits**.
- A modular **AI agent** using the **OpenRouter** SDK (defaults to free models) with a pluggable RAG backend.

**Out of scope v1:** advanced write operations that require elevated workflows (repo deletion, protected branch settings, org billing), code execution inside repos, and non-GitHub SCMs (GitLab/Bitbucket). These may be added later.

---

## 2. Goals & Non‑Goals
### 2.1 Goals
- Rich TUI with tabs/panes, smooth keyboard UX, and helpful tooltips.
- Bulk repository **queueing + downloading** with throttled concurrency.
- Search across users, repos, topics, issues, PRs, discussions, code.
- View/inspect PRs and issues; comment and edit PR titles/descriptions (where scope-safe).
- Gists: create, search, list, read, edit, delete own.
- **AI side-pane** with chat history that ingests the active repo context for Q&A.
- Robust configuration, logging, and error handling.

### 2.2 Non‑Goals (v1)
- Full GitHub Actions management (view only in v1).
- Code review automations beyond commenting.
- Multi-SCM abstraction. GitHub-only initially.

---

## 3. System Overview
```
+---------------------+       +--------------------+
|  Textual TUI (UI)   |<----->|   Domain Services  |
|  Tabs + Panes       |       |  (use-cases)       |
|  - Search           |       |  - SearchService   |
|  - Repo Browser     |       |  - DownloadService |
|  - PR/Issue/Gist    |       |  - GistService     |
|  - Queue/Jobs       |       |  - PRService       |
|  - AI Agent (RAG)   |       |  - RateLimitSvc    |
+----------^----------+       +-----^--------------+
           |                        |
           |                        |
           v                        v
     +-----------+            +-----------+
     | GitHub    |            | AI/RAG    |
     | Client    |            | Pipeline  |
     +-----^-----+            +-----^-----+
           |                        |
           | REST/GraphQL           | Embeddings, Vector DB
           v                        v
      GitHub API               OpenRouter + Vector Store
```

---

## 4. Architecture & Modules

### 4.1 UI Layer (Textual)
- **MainApp**: startup, routing, DI container init.
- **Tabs**: `SearchTab`, `RepoTab`, `PRsTab`, `IssuesTab`, `GistsTab`, `QueueTab`, `JobsTab`, `SettingsTab`, `AgentTab`.
- **Panes/Widgets**: search inputs, results lists, detail views, queue list, progress displays, logs console, agent chat, repo file tree, code preview.
- **Keybindings**: global and per-tab; configurable in settings.

### 4.2 Domain Services
- **SearchService**: faceted search across entities; paging.
- **RepositoryService**: repo metadata fetch, file tree read, archive download, cloning.
- **DownloadService**: queueing, concurrency control, resumable downloads, backoff.
- **PRService / IssueService / DiscussionService**: list/detail/comment; safe edits.
- **GistService**: CRUD for own gists; read public gists.
- **RateLimitService**: token bucket + API limit introspection; adaptive throttling.
- **AuthService**: token persistence, scopes validation, re-auth flow.
- **ConfigService**: load/save ~/.config/repobot-tui/config.yaml (see §9).
- **TelemetryService (optional)**: anonymized local metrics only.

### 4.3 Data/Integration Layer
- **GitHubClient**: typed wrapper over GitHub REST + GraphQL; retries/backoff.
- **OpenRouterClient**: chat/completions/embeddings with model registry.
- **VectorStore**: provider abstraction (e.g., SQLite+FAISS by default; pluggable to Qdrant/Weaviate/Postgres+pgvector).
- **Cache**: on-disk HTTP cache (ETags/If-None-Match), repo metadata cache.
- **Storage**: download targets, workspace root, temp dir management.

---

## 5. Data Models (Pydantic)
Create Pydantic models mirroring core GitHub entities—fields trimmed for v1 and extendable. Examples:
- `User`, `Organization`, `Repository`, `Branch`, `Commit`, `Release`.
- `Issue`, `PullRequest`, `Label`, `Milestone`, `Review`, `Comment`.
- `Gist`, `GistFile`.
- `SearchResult<T>` with paging cursor.
- `RateLimit` (core + secondary), `AbuseDetection` signal.
- `DownloadJob`, `JobStatus`, `JobResult`.
- `Embedding`, `DocumentChunk`, `RepoIndex`.

All models include `model_config = ConfigDict(arbitrary_types_allowed=True, extra='ignore')` and strict typing on inputs; validators for IDs/URLs; datetimes are timezone-aware (UTC).

---

## 6. API Clients & Endpoint Mapping

### 6.1 REST (primary)
- **Search**
  - `GET /search/repositories`, `/search/code`, `/search/issues`, `/search/users`, `/search/topics`.
- **Repositories**
  - `GET /repos/{owner}/{repo}` (details), `/contents/{path}`, `/readme`, `/releases`.
  - `GET /repos/{owner}/{repo}/zipball` (archive download).
- **Users/Orgs**
  - `GET /users/{username}`, `/users/{username}/repos`.
  - `GET /orgs/{org}`, `/orgs/{org}/repos`.
- **Issues/PRs**
  - `GET /repos/{owner}/{repo}/issues`, `/pulls`.
  - `GET /repos/{owner}/{repo}/pulls/{number}`; `POST /issues/{number}/comments`; `PATCH /pulls/{number}` (title/body edits only in v1).
- **Gists**
  - `GET /gists`, `GET /gists/public`, `POST /gists`, `PATCH /gists/{gist_id}`, `DELETE /gists/{gist_id}` (own only).
- **Rate Limit**
  - `GET /rate_limit`.

### 6.2 GraphQL (selected use)
- Consolidated queries for repo + issues + PR counts; cross-entity search with cursors; viewer/notifications overview for feed panel.

### 6.3 Auth
- **Personal Access Token (classic or fine‑grained)** via header `Authorization: token ...`.
- Required scopes by feature:
  - Read-only: `public_repo`, `read:org`, `gist`.
  - Write ops (optional): `repo`, `gist`.

---

## 7. Concurrency, Parallelism & Rate Limiting
- **Executor**: Asyncio + `httpx.AsyncClient` with a bounded semaphore.
- **Concurrency Controls**:
  - Global max in-flight requests (default 8; configurable).
  - Per-host limiter; per-feature limiter (downloads lower priority vs UI fetches).
- **Backoff**: Exponential with jitter on 429/secondary limit; respect `Retry-After`.
- **Queue**: Persistent job queue (`sqlite`), with states: `QUEUED`, `RUNNING`, `RETRYING`, `PAUSED`, `CANCELLED`, `DONE`, `FAILED`.
- **Chunked downloads** with resume support when cloning not requested.
- **Priority lanes**: UI-critical > metadata > bulk downloads.

---

## 8. AI Agent (RAG) Design
- **Goal**: Provide contextual Q&A on the focused repository.
- **Pipeline**:
  1. **Ingestion**: Read repo file list (respect .gitignore/size limits), extract text from code/README/markdown/LICENCE/issues (when accessible).
  2. **Chunking**: Token-aware chunking (e.g., 512–1024 tokens overlap 64–128).
  3. **Embeddings**: via OpenRouter free model (e.g., text-embedding class; model registry configurable).
  4. **Vector Store**: Default FAISS/SQLite; pluggable Qdrant/pgvector.
  5. **Retrieval**: Hybrid (BM25 + vector top‑k); rerank optional.
  6. **Generation**: OpenRouter chat completion with context + conversation history.
- **Privacy**: Local index by default; never uploads repo contents unless user opts in.
- **Controls**: Clear index, re-index, selective folders, token budget slider.

---

## 9. Configuration & Settings
Stored at `~/.config/repobot-tui/config.yaml` (XDG). Example keys:
```yaml
github:
  token: "env:GITHUB_TOKEN"   # env indirection supported
  api_base: "https://api.github.com"
  graphql_base: "https://api.github.com/graphql"
  concurrency: 8
  download_root: "~/Downloads/repobot"
  respect_gitignore: true
ai:
  provider: openrouter
  api_key: "env:OPENROUTER_API_KEY"
  chat_model: "free:best-available"
  embed_model: "free:embed"
  max_ctx_tokens: 8192
  top_k: 6
ui:
  theme: matrix_dark
  show_tooltips: true
logging:
  level: INFO
  file: "/tmp/CBW-repopot-tui.log"
```

---

## 10. TUI Information Architecture
- **Top Nav Tabs**: Search | Repos | Issues | PRs | Gists | Queue | Jobs | Agent | Settings
- **Left Pane**: Filters/Facets (entity, language, stars, updated, owner/org).
- **Main Pane**: Result lists or entity detail (with sub-tabs: README, Files, Issues, PRs, Releases, Insights).
- **Right Pane**: Agent chat + context inspector + snippets export.
- **Footer**: Status line (rate-limit remaining, queued jobs, network state).

---

## 11. Persistence & Caching
- **SQLite** for: job queue, small metadata cache, conversation history.
- **On-disk**: repo downloads and a content cache keyed by ETag.
- **Index**: vector DB files under `~/.local/share/repobot-tui/indexes/{owner}/{repo}`.

---

## 12. Error Handling & Resilience
- Centralized exception hierarchy; map HTTP errors to typed failures.
- User-facing toasts for transient issues, dialogs for destructive actions.
- Automatic **retry** on idempotent GETs; guard on writes.
- Detect **secondary rate-limits**; pause bulk jobs with countdown.
- Sanity checks: disk space, path writability, network reachability.

---

## 13. Security
- Tokens read via env or config; mask in logs; never printed.
- Config file mode `0600` with warnings if looser.
- Optional OS keyring/Bitwarden CLI integration in v1.1+.
- Strict URL allowlist (GitHub API domains) for HTTP clients.
- AI privacy guard: local-only indexing by default.

---

## 14. Logging, Metrics, and Diagnostics
- Structured logs (JSON optional). Levels: DEBUG..ERROR.
- Job timeline with durations; per-request timing; cache hits/misses.
- **Diagnostics panel** in UI: rate-limit remaining, queue depth, last errors.

---

## 15. Performance Targets
- 95th percentile UI action < 150ms (cached results).
- Indexing small repos (<10MB text) in < 10s on mid-range hardware.
- Bulk download throughput bound by API and network; keep CPU < 70%.

---

## 16. Testing Strategy
- **Unit tests** for models, clients (with HTTPX mocking), services.
- **Property tests** for search/filter combinations.
- **Integration tests** using GitHub sandbox repos; cassette/recorded fixtures.
- **Golden tests** for TUI views (Textual pilot testing utilities).
- **Load tests** for queue/download + rate-limit behavior.

---

## 17. CLI & Environment
- `repobot-tui` entrypoint; flags: `--config`, `--reset-cache`, `--safe-mode` (no writes), `--offline` (use cache only).
- Env vars: `GITHUB_TOKEN`, `OPENROUTER_API_KEY`.

---

## 18. Accessibility & UX
- Keyboard-first; visible focus; high-contrast themes.
- Tooltips on hover/focus; command palette (Ctrl+P) for quick actions.
- Non-blocking background tasks with progress bars.

---

## 19. Roadmap
- **v1.0**: Read/search/browse + queue/bulk download + AI side-pane (local index).
- **v1.1**: Keyring/Bitwarden secrets, repo cloning with shallow/fetch depth.
- **v1.2**: Notifications feed, PR reviews, label/milestone management.
- **v1.3**: Multi-provider vector stores; advanced reranking; export Q/A snippets.

---

## 20. Risks & Mitigations
- **Rate limiting**: multi-tier backoff + visibility in UI.
- **Large repos**: size caps; selective ingestion; file-type filters.
- **API changes**: typed client + contract tests; version pinning.
- **Privacy**: default local processing; opt-in remote LLM calls.

---

## 21. Open Questions (to resolve during design)
1. Preferred default download method: Git archive vs. `git clone` (shallow)?
2. Maximum file size and binary handling in ingestion? (e.g., 5 MB per file)
3. Which OpenRouter free models to default to for chat and embeddings?

---

## 22. Acceptance Criteria (v1)
- Can search repos/issues/PRs/users and open details without errors.
- Can add ≥50 repos to queue and download with adaptive throttling.
- AI panel can ingest and answer questions about the focused repo offline (local vector index), with optional online generation.
- Settings persist across sessions; secrets not leaked to logs.

---

## 23. Implementation Sketch (Module & Class Breakdown)

### 23.1 Models (`repobot.models`)
- `UserModel`, `OrgModel`, `RepoModel`, `IssueModel`, `PRModel`, `GistModel`, `SearchPage[T]`, `RateLimitModel`, `DownloadJobModel`, `EmbeddingModel`, `ChunkModel`.

### 23.2 Clients (`repobot.clients`)
- `GitHubClient` (REST + GraphQL) — `get_repo()`, `search_repos()`, `list_org_repos()`, `get_pr()`, `comment_issue()`, `edit_pr()`, `get_gist()`, `create_gist()`...
- `OpenRouterClient` — `embed(texts)`, `chat(messages, system_prompt, model)`.

### 23.3 Services (`repobot.services`)
- `SearchService`, `RepositoryService`, `PRService`, `IssueService`, `GistService`, `DownloadService`, `RateLimitService`, `AuthService`, `ConfigService`, `IndexService` (for RAG).

### 23.4 UI (`repobot.ui`)
- `MainApp`, `SearchTab`, `RepoTab`, `IssuesTab`, `PRsTab`, `GistsTab`, `QueueTab`, `JobsTab`, `AgentTab`, `SettingsTab`.
- Widgets: `RepoList`, `RepoDetail`, `FileTree`, `JobTable`, `ProgressBar`, `ChatPane`, `InspectorPane`.

### 23.5 Storage (`repobot.storage`)
- `SQLiteStore` (jobs, cache, history), `FSStore` (downloads, artifacts), `VectorStoreAdapter` (faiss/sqlite default).

### 23.6 Infra (`repobot.infra`)
- `LoggerFactory`, `RetryPolicy`, `Backoff`, `HttpCache`, `TaskRunner` (bounded semaphore), `Env` helpers.

---

## 24. Endpoint-to-Method Mapping (Examples)
| Feature | REST Endpoint | Client Method | Service Method |
|---|---|---|---|
| Search Repos | `GET /search/repositories` | `GitHubClient.search_repos(q, sort, order, page)` | `SearchService.search_repos(filters)` |
| Repo Details | `GET /repos/{owner}/{repo}` | `get_repo(owner, repo)` | `RepositoryService.get_repo(ref)` |
| Repo Zipball | `GET /repos/{o}/{r}/zipball` | `download_zipball(ref, dest)` | `DownloadService.enqueue_zip(ref, dest)` |
| Org Repos | `GET /orgs/{org}/repos` | `list_org_repos(org, type)` | `SearchService.list_org_repos(org, filters)` |
| Issues | `GET /repos/{o}/{r}/issues` | `list_issues(ref, state, labels)` | `IssueService.list(ref, query)` |
| Pulls | `GET /repos/{o}/{r}/pulls` | `list_pulls(ref, state)` | `PRService.list(ref, query)` |
| PR Detail | `GET /repos/{o}/{r}/pulls/{n}` | `get_pr(ref, n)` | `PRService.get(ref, n)` |
| Comment Issue | `POST /repos/{o}/{r}/issues/{n}/comments` | `comment_issue(ref, n, body)` | `IssueService.comment(...)` |
| Create Gist | `POST /gists` | `create_gist(files, desc, public)` | `GistService.create(...)` |

---

## 25. Realism Fixes & Guardrails
- Default to **REST** for most operations; use GraphQL only when it reduces roundtrips.
- Prefer **zipball** for mass downloads over `git clone` to avoid SSH dependency; allow toggle.
- Respect **robots of rate-limits**: consult `GET /rate_limit` frequently; show remaining in footer.
- Enforce per-repo size caps and exclude common large/binary files from ingestion by default.
- Implement **safe-mode** that disables all write calls (only reads) for first-run safety.

---

## 26. Deployment & Distribution
- Ship as a Python package (`pipx install repobot-tui`).
- Optional `brew install repobot-tui` tap later.
- Pre-built binaries with PyInstaller as stretch goal.

---

## 27. Documentation
- `README.md` (quickstart), `USAGE.md` (keybindings, workflows), `CONFIG.md`, `DEVELOPING.md`, `SECURITY.md`, `PRIVACY.md`.

---

## 28. Improvements / Next Steps
1. **Bitwarden CLI/OS keyring** integration for secrets management.
2. **Offline embeddings** (e.g., local model via `llama.cpp`/Ollama) to avoid any outbound calls.
3. **Smart prefetcher** that learns your patterns and preloads likely next views.
4. **Workspace Profiles** (multiple config profiles; switch in UI).
5. **Agent skills** for automated repo triage (generate labels, draft PR descriptions, summarize issues).

---

## 29. Glossary
- **RAG**: Retrieval-Augmented Generation.
- **Vector Store**: DB optimized for nearest-neighbor search over embeddings.
- **Zipball**: Zip archive of repo contents via GitHub REST.

