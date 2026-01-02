from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Database
    database_url: str = "sqlite:///./secrets.db"

    # Limits
    max_ciphertext_size: int = 1_000_000  # 1MB
    max_unlock_days: int = 730  # 2 years
    min_unlock_minutes: int = 5
    max_expiry_days: int = 1825  # 5 years
    min_expiry_gap_minutes: int = 15  # minimum gap between unlock_at and expires_at

    # Proof of Work
    pow_base_difficulty: int = 18  # ~1-2 sec on modern CPU
    pow_challenge_ttl_seconds: int = 300  # 5 minutes

    # Rate Limiting
    rate_limit_challenges: str = "10/minute"
    rate_limit_creates: str = "5/minute"
    rate_limit_retrieves: str = "30/minute"

    # Cleanup Scheduler
    cleanup_interval_hours: int = 1

    # CORS
    # Can be set as comma-separated string via environment variable
    # e.g., CORS_ORIGINS="https://ieomd.com,https://www.ieomd.com"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]

    # Logging
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    log_format: str = "console"  # "console" or "json"

    # Discord Webhooks
    discord_feedback_webhook_url: str | None = None

    # Rate Limiting - Feedback
    rate_limit_feedback: str = "5/minute"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> list[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()
