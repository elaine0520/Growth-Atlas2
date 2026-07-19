from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
