"""MoodFeed Application Settings & Environment Configuration.

Provides typed configuration models, environment-specific defaults,
and strict startup validation for development, staging, and production.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

# Automatically locate and load .env from project root
_ROOT_DIR = Path(__file__).resolve().parent.parent
_env_file = _ROOT_DIR / ".env"
if _env_file.exists():
    load_dotenv(dotenv_path=_env_file, override=False)
# Turkish News RSS Feeds List (20+ Sources)
RSS_FEEDS = [
    # TÜRKİYE - GENEL
    "https://www.trthaber.com/rss.php",
    "https://www.ntv.com.tr/rss",
    "https://www.haberturk.com/rss",
    "https://www.sozcu.com.tr/feed/",
    "https://www.milliyet.com.tr/rss/",

    # DÜNYA - TÜRKÇE
    "https://www.bbc.com/turkce/index.xml",
    "https://www.dw.com/tr/rss",
    "https://tr.euronews.com/rss",
    "https://www.voaturkce.com/api/z",

    # EKONOMİ
    "https://www.paraanaliz.com/rss",
    "https://www.doviz.com/rss",
    "https://www.altin.in/rss",

    # SPOR
    "https://www.fanatik.com.tr/rss",
    "https://www.sporx.com/rss",
    "https://www.90min.com.tr/rss",

    # TEKNOLOJİ
    "https://www.webtekno.com/rss/",
    "https://www.shiftdelete.net/feed/",
    "https://www.donanimhaber.com/rss/",

    # MAGAZİN
    "https://www.hurriyet.com.tr/rss/magazin/",
    "https://www.milliyet.com.tr/rss/magazin/",
]


class Settings(BaseModel):
    """Production-grade typed application settings."""

    # Application & Environment
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Active runtime environment",
    )
    app_name: str = "MoodFeed"
    app_version: str = "1.0.0"
    app_base_url: str = "http://localhost:8000"
    api_base_url: str = "http://localhost:8000/v1"
    debug: bool = True

    # Server & Networking
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 2
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    )
    csrf_origin: str = "http://localhost:8000"

    # Database
    database_url: str = "postgresql://moodfeed_user:dev_pass@localhost:5432/moodfeed_db"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_timeout_seconds: int = 30
    database_ssl_mode: str = "prefer"

    # Authentication & Secrets
    auth_provider: Literal["clerk", "local"] = "clerk"
    session_secret: str = "dev_insecure_session_secret_replace_in_production_min32chars"
    jwt_secret: str = "dev_insecure_jwt_secret_replace_in_production_min32chars"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 14
    password_hash_algorithm: str = "argon2id"
    clerk_publishable_key: str | None = None
    clerk_secret_key: str | None = None
    clerk_issuer: str | None = None
    clerk_jwks_url: str | None = None

    # Redis & Rate Limiting
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_redis_url: str = "redis://localhost:6379/1"
    rate_limit_requests_per_minute: int = 60

    # Content Ingestion & RSS Archiving
    content_provider_enabled: bool = False
    content_provider_type: str = "rss"
    content_provider_base_url: str = "https://example.com/feed.xml"
    content_provider_api_key: str | None = None
    content_provider_sync_interval_minutes: int = 30
    content_provider_timeout_seconds: int = 10
    rss_sync_interval_minutes: int = 1
    rss_batch_limit: int = 500

    # ML & Mood Thresholds
    model_provider: Literal["rule_based", "berturk"] = "rule_based"
    model_name: str = "dbmdz/bert-base-turkish-sentiment-cased"
    model_version: str = "1.0.0"
    model_timeout_ms: int = 500
    model_device: str = "cpu"
    model_batch_size: int = 16
    mood_threshold_angry: float = 0.20
    mood_threshold_anxious: float = 0.20
    mood_threshold_sad: float = 0.20
    mood_threshold_happy: float = 0.25
    mood_threshold_calm: float = 0.25

    # Observability & Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "text"] = "json"
    sentry_dsn: str | None = None
    otel_exporter_endpoint: str | None = None
    otel_service_name: str = "moodfeed-service"
    metrics_enabled: bool = True

    # Data Export & Privacy
    export_signing_secret: str = "dev_export_signing_secret_replace_in_production_min32chars"
    export_url_ttl_seconds: int = 900
    data_retention_days: int = 90

    # Feature Flags
    feature_flag_mock_adapter: bool = False
    feature_flag_auth: bool = True
    feature_flag_clerk_auth: bool = True
    feature_flag_persistence: bool = True
    feature_flag_pilot_mode: bool = True
    feature_flag_berturk_inference: bool = False

    # Admin config
    admin_role_config: dict[str, Any] = Field(
        default_factory=lambda: {
            "admin_email": "admin@moodfeed.local",
            "default_role": "admin",
        }
    )

    @field_validator("app_env", mode="before")
    @classmethod
    def validate_app_env(cls, v: Any) -> str:
        val = str(v).lower()
        if val not in ("development", "staging", "production"):
            raise ValueError(f"Invalid APP_ENV: '{v}'. Must be development, staging, or production.")
        return val

    def validate_production_invariants(self) -> None:
        """Enforce strict production checks on server startup."""
        if self.app_env == "production":
            insecure_defaults = [
                "dev_insecure_session_secret_replace_in_production_min32chars",
                "dev_insecure_jwt_secret_replace_in_production_min32chars",
                "dev_export_signing_secret_replace_in_production_min32chars",
            ]
            if self.session_secret in insecure_defaults or len(self.session_secret) < 32:
                raise ValueError("PRODUCTION ERROR: Insecure or default SESSION_SECRET detected. Must be at least 32 high-entropy characters.")
            if self.jwt_secret in insecure_defaults or len(self.jwt_secret) < 32:
                raise ValueError("PRODUCTION ERROR: Insecure or default JWT_SECRET detected. Must be at least 32 high-entropy characters.")
            if self.export_signing_secret in insecure_defaults or len(self.export_signing_secret) < 32:
                raise ValueError("PRODUCTION ERROR: Insecure or default EXPORT_SIGNING_SECRET detected.")
            if self.debug:
                raise ValueError("PRODUCTION ERROR: DEBUG mode cannot be enabled in production environment.")


def load_settings_from_env() -> Settings:
    """Instantiates Settings from environment variables with fallback defaults."""
    env_vars: dict[str, Any] = {}

    def get_env_bool(key: str, default: bool) -> bool:
        v = os.getenv(key)
        if v is None:
            return default
        return v.strip().lower() in ("true", "1", "yes", "on")

    def get_env_int(key: str, default: int) -> int:
        v = os.getenv(key)
        if v is None:
            return default
        try:
            return int(v.strip())
        except ValueError:
            return default

    app_env = os.getenv("APP_ENV", "development").lower()
    env_vars["app_env"] = app_env
    env_vars["app_name"] = os.getenv("APP_NAME", "MoodFeed")
    env_vars["app_version"] = os.getenv("APP_VERSION", "1.0.0")
    env_vars["app_base_url"] = os.getenv("APP_BASE_URL", "http://localhost:8000")
    env_vars["api_base_url"] = os.getenv("API_BASE_URL", "http://localhost:8000/v1")
    env_vars["debug"] = get_env_bool("DEBUG", app_env != "production")

    env_vars["host"] = os.getenv("HOST", "0.0.0.0")
    env_vars["port"] = get_env_int("PORT", 8000)
    env_vars["workers"] = get_env_int("WORKERS", 2)
    env_vars["csrf_origin"] = os.getenv("CSRF_ORIGIN", "http://localhost:8000")

    cors_str = os.getenv("CORS_ORIGINS", "")
    if cors_str:
        origins = [orig.strip() for orig in cors_str.split(",") if orig.strip()]
        if origins:
            env_vars["cors_origins"] = origins
    else:
        env_vars["cors_origins"] = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "https://moodfeed.vercel.app",
            "*",
        ]

    env_vars["database_url"] = os.getenv("DATABASE_URL", "postgresql://moodfeed_user:dev_pass@localhost:5432/moodfeed_db")
    env_vars["database_pool_size"] = get_env_int("DATABASE_POOL_SIZE", 10)
    env_vars["database_max_overflow"] = get_env_int("DATABASE_MAX_OVERFLOW", 20)
    env_vars["database_timeout_seconds"] = get_env_int("DATABASE_TIMEOUT_SECONDS", 30)

    # Auth & Clerk Configuration
    raw_provider = os.getenv("AUTH_PROVIDER", "").strip().lower()
    clerk_pub_key = os.getenv("CLERK_PUBLISHABLE_KEY")
    if raw_provider in ("clerk", "local"):
        auth_provider = raw_provider
    elif clerk_pub_key:
        auth_provider = "clerk"
    else:
        auth_provider = "local"
    env_vars["auth_provider"] = auth_provider

    env_vars["session_secret"] = os.getenv("SESSION_SECRET", "dev_insecure_session_secret_replace_in_production_min32chars")
    env_vars["jwt_secret"] = os.getenv("JWT_SECRET", "dev_insecure_jwt_secret_replace_in_production_min32chars")
    env_vars["jwt_algorithm"] = os.getenv("JWT_ALGORITHM", "HS256")
    env_vars["access_token_ttl_minutes"] = get_env_int("ACCESS_TOKEN_TTL_MINUTES", 30)
    env_vars["refresh_token_ttl_days"] = get_env_int("REFRESH_TOKEN_TTL_DAYS", 14)

    env_vars["clerk_publishable_key"] = clerk_pub_key
    env_vars["clerk_secret_key"] = os.getenv("CLERK_SECRET_KEY")
    env_vars["clerk_issuer"] = os.getenv("CLERK_ISSUER")
    env_vars["clerk_jwks_url"] = os.getenv("CLERK_JWKS_URL")

    # Automatically derive Clerk frontend API domain and JWKS URL if publishable key is present
    if clerk_pub_key and not env_vars["clerk_jwks_url"]:
        try:
            import base64
            parts = clerk_pub_key.split("_", 2)
            if len(parts) == 3:
                raw_b64 = parts[2]
                padding = "=" * (4 - (len(raw_b64) % 4)) if len(raw_b64) % 4 != 0 else ""
                frontend_domain = base64.b64decode(raw_b64 + padding).decode("utf-8").rstrip("$")
                if frontend_domain:
                    if not env_vars["clerk_issuer"]:
                        env_vars["clerk_issuer"] = f"https://{frontend_domain}"
                    env_vars["clerk_jwks_url"] = f"https://{frontend_domain}/.well-known/jwks.json"
        except Exception:
            pass

    env_vars["redis_url"] = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    env_vars["rate_limit_redis_url"] = os.getenv("RATE_LIMIT_REDIS_URL", "redis://localhost:6379/1")
    env_vars["rate_limit_requests_per_minute"] = get_env_int("RATE_LIMIT_REQUESTS_PER_MINUTE", 60)

    env_vars["content_provider_enabled"] = get_env_bool("CONTENT_PROVIDER_ENABLED", False)
    env_vars["content_provider_type"] = os.getenv("CONTENT_PROVIDER_TYPE", "rss")
    env_vars["content_provider_base_url"] = os.getenv("CONTENT_PROVIDER_BASE_URL", "https://example.com/feed.xml")
    env_vars["content_provider_api_key"] = os.getenv("CONTENT_PROVIDER_API_KEY")

    scorer_mode = os.getenv("MOODFEED_SCORER", os.getenv("MODEL_PROVIDER", "rule_based")).lower()
    env_vars["model_provider"] = "berturk" if scorer_mode == "berturk" else "rule_based"
    env_vars["model_name"] = os.getenv("MODEL_NAME", "dbmdz/bert-base-turkish-sentiment-cased")
    env_vars["model_version"] = os.getenv("MODEL_VERSION", "1.0.0")

    env_vars["log_level"] = os.getenv("LOG_LEVEL", "INFO")
    env_vars["log_format"] = os.getenv("LOG_FORMAT", "json")
    env_vars["sentry_dsn"] = os.getenv("SENTRY_DSN")
    env_vars["otel_exporter_endpoint"] = os.getenv("OTEL_EXPORTER_ENDPOINT")

    env_vars["export_signing_secret"] = os.getenv("EXPORT_SIGNING_SECRET", "dev_export_signing_secret_replace_in_production_min32chars")
    env_vars["data_retention_days"] = get_env_int("DATA_RETENTION_DAYS", 90)

    # Feature Flags
    env_vars["feature_flag_mock_adapter"] = get_env_bool("FEATURE_FLAG_MOCK_ADAPTER", False)
    env_vars["feature_flag_auth"] = get_env_bool("FEATURE_FLAG_AUTH", True)
    env_vars["feature_flag_clerk_auth"] = get_env_bool("FEATURE_FLAG_CLERK_AUTH", True)
    env_vars["feature_flag_persistence"] = get_env_bool("FEATURE_FLAG_PERSISTENCE", True)
    env_vars["feature_flag_pilot_mode"] = get_env_bool("FEATURE_FLAG_PILOT_MODE", True)

    settings = Settings(**env_vars)
    settings.validate_production_invariants()
    return settings


# Global singleton settings instance
settings = load_settings_from_env()
