"""Optional judge-friendly upload to GCS: POST /upload."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import get_settings
from app.storage import allowed_image_suffix, upload_bytes_to_gcs

router = APIRouter(tags=["upload"])


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
) -> dict:
    """
    Upload one image to gs://GCS_BUCKET/{GCS_UPLOAD_PREFIX}/{uuid}.{ext}.
    Requires the runtime service account to have storage.objects.create on the bucket.

    **Important Note:** For best results and compatibility with dlib, please upload images
    in JPEG/RGB format.
    """
    settings = get_settings()
    if not settings.gcs_bucket:
        raise HTTPException(status_code=503, detail="GCS_BUCKET is not configured")

    filename = file.filename or "image.jpg"
    if not allowed_image_suffix(filename):
        raise HTTPException(
            status_code=400,
            detail="Allowed extensions: .jpg, .jpeg, .png, .webp",
        )

    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large (max {settings.max_upload_bytes} bytes)",
        )
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"

    blob_name = f"{settings.gcs_upload_prefix.strip().strip('/')}/{uuid.uuid4()}{ext}"
    content_type = file.content_type or "image/jpeg"
    gcs_uri = upload_bytes_to_gcs(
        settings.gcs_bucket,
        blob_name,
        data,
        content_type=content_type,
    )
    return {
        "gcs_uri": gcs_uri,
        "blob_name": blob_name,
        "bytes": len(data),
    }
