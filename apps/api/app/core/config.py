from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and a local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Agent Tool Platform"
    app_env: str = "development"
    app_version: str = "0.4.0"
    api_prefix: str = "/api/v1"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    database_url: SecretStr | None = None
    database_connect_timeout_seconds: int = Field(default=5, ge=1, le=30)
    sql_echo: bool = False

    local_principal_external_id: str = "local-admin"
    sql_tool_database_url: SecretStr | None = None
    sql_tool_allowed_schemas: list[str] = Field(default_factory=lambda: ["public"])
    sql_tool_statement_timeout_ms: int = Field(default=5_000, ge=100, le=30_000)
    sql_tool_default_max_rows: int = Field(default=100, ge=1, le=1_000)
    sql_tool_absolute_max_rows: int = Field(default=1_000, ge=1, le=10_000)

    http_tool_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:8000"]
    )
    http_health_check_url: str = "http://127.0.0.1:8000/api/v1/health"
    http_tool_max_response_bytes: int = Field(default=1_000_000, ge=1_024, le=10_000_000)

    mcp_allowed_endpoints: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:8101/mcp"]
    )
    mcp_connect_timeout_seconds: int = Field(default=10, ge=1, le=60)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.rstrip("/") for origin in self.api_cors_origins]

    @property
    def database_url_value(self) -> str | None:
        if self.database_url is None:
            return None
        value = self.database_url.get_secret_value().strip()
        return value or None

    @property
    def sql_tool_database_url_value(self) -> str | None:
        if self.sql_tool_database_url is None:
            return None
        value = self.sql_tool_database_url.get_secret_value().strip()
        return value or None


@lru_cache
def get_settings() -> Settings:
    return Settings()

