"""GCS crawl job: POST /crawl, GET /crawl/status/{job_id}."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db, get_session_factory
from app.faces import assign_grab_id, embedding_to_list, encode_image
from app.models import CrawlJob, Image, ImageFace
from app.storage import download_bytes, list_image_blobs

logger = logging.getLogger(__name__)

router = APIRouter(tags=["crawl"])


class CrawlAccepted(BaseModel):
    job_id: str
    status: str


class CrawlStatusOut(BaseModel):
    job_id: str
    status: str
    total_images: int | None
    processed: int
    faces_found: int
    identities_created: int
    started_at: str | None
    finished_at: str | None
    error: str | None


def run_crawl_job(job_id: uuid.UUID) -> None:
    settings = get_settings()
    factory = get_session_factory()
    db = factory()
    bucket = settings.gcs_bucket
    if not bucket:
        job = db.get(CrawlJob, job_id)
        if job:
            job.status = "error"
            job.error = "GCS_BUCKET is not configured"
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        logger.error("Crawl job %s: no GCS bucket", job_id)
        db.close()
        return

    try:
        job = db.get(CrawlJob, job_id)
        if not job:
            db.close()
            return
        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        uris = list(list_image_blobs(bucket))
        job.total_images = len(uris)
        db.commit()

        identities_created = 0
        faces_found = 0
        processed = 0

        for gcs_uri, blob_name in uris:
            try:
                existing = db.scalar(select(Image.id).where(Image.gcs_uri == gcs_uri))
                if existing is not None:
                    processed += 1
                    if processed % 50 == 0:
                        job = db.get(CrawlJob, job_id)
                        if job:
                            job.processed = processed
                            job.faces_found = faces_found
                            job.identities_created = identities_created
                            db.commit()
                    continue

                raw = download_bytes(bucket, blob_name)
                faces = encode_image(raw)
                img = Image(gcs_uri=gcs_uri)
                db.add(img)
                db.flush()

                for enc, (top, right, bottom, left) in faces:
                    gid, is_new = assign_grab_id(db, enc)
                    if is_new:
                        identities_created += 1
                    faces_found += 1
                    db.add(
                        ImageFace(
                            image_id=img.id,
                            grab_id=gid,
                            embedding=embedding_to_list(enc),
                            top=top,
                            right=right,
                            bottom=bottom,
                            left=left,
                        )
                    )

                processed += 1
                if processed % 50 == 0:
                    job = db.get(CrawlJob, job_id)
                    if job:
                        job.processed = processed
                        job.faces_found = faces_found
                        job.identities_created = identities_created
                        db.commit()

            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed processing %s: %s", gcs_uri, exc)
                db.rollback()
                continue

        job = db.get(CrawlJob, job_id)
        if job:
            job.status = "done"
            job.processed = processed
            job.faces_found = faces_found
            job.identities_created = identities_created
            job.finished_at = datetime.now(timezone.utc)
            job.error = None
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Crawl job %s failed", job_id)
        try:
            job = db.get(CrawlJob, job_id)
            if job:
                job.status = "error"
                job.error = str(exc)
                job.finished_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Could not persist crawl error for %s", job_id)
    finally:
        db.close()


@router.post("/crawl", status_code=status.HTTP_202_ACCEPTED, response_model=CrawlAccepted)
def start_crawl(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> CrawlAccepted:
    job = CrawlJob(status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(run_crawl_job, job.id)
    return CrawlAccepted(job_id=str(job.id), status="pending")


@router.get("/crawl/status/{job_id}", response_model=CrawlStatusOut)
def crawl_status(job_id: uuid.UUID, db: Session = Depends(get_db)) -> CrawlStatusOut:
    job = db.get(CrawlJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return CrawlStatusOut(
        job_id=str(job.id),
        status=job.status,
        total_images=job.total_images,
        processed=job.processed,
        faces_found=job.faces_found,
        identities_created=job.identities_created,
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
        error=job.error,
    )
