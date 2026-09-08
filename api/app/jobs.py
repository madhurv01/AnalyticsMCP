"""Job execution shared by the inline request path and the Celery worker."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.analytics.engine import run_workflow
from app.config import settings
from app.models import AnalysisJob, Dataset, Report
from app.storage import get_bytes, put_bytes


def execute_job(db: Session, job_id: uuid.UUID) -> None:
    job = db.get(AnalysisJob, job_id)
    if job is None:
        return
    dataset = db.get(Dataset, job.dataset_id)

    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    db.commit()

    def progress_cb(step: str, pct: int) -> None:
        job.step = step
        job.progress = pct
        db.commit()

    try:
        raw = get_bytes(dataset.storage_key)

        # Feature 3: diff this run against the last successful run of a same-named file.
        prior = (
            db.query(AnalysisJob)
            .join(Dataset, AnalysisJob.dataset_id == Dataset.id)
            .filter(
                AnalysisJob.user_id == job.user_id,
                AnalysisJob.status == "succeeded",
                AnalysisJob.id != job.id,
                Dataset.filename == dataset.filename,
            )
            .order_by(AnalysisJob.created_at.desc())
            .first()
        )
        prior_fp = (prior.profile_json or {}).get("schema_fingerprint") if prior else None

        result = run_workflow(
            raw, dataset.filename, progress_cb,
            raw_rows_cap=settings.raw_rows_cap, prior_fingerprint=prior_fp,
        )

        report_key = f"users/{job.user_id}/reports/{job.id}.xlsx"
        put_bytes(
            report_key,
            result["xlsx_bytes"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        job.profile_json = result["profile"]
        job.insights_json = {
            **result["insights"],
            "quality": result["quality"],
            "drivers": result["drivers"],
            "drift": result["drift"],
            "analysis": result["analysis"],
        }
        job.status = "succeeded"
        job.progress = 100
        job.step = "final_export"
        job.finished_at = datetime.now(timezone.utc)

        dataset.status = "profiled"
        dataset.row_count = result["row_count"]
        dataset.col_count = result["col_count"]

        db.add(Report(
            job_id=job.id,
            user_id=job.user_id,
            storage_key=report_key,
            size_bytes=len(result["xlsx_bytes"]),
            sheet_names=result["sheet_names"],
        ))
        db.commit()
    except Exception as exc:  # noqa: BLE001 — record failure, don't crash the worker
        db.rollback()
        job = db.get(AnalysisJob, job_id)
        job.status = "failed"
        job.error = f"{type(exc).__name__}: {exc}"[:1000]
        job.finished_at = datetime.now(timezone.utc)
        if dataset := db.get(Dataset, job.dataset_id):
            dataset.status = "failed"
        db.commit()
