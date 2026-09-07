import uuid

from celery import Celery

from app.config import settings
from app.db import SessionLocal, init_db
from app.jobs import execute_job

celery_app = Celery("insightforge", broker=settings.celery_broker_url, backend=settings.celery_broker_url)
celery_app.conf.update(task_track_started=True, task_time_limit=1800, worker_max_tasks_per_child=20)


@celery_app.on_after_configure.connect
def _setup(sender, **_):
    init_db()


@celery_app.task(name="analyze_dataset")
def analyze_dataset(job_id: str) -> str:
    db = SessionLocal()
    try:
        execute_job(db, uuid.UUID(job_id))
        return job_id
    finally:
        db.close()
