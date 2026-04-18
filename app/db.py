import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Base

logger = logging.getLogger(__name__)

_engine = None
SessionLocal: sessionmaker[Session] | None = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return SessionLocal


def init_db() -> None:
    """Enable pgvector extension and create tables + IVFFLAT index."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS identities_centroid_ivfflat
                    ON identities USING ivfflat (centroid vector_l2_ops)
                    WITH (lists = 100)
                    """
                )
            )
    except Exception as exc:  # noqa: BLE001
        # IVFFLAT may fail on very old pgvector; sequential scan still works
        logger.warning("Could not create IVFFLAT index (continuing): %s", exc)
    logger.info("Database initialized")


def get_db():
    """FastAPI dependency."""
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()
