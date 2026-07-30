"""
Service: proposal confirmation.

Extracted from the /proposals/{id}/confirm endpoint. The endpoint was doing
four distinct jobs inline - normalizing the submitted payload, merging or
creating the contact, recording the interaction, and materializing tasks - which
made the most consequential write path in the application also the least
testable, since exercising any part of it required an HTTP request and an
authenticated session.

Nothing here touches FastAPI. It takes a session and a plain dataclass, so it
can be tested against a session directly.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Contact, Interaction, Task
from src.db.queries import interactions as interaction_queries
from src.db.queries import proposals as proposal_queries
from src.db.queries import tasks as task_queries
from src.schemas.contacts import ExtractedContactData
from src.services.dedup import merge_or_create
from src.utils.category import clamp_category
from src.utils.dates import parse_relative_date
from src.utils.text import blank_to_none

logger = logging.getLogger(__name__)


class ProposalNotFoundError(Exception):
    """Raised when the proposal id does not resolve within the current tenant."""


@dataclass(slots=True)
class ConfirmationInput:
    """The values a user confirmed on the review screen."""

    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    website: str | None = None
    category: str | None = None
    context: str | None = None
    interaction_summary: str | None = None
    tasks: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class ConfirmationResult:
    contact: Contact
    interaction: Interaction | None
    tasks: list[Task]
    contact_was_created: bool


async def confirm_proposal(
    db: AsyncSession,
    proposal_id: str,
    submitted: ConfirmationInput,
) -> ConfirmationResult:
    """
    Apply a user-confirmed proposal: merge or create the contact, record the
    interaction, create any tasks, and resolve the proposal.

    Raises ProposalNotFoundError if the id doesn't resolve in this tenant.
    """
    proposal = await proposal_queries.get_proposal_by_id(db, proposal_id)
    if not proposal:
        raise ProposalNotFoundError(proposal_id)

    # raw_text was stashed alongside the LLM's structured fields at capture
    # time; it becomes the Interaction's raw_transcript.
    raw_text = (proposal.extracted_data or {}).get("raw_text")

    # Build from `submitted` - what the user confirmed - NOT from
    # proposal.extracted_data. The endpoint previously deduped against the LLM's
    # original extraction while writing the user's edits, so correcting a
    # misread email on the review screen had no effect on duplicate detection.
    confirmed = ExtractedContactData(
        name=submitted.name,
        email=blank_to_none(submitted.email),
        phone=blank_to_none(submitted.phone),
        company=blank_to_none(submitted.company),
        role=blank_to_none(submitted.role),
        website=blank_to_none(submitted.website),
        # clamp rather than validate: ExtractedContactData.category is typed as
        # the ContactCategory enum and Pydantic validates at construction, so an
        # unrecognized value would raise here and surface as a 500. Note this is
        # the opposite policy from CategoryField on ContactCreate/ContactUpdate -
        # deliberately, because this path carries inferred data and must degrade
        # rather than reject the user's whole capture.
        category=clamp_category(blank_to_none(submitted.category)),
        context=blank_to_none(submitted.context),
    )

    # merge_or_create() is the single source of truth for merge semantics.
    contact, was_created = await merge_or_create(db, confirmed)

    interaction = None
    summary = blank_to_none(submitted.interaction_summary)
    if summary:
        interaction = await interaction_queries.create_interaction(
            db,
            contact_id=contact.id,
            interaction_type="note",
            summary=summary,
            occurred_at=datetime.now(UTC),
            raw_transcript=raw_text,
        )

    created_tasks = await _create_tasks(db, contact.id, submitted.tasks)

    await proposal_queries.confirm_proposal(
        db,
        proposal_id,
        contact_id=contact.id,
        interaction_id=interaction.id if interaction else None,
    )

    logger.info(
        "Confirmed proposal %s -> contact %s (%s), %d task(s)",
        proposal_id,
        contact.id,
        "created" if was_created else "merged",
        len(created_tasks),
    )

    return ConfirmationResult(
        contact=contact,
        interaction=interaction,
        tasks=created_tasks,
        contact_was_created=was_created,
    )


async def _create_tasks(db: AsyncSession, contact_id: str, task_payloads: list[dict]) -> list[Task]:
    """
    Materialize extracted tasks, skipping any without a usable title.

    Due dates are parsed leniently here rather than by a schema validator: these
    phrases come from LLM extraction, so an uninterpretable one must degrade to
    "no due date" instead of rejecting the user's entire capture. Contrast
    TaskCreate/TaskUpdate, where a bad date is a 422 because a human typed it.
    """
    created: list[Task] = []

    for payload in task_payloads:
        title = blank_to_none(payload.get("title"))
        if not title:
            continue

        raw_due = payload.get("due_date")
        due_date = parse_relative_date(raw_due) if raw_due else None
        if raw_due and due_date is None:
            logger.info("Could not parse extracted due date %r for task %r", raw_due, title)

        created.append(
            await task_queries.create_task(
                db,
                title=title,
                contact_id=contact_id,
                due_date=due_date,
            )
        )

    return created
