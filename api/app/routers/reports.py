import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Report, User
from app.schemas import Page, ReportOut
from app.security import current_user
from app.storage import delete_key, presigned_get

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _owned(db: Session, user: User, report_id: uuid.UUID) -> Report:
    rep = db.get(Report, report_id)
    if rep is None or rep.user_id != user.id:
        raise HTTPException(404, "report not found")
    return rep


@router.get("", response_model=Page)
def list_reports(
    limit_: int = Query(20, alias="limit", le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    total = db.scalar(select(func.count()).select_from(Report).where(Report.user_id == user.id))
    rows = db.scalars(
        select(Report).where(Report.user_id == user.id)
        .order_by(Report.created_at.desc()).limit(limit_).offset(offset)
    ).all()
    return Page(items=[ReportOut.model_validate(r).model_dump(mode="json") for r in rows],
               total=total or 0, limit=limit_, offset=offset)


@router.get("/{report_id}/download")
def download(report_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    rep = _owned(db, user, report_id)
    filename = f"insightforge-report-{report_id}.xlsx"
    return RedirectResponse(presigned_get(rep.storage_key, filename, ttl=300))


@router.delete("/{report_id}")
def delete_report(report_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    rep = _owned(db, user, report_id)
    try:
        delete_key(rep.storage_key)
    except Exception:
        pass
    db.delete(rep)
    db.commit()
    return {"ok": True}
