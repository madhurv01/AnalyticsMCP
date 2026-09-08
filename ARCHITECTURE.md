# InsightForge — Architecture

## 1. Overview

InsightForge is an AI data-analyst platform. A user signs in with Google, drops a CSV, and
the platform runs a real analytics workflow and returns a premium Excel report plus an
in-app insight dashboard. The same analytics capability is exposed to LLM clients through an
MCP server mounted on the API.

```
┌────────────┐      HTTPS       ┌──────────────────────────────┐
│  Next.js   │ ───────────────▶ │  FastAPI (uvicorn)            │
│  web (SSR) │  session cookie  │  ├─ /api/*   REST            │
│            │ ◀─────────────── │  ├─ /mcp     MCP (SSE/HTTP)  │
└────────────┘                  │  └─ analytics engine (pkg)  │
      │                         └────────┬─────────────────────┘
      │                                  │ enqueue
      ▼                                  ▼
  Google OIDC                    ┌─────────────┐   ┌──────────┐
                                 │ Celery      │──▶│ Postgres │
                                 │ worker(s)   │   ├──────────┤
                                 │ (same pkg)  │──▶│  Redis   │ broker + rate limit + cache
                                 └──────┬──────┘   ├──────────┤
                                        └─────────▶│  MinIO   │ raw CSV + generated .xlsx
                                                   └──────────┘
```

**Sync vs async:** files ≤ `INLINE_MAX_BYTES` (default 5 MB) are analyzed inline in the
request worker; larger files are pushed to Celery and the job is polled from the UI.

## 2. Repository layout

```
CSVMcp/
├── docker-compose.yml
├── .env.example
├── api/
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── app/
│       ├── main.py            # FastAPI app factory, router + MCP mount, middleware
│       ├── config.py          # pydantic-settings
│       ├── db.py              # engine, session, Base
│       ├── models.py          # User, Dataset, AnalysisJob, Report
│       ├── schemas.py         # Pydantic DTOs
│       ├── security.py        # JWT session cookies, current_user dep
│       ├── ratelimit.py       # Redis fixed-window limiter
│       ├── storage.py         # S3/MinIO helpers
│       ├── routers/
│       │   ├── auth.py        # /api/auth/google/login, /callback, /me, /logout
│       │   ├── datasets.py    # upload, list, get, delete, trigger analysis
│       │   └── reports.py     # list, download (presigned), delete
│       ├── analytics/
│       │   ├── engine.py      # orchestrator: run_workflow()
│       │   ├── profiling.py   # column type inference, dataset profile
│       │   ├── stats.py       # summary stats, correlation
│       │   ├── outliers.py    # IQR + IsolationForest
│       │   ├── relationships.py  # numeric/categorical association discovery
│       │   ├── insights.py    # deterministic insight/recommendation rules
│       │   └── excel.py       # XlsxWriter multi-sheet report builder
│       ├── mcp_server.py      # MCP tool definitions
│       └── worker.py          # celery app + analyze_dataset task
└── web/
    ├── package.json
    ├── Dockerfile
    ├── next.config.mjs
    ├── tailwind.config.ts
    └── src/
        ├── app/               # App Router pages
        ├── components/        # UI + workflow animation
        └── lib/               # api client, types
```

## 3. Database schema

```sql
-- users: one row per Google account
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  google_sub    TEXT UNIQUE NOT NULL,      -- OIDC subject
  email         TEXT UNIQUE NOT NULL,
  name          TEXT,
  picture_url   TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login_at TIMESTAMPTZ
);

-- datasets: one row per uploaded CSV
CREATE TABLE datasets (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  filename      TEXT NOT NULL,
  storage_key   TEXT NOT NULL,             -- s3://bucket/users/<uid>/datasets/<id>.csv
  size_bytes    BIGINT NOT NULL,
  row_count     INTEGER,
  col_count     INTEGER,
  sha256        TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'uploaded',  -- uploaded|profiled|failed
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_datasets_user_created ON datasets(user_id, created_at DESC);

-- analysis_jobs: one row per analytics run against a dataset
CREATE TABLE analysis_jobs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_id    UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  mode          TEXT NOT NULL,             -- inline|celery
  status        TEXT NOT NULL DEFAULT 'queued',  -- queued|running|succeeded|failed
  step          TEXT,                      -- current workflow step (for UI progress)
  progress      SMALLINT NOT NULL DEFAULT 0,     -- 0..100
  error         TEXT,
  profile_json  JSONB,                     -- dataset profile + column types
  insights_json JSONB,                     -- deterministic insights payload
  started_at    TIMESTAMPTZ,
  finished_at   TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_jobs_user_created ON analysis_jobs(user_id, created_at DESC);

-- reports: generated Excel artifacts
CREATE TABLE reports (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id        UUID NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  storage_key   TEXT NOT NULL,
  size_bytes    BIGINT NOT NULL,
  sheet_names   JSONB NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_reports_user_created ON reports(user_id, created_at DESC);
```

