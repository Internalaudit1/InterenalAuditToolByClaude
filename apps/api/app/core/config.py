from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), extra="ignore", case_sensitive=False)

    app_name: str = Field(
        default="HCL Internal Audit API",
        validation_alias=AliasChoices("APP_NAME", "API_APP_NAME", "app_name"),
    )
    api_env: Literal["development", "test", "production"] = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    secret_key: str = Field(
        default="change-me",
        validation_alias=AliasChoices("API_SECRET_KEY", "SECRET_KEY", "secret_key"),
    )
    access_token_expire_minutes: int = Field(
        default=60,
        validation_alias=AliasChoices(
            "API_ACCESS_TOKEN_EXPIRE_MINUTES",
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            "access_token_expire_minutes",
        ),
    )
    refresh_token_expire_days: int = Field(
        default=7,
        validation_alias=AliasChoices(
            "API_REFRESH_TOKEN_EXPIRE_DAYS",
            "REFRESH_TOKEN_EXPIRE_DAYS",
            "refresh_token_expire_days",
        ),
    )
    database_url: str = Field(
        default="sqlite+pysqlite:///./dia_replica.db",
        validation_alias=AliasChoices("API_DATABASE_URL", "DATABASE_URL", "database_url"),
    )
    storage_root: str = Field(
        default="./storage/uploads",
        validation_alias=AliasChoices("API_STORAGE_ROOT", "STORAGE_ROOT", "storage_root"),
    )
    run_seed_on_startup: bool = Field(
        default=False,
        validation_alias=AliasChoices("API_RUN_SEED_ON_STARTUP", "RUN_SEED_ON_STARTUP", "run_seed_on_startup"),
    )
    max_upload_size_mb: int = Field(
        default=10,
        validation_alias=AliasChoices("API_MAX_UPLOAD_SIZE_MB", "MAX_UPLOAD_SIZE_MB", "max_upload_size_mb"),
    )
    access_token_algorithm: str = Field(
        default="HS256",
        validation_alias=AliasChoices(
            "API_ACCESS_TOKEN_ALGORITHM",
            "ACCESS_TOKEN_ALGORITHM",
            "access_token_algorithm",
        ),
    )

    @computed_field
    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_database_backend(self) -> "Settings":
        if self.api_env != "test" and not self.database_url.lower().startswith("postgresql"):
            raise ValueError("API_DATABASE_URL must point to PostgreSQL for non-test environments.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
