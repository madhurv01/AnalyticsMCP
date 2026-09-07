
<img
    src="CSVMcp.png"
    alt="LocalDB Agent"
    width="100%"
  />


<div align="center">

# InsightForge

### An AI data-analyst platform — not a CSV converter

Upload a CSV. Get back what a data analyst would spend a day producing:
a profiled schema, real statistical analysis, discovered relationships, anomaly
detection, plain-language findings, actionable recommendations, and a
premium multi-sheet Excel report.

**Multi-user · Google sign-in · persistent history · MCP-native · Docker-deployable**

</div>

---

## Table of contents

- [Why this exists](#why-this-exists)
- [What it actually does](#what-it-actually-does)
- [The analytics workflow](#the-analytics-workflow-12-steps)
- [The Excel report](#the-excel-report)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Repository layout](#repository-layout)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Using the platform](#using-the-platform)
  - [Web app](#1-web-app)
  - [REST API](#2-rest-api)
  - [MCP server](#3-mcp-server-for-llm-clients)
- [Database schema](#database-schema)
- [Security model](#security-model)
- [Rate limiting](#rate-limiting)
- [Testing](#testing)
- [Deployment](#deployment)
- [Implemented vs. planned](#implemented-vs-planned)
- [Troubleshooting](#troubleshooting)

---

## Why this exists

Most "CSV tools" do one of two things: they convert a file from one format to
another, or they draw a couple of charts from columns you hand-pick. Neither
tells you anything you didn't already know.

A real analyst does something different. Given a raw dataset they will:

1. Figure out what each column *is* — an identifier, a category, a measurement, a
   date, a flag — without being told.
2. Assess whether the data can even be trusted — how much is missing, how much is
   duplicated, which values are impossible.
3. Look for structure — which variables move together, which categories drive
   which outcomes.
4. Find the surprises — the outliers, the rows that don't fit the pattern.
5. Summarise all of it in language a decision-maker can act on, and hand over a
   clean, formatted workbook.

**InsightForge automates that entire loop.** It runs genuine analysis with the
same libraries a data scientist would use (pandas, NumPy, SciPy,
scikit-learn), and it packages the result as an in-app dashboard *and* a
branded Excel report. It is also exposed over the **Model Context Protocol**, so
an LLM agent can drive the same analysis programmatically.

There is **no mock data anywhere**. Every number in the report is computed from
the file you uploaded.

---

## What it actually does

| Capability | Detail |
|---|---|
| **Automatic column typing** | Detects `numeric`, `categorical`, `text`, `datetime`, `boolean`, and `id` roles by parse-success ratios, cardinality, uniqueness and name heuristics — not by trusting the CSV's dtypes. |
| **Data-quality profiling** | Per-column null %, rows-with-any-missing, exact duplicate rows, memory footprint, cardinality, sample values. |
| **Data cleaning** | Trims strings, coerces numerics, parses mixed-format dates, normalises booleans, drops fully-empty rows — then re-infers types on the cleaned frame. |
| **Statistical analysis** | `describe()` plus skewness, kurtosis, coefficient of variation, and a Shapiro–Wilk normality test (on a capped sample) for every numeric column. |
| **Correlation** | Full Pearson matrix + ranked top pairs; flags likely multicollinearity / redundant columns. |
| **Relationship discovery** | Cross-type association mining: numeric↔numeric (Pearson & Spearman), categorical↔numeric (correlation ratio η), categorical↔categorical (Cramér's V) — ranked by strength with a `strong / moderate / weak / negligible` label. |
| **Anomaly detection** | Per-numeric IQR fences (1.5×) **and** a multivariate `IsolationForest` that flags whole rows that don't fit. |
| **Chart generation** | Chooses appropriate visualisations per column type (histograms, box plots, bar charts, scatter of the top-correlated pair, correlation heatmap) and embeds them as **native Excel charts**. |
| **Deterministic insights** | Rule-based findings, each carrying its evidence and a severity (`critical / warning / info`), plus prioritised recommendations. Fully explainable — no LLM, no hallucination. |
| **Premium Excel export** | 9 professionally formatted sheets: KPI cards, conditional formatting, data bars, 3-colour scales, frozen panes, autofilters, embedded charts, branded palette. |
| **History & report management** | Every upload, job and report is persisted per user and listed in the dashboard; reports download via short-lived presigned URLs. |
| **Background processing** | Files under 5 MB analyse inline in the request; larger files are handed to a Celery worker and the UI polls live progress. |
| **MCP server** | The same analytics capability exposed as 7 MCP tools over Streamable HTTP, authenticated with the user's session token, scoped to that user's data. |

---

## The analytics workflow (12 steps)

When a job runs, the engine emits progress after each step so the UI can animate
it. These are real processing stages, not a loading spinner:

| # | Step | What happens |
|---|------|--------------|
| 1 | `dataset_loading` | Read the CSV — encoding fallback (utf-8 → utf-8-sig → latin-1), delimiter sniffing, bad-line skipping. |
| 2 | `schema_detection` | First-pass column-role inference on the raw frame. |
| 3 | `data_cleaning` | Trim, coerce, parse dates, normalise booleans, drop empty rows. |
| 4 | `type_inference` | Re-infer roles on the cleaned frame; lock in numeric/categorical/datetime sets. |
| 5 | `missing_value_analysis` | Build the full dataset profile — null %, missingness patterns, duplicates, memory. |
| 6 | `relationship_discovery` | Mine associations across every type combination; rank them. |
| 7 | `statistical_analysis` | Summary stats, distribution shape, normality; correlation matrix + top pairs. |
| 8 | `anomaly_detection` | IQR outliers per numeric column + `IsolationForest` on the numeric subspace. |
| 9 | `chart_generation` | Decide the chart specs the report will render. |
| 10 | `insight_extraction` | Apply the deterministic rule set → findings + recommendations + headline. |
| 11 | `excel_report_creation` | Build the 9-sheet workbook with XlsxWriter. |
| 12 | `final_export` | Upload the `.xlsx` to object storage, write the `reports` row. |

---

## The Excel report

Workbook theme: indigo `#4F46E5` brand accent, slate ink, off-white ground,
hidden gridlines, frozen header rows, autofilters.

| Sheet | Contents |
|-------|----------|
| **Executive Dashboard** | KPI cards (rows, columns, cells, missing %, numeric columns, outlier rows), the analysis headline, the top-3 findings, and an embedded column-type-mix bar chart. |
| **Dataset Profile** | Every column: role, dtype, non-null count, null % (with data-bar formatting), unique count, sample values. Autofiltered, frozen panes. |
| **Summary Statistics** | For each numeric column: count, mean, std, min, quartiles, median, max, skew, kurtosis, CV, and a normality verdict. |
| **Correlation Matrix** | Full Pearson matrix with a red–white–blue 3-colour scale, plus the ranked top-10 correlated pairs. |
| **Relationship Analysis** | Every discovered association (all type combinations) with method, strength and label, ranked and autofiltered. |
| **Outlier Detection** | Per-numeric IQR fences and outlier counts/percentages with example values; the `IsolationForest` flagged-row count and indices. |
| **AI Insights** | The headline, the full findings table (severity-coloured, with evidence), and the prioritised recommendations table. |
| **Charts** | Native Excel histograms for the top numeric columns and a scatter of the most-correlated pair. |
| **Raw Data** | The first 5,000 rows of the cleaned frame, autofiltered with frozen header. |

*Planned sheets (specified in `ARCHITECTURE.md`, not yet built): Time-Series
Insights, Segment Analysis, Pivot Tables.*

---

## Architecture

```
┌────────────┐      HTTPS       ┌──────────────────────────────┐
│  Next.js   │ ───────────────▶ │  FastAPI (uvicorn)            │
│  web app   │  session cookie  │  ├─ /api/*   REST            │
│            │ ◀─────────────── │  ├─ /mcp     MCP (HTTP/SSE)  │
└────────────┘                  │  └─ analytics engine (pkg)  │
      │                         └────────┬─────────────────────┘
      │ OAuth                            │ enqueue (files > 5 MB)
      ▼                                  ▼
  Google OIDC                    ┌─────────────┐   ┌──────────┐
                                 │ Celery      │──▶│ Postgres │  users, datasets,
                                 │ worker(s)   │   ├──────────┤  jobs, reports
                                 │ (same pkg)  │──▶│  Redis   │  broker · rate limit
                                 └──────┬──────┘   ├──────────┤
                                        └─────────▶│  MinIO   │  raw CSVs + .xlsx
                                                   └──────────┘  (S3-compatible)
```

- **One FastAPI process** serves the REST API *and* mounts the MCP server at
  `/mcp`. The analytics engine is a plain importable package shared by the
  request path and the Celery worker.
- **Sync vs. async:** `size ≤ INLINE_MAX_BYTES` (default 5 MB) analyses inside the
  request; anything larger is queued to Celery and polled via `GET /api/jobs/{id}`.
- **Object storage** is accessed through boto3, so moving from MinIO to real S3
  is a credentials change, not a code change.

Full details — schema, endpoint list, MCP tool specs, cloud migration path — are
in [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## Technology stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Framer Motion, lucide-react |
| API | FastAPI, Uvicorn, SQLAlchemy 2, Pydantic v2, Authlib (Google OIDC), python-jose |
| Analytics | pandas, NumPy, SciPy, scikit-learn |
| Reporting | XlsxWriter (native charts, conditional formatting) |
| MCP | `mcp` Python SDK — `FastMCP`, Streamable HTTP transport |
| Async | Celery, Redis (broker + result backend) |
| Data | PostgreSQL 16, Redis 7, MinIO (S3-compatible object storage) |
| Packaging | Docker, Docker Compose |

---

## Repository layout

```
.
├── docker-compose.yml         # web · api · worker · postgres · redis · minio
├── .env.example               # copy to .env and fill in
├── ARCHITECTURE.md            # deep design doc
│
├── api/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py            # FastAPI factory, router + MCP mount, middleware
│   │   ├── config.py          # pydantic-settings
│   │   ├── db.py              # engine, session, Base, create_all
│   │   ├── models.py          # User, Dataset, AnalysisJob, Report
│   │   ├── schemas.py         # Pydantic DTOs
│   │   ├── security.py        # JWT session cookies, current_user dependency
│   │   ├── ratelimit.py       # Redis fixed-window limiter
│   │   ├── storage.py         # S3 / MinIO helpers (put, get, delete, presign)
│   │   ├── jobs.py            # execute_job() — shared by request path & worker
│   │   ├── worker.py          # Celery app + analyze_dataset task
│   │   ├── mcp_server.py      # 7 MCP tools + bearer-auth middleware
│   │   ├── routers/
│   │   │   ├── auth.py        # Google login / callback / me / logout
│   │   │   ├── datasets.py    # upload, list, get, delete, analyze, jobs
│   │   │   └── reports.py     # list, download (presigned), delete
│   │   └── analytics/
│   │       ├── engine.py          # run_workflow() orchestrator
│   │       ├── profiling.py       # role inference, cleaning, profile
│   │       ├── stats.py           # summary stats, correlation
│   │       ├── relationships.py   # cross-type association discovery
│   │       ├── outliers.py        # IQR + IsolationForest
│   │       ├── insights.py        # deterministic rule engine
│   │       └── excel.py           # XlsxWriter report builder
│   ├── tests/
│   │   └── test_engine.py     # real end-to-end engine test (no infra needed)
│   └── sample_data/
│       ├── orders.csv                 # tiny dirty sample
│       ├── insightforge_test_50k.csv  # 50k-row feature-exercising dataset
│       └── generate_big_test.py       # generator for the above
│
└── web/
    ├── Dockerfile
    ├── package.json
    ├── tailwind.config.ts
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx           # landing
        │   ├── globals.css
        │   └── dashboard/page.tsx # the app
        ├── components/
        │   ├── theme-provider.tsx     # dark / light
        │   ├── top-bar.tsx
        │   ├── upload-dropzone.tsx    # drag & drop
        │   ├── workflow-animation.tsx # 12-step animated progress
        │   └── insights-panel.tsx     # KPI cards + findings + recommendations
        └── lib/
            ├── api.ts        # typed API client
            ├── workflow.ts   # step metadata
            └── utils.ts
```

---

## Getting started

### Prerequisites

- Docker + Docker Compose
- A Google OAuth 2.0 Client (Web application type) — **only needed for login**

### Run everything

```bash
git clone https://github.com/madhurv01/AnalyticsMCP.git
cd AnalyticsMCP
git checkout csvmcpDevelopment

cp .env.example .env
# generate a session secret:
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(48))"
# paste that into .env, then add your Google client id/secret (see Configuration)

docker compose up --build -d
```

| Service | URL |
|---------|-----|
| Web app | http://localhost:3000 |
| API (Swagger UI) | http://localhost:8000/docs |
| MCP endpoint | http://localhost:8000/mcp |
| MinIO console | http://localhost:9001 &nbsp;(`minioadmin` / `minioadmin`) |

```bash
docker compose logs -f api        # tail logs
docker compose down               # stop, keep data
docker compose down -v            # stop, wipe database + object storage
```

### Run just the analytics engine (no Docker)

```bash
cd api
pip install .
python -m pytest tests/ -q        # generates a real dataset, runs all 12 steps,
                                  # asserts a valid 9-sheet .xlsx is produced
```

---

## Configuration

All configuration is environment variables (see [`.env.example`](.env.example)).
`.env` is **git-ignored** — never commit real credentials.

| Variable | Purpose | Default |
|----------|---------|---------|
| `SECRET_KEY` | Signs session JWTs — **must** be set to a long random string | `dev-secret` |
| `ENV` | `development` / `production` (controls cookie `Secure` flag) | `development` |
| `WEB_ORIGIN` | Allowed CORS origin for the web app | `http://localhost:3000` |
| `API_BASE_URL` | Public base URL of the API (used to build the OAuth redirect) | `http://localhost:8000` |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth credentials | *(empty)* |
| `DATABASE_URL` | PostgreSQL SQLAlchemy URL | compose default |
| `REDIS_URL` / `CELERY_BROKER_URL` | Redis connections | compose default |
| `S3_ENDPOINT_URL` | Internal S3 endpoint (MinIO service) | `http://minio:9000` |
| `S3_PUBLIC_ENDPOINT_URL` | Browser-reachable S3 endpoint (for presigned URLs) | `http://localhost:9000` |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_BUCKET` | Object storage credentials | `minioadmin` / `minioadmin` / `insightforge` |
| `UPLOAD_MAX_BYTES` | Hard upload size cap | `104857600` (100 MB) |
| `INLINE_MAX_BYTES` | Files at or below this analyse inline; above → Celery | `5242880` (5 MB) |
| `RAW_ROWS_CAP` | Max rows written to the report's Raw Data sheet | `5000` |
| `NEXT_PUBLIC_API_BASE_URL` | API base URL the browser calls | `http://localhost:8000` |

### Setting up Google OAuth

1. [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
   → **Create Credentials → OAuth client ID → Web application**.
2. **Authorized redirect URI** (exact):
   `http://localhost:8000/api/auth/google/callback`
3. On the OAuth consent screen, add your Google account under **Test users**
   (or publish the app).
4. Put the client ID and secret in `.env`, then
   `docker compose up -d --force-recreate api`.

> **Paste carefully** — a stray character in `GOOGLE_CLIENT_ID` produces
> `Error 401: invalid_client` at the Google screen.

### Trying it without OAuth

The engine and API work without Google. Mint a session token directly:

```bash
docker compose exec api python -c "from app.db import SessionLocal; from app.models import User; from app.security import issue_session; db=SessionLocal(); u=db.query(User).first() or User(google_sub='dev',email='dev@example.com'); db.add(u); db.commit(); db.refresh(u); print(issue_session(u.id))"
```

Use the printed token as `Authorization: Bearer <token>` against the API / MCP
endpoint, or set it as the `if_session` cookie for the web app.

---

## Using the platform

### 1. Web app

1. Sign in with Google.
2. Drag a `.csv` onto the dropzone (or click to browse).
3. Watch the 12-step workflow animate with live progress.
4. When it finishes: KPI cards, the headline, severity-coded findings and
   recommendations render in the dashboard, and the Excel report is one click away.
5. Every dataset and report stays in the sidebar history — re-run analysis or
   re-download any time.

### 2. REST API

Interactive docs at `/docs`. Core flow:

```bash
BASE=http://localhost:8000
TOKEN=<session jwt>

# upload
curl -s -H "Authorization: Bearer $TOKEN" \
  -F "file=@api/sample_data/insightforge_test_50k.csv;type=text/csv" \
  $BASE/api/datasets
# → { "id": "<dataset_id>", ... }

# start analysis  (add {"force_async": true} to force the Celery path)
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "content-type: application/json" \
  -d '{}' $BASE/api/datasets/<dataset_id>/analyze
# → { "id": "<job_id>", "status": "...", ... }

# poll
curl -s -H "Authorization: Bearer $TOKEN" $BASE/api/jobs/<job_id>
# → status, step, progress (0-100), profile_json, insights_json

# list reports, then download (302 → presigned URL, 5-min TTL)
curl -s -H "Authorization: Bearer $TOKEN" $BASE/api/reports
curl -sL -H "Authorization: Bearer $TOKEN" $BASE/api/reports/<report_id>/download -o report.xlsx
```

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | liveness |
| `GET` | `/api/auth/google/login` | → Google consent |
| `GET` | `/api/auth/google/callback` | exchange code, set session cookie |
| `GET` | `/api/auth/me` | current user |
| `POST` | `/api/auth/logout` | clear session |
| `POST` | `/api/datasets` | upload a CSV |
| `GET` | `/api/datasets` | list (paginated) |
| `GET` / `DELETE` | `/api/datasets/{id}` | detail / delete |
| `POST` | `/api/datasets/{id}/analyze` | start a job |
| `GET` | `/api/jobs` · `/api/jobs/{id}` | job history / status |
| `GET` | `/api/reports` | report history |
| `GET` | `/api/reports/{id}/download` | presigned download |
| `DELETE` | `/api/reports/{id}` | delete a report |

### 3. MCP server (for LLM clients)

Streamable HTTP at `http://localhost:8000/mcp`. Authenticate with the session
JWT as a bearer token. Example client config:

```jsonc
{
  "mcpServers": {
    "insightforge": {
      "type": "http",
      "url": "http://localhost:8000/mcp",
      "headers": { "Authorization": "Bearer <your-session-jwt>" }
    }
  }
}
```

| Tool | Arguments | Returns |
|------|-----------|---------|
| `list_datasets` | `limit?` | recent datasets for the caller |
| `get_dataset_profile` | `dataset_id` | column roles, shape, missingness (needs a completed job) |
| `analyze_dataset` | `dataset_id` | new `job_id` (queued to Celery) |
| `get_job_status` | `job_id` | `status`, `step`, `progress`, `error` |
| `get_insights` | `job_id` | headline, findings, recommendations |
| `get_report_url` | `job_id` | 5-minute presigned Excel URL + sheet list |
| `summarize_column` | `job_id`, `column` | computed stats / profile for one column |

Every tool resolves the bearer token to a user and filters strictly by that
user's id — an MCP client can never see another user's data.

---

## Database schema

Four tables, all owned by a user, all cascade-deleting so a user can be fully
removed in one statement.

- **`users`** — one row per Google account (`google_sub`, `email`, `name`,
  `picture_url`, timestamps).
- **`datasets`** — one row per uploaded CSV (`storage_key`, `size_bytes`,
  `sha256`, `row_count`, `col_count`, `status`).
- **`analysis_jobs`** — one row per analytics run (`mode` inline/celery,
  `status`, `step`, `progress`, `error`, `profile_json`, `insights_json`,
  timestamps).
- **`reports`** — one row per generated workbook (`storage_key`, `size_bytes`,
  `sheet_names`).

The MVP creates tables with SQLAlchemy `create_all` on startup. Production should
switch to Alembic migrations. Full DDL is in
[`ARCHITECTURE.md`](ARCHITECTURE.md#3-database-schema).

---

## Security model

- **Authentication:** Google OIDC only. No passwords are stored or accepted.
  OAuth `state` and `nonce` are verified by Authlib.
- **Sessions:** a short-lived JWT (HS256, 7-day expiry) in an
  `HttpOnly; SameSite=Lax` cookie (`Secure` in production). No token in
  `localStorage`.
- **Authorisation:** every query is filtered by `user_id`; object-storage keys
  are namespaced `users/<uid>/…`; download URLs are presigned and expire in
  5 minutes.
- **Uploads:** `.csv` extension + content-type allowlist, a hard byte cap,
  streamed to storage, SHA-256 recorded. CSVs are parsed with bounded pandas
  options; **no user input is ever `eval`/`exec`'d**, and `pd.eval` is not used.
- **Isolation:** the analytics engine operates on data only — column names and
  cell values never become code.
- **Transport:** designed to sit behind a TLS-terminating reverse proxy with
  HSTS; CORS is locked to `WEB_ORIGIN` with credentials.
- **Secrets:** `.env` for local dev (git-ignored); Docker secrets or a cloud
  parameter store in production.
- **One running job per user** is enforced to cap compute abuse.

---

## Rate limiting

Redis fixed-window limiter, keyed per user (falls back to IP), fail-open if Redis
is unavailable:

| Class | Limit |
|-------|-------|
| OAuth callback | 10 / 5 min |
| Upload | 20 / hour |
| Analyze | 30 / hour |
| Read endpoints | 240 / min |
| MCP tool calls | 120 / min |

Exceeding a limit returns `429` with a `Retry-After` header.

---

## Testing

```bash
cd api
pip install .
python -m pytest tests/ -q
```

`tests/test_engine.py` builds a 500-row synthetic dataset with injected nulls and
outliers, runs the complete 12-step workflow, and asserts:

- all 12 steps fire, in order;
- column roles are inferred correctly (`region` → categorical, `order_date` →
  datetime, `revenue` → numeric);
- outlier findings are produced;
- the output is a valid `.xlsx` with 9 sheets.

No database, Redis or object storage is required for the engine test.

---

## Deployment

**Local / single VPS (this repo):** `docker compose up -d` behind a
TLS-terminating reverse proxy (Caddy or Traefik). Nightly `pg_dump` to object
storage for backups. Deploy with `docker compose pull && docker compose up -d`.

**Cloud (design in `ARCHITECTURE.md`):**

- `web`, `api`, `worker` → container images, run as services on ECS Fargate /
  Cloud Run behind a load balancer (path routing: `/` → web, `/api` + `/mcp` →
  api).
- PostgreSQL → RDS / Cloud SQL (Multi-AZ). Redis → ElastiCache / Memorystore.
  Object storage → S3 / GCS (swap credentials — the code already uses boto3).
- Secrets → SSM Parameter Store / Secret Manager.
- Migrations → run `alembic upgrade head` as a one-off task in the deploy
  pipeline.
- Autoscaling → api on CPU/RPS, worker on Redis queue depth.

---

## Implemented vs. planned

**Implemented (this MVP):** Google OAuth + session cookies, upload → object
storage, inline + Celery analysis paths, the full 12-step pandas/SciPy/sklearn
workflow, deterministic insight engine, 9-sheet XlsxWriter report, dataset / job
/ report history, presigned downloads, Redis rate limiting, MCP server with 7
tools, Next.js dashboard with animated workflow, dark/light theme and
drag-and-drop upload.

**Planned (specified, not built):** Time-Series / Segment / Pivot-Table Excel
sheets, per-user MCP API keys, Alembic migrations, in-app chart image previews,
Terraform for AWS/GCP, OpenTelemetry tracing, an LLM-narrated insight layer on
top of the deterministic one.

---

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| Google: `Error 401: invalid_client` / "OAuth client was not found" | `GOOGLE_CLIENT_ID` in `.env` is wrong or has stray characters. Fix it and `docker compose up -d --force-recreate api`. |
| Google: `redirect_uri_mismatch` | Add `http://localhost:8000/api/auth/google/callback` exactly to the client's Authorized redirect URIs. |
| Google: `access_denied` | Add your account as a Test user on the OAuth consent screen. |
| `api` container exits on boot | Check `docker compose logs api`. Usually a bad `DATABASE_URL` or an unset `SECRET_KEY` isn't fatal but Google vars being malformed can be. |
| Report download 404 | The job must have `status = succeeded`; check `GET /api/jobs/{id}`. |
| Large file "stuck" at low progress | It's on the Celery path — check `docker compose logs worker`. |
| `429 Too Many Requests` | You hit a rate-limit window; wait for `Retry-After` seconds. |

---

<div align="center">

Built as a demonstration of a production-shaped AI analytics platform.
See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full design.

</div>
