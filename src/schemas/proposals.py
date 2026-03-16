# Schemas: Pydantic models for proposals and confirmation cards

from datetime import datetime

from pydantic import BaseModel

from src.db.models import ProposalStatus


class ProposalResponse(BaseModel):
    """Proposal data response."""

    id: str
    tenant_id: str
    source_type: str
    whatsapp_user_id: str
    extracted_data: dict
    confidence_score: float | None = None
    status: ProposalStatus
    contact_id: str | None = None
    interaction_id: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None

    class Config:
        from_attributes = True


class ConfirmationCard(BaseModel):
    """Data for rendering a confirmation card in WhatsApp."""

    proposal_id: str
    title: str
    fields: list[dict]  # [{label: str, value: str}, ...]
    buttons: list[dict]  # [{id: str, text: str}, ...]


class EditRequest(BaseModel):
    """Request to edit extracted data before confirmation."""

    field: str
    new_value: str
