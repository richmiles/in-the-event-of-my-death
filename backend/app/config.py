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

    # Proof of Work
    pow_base_difficulty: int = 18  # ~1-2 sec on modern CPU
    pow_challenge_ttl_seconds: int = 300  # 5 minutes

    # Rate Limiting
    rate_limit_challenges: str = "10/minute"
    rate_limit_creates: str = "5/minute"
    rate_limit_retrieves: str = "30/minute"

    # CORS
    cors_origins: list[str] | str = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()
