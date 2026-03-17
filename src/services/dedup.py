# Service: Contact deduplication using exact email/phone matching

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Contact
from src.db.queries import contacts as contact_queries
from src.schemas.contacts import ExtractedContactData
from src.utils.phone import normalize_phone

logger = logging.getLogger(__name__)


async def find_duplicate(
    db: AsyncSession,
    extracted: ExtractedContactData,
    tenant_id: str = "default",
) -> Contact | None:
    """
    Find an existing contact that matches the extracted data.
    Checks: exact email, exact phone, or exact name + company match.
    """
    email = extracted.email.lower().strip() if extracted.email else None
    phone = normalize_phone(extracted.phone) if extracted.phone else None
    name = extracted.name.strip().lower() if extracted.name else None
    company = extracted.company.strip().lower() if extracted.company else None

    # First try email/phone match
    if email or phone:
        duplicate = await contact_queries.find_duplicate_contact(
            db,
            email=email,
            phone=phone,
            tenant_id=tenant_id,
        )
        if duplicate:
            logger.info(f"Found duplicate by email/phone: {duplicate.id} ({duplicate.name})")
            return duplicate

    # Then try name + company match
    if name:
        contacts = await contact_queries.search_contacts_by_name(db, name, tenant_id, limit=10)
        for contact in contacts:
            contact_name = contact.name.strip().lower() if contact.name else ""
            contact_company = contact.company.strip().lower() if contact.company else ""

            # Exact name match
            if contact_name == name:
                # If both have company, they must match
                if company and contact_company:
                    if company == contact_company:
                        logger.info(f"Found duplicate by name+company: {contact.id}")
                        return contact
                # If no company info, name match is enough
                elif not company and not contact_company:
                    logger.info(f"Found duplicate by name: {contact.id}")
                    return contact
                # If only one has company, still consider it a match
                elif not company or not contact_company:
                    logger.info(f"Found duplicate by name (partial company): {contact.id}")
                    return contact

    logger.info("No duplicate found")
    return None


async def merge_or_create(
    db: AsyncSession,
    extracted: ExtractedContactData,
    tenant_id: str = "default",
) -> tuple[Contact, bool]:
    """
    Find duplicate and merge, or create new contact.
    Returns (contact, is_new) tuple.
    """
    duplicate = await find_duplicate(db, extracted, tenant_id)

    if duplicate:
        # Update existing contact with new info
        updates = {}

        if extracted.name and not duplicate.name:
            updates["name"] = extracted.name
        if extracted.email and not duplicate.email:
            updates["email"] = extracted.email.lower().strip()
        if extracted.phone and not duplicate.phone:
            updates["phone"] = normalize_phone(extracted.phone)
        if extracted.company and not duplicate.company:
            updates["company"] = extracted.company
        if extracted.role and not duplicate.role:
            updates["role"] = extracted.role
        if extracted.category and not duplicate.category:
            updates["category"] = extracted.category

        # Append context if new
        if extracted.context:
            existing_context = duplicate.context or ""
            if extracted.context not in existing_context:
                updates["context"] = f"{existing_context}\n{extracted.context}".strip()

        if updates:
            duplicate = await contact_queries.update_contact(db, duplicate.id, **updates)
            logger.info(f"Updated existing contact {duplicate.id} with new fields")

        return duplicate, False

    else:
        # Create new contact
        contact = await contact_queries.create_contact(
            db,
            name=extracted.name or "Unknown",
            email=extracted.email.lower().strip() if extracted.email else None,
            phone=normalize_phone(extracted.phone) if extracted.phone else None,
            company=extracted.company,
            role=extracted.role,
            category=extracted.category,
            context=extracted.context,
            tenant_id=tenant_id,
        )
        logger.info(f"Created new contact: {contact.id}")
        return contact, True
