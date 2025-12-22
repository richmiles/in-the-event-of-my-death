from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.middleware.rate_limit import limiter
from app.routers import challenges, secrets
from app.scheduler import shutdown_scheduler, start_scheduler

# Database tables are managed by Alembic migrations
# Run: poetry run alembic upgrade head


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - start/stop scheduler."""
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="InTheEventOfMyDeath",
    description="Zero-knowledge time-locked secret delivery service",
    version="0.1.0",
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

# Routers
app.include_router(challenges.router, prefix="/api/v1", tags=["challenges"])
app.include_router(secrets.router, prefix="/api/v1", tags=["secrets"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
