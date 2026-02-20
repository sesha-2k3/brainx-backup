# Schemas: Pydantic models for incoming webhook requests from OpenClaw

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class MediaInfo(BaseModel):
    """Media attachment info from WhatsApp."""
    media_id: str
    mime_type: str
    url: Optional[str] = None
    file_size: Optional[int] = None


class InboundMessage(BaseModel):
    """Incoming message from WhatsApp via OpenClaw."""
    message_id: str = Field(..., description="Unique message identifier")
    from_number: str = Field(..., description="Sender's WhatsApp number")
    timestamp: datetime
    
    # Message type
    message_type: Literal["text", "voice", "image", "document"]
    
    # Content (depends on type)
    text: Optional[str] = None
    media: Optional[MediaInfo] = None
    caption: Optional[str] = None


class InboundWebhookPayload(BaseModel):
    """Full webhook payload from OpenClaw."""
    event_type: Literal["message", "status"]
    message: Optional[InboundMessage] = None
    
    # For status events
    status: Optional[str] = None
    message_id: Optional[str] = None


class ActionButton(BaseModel):
    """Button pressed in an interactive message."""
    button_id: str
    button_text: Optional[str] = None


class ActionPayload(BaseModel):
    """Payload for user action webhooks (button presses, replies)."""
    action_type: Literal["button", "reply", "list_select"]
    message_id: str
    from_number: str
    timestamp: datetime
    
    # For button actions
    button: Optional[ActionButton] = None
    
    # For quick replies or list selections
    selected_id: Optional[str] = None
    selected_text: Optional[str] = None
    
    # Original context
    context_message_id: Optional[str] = None


class WebhookResponse(BaseModel):
    """Standard webhook response."""
    success: bool
    message: Optional[str] = None
    proposal_id: Optional[str] = None
