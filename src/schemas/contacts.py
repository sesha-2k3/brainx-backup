# Schemas: Pydantic models for contact data

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ContactBase(BaseModel):
    """Base contact fields."""
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    category: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    context: Optional[str] = None


class ContactCreate(ContactBase):
    """Fields for creating a new contact."""
    pass


class ContactUpdate(BaseModel):
    """Fields for updating a contact (all optional)."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None
    context: Optional[str] = None


class ContactResponse(ContactBase):
    """Contact response with all fields."""
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContactSummary(BaseModel):
    """Minimal contact info for lists."""
    id: str
    name: str
    company: Optional[str] = None
    category: Optional[str] = None

    class Config:
        from_attributes = True


class ExtractedContactData(BaseModel):
    """Structured data extracted from voice/text input."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    category: Optional[str] = None
    context: Optional[str] = None
    interaction_summary: Optional[str] = None
    tasks: list[ExtractedTask] = []
    
    # Legacy fields for backward compatibility
    follow_up: Optional[str] = None
    follow_up_date: Optional[str] = None

class ExtractedTask(BaseModel):
    """A single extracted task."""
    title: str
    due_date: Optional[str] = None
