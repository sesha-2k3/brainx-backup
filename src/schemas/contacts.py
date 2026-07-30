"""
Contact Schemas - Pydantic models for contact data
"""

from datetime import datetime

from pydantic import BaseModel, Field

from src.schemas.contact_category_enums import ContactCategory
from src.schemas.fields import CategoryField


class ContactBase(BaseModel):
    """Base contact fields."""

    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    website: str | None = None
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
    website: str | None = None
    # Validated against ContactCategory rather than accepting any string. The
    # old "str to accept any value from API" looseness protected nothing: LLM
    # output reaches the DB via clamp_category() on the extraction path, never
    # through this schema. All it did was let a client's typo be stored verbatim.
    category: CategoryField = None
    context: str | None = None
    notes: str | None = None


class ContactUpdate(BaseModel):
    """Fields for updating a contact (all optional)."""

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    website: str | None = None
    category: CategoryField = None
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
    website: str | None = None
    category: ContactCategory | None = None
    context: str | None = None
    interaction_summary: str | None = None
    tasks: list[ExtractedTask] = Field(default_factory=list)

    # Legacy fields for backward compatibility
    follow_up: str | None = None
    follow_up_date: str | None = None
