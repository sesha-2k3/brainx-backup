# Queries: Interaction CRUD operations

from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Interaction
from src.utils.text import escape_like


async def create_interaction(
    db: AsyncSession,
    *,
    contact_id: str,
    interaction_type: str,
    summary: str,
    occurred_at: datetime,
    raw_transcript: Optional[str] = None,
    extra_data: Optional[dict] = None,
    tenant_id: str = "default",
) -> Interaction:
    interaction = Interaction(
        contact_id=contact_id,
        tenant_id=tenant_id,
        interaction_type=interaction_type,
        summary=summary,
        occurred_at=occurred_at,
        raw_transcript=raw_transcript,
        extra_data=extra_data,
    )
    # Build search vector
    interaction.search_vector = _build_search_vector(interaction)
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
    tenant_id: str = "default",
    since: Optional[datetime] = None,
    limit: int = 50,
) -> list[Interaction]:
    query = select(Interaction).where(Interaction.tenant_id == tenant_id)
    if since:
        query = query.where(Interaction.occurred_at >= since)
    query = query.order_by(Interaction.occurred_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def search_interactions(
    db: AsyncSession,
    query_text: str,
    tenant_id: str = "default",
    contact_id: Optional[str] = None,
    limit: int = 20,
) -> list[Interaction]:
    """Search interactions by summary/transcript using ILIKE."""
    # Escape special LIKE characters
    escaped_query = escape_like(query_text.lower())
    
    query = select(Interaction).where(
        Interaction.tenant_id == tenant_id,
        Interaction.search_vector.ilike(f"%{escaped_query}%", escape="\\"),
    )
    if contact_id:
        query = query.where(Interaction.contact_id == contact_id)
    query = query.order_by(Interaction.occurred_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


def _build_search_vector(interaction: Interaction) -> str:
    """Build text search vector from interaction fields."""
    parts = [
        interaction.summary,
        interaction.raw_transcript or "",
    ]
    return " ".join(filter(None, parts)).lower()


async def get_interaction_by_id(
    db: AsyncSession,
    interaction_id: str,
    tenant_id: str = "default",
) -> Optional[Interaction]:
    """Get an interaction by ID, scoped to tenant."""
    result = await db.execute(
        select(Interaction).where(
            Interaction.id == interaction_id,
            Interaction.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def update_interaction(
    db: AsyncSession,
    interaction_id: str,
    **kwargs,
) -> Optional[Interaction]:
    """Update an interaction."""
    interaction = await db.get(Interaction, interaction_id)
    if not interaction:
        return None
    
    for key, value in kwargs.items():
        if hasattr(interaction, key):
            setattr(interaction, key, value)
    
    # Rebuild search vector if summary or transcript changed
    if "summary" in kwargs or "raw_transcript" in kwargs:
        interaction.search_vector = _build_search_vector(interaction)
    
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