"""
Contact Schemas - Pydantic models for contact data
"""

from datetime import datetime

from pydantic import BaseModel, Field

from src.schemas.contact_category_enums import ContactCategory


class ContactBase(BaseModel):
    """Base contact fields."""

    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    category: ContactCategory | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    context: str | None = None


class ContactCreate(BaseModel):
    """Fields for creating a new contact."""

    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    category: str | None = None  # str to accept any value from API
    context: str | None = None
    notes: str | None = None


class ContactUpdate(BaseModel):
    """Fields for updating a contact (all optional)."""

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    category: str | None = None  # str to accept any value from API
    tags: list[str] | None = None
    notes: str | None = None
    context: str | None = None
    reminder_frequency: str | None = None  # weekly, every_3_days, every_2_weeks, monthly


class ContactResponse(ContactBase):
    """Contact response with all fields."""

    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContactSummary(BaseModel):
    """Minimal contact info for lists."""

    id: str
    name: str
    company: str | None = None
    category: ContactCategory | None = None

    class Config:
        from_attributes = True


class ExtractedTask(BaseModel):
    """A single extracted task."""

    title: str
    due_date: str | None = None


class ExtractedContactData(BaseModel):
    """Structured data extracted from voice/text input."""

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    category: ContactCategory | None = None
    context: str | None = None
    interaction_summary: str | None = None
    tasks: list[ExtractedTask] = Field(default_factory=list)

    # Legacy fields for backward compatibility
    follow_up: str | None = None
    follow_up_date: str | None = None
