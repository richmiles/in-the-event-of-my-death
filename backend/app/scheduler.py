"""Background scheduler for periodic cleanup tasks."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.database import SessionLocal
from app.services.pow_service import cleanup_expired_challenges
from app.services.secret_service import clear_expired_secrets

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def cleanup_secrets_job() -> None:
    """Run periodic cleanup of expired and retrieved secrets."""
    db = SessionLocal()
    try:
        cleared = clear_expired_secrets(db)
        if cleared:
            logger.info(f"Secrets cleanup: cleared {cleared} secrets")
    except Exception as e:
        logger.error(f"Secrets cleanup failed: {e}")
    finally:
        db.close()


def cleanup_challenges_job() -> None:
    """Run periodic cleanup of expired PoW challenges."""
    db = SessionLocal()
    try:
        deleted = cleanup_expired_challenges(db)
        if deleted:
            logger.info(f"Challenges cleanup: deleted {deleted} expired challenges")
    except Exception as e:
        logger.error(f"Challenges cleanup failed: {e}")
    finally:
        db.close()


def start_scheduler() -> None:
    """Start the background scheduler."""
    scheduler.add_job(
        cleanup_secrets_job,
        trigger=IntervalTrigger(hours=settings.cleanup_interval_hours),
        id="cleanup_expired_secrets",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_challenges_job,
        trigger=IntervalTrigger(hours=settings.cleanup_interval_hours),
        id="cleanup_expired_challenges",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started - cleanup runs every {settings.cleanup_interval_hours} hour(s)")


def shutdown_scheduler() -> None:
    """Shutdown the scheduler gracefully."""
    scheduler.shutdown()
    logger.info("Scheduler stopped")
