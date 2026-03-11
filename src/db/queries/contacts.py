# Queries: Contact CRUD and lookup operations

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Contact


async def create_contact(
    db: AsyncSession,
    *,
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    role: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[list[str]] = None,
    notes: Optional[str] = None,
    context: Optional[str] = None,
    tenant_id: str = "default",
) -> Contact:
    contact = Contact(
        name=name,
        email=email,
        phone=phone,
        company=company,
        role=role,
        category=category,
        tags=tags or [],
        notes=notes,
        context=context,
        tenant_id=tenant_id,
    )
    # Build search vector
    contact.search_vector = _build_search_vector(contact)
    db.add(contact)
    await db.flush()
    return contact


async def get_contact_by_id(db: AsyncSession, contact_id: str) -> Optional[Contact]:
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    return result.scalar_one_or_none()


async def get_contact_by_email(db: AsyncSession, email: str, tenant_id: str = "default") -> Optional[Contact]:
    result = await db.execute(
        select(Contact).where(Contact.email == email, Contact.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def get_contact_by_phone(db: AsyncSession, phone: str, tenant_id: str = "default") -> Optional[Contact]:
    result = await db.execute(
        select(Contact).where(Contact.phone == phone, Contact.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def find_duplicate_contact(
    db: AsyncSession,
    email: Optional[str],
    phone: Optional[str],
    tenant_id: str = "default",
) -> Optional[Contact]:
    """Find existing contact by exact email or phone match."""
    if not email and not phone:
        return None
    
    conditions = []
    if email:
        conditions.append(Contact.email == email)
    if phone:
        conditions.append(Contact.phone == phone)
    
    result = await db.execute(
        select(Contact).where(Contact.tenant_id == tenant_id, or_(*conditions))
    )
    return result.scalar_one_or_none()


async def update_contact(
    db: AsyncSession,
    contact_id: str,
    **updates,
) -> Optional[Contact]:
    contact = await get_contact_by_id(db, contact_id)
    if not contact:
        return None
    
    for key, value in updates.items():
        if hasattr(contact, key):
            setattr(contact, key, value)
    
    contact.search_vector = _build_search_vector(contact)
    contact.updated_at = datetime.utcnow()
    await db.flush()
    return contact


async def list_contacts(
    db: AsyncSession,
    tenant_id: str = "default",
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Contact]:
    query = select(Contact).where(Contact.tenant_id == tenant_id)
    if category:
        query = query.where(Contact.category == category)
    query = query.order_by(Contact.updated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())

def escape_like(value: str) -> str:
    """Escape special characters for LIKE queries."""
    return (
        value
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )

async def search_contacts_by_name(
    db: AsyncSession,
    name: str,
    tenant_id: str = "default",
    limit: int = 10,
) -> list[Contact]:
    escaped_name = escape_like(name)
    result = await db.execute(
        select(Contact)
        .where(
            Contact.tenant_id == tenant_id,
            Contact.name.ilike(f"%{escaped_name}%", escape="\\")
        )
        .order_by(Contact.name)
        .limit(limit)
    )
    return list(result.scalars().all())


def _build_search_vector(contact: Contact) -> str:
    """Build a simple text search vector from contact fields."""
    parts = [
        contact.name,
        contact.email or "",
        contact.company or "",
        contact.role or "",
        contact.notes or "",
        contact.context or "",
    ]
    return " ".join(filter(None, parts)).lower()

async def get_contacts_due_for_reminder(
    db: AsyncSession,
    tenant_id: str = "default",
) -> list[Contact]:
    """Get contacts whose next_reminder_at is due."""
    now = datetime.utcnow()
    result = await db.execute(
        select(Contact)
        .where(
            Contact.tenant_id == tenant_id,
            Contact.reminder_frequency.isnot(None),
            Contact.next_reminder_at <= now,
        )
        .order_by(Contact.next_reminder_at.asc())
    )
    return list(result.scalars().all())


def calculate_next_reminder(frequency: str, from_date: datetime = None) -> datetime:
    """Calculate next reminder date based on frequency."""
    from_date = from_date or datetime.utcnow()
    
    if frequency == "every_3_days":
        return from_date + timedelta(days=3)
    elif frequency == "weekly":
        return from_date + timedelta(weeks=1)
    elif frequency == "every_2_weeks":
        return from_date + timedelta(weeks=2)
    elif frequency == "monthly":
        return from_date + timedelta(days=30)
    else:
        return None
