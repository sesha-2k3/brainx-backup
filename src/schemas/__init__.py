# Pydantic schemas package
from src.schemas.contacts import (
    ContactCreate,
    ContactUpdate,
    ContactResponse,
    ContactSummary,
    ExtractedContactData,
    ExtractedTask,
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
from src.schemas.interactions import (
    InteractionCreate,
    InteractionUpdate,
    InteractionResponse,
    InteractionSummary,
)

__all__ = [
    # Contacts
    "ContactCreate",
    "ContactUpdate",
    "ContactResponse",
    "ContactSummary",
    "ExtractedContactData",
    "ExtractedTask",
    # Proposals
    "ProposalResponse",
    "ConfirmationCard",
    "EditRequest",
    # Tasks
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "TaskSummary",
    # Interactions
    "InteractionCreate",
    "InteractionUpdate",
    "InteractionResponse",
    "InteractionSummary",
]