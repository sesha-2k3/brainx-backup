# Queries: Contact CRUD and lookup operations

from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Contact
from src.utils.text import escape_like


async def create_contact(
    db: AsyncSession,
    *,
    name: str,
    email: str | None = None,
    phone: str | None = None,
    company: str | None = None,
    role: str | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
    notes: str | None = None,
    context: str | None = None,
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
    )
    # Build search vector
    contact.search_vector = _build_search_vector(contact)
    db.add(contact)
    await db.flush()
    return contact


async def get_contact_by_id(
    db: AsyncSession,
    contact_id: str,
) -> Contact | None:
    """Get a contact by ID, scoped to tenant."""
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    return result.scalar_one_or_none()


async def get_contact_by_email(
    db: AsyncSession,
    email: str,
) -> Contact | None:
    result = await db.execute(select(Contact).where(Contact.email == email))
    return result.scalar_one_or_none()


async def get_contact_by_phone(
    db: AsyncSession,
    phone: str,
) -> Contact | None:
    result = await db.execute(select(Contact).where(Contact.phone == phone))
    return result.scalar_one_or_none()


async def find_duplicate_contact(
    db: AsyncSession,
    email: str | None,
    phone: str | None,
) -> Contact | None:
    """Find existing contact by exact email or phone match."""
    if not email and not phone:
        return None

    conditions = []
    if email:
        conditions.append(Contact.email == email)
    if phone:
        conditions.append(Contact.phone == phone)

    result = await db.execute(
        select(Contact).where(
            or_(*conditions),
        )
    )
    return result.scalar_one_or_none()


async def update_contact(
    db: AsyncSession,
    contact_id: str,
    **updates,
) -> Contact | None:
    """Update a contact, scoped to tenant."""
    contact = await get_contact_by_id(db, contact_id)
    if not contact:
        return None

    for key, value in updates.items():
        if hasattr(contact, key):
            setattr(contact, key, value)

    contact.search_vector = _build_search_vector(contact)
    contact.updated_at = datetime.now(UTC)
    await db.flush()
    return contact


async def list_contacts(
    db: AsyncSession,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Contact]:
    query = select(Contact)
    if category:
        query = query.where(Contact.category == category)
    query = query.order_by(Contact.updated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def search_contacts_by_name(
    db: AsyncSession,
    name: str,
    limit: int = 10,
) -> list[Contact]:
    escaped_name = escape_like(name)
    result = await db.execute(
        select(Contact)
        .where(
            Contact.name.ilike(f"%{escaped_name}%", escape="\\"),
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
) -> list[Contact]:
    """Get contacts whose next_reminder_at is due."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(Contact)
        .where(
            Contact.reminder_frequency.isnot(None),
            Contact.next_reminder_at <= now,
        )
        .order_by(Contact.next_reminder_at.asc())
    )
    return list(result.scalars().all())


def calculate_next_reminder(frequency: str, from_date: datetime | None = None) -> datetime | None:
    """Calculate next reminder date based on frequency."""
    from_date = from_date or datetime.now(UTC)

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
