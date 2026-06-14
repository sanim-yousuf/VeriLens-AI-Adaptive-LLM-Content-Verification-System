from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    triage_model: str = Field(default="gpt-5-nano", alias="OPENAI_TRIAGE_MODEL")
    standard_model: str = Field(default="gpt-5-mini", alias="OPENAI_STANDARD_MODEL")
    advanced_model: str = Field(default="gpt-5", alias="OPENAI_ADVANCED_MODEL")
    premium_model: str = Field(default="gpt-5.2", alias="OPENAI_PREMIUM_MODEL")
    moderation_model: str = Field(default="omni-moderation-latest", alias="OPENAI_MODERATION_MODEL")

    max_input_chars: int = Field(default=40000, alias="MAX_INPUT_CHARS")
    max_output_tokens: int = Field(default=1800, alias="OPENAI_MAX_OUTPUT_TOKENS")
    cache_ttl_seconds: int = Field(default=86400, alias="CACHE_TTL_SECONDS")
    rate_limit_per_minute: int = Field(default=30, alias="RATE_LIMIT_PER_MINUTE")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
