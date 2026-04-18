"""Face encoding and identity assignment using face_recognition + pgvector L2."""

from __future__ import annotations

import io
import logging
import uuid
from typing import TYPE_CHECKING

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Identity

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def encode_image(
    image_bytes: bytes,
) -> list[tuple[np.ndarray, tuple[int, int, int, int]]]:
    """
    Detect faces and return list of (128-d encoding, (top, right, bottom, left)).
    """
    import face_recognition  # noqa: PLC0415 — heavy; load only when encoding

    image = face_recognition.load_image_file(io.BytesIO(image_bytes))
    locations = face_recognition.face_locations(image)
    if not locations:
        return []
    encodings = face_recognition.face_encodings(image, locations)
    out: list[tuple[np.ndarray, tuple[int, int, int, int]]] = []
    for enc, loc in zip(encodings, locations):
        top, right, bottom, left = loc
        out.append((np.asarray(enc, dtype=np.float64), (top, right, bottom, left)))
    return out


def _as_vec_list(encoding: np.ndarray) -> list[float]:
    return np.asarray(encoding, dtype=np.float64).reshape(-1).tolist()


def embedding_to_list(encoding: np.ndarray) -> list[float]:
    """Public helper for persisting a 128-d embedding as a list for pgvector."""
    return _as_vec_list(encoding)


def assign_grab_id(session: Session, encoding: np.ndarray) -> tuple[uuid.UUID, bool]:
    """
    Nearest-neighbor in L2 space; merge if within threshold else new identity.
    Returns (grab_id, created_new_identity).
    """
    settings = get_settings()
    threshold = settings.face_dist_threshold
    vec = _as_vec_list(encoding)
    dist_expr = Identity.centroid.l2_distance(vec)
    stmt = (
        select(Identity.grab_id, dist_expr.label("dist"))
        .order_by(dist_expr.asc())
        .limit(1)
    )
    row = session.execute(stmt).first()

    if row is None:
        gid = uuid.uuid4()
        session.add(Identity(grab_id=gid, centroid=vec, face_count=1))
        return gid, True

    grab_id, dist = row[0], float(row[1])
    if dist < threshold:
        ident = session.get(Identity, grab_id)
        if ident is None:
            gid = uuid.uuid4()
            session.add(Identity(grab_id=gid, centroid=vec, face_count=1))
            return gid, True
        n = ident.face_count
        cent = np.asarray(ident.centroid, dtype=np.float64)
        enc_arr = np.asarray(encoding, dtype=np.float64).reshape(-1)
        new_cent = (cent * n + enc_arr) / (n + 1)
        ident.centroid = new_cent.tolist()
        ident.face_count = n + 1
        return grab_id, False

    gid = uuid.uuid4()
    session.add(Identity(grab_id=gid, centroid=vec, face_count=1))
    return gid, True


def find_nearest_identity(session: Session, encoding: np.ndarray) -> tuple[uuid.UUID, float] | None:
    """Return nearest grab_id and L2 distance, or None if no identities indexed."""
    vec = _as_vec_list(encoding)
    dist_expr = Identity.centroid.l2_distance(vec)
    stmt = (
        select(Identity.grab_id, dist_expr.label("dist"))
        .order_by(dist_expr.asc())
        .limit(1)
    )
    row = session.execute(stmt).first()
    if row is None:
        return None
    return row[0], float(row[1])
