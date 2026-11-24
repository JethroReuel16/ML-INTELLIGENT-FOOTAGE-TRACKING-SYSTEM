"""
Central configuration for the ML Footage Tracking System backend.

Every deployment-specific value comes from environment variables (optionally
loaded from backend/.env). See .env.example for the full list.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(APP_DIR)
PROJECT_DIR = os.path.dirname(BACKEND_DIR)

# Real environment variables always win over the .env file.
load_dotenv(os.path.join(BACKEND_DIR, ".env"), override=False)


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _env_bool(name: str, default: bool) -> bool:
    value = _env(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _env_optional_bool(name: str) -> Optional[bool]:
    return None if _env(name) is None else _env_bool(name, False)


def _storage_dir() -> str:
    """STORAGE_DIR; relative paths are resolved against the backend folder
    (not the process working directory)."""
    value = _env("STORAGE_DIR") or _env("VISIONTRACE_STORAGE_DIR")
    if not value:
        return BACKEND_DIR
    if not os.path.isabs(value):
        value = os.path.join(BACKEND_DIR, value)
    return os.path.abspath(value)


def _env_list(name: str, default: str = "") -> List[str]:
    raw = _env(name, default) or ""
    return [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]


def _database_url():
    """DATABASE_URL wins; otherwise build one from the DB_* variables."""
    explicit = _env("DATABASE_URL")

    if explicit:
        url = make_url(explicit)
        # Normalise plain postgres URLs to the installed psycopg (v3) driver.
        if url.drivername in {"postgres", "postgresql"}:
            url = url.set(drivername="postgresql+psycopg")
        return url

    return URL.create(
        drivername="postgresql+psycopg",
        username=_env("DB_USER"),
        password=_env("DB_PASSWORD"),
        host=_env("DB_HOST", "localhost"),
        port=_env_int("DB_PORT", 5432),
        database=_env("DB_NAME"),
    )


@dataclass(frozen=True)
class Settings:
    app_name: str = "ML Footage Tracking System"
    version: str = "1.0.0"

    # "development" or "production". Production tightens defaults.
    environment: str = field(default_factory=lambda: (_env("APP_ENV", "development") or "").lower())
    log_level: str = field(default_factory=lambda: (_env("LOG_LEVEL", "INFO") or "INFO").upper())

    database_url: URL = field(default_factory=_database_url)

    # Browser origins allowed to call the API with cookies.
    cors_origins: List[str] = field(
        default_factory=lambda: _env_list(
            "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        )
    )

    # Session cookie. The name is kept for compatibility with existing sessions.
    cookie_name: str = field(default_factory=lambda: _env("SESSION_COOKIE_NAME", "visiontrace_session"))
    cookie_secure: Optional[bool] = field(
        default_factory=lambda: None if _env("COOKIE_SECURE") is None else _env_bool("COOKIE_SECURE", False)
    )
    cookie_samesite: str = field(default_factory=lambda: (_env("COOKIE_SAMESITE", "lax") or "lax").lower())
    cookie_domain: Optional[str] = field(default_factory=lambda: _env("COOKIE_DOMAIN"))
    session_days: int = field(default_factory=lambda: _env_int("SESSION_DAYS", 7))

    # Brute-force protection for /api/auth/login (per client IP + email).
    login_max_attempts: int = field(default_factory=lambda: _env_int("LOGIN_MAX_ATTEMPTS", 10))
    login_window_seconds: int = field(default_factory=lambda: _env_int("LOGIN_WINDOW_SECONDS", 900))

    # Persistent storage for uploads, results and debug crops.
    storage_dir: str = field(default_factory=_storage_dir)

    # Self-service sign-up. Defaults to off in production: create accounts
    # with `python manage.py create-user` instead.
    registration_enabled: Optional[bool] = field(default_factory=lambda: _env_optional_bool("ALLOW_REGISTRATION"))

    # Load the ML models in the background at start-up (default: production).
    ml_preload: Optional[bool] = field(default_factory=lambda: _env_optional_bool("ML_PRELOAD"))

    # Sources pointing at this server itself (127.0.0.1). Off in production.
    loopback_sources: Optional[bool] = field(default_factory=lambda: _env_optional_bool("ALLOW_LOOPBACK_SOURCES"))

    # Upload limits.
    max_video_upload_mb: int = field(default_factory=lambda: _env_int("MAX_VIDEO_UPLOAD_MB", 2048))
    max_image_upload_mb: int = field(default_factory=lambda: _env_int("MAX_IMAGE_UPLOAD_MB", 20))

    # Optional allow-list of directories that "local" / "network" sources may
    # point into. Empty = any readable video file (fine for a single-tenant
    # install; set it on shared servers).
    allowed_source_roots: List[str] = field(
        default_factory=lambda: [
            os.path.abspath(p) for p in _env_list("ALLOWED_SOURCE_ROOTS") if p
        ]
    )

    # Location of the ML engine package.
    ml_engine_dir: str = field(
        default_factory=lambda: os.path.abspath(
            _env("ML_ENGINE_DIR", os.path.join(PROJECT_DIR, "ml-engene"))
        )
    )

    # Interactive API docs (/docs). Off by default in production.
    enable_docs: Optional[bool] = field(
        default_factory=lambda: None if _env("ENABLE_DOCS") is None else _env_bool("ENABLE_DOCS", True)
    )

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def secure_cookies(self) -> bool:
        # Secure cookies by default in production (requires HTTPS).
        return self.cookie_secure if self.cookie_secure is not None else self.is_production

    @property
    def allow_registration(self) -> bool:
        return self.registration_enabled if self.registration_enabled is not None else not self.is_production

    @property
    def preload_models(self) -> bool:
        return self.ml_preload if self.ml_preload is not None else self.is_production

    @property
    def allow_loopback_sources(self) -> bool:
        return self.loopback_sources if self.loopback_sources is not None else not self.is_production

    @property
    def docs_enabled(self) -> bool:
        return self.enable_docs if self.enable_docs is not None else not self.is_production


settings = Settings()

if settings.cookie_samesite not in {"lax", "strict", "none"}:
    raise RuntimeError("COOKIE_SAMESITE must be lax, strict or none.")

if "*" in settings.cors_origins:
    raise RuntimeError(
        "CORS_ORIGINS cannot be '*': browsers refuse credentialed requests to a "
        "wildcard origin. List the exact frontend origin(s)."
    )

if settings.cookie_samesite == "none" and not settings.secure_cookies:
    raise RuntimeError("COOKIE_SAMESITE=none requires COOKIE_SECURE=true (HTTPS).")
