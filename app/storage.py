"""GCS helpers: list image blobs, download bytes, signed URLs."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Iterator

from google.cloud import storage

from app.config import get_settings

logger = logging.getLogger(__name__)

_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG", ".WEBP")


def _client() -> storage.Client:
    return storage.Client()


def list_image_blobs(bucket_name: str) -> Iterator[tuple[str, str]]:
    """
    Yield (gcs_uri, blob_name) for each image-like object in the bucket.
    gcs_uri format: gs://bucket/name
    """
    if not bucket_name:
        raise ValueError("GCS_BUCKET is not configured")
    client = _client()
    bucket = client.bucket(bucket_name)
    for blob in client.list_blobs(bucket):
        if blob.name.endswith("/") or not blob.name:
            continue
        lower = blob.name.lower()
        if not any(lower.endswith(s.lower()) for s in _IMAGE_SUFFIXES):
            continue
        uri = f"gs://{bucket_name}/{blob.name}"
        yield uri, blob.name


def download_bytes(bucket_name: str, blob_name: str) -> bytes:
    client = _client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    return blob.download_as_bytes()


def gcs_uri_to_blob_name(gcs_uri: str) -> tuple[str, str]:
    """Parse gs://bucket/path -> (bucket, blob_name)."""
    if not gcs_uri.startswith("gs://"):
        raise ValueError("Invalid gcs_uri")
    rest = gcs_uri[5:]
    slash = rest.find("/")
    if slash < 0:
        raise ValueError("Invalid gcs_uri")
    return rest[:slash], rest[slash + 1 :]


def signed_url_for_gcs_uri(gcs_uri: str, expiration_seconds: int | None = None) -> str:
    """
    V4 signed GET URL. Uses default credentials (Cloud Run SA or local ADC).
    """
    settings = get_settings()
    ttl = expiration_seconds if expiration_seconds is not None else settings.signed_url_ttl_seconds
    bucket_name, blob_name = gcs_uri_to_blob_name(gcs_uri)
    client = _client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(seconds=ttl),
        method="GET",
    )
