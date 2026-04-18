import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # pending, processing, done, error
    total_images: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    faces_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    identities_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Image(Base):
    __tablename__ = "images"
    __table_args__ = (UniqueConstraint("gcs_uri", name="uq_images_gcs_uri"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gcs_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    faces: Mapped[list["ImageFace"]] = relationship("ImageFace", back_populates="image")


class Identity(Base):
    __tablename__ = "identities"

    grab_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    centroid: Mapped[list] = mapped_column(Vector(128), nullable=False)
    face_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    image_faces: Mapped[list["ImageFace"]] = relationship("ImageFace", back_populates="identity")


class ImageFace(Base):
    __tablename__ = "image_faces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False
    )
    grab_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identities.grab_id", ondelete="CASCADE"), nullable=False
    )
    embedding: Mapped[list] = mapped_column(Vector(128), nullable=False)
    top: Mapped[int] = mapped_column(Integer, nullable=False)
    right: Mapped[int] = mapped_column(Integer, nullable=False)
    bottom: Mapped[int] = mapped_column(Integer, nullable=False)
    left: Mapped[int] = mapped_column(Integer, nullable=False)

    image: Mapped["Image"] = relationship("Image", back_populates="faces")
    identity: Mapped["Identity"] = relationship("Identity", back_populates="image_faces")
