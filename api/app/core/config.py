from __future__ import annotations

from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str
    jwt_secret: str
    jwt_refresh_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    access_cookie_name: str = "sentinelkit_access"
    refresh_cookie_name: str = "sentinelkit_refresh"
    cookie_secure: bool = False
    cookie_samesite: str = "strict"
    cookie_domain: str | None = None
    cookie_path: str = "/auth"

    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    frontend_origin: str = "http://localhost:5173"
    allowed_scan_targets: list[str] = ["localhost", "127.0.0.1", "::1"]

    max_upload_bytes: int = 2_097_152
    siem_enumeration_404_threshold: int = 10
    siem_brute_force_threshold: int = 10
    siem_detection_window_seconds: int = 60
    scan_tasks_per_user_per_hour: int = 10
    scan_default_timeout_seconds: float = 2
    scan_max_ports: int = 100
    scan_concurrency: int = 20
    scan_banner_max_bytes: int = 1024
    web_audit_timeout_seconds: float = 10
    web_audit_max_redirects: int = 5
    web_audit_max_response_bytes: int = 65_536

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    desktop_runtime_nonce: str | None = None

    @field_validator("allowed_scan_targets", mode="before")
    @classmethod
    def parse_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("cookie_domain", mode="before")
    @classmethod
    def empty_domain_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("database_url", "jwt_secret", "jwt_refresh_secret")
    @classmethod
    def required_value(cls, value: str, info) -> str:
        if not value.strip():
            names = {
                "database_url": "DATABASE_URL",
                "jwt_secret": "JWT_SECRET",
                "jwt_refresh_secret": "JWT_REFRESH_SECRET",
            }
            raise ValueError(f"{names[info.field_name]} é obrigatório")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