The MVP uses SQLAlchemy `create_all` on startup. Production: swap to Alembic migrations
(`alembic init`, autogenerate, `alembic upgrade head` in an entrypoint).

## 4. API design

All routes require a valid `if_session` cookie except the auth handshake and health.

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/health` | liveness |
| GET  | `/api/auth/google/login` | 302 → Google consent |
| GET  | `/api/auth/google/callback` | exchange code, upsert user, set session cookie, 302 → web |
| GET  | `/api/auth/me` | current user profile |
| POST | `/api/auth/logout` | clear cookie |
| POST | `/api/datasets` | multipart upload; stores CSV, returns dataset + quick profile |
| GET  | `/api/datasets` | paginated history for current user |
| GET  | `/api/datasets/{id}` | dataset detail |
| DELETE | `/api/datasets/{id}` | delete dataset + cascade |
| POST | `/api/datasets/{id}/analyze` | start analysis job (inline or celery); returns job |
| GET  | `/api/jobs/{id}` | job status + progress + step (poll target) |
| GET  | `/api/jobs` | job history |
| GET  | `/api/reports` | report history |
| GET  | `/api/reports/{id}/download` | 302 → presigned MinIO URL (TTL 300s) |
| DELETE | `/api/reports/{id}` | delete report artifact |

Errors: RFC-7807-ish JSON `{ "detail": "...", "code": "..." }`. Validation → 422.
Rate-limited → 429 with `Retry-After`.

## 5. MCP tools

MCP server mounted at `/mcp` (Streamable HTTP). Auth: bearer token = the same session JWT,
or a per-user API key (`mcp_keys` table — planned). Tools operate only on the caller's data.

| Tool | Args | Returns |
|------|------|---------|
| `list_datasets` | `limit?, cursor?` | recent datasets for the user |
| `get_dataset_profile` | `dataset_id` | column types, shape, missingness, memory |
| `analyze_dataset` | `dataset_id, wait?` | job id (+ inline result if `wait` and small) |
| `get_job_status` | `job_id` | status, step, progress |
| `get_insights` | `job_id` | deterministic insights + recommendations |
| `get_report_url` | `job_id` | presigned Excel download URL |
| `summarize_column` | `dataset_id, column` | stats / value counts for one column |

Resources: `insightforge://datasets/{id}/profile`, `insightforge://jobs/{id}/insights`.

## 6. Analytics workflow

`analytics/engine.py::run_workflow(df, job, progress_cb)` executes ordered steps, each
emitting `(step_name, progress)` so the UI can animate them:

