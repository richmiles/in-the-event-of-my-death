"""Background scheduler for periodic cleanup tasks."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.database import SessionLocal
from app.logging_config import get_logger
from app.services.discord_service import send_error_alert_sync
from app.services.pow_service import cleanup_expired_challenges
from app.services.secret_service import clear_expired_secrets

logger = get_logger("scheduler")

scheduler = BackgroundScheduler()


def cleanup_secrets_job() -> None:
    """Run periodic cleanup of expired and retrieved secrets."""
    db = SessionLocal()
    try:
        cleared = clear_expired_secrets(db)
        logger.info("cleanup_secrets_completed", cleared_count=cleared)
    except Exception as e:
        logger.error("cleanup_secrets_failed", error=str(e))
        send_error_alert_sync(
            error_type="Scheduler Job Failed",
            message=str(e),
            context={"job_name": "cleanup_secrets"},
        )
    finally:
        db.close()


def cleanup_challenges_job() -> None:
    """Run periodic cleanup of expired PoW challenges."""
    db = SessionLocal()
    try:
        deleted = cleanup_expired_challenges(db)
        logger.info("cleanup_challenges_completed", deleted_count=deleted)
    except Exception as e:
        logger.error("cleanup_challenges_failed", error=str(e))
        send_error_alert_sync(
            error_type="Scheduler Job Failed",
            message=str(e),
            context={"job_name": "cleanup_challenges"},
        )
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
    logger.info("scheduler_started", cleanup_interval_hours=settings.cleanup_interval_hours)


def shutdown_scheduler() -> None:
    """Shutdown the scheduler gracefully."""
    scheduler.shutdown()
    logger.info("scheduler_stopped")
