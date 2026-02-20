# API: Webhook endpoints for OpenClaw integration

import logging
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.db import get_db
from src.db.models import JobType
from src.db.queries import jobs as job_queries
from src.db.queries import proposals as proposal_queries
from src.schemas.webhooks import (
    ActionPayload,
    InboundWebhookPayload,
    WebhookResponse,
)
from src.services.confirmation import handle_user_action

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_token(authorization: str = Header(...)) -> str:
    """Verify the bearer token from OpenClaw."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )
    token = authorization[7:]
    if token != settings.openclaw_webhook_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return token


@router.post("/inbound", response_model=WebhookResponse)
async def handle_inbound(
    payload: InboundWebhookPayload,
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(verify_token),
):
    """
    Receive inbound messages from WhatsApp via OpenClaw.
    Enqueues a job for async processing.
    """
    if payload.event_type != "message" or not payload.message:
        return WebhookResponse(success=True, message="Ignored non-message event")
    
    msg = payload.message
    logger.info(f"Received {msg.message_type} message from {msg.from_number}")
    
    # Enqueue processing job
    job = await job_queries.enqueue_job(
        db,
        job_type=JobType.PROCESS_INBOUND,
        payload={
            "message_id": msg.message_id,
            "from_number": msg.from_number,
            "timestamp": msg.timestamp.isoformat(),
            "message_type": msg.message_type,
            "text": msg.text,
            "caption": msg.caption,
            "media": msg.media.model_dump() if msg.media else None,
        },
    )
    
    logger.info(f"Enqueued job {job.id} for message {msg.message_id}")
    return WebhookResponse(success=True, message=f"Queued job {job.id}")


@router.post("/action", response_model=WebhookResponse)
async def handle_action(
    payload: ActionPayload,
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(verify_token),
):
    """
    Handle user actions (button presses, list selections) from WhatsApp.
    """
    logger.info(f"Received action {payload.action_type} from {payload.from_number}")
    
    # Determine what action was taken
    action_id = None
    if payload.button:
        action_id = payload.button.button_id
    elif payload.selected_id:
        action_id = payload.selected_id
    
    if not action_id:
        return WebhookResponse(success=False, message="No action ID found")
    
    # Handle the action
    result = await handle_user_action(
        db=db,
        whatsapp_user_id=payload.from_number,
        action_id=action_id,
    )
    
    return WebhookResponse(
        success=result.get("success", False),
        message=result.get("message"),
        proposal_id=result.get("proposal_id"),
    )