1. `dataset_loading` — read CSV (pandas, dtype sniff, encoding fallback)
2. `schema_detection` — infer column roles: numeric / categorical / text / datetime / boolean / id
3. `data_cleaning` — trim strings, parse dates, coerce numerics, dedupe fully-null rows
4. `type_inference` — finalize dtypes, cardinality, sample values
5. `missing_value_analysis` — per-column null %, rows with any null, missingness patterns
6. `relationship_discovery` — numeric↔numeric (Pearson/Spearman), cat↔num (eta²/ANOVA F),
   cat↔cat (Cramér's V)
7. `statistical_analysis` — describe(), skew/kurtosis, normality (Shapiro sample), CV
8. `anomaly_detection` — per-numeric IQR fences + multivariate IsolationForest score
9. `chart_generation` — pick chart specs (hist, bar, scatter of top corr, box, corr heatmap)
10. `insight_extraction` — deterministic rules → findings + recommendations (`insights.py`)
11. `excel_report_creation` — XlsxWriter workbook (`excel.py`)
12. `final_export` — upload .xlsx to object storage, write `reports` row

Column-type detection (`profiling.py`): datetime via `pd.to_datetime` success ratio ≥ 0.8;
numeric via successful `to_numeric` ratio ≥ 0.8; boolean via 2-value {0,1}/{true,false};
id via uniqueness ≥ 0.98 + name regex; categorical via `nunique <= max(20, 0.05*n)`; else
text.

## 7. Excel report (XlsxWriter)

Workbook theme: branded palette (indigo `#4F46E5`, slate ink, off-white ground), Inter-like
font, frozen header rows, autofilters, conditional formatting, embedded native charts.

| Sheet | Contents (MVP) |
|-------|----------------|
| Executive Dashboard | KPI cards (rows, cols, cells, missing %, numeric cols, outlier rows), top-3 insights, embedded bar of column-type mix |
| Dataset Profile | per-column: role, dtype, non-null, null %, unique, sample; data-bar formatting on null % |
| Summary Statistics | describe() + skew, kurtosis, CV, normal? for numeric columns |
| Correlation Matrix | Pearson matrix, 3-color scale conditional formatting |
| Relationship Analysis | ranked pairs across all type combos with method + strength label |
| Outlier Detection | per-numeric IQR bounds + count; IsolationForest flagged row indices |
| AI Insights | findings (severity, evidence) + actionable recommendations |
| Charts | histograms + top-correlation scatter + box plots as native Excel charts |
| Raw Data | first `RAW_ROWS_CAP` (5000) rows, autofilter, frozen panes |

Planned sheets (documented, not built): Time-Series Insights, Segment Analysis, Pivot Tables.

## 8. Security

- **AuthN:** Google OIDC only (Authlib). No passwords. `state` + `nonce` verified.
- **Session:** short-lived JWT (HS256, 7-day exp) in `HttpOnly; Secure; SameSite=Lax` cookie.
  `SECRET_KEY` from env. No JWT in localStorage.
- **AuthZ:** every query filters by `user_id`; object-storage keys namespaced per user;
  presigned URLs expire in 5 min.
- **Uploads:** extension + MIME allowlist (`text/csv`, `text/plain`), size cap
  (`UPLOAD_MAX_BYTES`, default 100 MB), streamed to storage, sha256 computed, parsed in a
  bounded worker. CSV parsed with `engine="python"` guardrails; no `pd.eval`.
- **Isolation:** analytics runs on data only; no user string is ever `exec`/`eval`'d.
- **Transport:** HTTPS terminated at the reverse proxy; HSTS; CSP on the web app.
- **Secrets:** `.env` for local; production uses Docker secrets / SSM Parameter Store.
- **CORS:** web origin allowlist, credentials true.
- **DB:** least-privilege app role; `ON DELETE CASCADE` for full user data removal (GDPR).

## 9. Rate limiting

Redis fixed-window limiter keyed `rl:{user_id}:{route_class}:{window}`:

| Class | Limit |
|-------|-------|
| auth callback | 10 / 5 min / IP |
| upload | 20 / hour / user |
| analyze | 30 / hour / user |
| read endpoints | 240 / min / user |
| MCP tool calls | 120 / min / user |

Exceed → 429 + `Retry-After`. Celery concurrency and a per-user "1 running job" guard cap
compute abuse.

## 10. Production deployment

**MVP (this repo):** `docker compose up` runs web, api, worker, postgres, redis, minio,
and a `createbuckets` init job. A reverse proxy (Caddy/Traefik) terminates TLS.

**Single VPS:** same compose file + Caddy with automatic HTTPS; nightly `pg_dump` to
object storage; `docker compose pull && up -d` deploys.

**Cloud migration path (AWS example):**
- web + api + worker → container images in ECR, run on ECS Fargate services behind an ALB
  (path routing `/` → web, `/api` + `/mcp` → api).
- Postgres → RDS (Multi-AZ). Redis → ElastiCache. Object storage → S3 (swap MinIO creds,
  code already uses boto3). 
- Secrets → SSM Parameter Store / Secrets Manager, injected as task env.
- CI: GitHub Actions builds/pushes images, runs `alembic upgrade head` as a one-off task,
  updates the ECS service.
- Autoscaling: api on CPU/RPS, worker on Redis queue depth (custom CloudWatch metric).
- Observability: OpenTelemetry traces → OTLP collector; structured JSON logs → CloudWatch;
  Sentry for errors.

GCP equivalent: Cloud Run (web/api) + Cloud Run jobs or GKE (worker) + Cloud SQL +
Memorystore + GCS + Secret Manager.

## 11. Implemented vs. planned

**Implemented in this MVP:** Google OAuth + first-party session cookies (web proxies
`/api` + `/mcp` to the API), upload → storage, sync + Celery analysis, real
pandas/scipy/sklearn workflow (15 steps), deterministic insights, **Data Quality
Scorecard** (`analytics/quality.py`), **Driver Analysis** (`analytics/drivers.py` —
decision-tree drivers + rules + segment lift), **Schema Drift Detection**
(`analytics/drift.py` — fingerprint diff vs. the previous run of a same-named file),
12-sheet XlsxWriter report, dataset/job/report history, presigned downloads, Redis
rate limiting, MCP server with 7 tools, Next.js dashboard with animated workflow,
right-rail analysis panel + quality gauge, monogram avatar, dark/light + drag-drop.

**Planned (specified, not built):** Time-Series / Pivot Excel sheets, per-user MCP
API keys, Alembic migrations, chart image previews in-app (currently spec-only chart
metadata + Excel-native charts), Terraform for AWS/GCP, OTel wiring.
