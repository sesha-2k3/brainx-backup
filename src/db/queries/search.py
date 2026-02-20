# Queries: Full-text search and filtered listing queries

from datetime import datetime
from typing import Optional
from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Contact, Interaction


async def search_all(
    db: AsyncSession,
    query_text: str,
    tenant_id: str = "default",
    limit: int = 20,
) -> dict:
    """
    Search across contacts and interactions.
    Returns dict with 'contacts' and 'interactions' lists.
    """
    query_lower = query_text.lower()
    
    # Search contacts
    contacts_result = await db.execute(
        select(Contact)
        .where(
            Contact.tenant_id == tenant_id,
            Contact.search_vector.ilike(f"%{query_lower}%"),
        )
        .order_by(Contact.updated_at.desc())
        .limit(limit)
    )
    contacts = list(contacts_result.scalars().all())
    
    # Search interactions
    interactions_result = await db.execute(
        select(Interaction)
        .where(
            Interaction.tenant_id == tenant_id,
            Interaction.search_vector.ilike(f"%{query_lower}%"),
        )
        .order_by(Interaction.occurred_at.desc())
        .limit(limit)
    )
    interactions = list(interactions_result.scalars().all())
    
    return {
        "contacts": contacts,
        "interactions": interactions,
    }


async def get_contacts_by_category(
    db: AsyncSession,
    category: str,
    tenant_id: str = "default",
    since: Optional[datetime] = None,
    limit: int = 50,
) -> list[Contact]:
    """Get contacts filtered by category, optionally since a date."""
    query = select(Contact).where(
        Contact.tenant_id == tenant_id,
        Contact.category == category,
    )
    if since:
        query = query.where(Contact.updated_at >= since)
    query = query.order_by(Contact.updated_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_interactions_by_company(
    db: AsyncSession,
    company: str,
    tenant_id: str = "default",
    since: Optional[datetime] = None,
    limit: int = 20,
) -> list[Interaction]:
    """Get interactions for contacts at a specific company."""
    # First get contacts at this company
    contacts_result = await db.execute(
        select(Contact.id)
        .where(
            Contact.tenant_id == tenant_id,
            Contact.company.ilike(f"%{company}%"),
        )
    )
    contact_ids = [row[0] for row in contacts_result.fetchall()]
    
    if not contact_ids:
        return []
    
    # Get interactions for those contacts
    query = select(Interaction).where(
        Interaction.tenant_id == tenant_id,
        Interaction.contact_id.in_(contact_ids),
    )
    if since:
        query = query.where(Interaction.occurred_at >= since)
    query = query.order_by(Interaction.occurred_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_recent_activity(
    db: AsyncSession,
    tenant_id: str = "default",
    days: int = 7,
    limit: int = 50,
) -> list[Interaction]:
    """Get all interactions from the last N days."""
    since = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    since = since - timedelta(days=days)
    
    result = await db.execute(
        select(Interaction)
        .where(
            Interaction.tenant_id == tenant_id,
            Interaction.occurred_at >= since,
        )
        .order_by(Interaction.occurred_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_contact_with_interactions(
    db: AsyncSession,
    contact_id: str,
    interaction_limit: int = 10,
) -> Optional[dict]:
    """Get a contact with their recent interactions."""
    contact = await db.get(Contact, contact_id)
    if not contact:
        return None
    
    interactions_result = await db.execute(
        select(Interaction)
        .where(Interaction.contact_id == contact_id)
        .order_by(Interaction.occurred_at.desc())
        .limit(interaction_limit)
    )
    interactions = list(interactions_result.scalars().all())
    
    return {
        "contact": contact,
        "interactions": interactions,
    }
