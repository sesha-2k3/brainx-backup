# Queries: Proposal CRUD and state transitions

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Proposal, ProposalStatus


async def create_proposal(
    db: AsyncSession,
    *,
    source_type: str,
    extracted_data: dict,
    source_message_id: str | None = None,
    confidence_score: float | None = None,
) -> Proposal:
    proposal = Proposal(
        source_type=source_type,
        source_message_id=source_message_id,
        extracted_data=extracted_data,
        confidence_score=confidence_score,
        status=ProposalStatus.PENDING,
    )
    db.add(proposal)
    await db.flush()
    return proposal


async def get_proposal_by_id(db: AsyncSession, proposal_id: str) -> Proposal | None:
    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    return result.scalar_one_or_none()


async def get_latest_pending_proposal(db: AsyncSession) -> Proposal | None:
    """
    Most recent pending proposal for the session's tenant.

    Replaces get_pending_proposal_for_user(whatsapp_user_id), which had zero
    callers and filtered on a column hardcoded to "web" - so it would have
    returned another tenant's proposal had the TenantSession filter not been
    doing the real scoping work anyway. Tenancy is applied automatically here.
    """
    result = await db.execute(
        select(Proposal)
        .where(Proposal.status == ProposalStatus.PENDING)
        .order_by(Proposal.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def confirm_proposal(
    db: AsyncSession,
    proposal_id: str,
    contact_id: str,
    interaction_id: str | None = None,
) -> Proposal | None:
    proposal = await get_proposal_by_id(db, proposal_id)
    if not proposal:
        return None

    proposal.status = ProposalStatus.CONFIRMED
    proposal.contact_id = contact_id
    proposal.interaction_id = interaction_id
    proposal.resolved_at = datetime.now(UTC)
    await db.flush()
    return proposal


async def update_proposal_data(
    db: AsyncSession,
    proposal_id: str,
    extracted_data: dict,
) -> Proposal | None:
    """Update extracted data (for edits before confirmation)."""
    proposal = await get_proposal_by_id(db, proposal_id)
    if not proposal:
        return None

    proposal.extracted_data = extracted_data
    proposal.status = ProposalStatus.EDITED
    await db.flush()
    return proposal


async def reject_proposal(
    db: AsyncSession,
    proposal_id: str,
) -> Proposal | None:
    proposal = await get_proposal_by_id(db, proposal_id)
    if not proposal:
        return None

    proposal.status = ProposalStatus.REJECTED
    proposal.resolved_at = datetime.now(UTC)
    await db.flush()
    return proposal


async def list_pending_proposals(
    db: AsyncSession,
    limit: int = 20,
) -> list[Proposal]:
    result = await db.execute(
        select(Proposal)
        .where(Proposal.status == ProposalStatus.PENDING)
        .order_by(Proposal.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
