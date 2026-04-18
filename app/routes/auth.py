"""Selfie-as-a-key: POST /auth/selfie."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.faces import encode_image, find_nearest_identity
from app.models import Identity

router = APIRouter(tags=["auth"])


class SelfieAuthResponse(BaseModel):
    grab_id: str
    distance: float
    match: bool


@router.post("/auth/selfie", response_model=SelfieAuthResponse)
async def auth_selfie(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> SelfieAuthResponse:
    settings = get_settings()
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    faces = encode_image(data)
    if len(faces) == 0:
        raise HTTPException(status_code=400, detail="No face detected in image")
    if len(faces) > 1:
        raise HTTPException(
            status_code=400,
            detail="Multiple faces detected; upload a single-face selfie",
        )

    enc, _bbox = faces[0]
    nearest = find_nearest_identity(db, enc)
    if nearest is None:
        raise HTTPException(
            status_code=404,
            detail="No indexed identities yet; run POST /crawl first",
        )

    grab_id, dist = nearest
    match = dist < settings.face_dist_threshold
    if not match:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Face does not match any known identity within threshold",
                "grab_id": str(grab_id),
                "distance": dist,
                "match": False,
            },
        )

    return SelfieAuthResponse(
        grab_id=str(grab_id),
        distance=dist,
        match=True,
    )
