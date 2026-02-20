# Worker: Job processor that dequeues and handles jobs

import asyncio
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.db import async_session_factory
from src.db.models import Job, JobType
from src.db.queries import jobs as job_queries
from src.db.queries import proposals as proposal_queries
from src.schemas.contacts import ExtractedContactData
from src.services.confirmation import build_confirmation_card
from src.services.dedup import find_duplicate
from src.services.extraction import extract_contact_data
from src.services.messaging import (
    download_media,
    send_confirmation_card,
    send_text_message,
)
from src.services.ocr import process_business_card_bytes
from src.services.transcription import transcribe_audio_bytes

logger = logging.getLogger(__name__)
settings = get_settings()


async def process_job(db: AsyncSession, job: Job) -> None:
    """
    Process a single job based on its type.
    """
    logger.info(f"Processing job {job.id} of type {job.job_type}")
    
    if job.job_type == JobType.PROCESS_INBOUND:
        await handle_inbound_message(db, job.payload)
    
    elif job.job_type == JobType.SEND_MESSAGE:
        await handle_send_message(job.payload)
    
    elif job.job_type == JobType.DAILY_DIGEST:
        await handle_daily_digest(db, job.payload)
    
    else:
        logger.warning(f"Unknown job type: {job.job_type}")


async def handle_inbound_message(db: AsyncSession, payload: dict) -> None:
    """
    Process an inbound WhatsApp message.
    """
    message_type = payload["message_type"]
    from_number = payload["from_number"]
    
    extracted = None
    confidence = None
    source_type = message_type
    
    if message_type == "voice":
        # Download and transcribe audio
        media_info = payload.get("media")
        if media_info:
            audio_bytes = await download_media(
                media_info.get("url", ""),
                media_info["media_id"],
            )
            if audio_bytes:
                result = await transcribe_audio_bytes(audio_bytes)
                extracted = await extract_contact_data(result["text"])
    
    elif message_type == "text":
        text = payload.get("text", "")
        if text:
            extracted = await extract_contact_data(text)
    
    elif message_type == "image":
        # Check if it might be a business card
        media_info = payload.get("media")
        if media_info:
            image_bytes = await download_media(
                media_info.get("url", ""),
                media_info["media_id"],
            )
            if image_bytes:
                result = await process_business_card_bytes(image_bytes)
                extracted = result["extracted"]
                confidence = result["confidence"]
                source_type = "business_card"
    
    if not extracted or not extracted.name:
        # Couldn't extract meaningful data
        await send_text_message(
            from_number,
            "I couldn't extract contact information from that. Please try again with a clearer voice note, text, or business card image.",
        )
        return
    
    # Check for duplicate
    duplicate = await find_duplicate(db, extracted, settings.tenant_id)
    
    # Create proposal
    proposal = await proposal_queries.create_proposal(
        db,
        source_type=source_type,
        whatsapp_user_id=from_number,
        extracted_data=extracted.model_dump(),
        source_message_id=payload.get("message_id"),
        confidence_score=confidence,
        tenant_id=settings.tenant_id,
    )
    
    # Build and send confirmation card
    card = build_confirmation_card(
        proposal.id,
        extracted,
        duplicate_name=duplicate.name if duplicate else None,
    )
    
    await send_confirmation_card(from_number, card)
    logger.info(f"Sent confirmation card for proposal {proposal.id}")


async def handle_send_message(payload: dict) -> None:
    """
    Send an outbound message.
    """
    to = payload["to"]
    text = payload.get("text")
    
    if text:
        await send_text_message(to, text)


async def handle_daily_digest(db: AsyncSession, payload: dict) -> None:
    """
    Generate and send daily digest.
    """
    from src.db.queries import tasks as task_queries
    from src.db.queries import search as search_queries
    
    user_id = payload.get("user_id")
    if not user_id:
        logger.error("No user_id in daily digest payload")
        return
    
    # Get tasks due today
    today = datetime.utcnow().replace(hour=23, minute=59, second=59)
    tasks = await task_queries.list_tasks_due_by(db, today, settings.tenant_id)
    
    # Get recent activity
    interactions = await search_queries.get_recent_activity(db, settings.tenant_id, days=1)
    
    # Build digest message
    lines = ["Daily Digest", ""]
    
    if tasks:
        lines.append(f"Tasks due today ({len(tasks)}):")
        for task in tasks[:5]:
            contact_info = f" - {task.contact.name}" if task.contact else ""
            lines.append(f"- {task.title}{contact_info}")
        lines.append("")
    
    if interactions:
        lines.append(f"Yesterday's activity ({len(interactions)}):")
        for i in interactions[:5]:
            lines.append(f"- {i.summary[:60]}...")
        lines.append("")
    
    if not tasks and not interactions:
        lines.append("No pending tasks or recent activity.")
    
    await send_text_message(user_id, "\n".join(lines))


async def run_worker() -> None:
    """
    Main worker loop - continuously polls for and processes jobs.
    """
    logger.info("Starting worker...")
    
    while True:
        try:
            async with async_session_factory() as db:
                job = await job_queries.dequeue_job(db)
                
                if job:
                    try:
                        await process_job(db, job)
                        await job_queries.complete_job(db, job.id)
                        await db.commit()
                        logger.info(f"Completed job {job.id}")
                    
                    except Exception as e:
                        logger.error(f"Job {job.id} failed: {e}")
                        await db.rollback()
                        async with async_session_factory() as db2:
                            await job_queries.fail_job(db2, job.id, str(e))
                            await db2.commit()
                
                else:
                    # No jobs available, wait before polling again
                    await asyncio.sleep(settings.worker_poll_interval)
        
        except Exception as e:
            logger.error(f"Worker error: {e}")
            await asyncio.sleep(5)  # Wait before retrying


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(run_worker())
