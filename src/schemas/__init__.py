# Pydantic schemas package
from src.schemas.contacts import (
    ContactCreate,
    ContactUpdate,
    ContactResponse,
    ContactSummary,
    ExtractedContactData,
)
from src.schemas.proposals import (
    ProposalResponse,
    ConfirmationCard,
    EditRequest,
)
from src.schemas.tasks import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskSummary,
)   
__all__ = [
    "ContactCreate",
    "ContactUpdate",
    "ContactResponse",
    "ContactSummary",
    "ExtractedContactData",
    "ExtractedTask",
    "ProposalResponse",
    "ConfirmationCard",
    "EditRequest",
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "TaskSummary",
]
