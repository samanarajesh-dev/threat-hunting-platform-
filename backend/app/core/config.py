"""Central configuration. Every value can be overridden with an environment variable
(or a .env file) -- never hard-code secrets."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Threat Hunting Platform"
    environment: str = "dev"  # dev | prod

    # Postgres (cases, users, alerts ...). SQLite default keeps unit tests simple.
    database_url: str = "sqlite:///./thp.db"

    # Elasticsearch (raw events)
    es_url: str = "http://localhost:9200"
    es_username: str | None = None
    es_password: str | None = None
    es_verify_certs: bool = True
    events_index: str = "thp-events-*"

    # Auth
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    admin_username: str = "admin"
    admin_password: str | None = None  # if set and no users exist, an admin is created at startup

    # Threat-intel providers (all optional; the platform degrades gracefully)
    vt_api_key: str | None = None
    abuseipdb_api_key: str | None = None
    otx_api_key: str | None = None
    ioc_cache_ttl_hours: int = 24

    # Detection + correlation
    rules_dir: str = "app/detections/rules"
    detection_enabled: bool = True
    detection_interval_seconds: int = 60
    correlation_window_minutes: int = 60

    # Evidence storage
    evidence_dir: str = "./evidence"
    max_evidence_bytes: int = 10 * 1024 * 1024

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    def validate_for_runtime(self) -> None:
        if self.environment != "dev" and self.jwt_secret == "change-me":
            raise RuntimeError("JWT_SECRET must be set to a long random value outside dev")


@lru_cache
def get_settings() -> Settings:
    return Settings()
