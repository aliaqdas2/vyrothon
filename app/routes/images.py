"""Fetch images for a grab_id: GET /users/{grab_id}/images."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Identity, Image, ImageFace
from app.storage import signed_url_for_gcs_uri

logger = logging.getLogger(__name__)

router = APIRouter(tags=["images"])


class UserImagesResponse(BaseModel):
    grab_id: str
    count: int
    images: list[str]


@router.get("/users/{grab_id}/images", response_model=UserImagesResponse)
def get_user_images(grab_id: uuid.UUID, db: Session = Depends(get_db)) -> UserImagesResponse:
    ident = db.get(Identity, grab_id)
    if not ident:
        raise HTTPException(status_code=404, detail="Unknown grab_id")

    stmt = (
        select(Image.gcs_uri)
        .join(ImageFace, ImageFace.image_id == Image.id)
        .where(ImageFace.grab_id == grab_id)
        .distinct()
    )
    uris = list(db.scalars(stmt).all())

    urls: list[str] = []
    for uri in uris:
        try:
            urls.append(signed_url_for_gcs_uri(uri))
        except Exception:
            logger.warning("Could not sign URL for %s; returning gs:// URI", uri)
            urls.append(uri)

    return UserImagesResponse(
        grab_id=str(grab_id),
        count=len(urls),
        images=urls,
    )
