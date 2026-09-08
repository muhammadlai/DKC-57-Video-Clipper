"""Application settings (pydantic-settings).

Every value can be provided via environment variables prefixed with
``AITZAZ_`` or via a ``.env`` file (searched upward from the working
directory so the repo-root ``.env`` works no matter where the API starts).
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_dotenv() -> tuple[str, ...]:
    """Search upward for a .env file so dev commands work from any cwd."""
    candidates: list[str] = []
    current = Path.cwd().resolve()
    for directory in [current, *current.parents]:
        candidate = directory / ".env"
        if candidate.is_file():
            candidates.append(str(candidate))
            break
    return tuple(candidates)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AITZAZ_",
        env_file=_find_dotenv(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- core -------------------------------------------------------------
    project_name: str = "Aitzaz AI"
    project_description: str = "Personal AI agent — foundation phase"
    version: str = "0.1.0"
    environment: str = "development"  # "development" | "production"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    # --- database -----------------------------------------------------------
    database_url: str = "postgresql+psycopg2://aitzaz:aitzaz@localhost:5432/aitzaz"
    auto_create_tables: bool = False  # dev/test convenience; use Alembic in prod

    # --- redis (optional) -----------------------------------------------------
    redis_url: str | None = None

    # --- security / auth ---------------------------------------------------------
    secret_key: str = "insecure-dev-secret-change-me"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    jwt_algorithm: str = "HS256"
    cookie_name: str = "aitzaz_session"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    bcrypt_rounds: int = 12

    # --- CORS ---------------------------------------------------------------
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # --- rate limiting ---------------------------------------------------------
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 240

    # --- LLM ----------------------------------------------------------------------
    llm_provider: str = "mock"  # mock | openai | anthropic
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-haiku-latest"
    mock_llm_delay_ms: int = 250

    # --- agent runtime ----------------------------------------------------------------
    default_timezone: str = "UTC"

    # --- seed data (development only) ----------------------------------------------------
    demo_user_email: str = "demo@aitzaz.ai"
    demo_user_name: str = "Demo User"
    demo_user_password: str = "demo-user-2026"
    seed_demo_user: bool = True

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    def validate_secrets(self) -> None:
        """Refuse to boot production with an insecure configuration."""
        if self.is_production:
            if not self.secret_key or len(self.secret_key) < 32 or self.secret_key.startswith("insecure"):
                raise RuntimeError(
                    "AITZAZ_SECRET_KEY must be a strong random value in production "
                    "(generate: python -c \"import secrets; print(secrets.token_urlsafe(48))\")"
                )
            if self.demo_user_password == "demo-user-2026" and self.seed_demo_user:
                raise RuntimeError(
                    "Refusing to seed the documented demo account in production. "
                    "Set AITZAZ_SEED_DEMO_USER=false."
                )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> Settings:
    """Reload settings (used by tests)."""
    global _settings
    _settings = Settings()
    return _settings
