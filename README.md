# InsightForge — AI-Powered CSV Analytics Platform

A production-oriented **vertical-slice MVP** of an AI data-analyst platform. Upload a CSV, a
Python analytics engine (Pandas / NumPy / SciPy / scikit-learn) profiles it, runs real
statistical analysis, detects outliers and relationships, generates deterministic business
insights, and produces a premium multi-sheet Excel report. Multi-user, Google OAuth only,
persistent history, MCP server mounted on the same FastAPI app, background workers for large
files.

> This repo is the MVP slice described in `ARCHITECTURE.md`. It is end-to-end runnable via
> `docker compose up`. Not every sheet/analysis in the full spec is implemented — see
> "Implemented vs. planned" in `ARCHITECTURE.md`.

## Quick start

```bash
cp .env.example .env
# put real Google OAuth credentials in .env (see ARCHITECTURE.md "Auth setup")
docker compose up --build
# web:  http://localhost:3000
# api:  http://localhost:8000/docs
# mcp:  http://localhost:8000/mcp   (Streamable HTTP)
```

## Stack

| Layer      | Tech |
|------------|------|
| Frontend   | Next.js 14 (App Router), React 18, TypeScript, Tailwind, Framer Motion, shadcn-style UI |
| API        | FastAPI, SQLAlchemy 2, Pydantic v2, Authlib (Google OIDC), python-jose |
| Analytics  | pandas, numpy, scipy, scikit-learn |
| Reports    | XlsxWriter |
| MCP        | `mcp` Python SDK, Streamable-HTTP transport mounted at `/mcp` |
| Async      | Celery + Redis |
| Data       | PostgreSQL 16, Redis 7, MinIO (S3-compatible object storage) |
| Deploy     | Docker Compose (local / single VPS) |

See `ARCHITECTURE.md` for schema, API surface, MCP tools, workflow, security, rate limiting
and the cloud migration path.

## Run the analytics engine without Docker

```bash
cd api && pip install . && python -m pytest tests/ -q   # real end-to-end engine test
```

## MCP client

The MCP server is Streamable HTTP at `http://localhost:8000/mcp`. Authenticate with the
session JWT from a browser login (cookie `if_session`) as a bearer token:

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

Tools: `list_datasets`, `get_dataset_profile`, `analyze_dataset`, `get_job_status`,
`get_insights`, `get_report_url`, `summarize_column`.

## Auth setup

Create an OAuth 2.0 Client ID (type: Web) in Google Cloud Console. Authorized redirect URI:
`http://localhost:8000/api/auth/google/callback`. Put the client id/secret in `.env`.
