from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "Growth Atlas API"
    debug: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api"
    log_level: str = "DEBUG"
    cors_allowed_origins: str = "http://localhost:5173"
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    kimi_api_key: str | None = None
    kimi_model: str = "moonshot-v1-8k"
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    ai_timeout_seconds: float = Field(default=60, gt=0, le=180)
    ai_output_attempts: int = Field(default=2, ge=1, le=3)

    model_config = SettingsConfigDict(
        # Resolve from the backend package instead of the shell's current directory.
        # This keeps configuration consistent when an IDE or task runner uses
        # a working directory other than `backend`.
        env_file=BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)

    @property
    def supabase_auth_configured(self) -> bool:
        """Return whether the Auth endpoint has a plausible API key."""
        if not self.supabase_configured:
            return False
        key = (self.supabase_anon_key or "").strip()
        return not key.lower().startswith(("http://", "https://"))

    @property
    def production_issues(self) -> list[str]:
        if self.app_env.lower() != "production":
            return []
        issues: list[str] = []
        if self.debug:
            issues.append("DEBUG must be false in production")
        if not self.supabase_configured:
            issues.append("Supabase configuration is incomplete")
        if not self.kimi_api_key:
            issues.append("KIMI_API_KEY is missing")
        if not self._is_https(self.supabase_url):
            issues.append("SUPABASE_URL must use HTTPS")
        if not self._is_https(self.kimi_base_url):
            issues.append("KIMI_BASE_URL must use HTTPS")
        if not self.cors_origins or "*" in self.cors_origins:
            issues.append("CORS_ALLOWED_ORIGINS must explicitly list the production frontend")
        if any("localhost" in origin or "127.0.0.1" in origin for origin in self.cors_origins):
            issues.append("CORS_ALLOWED_ORIGINS contains a local development origin")
        return issues

    @staticmethod
    def _is_https(value: str | None) -> bool:
        return bool(value and urlparse(value).scheme == "https")


@lru_cache
def get_settings() -> Settings:
    return Settings()
