"""MCP server exposing the analytics platform to LLM clients.

Mounted on the FastAPI app at /mcp (Streamable HTTP transport).

Auth: every request must carry `Authorization: Bearer <session-jwt>` — the same token
issued by the web login. A contextvar carries the resolved user id into each tool call so
tools only ever touch the caller's own data.
"""
import contextvars
import uuid
from typing import Optional

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.db import SessionLocal
from app.models import AnalysisJob, Dataset
from app.security import _decode  # noqa: PLC2701 — internal reuse is intentional
from app.storage import presigned_get

_current_user_id: "contextvars.ContextVar[Optional[uuid.UUID]]" = contextvars.ContextVar(
    "mcp_user_id", default=None
)

mcp = FastMCP("InsightForge", streamable_http_path="/")


def _uid() -> uuid.UUID:
    uid = _current_user_id.get()
    if uid is None:
        raise PermissionError("missing or invalid bearer token")
    return uid


class BearerAuthMiddleware:
    """Resolve the session JWT before the MCP ASGI app handles the request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            request = Request(scope, receive)
            auth = request.headers.get("authorization", "")
            token = auth[7:] if auth.lower().startswith("bearer ") else None
            if token:
                try:
                    _current_user_id.set(_decode(token))
                except Exception:
                    _current_user_id.set(None)
            else:
                _current_user_id.set(None)
        await self.app(scope, receive, send)


@mcp.tool()
def list_datasets(limit: int = 10) -> list[dict]:
    """List the caller's most recently uploaded datasets."""
    with SessionLocal() as db:
        rows = (
            db.query(Dataset)
            .filter(Dataset.user_id == _uid())
            .order_by(Dataset.created_at.desc())
            .limit(min(limit, 50))
            .all()
        )
        return [
            {
                "id": str(r.id),
                "filename": r.filename,
                "rows": r.row_count,
                "cols": r.col_count,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]


@mcp.tool()
def get_dataset_profile(dataset_id: str) -> dict:
    """Return the profiled schema (column roles, shape, missingness) for a dataset.

    Requires a completed analysis job; run `analyze_dataset` first if needed.
    """
    with SessionLocal() as db:
        job = (
            db.query(AnalysisJob)
            .filter(
                AnalysisJob.user_id == _uid(),
                AnalysisJob.dataset_id == uuid.UUID(dataset_id),
                AnalysisJob.status == "succeeded",
            )
            .order_by(AnalysisJob.created_at.desc())
            .first()
        )
        if job is None:
            return {"error": "no completed analysis for this dataset"}
        return job.profile_json or {}


@mcp.tool()
def analyze_dataset(dataset_id: str) -> dict:
    """Start an analysis job for a dataset. Returns the job id to poll with get_job_status."""
    from app.worker import analyze_dataset as task

    with SessionLocal() as db:
        ds = db.get(Dataset, uuid.UUID(dataset_id))
        if ds is None or ds.user_id != _uid():
            return {"error": "dataset not found"}
        job = AnalysisJob(dataset_id=ds.id, user_id=_uid(), mode="celery")
        db.add(job)
        db.commit()
        db.refresh(job)
        task.delay(str(job.id))
        return {"job_id": str(job.id), "status": job.status}


@mcp.tool()
def get_job_status(job_id: str) -> dict:
    """Get the status, current workflow step and progress (0-100) of an analysis job."""
    with SessionLocal() as db:
        job = db.get(AnalysisJob, uuid.UUID(job_id))
        if job is None or job.user_id != _uid():
            return {"error": "job not found"}
        return {
            "status": job.status,
            "step": job.step,
            "progress": job.progress,
            "error": job.error,
        }


@mcp.tool()
def get_insights(job_id: str) -> dict:
    """Return the deterministic insights, findings and recommendations for a completed job."""
    with SessionLocal() as db:
        job = db.get(AnalysisJob, uuid.UUID(job_id))
        if job is None or job.user_id != _uid():
            return {"error": "job not found"}
        if job.status != "succeeded":
            return {"error": f"job is {job.status}"}
        payload = dict(job.insights_json or {})
        payload.pop("analysis", None)
        return payload


@mcp.tool()
def get_report_url(job_id: str) -> dict:
    """Return a short-lived presigned URL to download the Excel report for a job."""
    with SessionLocal() as db:
        job = db.get(AnalysisJob, uuid.UUID(job_id))
        if job is None or job.user_id != _uid() or job.report is None:
            return {"error": "no report available"}
        url = presigned_get(job.report.storage_key, f"report-{job_id}.xlsx", ttl=300)
        return {"url": url, "expires_in": 300, "sheets": job.report.sheet_names}


@mcp.tool()
def summarize_column(job_id: str, column: str) -> dict:
    """Return computed statistics for a single column from a completed analysis job."""
    with SessionLocal() as db:
        job = db.get(AnalysisJob, uuid.UUID(job_id))
        if job is None or job.user_id != _uid() or job.status != "succeeded":
            return {"error": "no completed job"}
        analysis = (job.insights_json or {}).get("analysis", {})
        for row in analysis.get("summary", []):
            if row["column"] == column:
                return row
        for col in (job.profile_json or {}).get("columns", []):
            if col["name"] == column:
                return col
        return {"error": "column not found"}


def build_mcp_app():
    """Starlette ASGI app for the MCP server, wrapped with bearer-token resolution.

    The returned app owns its own lifespan (session manager), so mount it and pass
    `.lifespan` through to the parent app.
    """
    app = mcp.streamable_http_app()
    app.add_middleware(BearerAuthMiddleware)
    return app
