# Worker: Scheduler for periodic tasks (digest, reminders)

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import get_settings
from src.db import async_session_factory
from src.db.models import JobType
from src.db.queries import jobs as job_queries
from src.db.queries import tasks as task_queries
from src.services.messaging import send_text_message

logger = logging.getLogger(__name__)
settings = get_settings()


async def schedule_daily_digest() -> None:
    """
    Enqueue daily digest job for configured user.
    This runs at the configured hour each day.
    """
    logger.info("Scheduling daily digest job")
    
    async with async_session_factory() as db:
        await job_queries.enqueue_job(
            db,
            job_type=JobType.DAILY_DIGEST,
            payload={
                "user_id": settings.openclaw_phone_number_id,  # The user's WhatsApp number
                "tenant_id": settings.tenant_id,
            },
        )
        await db.commit()
    
    logger.info("Daily digest job enqueued")


async def check_reminders() -> None:
    """
    Check for due reminders and send notifications.
    Runs every 15 minutes.
    """
    logger.info("Checking for due reminders")
    
    async with async_session_factory() as db:
        now = datetime.utcnow()
        due_tasks = await task_queries.get_due_reminders(db, now, settings.tenant_id)
        
        for task in due_tasks:
            # Build reminder message
            message = f"Reminder: {task.title}"
            if task.contact:
                message += f" ({task.contact.name})"
            if task.due_date:
                message += f"\nDue: {task.due_date.strftime('%Y-%m-%d')}"
            
            # Send reminder (using configured phone number)
            await send_text_message(settings.openclaw_phone_number_id, message)
            
            # Mark as sent
            await task_queries.mark_reminder_sent(db, task.id)
            logger.info(f"Sent reminder for task {task.id}")
        
        await db.commit()
    
    logger.info(f"Processed {len(due_tasks)} reminders")


def create_scheduler() -> AsyncIOScheduler:
    """
    Create and configure the scheduler.
    """
    scheduler = AsyncIOScheduler(timezone=settings.digest_timezone)
    
    # Daily digest at configured hour
    scheduler.add_job(
        schedule_daily_digest,
        CronTrigger(hour=settings.digest_hour, minute=0),
        id="daily_digest",
        replace_existing=True,
    )
    
    # Check reminders every 15 minutes
    scheduler.add_job(
        check_reminders,
        CronTrigger(minute="*/15"),
        id="check_reminders",
        replace_existing=True,
    )
    
    return scheduler


async def run_scheduler() -> None:
    """
    Run the scheduler.
    """
    logger.info("Starting scheduler...")
    
    scheduler = create_scheduler()
    scheduler.start()
    
    logger.info(f"Scheduler started. Digest scheduled for {settings.digest_hour}:00 {settings.digest_timezone}")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(run_scheduler())
