from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/grabpic"
    gcs_bucket: str = ""
    gcs_upload_prefix: str = "judge-uploads"
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MiB
    face_dist_threshold: float = 0.6
    signed_url_ttl_seconds: int = 900  # 15 minutes


@lru_cache
def get_settings() -> Settings:
    return Settings()
