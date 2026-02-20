# Service: Send messages via OpenClaw WhatsApp API

import logging
from typing import Optional

import httpx

from src.config import get_settings
from src.schemas.messages import (
    Button,
    InteractiveMessage,
    ListMessage,
    MessageResponse,
    TextMessage,
)
from src.schemas.proposals import ConfirmationCard

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_text_message(to: str, text: str) -> MessageResponse:
    """
    Send a simple text message.
    """
    logger.info(f"Sending text message to {to}: {text[:50]}...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.openclaw_api_url}/messages/send",
                headers={
                    "Authorization": f"Bearer {settings.openclaw_outbound_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "to": to,
                    "type": "text",
                    "text": {"body": text},
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            
            return MessageResponse(
                success=True,
                message_id=data.get("message_id"),
            )
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error sending message: {e}")
            return MessageResponse(success=False, error=str(e))
        
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return MessageResponse(success=False, error=str(e))


async def send_interactive_buttons(
    to: str,
    body: str,
    buttons: list[Button],
    header: Optional[str] = None,
    footer: Optional[str] = None,
) -> MessageResponse:
    """
    Send an interactive message with buttons.
    """
    logger.info(f"Sending interactive message to {to} with {len(buttons)} buttons")
    
    # WhatsApp allows max 3 buttons
    button_data = [
        {"type": "reply", "reply": {"id": b.id, "title": b.text[:20]}}
        for b in buttons[:3]
    ]
    
    message_data = {
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {"buttons": button_data},
        },
    }
    
    if header:
        message_data["interactive"]["header"] = {"type": "text", "text": header}
    if footer:
        message_data["interactive"]["footer"] = {"text": footer}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.openclaw_api_url}/messages/send",
                headers={
                    "Authorization": f"Bearer {settings.openclaw_outbound_token}",
                    "Content-Type": "application/json",
                },
                json=message_data,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            
            return MessageResponse(success=True, message_id=data.get("message_id"))
        
        except Exception as e:
            logger.error(f"Error sending interactive message: {e}")
            return MessageResponse(success=False, error=str(e))


async def send_confirmation_card(to: str, card: ConfirmationCard) -> MessageResponse:
    """
    Send a confirmation card as an interactive message.
    """
    # Build body text from fields
    body_lines = [card.title, ""]
    for field in card.fields:
        body_lines.append(f"{field['label']}: {field['value']}")
    
    body = "\n".join(body_lines)
    
    buttons = [Button(id=b["id"], text=b["text"]) for b in card.buttons]
    
    return await send_interactive_buttons(
        to=to,
        body=body,
        buttons=buttons,
        footer="Reply to confirm or edit",
    )


async def download_media(media_url: str, media_id: str) -> Optional[bytes]:
    """
    Download media file from WhatsApp via OpenClaw.
    """
    logger.info(f"Downloading media: {media_id}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.openclaw_api_url}/media/{media_id}",
                headers={
                    "Authorization": f"Bearer {settings.openclaw_outbound_token}",
                },
                timeout=60.0,
            )
            response.raise_for_status()
            return response.content
        
        except Exception as e:
            logger.error(f"Error downloading media: {e}")
            return None
