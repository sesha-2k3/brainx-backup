# Schemas: Pydantic models for interactions

from datetime import datetime

from pydantic import BaseModel


class InteractionCreate(BaseModel):
    """Fields for creating an interaction."""

    contact_id: str
    interaction_type: str = "note"
    summary: str
    occurred_at: str | None = None  # ISO string or None (defaults to now)


class InteractionUpdate(BaseModel):
    """Fields for updating an interaction."""

    interaction_type: str | None = None
    summary: str | None = None
    occurred_at: str | None = None  # ISO string


class InteractionResponse(BaseModel):
    """Interaction response with all fields."""

    id: str
    contact_id: str
    tenant_id: str
    interaction_type: str
    summary: str
    occurred_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class InteractionSummary(BaseModel):
    """Minimal interaction info for lists."""

    id: str
    interaction_type: str
    summary: str
    occurred_at: datetime

    class Config:
        from_attributes = True
