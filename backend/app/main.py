from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import inspect

from app.config import settings
from app.database import engine
from app.logging_config import get_logger, setup_logging
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import limiter
from app.routers import challenges, secrets
from app.scheduler import shutdown_scheduler, start_scheduler

# Initialize logging before anything else
setup_logging()
logger = get_logger("app")

# Database tables are managed by Alembic migrations
# Run: poetry run alembic upgrade head


def check_database_tables():
    """
    Check that required database tables exist.

    Raises RuntimeError with helpful message if tables are missing.
    This helps catch the case where migrations haven't been run.
    """
    required_tables = {"secrets", "pow_challenges"}
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    missing_tables = required_tables - existing_tables
    if missing_tables:
        raise RuntimeError(
            f"Database tables missing: {missing_tables}. "
            "Please run database migrations first: make migrate "
            "(or: cd backend && poetry run alembic upgrade head)"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - start/stop scheduler."""
    check_database_tables()
    logger.info("app_starting", version="0.1.0-beta")
    start_scheduler()
    yield
    logger.info("app_stopping")
    shutdown_scheduler()


app = FastAPI(
    title="InTheEventOfMyDeath",
    description="Zero-knowledge time-locked secret delivery service",
    version="0.1.0-beta",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging (after CORS so it sees all requests)
app.add_middleware(LoggingMiddleware)

# Routers
app.include_router(challenges.router, prefix="/api/v1", tags=["challenges"])
app.include_router(secrets.router, prefix="/api/v1", tags=["secrets"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
