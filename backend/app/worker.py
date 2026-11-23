import os
from datetime import datetime, timezone
from celery import Celery
from sqlalchemy import select, delete as sql_delete
from .db import DB, Document, Job, Fact, Consent, Evaluation
from . import storage
from .documents import process_bytes

celery = Celery("formflow", broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
celery.conf.update(
    task_ignore_result=True,
    task_soft_time_limit=150,
    task_time_limit=180,
    beat_schedule={
        "retention": {"task": "formflow.cleanup", "schedule": 3600},
        "source-monitor": {"task": "formflow.monitor", "schedule": 86400},
    },
)


@celery.task(name="formflow.process")
def process(document_id):
    with DB() as db:
        doc = db.get(Document, document_id)
        if not doc:
            return
        job = db.scalar(select(Job).where(Job.document_id == doc.id))
        consent = db.scalar(
            select(Consent).where(Consent.profile_id == doc.profile_id).order_by(Consent.created_at.desc())
        )
        if not consent or not consent.accepted:
            doc.status, job.state = "cancelled", "cancelled"
            db.commit()
            return
        doc.status, job.state = "processing", "processing"
        db.commit()
        try:
            facts, quality = process_bytes(storage.get(doc.id), doc.content_type)
            # Recheck consent and existence after OCR, before storing extracted facts.
            db.expire_all()
            doc = db.get(Document, document_id)
            if not doc:
                return
            consent = db.scalar(
                select(Consent).where(Consent.profile_id == doc.profile_id).order_by(Consent.created_at.desc())
            )
            if not consent or not consent.accepted:
                doc.status, job.state = "cancelled", "cancelled"
                db.commit()
                return
            db.execute(sql_delete(Fact).where(Fact.document_id == doc.id))
            for fact in facts:
                db.add(Fact(profile_id=doc.profile_id, document_id=doc.id, **fact))
            doc.quality = quality
            doc.status, job.state = "ready", "complete"
            if not facts:
                doc.error = "NO_FIELDS_FOUND: retake the image or use a clearer document. / ಸ್ಪಷ್ಟ ದಾಖಲೆ ಬಳಸಿ."
            db.commit()
        except Exception as exc:
            db.rollback()
            doc = db.get(Document, document_id)
            job = db.scalar(select(Job).where(Job.document_id == document_id))
            if doc and job:
                # Error class only; exception text may include document content.
                doc.status, job.state = "failed", "failed"
                doc.error = job.error = f"PROCESSING_FAILED ({type(exc).__name__}); verify OCR models and file quality."
                db.commit()


@celery.task(name="formflow.cleanup")
def cleanup():
    with DB() as db:
        expired = list(db.scalars(select(Document).where(Document.expires_at < datetime.now(timezone.utc))))
        profiles = {d.profile_id for d in expired}
        for d in expired:
            storage.delete(d.id)
            db.delete(d)
        # Historical results contain evidence values, so remove snapshots when source evidence expires.
        for profile_id in profiles:
            db.execute(sql_delete(Evaluation).where(Evaluation.profile_id == profile_id))
        db.commit()
        return len(expired)


@celery.task(name="formflow.monitor")
def monitor():
    from .monitor import monitor_all

    return monitor_all()
