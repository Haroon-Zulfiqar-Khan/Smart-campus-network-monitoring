from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator, SecretStr


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: str = "development"
    database_url: str = "sqlite:///./campus.db"
    secret_key: str = "development-only-change-this-secret-key-before-deploying"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]
    measurement_base_url: str = "http://localhost:8001/measure"
    campus_timezone: str = "Asia/Karachi"
    access_minutes: int = 30
    refresh_days: int = 7
    test_session_minutes: int = 10
    max_download_bytes: int = Field(8 * 1024 * 1024, ge=1024, le=64 * 1024 * 1024)
    max_upload_bytes: int = Field(8 * 1024 * 1024, ge=1024, le=64 * 1024 * 1024)
    max_session_bytes: int = 64 * 1024 * 1024
    max_concurrent_transfers: int = 8
    worker_interval_seconds: int = 30
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.8-flash"
    gemini_timeout_seconds: int = Field(15, ge=3, le=25)

    @model_validator(mode="after")
    def production(self):
        if self.environment == "production":
            if len(self.secret_key) < 32 or self.secret_key.startswith("development-"):
                raise ValueError(
                    "Production requires a random SECRET_KEY of at least 32 characters"
                )
            if not self.database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Production requires PostgreSQL (postgresql+psycopg://)")
            if not self.measurement_base_url.startswith("https://"):
                raise ValueError("Production measurement endpoint requires HTTPS")
        return self


settings = Settings()
