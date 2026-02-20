# Schemas: Pydantic models for outbound WhatsApp messages

from typing import Optional
from pydantic import BaseModel


class TextMessage(BaseModel):
    """Simple text message."""
    to: str
    text: str


class Button(BaseModel):
    """Interactive button."""
    id: str
    text: str


class InteractiveMessage(BaseModel):
    """Message with interactive buttons."""
    to: str
    body: str
    buttons: list[Button]
    header: Optional[str] = None
    footer: Optional[str] = None


class ListItem(BaseModel):
    """Item in a list message."""
    id: str
    title: str
    description: Optional[str] = None


class ListSection(BaseModel):
    """Section containing list items."""
    title: str
    items: list[ListItem]


class ListMessage(BaseModel):
    """Message with selectable list."""
    to: str
    body: str
    button_text: str
    sections: list[ListSection]
    header: Optional[str] = None
    footer: Optional[str] = None


class MessageResponse(BaseModel):
    """Response from sending a message."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
