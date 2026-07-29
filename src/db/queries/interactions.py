# Queries: Interaction CRUD operations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Interaction
from src.db.queries.filters import match_all_terms


async def create_interaction(
    db: AsyncSession,
    *,
    contact_id: str,
    interaction_type: str,
    summary: str,
    occurred_at: datetime,
    raw_transcript: str | None = None,
    extra_data: dict | None = None,
) -> Interaction:
    interaction = Interaction(
        contact_id=contact_id,
        interaction_type=interaction_type,
        summary=summary,
        occurred_at=occurred_at,
        raw_transcript=raw_transcript,
        extra_data=extra_data,
    )
    db.add(interaction)
    await db.flush()
    return interaction


async def list_interactions_for_contact(
    db: AsyncSession,
    contact_id: str,
    limit: int = 20,
    offset: int = 0,
) -> list[Interaction]:
    result = await db.execute(
        select(Interaction)
        .where(Interaction.contact_id == contact_id)
        .order_by(Interaction.occurred_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def list_recent_interactions(
    db: AsyncSession,
    since: datetime | None = None,
    limit: int = 50,
) -> list[Interaction]:
    query = select(Interaction)
    if since:
        query = query.where(Interaction.occurred_at >= since)
    query = query.order_by(Interaction.occurred_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def search_interactions(
    db: AsyncSession,
    query_text: str,
    contact_id: str | None = None,
    limit: int = 20,
) -> list[Interaction]:
    """Search interactions by summary/transcript using ILIKE."""
    text_filter = match_all_terms(query_text, Interaction.summary, Interaction.raw_transcript)
    if text_filter is None:
        return []

    query = select(Interaction).where(text_filter)
    if contact_id:
        query = query.where(Interaction.contact_id == contact_id)
    query = query.order_by(Interaction.occurred_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_interaction_by_id(
    db: AsyncSession,
    interaction_id: str,
) -> Interaction | None:
    """Get an interaction by ID, scoped to tenant."""
    result = await db.execute(
        select(Interaction).where(
            Interaction.id == interaction_id,
        )
    )
    return result.scalar_one_or_none()


async def update_interaction(
    db: AsyncSession,
    interaction_id: str,
    **kwargs,
) -> Interaction | None:
    """Update an interaction."""
    interaction = await db.get(Interaction, interaction_id)
    if not interaction:
        return None

    for key, value in kwargs.items():
        if hasattr(interaction, key):
            setattr(interaction, key, value)

    await db.flush()
    return interaction


async def delete_interaction(
    db: AsyncSession,
    interaction_id: str,
) -> bool:
    """Delete an interaction."""
    interaction = await db.get(Interaction, interaction_id)
    if not interaction:
        return False

    await db.delete(interaction)
    await db.flush()
    return True
