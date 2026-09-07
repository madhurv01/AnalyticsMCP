import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.jobs import execute_job
from app.models import AnalysisJob, Dataset, User
from app.ratelimit import limit
from app.schemas import AnalyzeRequest, DatasetOut, JobDetailOut, JobOut, Page
from app.security import current_user
from app.storage import delete_key, put_bytes

router = APIRouter(prefix="/api", tags=["datasets"])

ALLOWED_CT = {
    "text/csv", "text/plain", "application/csv", "application/vnd.ms-excel",
    "application/octet-stream", "",
}


def _owned_dataset(db: Session, user: User, dataset_id: uuid.UUID) -> Dataset:
    ds = db.get(Dataset, dataset_id)
    if ds is None or ds.user_id != user.id:
        raise HTTPException(404, "dataset not found")
    return ds


def _owned_job(db: Session, user: User, job_id: uuid.UUID) -> AnalysisJob:
    job = db.get(AnalysisJob, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(404, "job not found")
    return job


@router.post("/datasets", response_model=DatasetOut, dependencies=[Depends(limit("upload"))])
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(422, "only .csv files are accepted")
    if file.content_type not in ALLOWED_CT:
        raise HTTPException(422, f"unsupported content type: {file.content_type}")

    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(422, "file is empty")
    if len(raw) > settings.upload_max_bytes:
        raise HTTPException(413, "file exceeds the size limit")

    ds_id = uuid.uuid4()
    key = f"users/{user.id}/datasets/{ds_id}.csv"
    put_bytes(key, raw, "text/csv")

    ds = Dataset(
        id=ds_id,
        user_id=user.id,
        filename=file.filename,
        storage_key=key,
        size_bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),
        status="uploaded",
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds


@router.get("/datasets", response_model=Page)
def list_datasets(
    limit_: int = Query(20, alias="limit", le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    total = db.scalar(select(func.count()).select_from(Dataset).where(Dataset.user_id == user.id))
    rows = db.scalars(
        select(Dataset).where(Dataset.user_id == user.id)
        .order_by(Dataset.created_at.desc()).limit(limit_).offset(offset)
    ).all()
    return Page(items=[DatasetOut.model_validate(r).model_dump(mode="json") for r in rows],
               total=total or 0, limit=limit_, offset=offset)


@router.get("/datasets/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _owned_dataset(db, user, dataset_id)


@router.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ds = _owned_dataset(db, user, dataset_id)
    try:
        delete_key(ds.storage_key)
    except Exception:
        pass
    db.delete(ds)
    db.commit()
    return {"ok": True}


@router.post("/datasets/{dataset_id}/analyze", response_model=JobOut,
             dependencies=[Depends(limit("analyze"))])
def analyze(
    dataset_id: uuid.UUID,
    body: AnalyzeRequest = AnalyzeRequest(),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    ds = _owned_dataset(db, user, dataset_id)

    running = db.scalar(
        select(func.count()).select_from(AnalysisJob)
        .where(AnalysisJob.user_id == user.id, AnalysisJob.status.in_(["queued", "running"]))
    )
    if running:
        raise HTTPException(409, "you already have a job running")

    use_async = body.force_async or ds.size_bytes > settings.inline_max_bytes
    job = AnalysisJob(dataset_id=ds.id, user_id=user.id, mode="celery" if use_async else "inline")
    db.add(job)
    db.commit()
    db.refresh(job)

    if use_async:
        from app.worker import analyze_dataset as task

        task.delay(str(job.id))
    else:
        execute_job(db, job.id)
        db.refresh(job)
    return job


@router.get("/jobs", response_model=Page)
def list_jobs(
    limit_: int = Query(20, alias="limit", le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    total = db.scalar(select(func.count()).select_from(AnalysisJob).where(AnalysisJob.user_id == user.id))
    rows = db.scalars(
        select(AnalysisJob).where(AnalysisJob.user_id == user.id)
        .order_by(AnalysisJob.created_at.desc()).limit(limit_).offset(offset)
    ).all()
    return Page(items=[JobOut.model_validate(r).model_dump(mode="json") for r in rows],
               total=total or 0, limit=limit_, offset=offset)


@router.get("/jobs/{job_id}", response_model=JobDetailOut)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _owned_job(db, user, job_id)
