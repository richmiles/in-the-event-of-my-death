from pydantic import ConfigDict
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

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
