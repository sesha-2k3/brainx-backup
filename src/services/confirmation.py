# Service: Confirmation card generation and user action handling

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import JobType
from src.db.queries import contacts as contact_queries
from src.db.queries import interactions as interaction_queries
from src.db.queries import jobs as job_queries
from src.db.queries import proposals as proposal_queries
from src.db.queries import tasks as task_queries
from src.schemas.contacts import ExtractedContactData
from src.schemas.proposals import ConfirmationCard
from src.services.dedup import find_duplicate
from src.utils.dates import parse_relative_date

logger = logging.getLogger(__name__)


def build_confirmation_card(
    proposal_id: str,
    extracted: ExtractedContactData,
    duplicate_name: Optional[str] = None,
) -> ConfirmationCard:
    """
    Build a confirmation card for user review.
    """
    fields = []
    
    if extracted.name:
        fields.append({"label": "Name", "value": extracted.name})
    if extracted.email:
        fields.append({"label": "Email", "value": extracted.email})
    if extracted.phone:
        fields.append({"label": "Phone", "value": extracted.phone})
    if extracted.company:
        fields.append({"label": "Company", "value": extracted.company})
    if extracted.role:
        fields.append({"label": "Role", "value": extracted.role})
    if extracted.category:
        fields.append({"label": "Category", "value": extracted.category})
    if extracted.interaction_summary:
        fields.append({"label": "Notes", "value": extracted.interaction_summary[:200]})
    if extracted.follow_up:
        fields.append({"label": "Follow-up", "value": extracted.follow_up})
    
    # Build title
    if duplicate_name:
        title = f"Update contact: {duplicate_name}"
    else:
        title = f"New contact: {extracted.name or 'Unknown'}"
    
    buttons = [
        {"id": f"confirm_{proposal_id}", "text": "Confirm"},
        {"id": f"edit_{proposal_id}", "text": "Edit"},
        {"id": f"reject_{proposal_id}", "text": "Cancel"},
    ]
    
    return ConfirmationCard(
        proposal_id=proposal_id,
        title=title,
        fields=fields,
        buttons=buttons,
    )


async def handle_user_action(
    db: AsyncSession,
    whatsapp_user_id: str,
    action_id: str,
) -> dict:
    """
    Handle a user action (confirm, edit, reject) on a proposal.
    Returns dict with result info.
    """
    logger.info(f"Handling action {action_id} from {whatsapp_user_id}")
    
    # Parse action ID
    parts = action_id.split("_", 1)
    if len(parts) != 2:
        return {"success": False, "message": "Invalid action format"}
    
    action, proposal_id = parts[0], parts[1]
    
    # Get the proposal
    proposal = await proposal_queries.get_proposal_by_id(db, proposal_id)
    if not proposal:
        return {"success": False, "message": "Proposal not found"}
    
    if proposal.whatsapp_user_id != whatsapp_user_id:
        return {"success": False, "message": "Unauthorized"}
    
    if action == "confirm":
        return await _handle_confirm(db, proposal)
    elif action == "edit":
        return await _handle_edit(db, proposal)
    elif action == "reject":
        return await _handle_reject(db, proposal)
    else:
        return {"success": False, "message": f"Unknown action: {action}"}


async def _handle_confirm(db: AsyncSession, proposal) -> dict:
    """
    Confirm a proposal - create/update contact and interaction.
    """
    extracted = ExtractedContactData(**proposal.extracted_data)
    
    # Find or create contact
    duplicate = await find_duplicate(db, extracted, proposal.tenant_id)
    
    if duplicate:
        contact = duplicate
        # Update with any new info
        updates = {}
        if extracted.email and not contact.email:
            updates["email"] = extracted.email
        if extracted.phone and not contact.phone:
            updates["phone"] = extracted.phone
        if extracted.company and not contact.company:
            updates["company"] = extracted.company
        if extracted.role and not contact.role:
            updates["role"] = extracted.role
        
        if updates:
            await contact_queries.update_contact(db, contact.id, **updates)
    else:
        contact = await contact_queries.create_contact(
            db,
            name=extracted.name or "Unknown",
            email=extracted.email,
            phone=extracted.phone,
            company=extracted.company,
            role=extracted.role,
            category=extracted.category,
            context=extracted.context,
            tenant_id=proposal.tenant_id,
        )
    
    # Create interaction
    interaction = None
    if extracted.interaction_summary:
        interaction = await interaction_queries.create_interaction(
            db,
            contact_id=contact.id,
            interaction_type="note",
            summary=extracted.interaction_summary,
            occurred_at=proposal.created_at,
            tenant_id=proposal.tenant_id,
        )
    
    # Create task if follow-up specified
    if extracted.follow_up:
        due_date = None
        if extracted.follow_up_date:
            due_date = parse_relative_date(extracted.follow_up_date)
        
        await task_queries.create_task(
            db,
            title=extracted.follow_up,
            contact_id=contact.id,
            due_date=due_date,
            tenant_id=proposal.tenant_id,
        )
    
    # Mark proposal confirmed
    await proposal_queries.confirm_proposal(
        db,
        proposal.id,
        contact_id=contact.id,
        interaction_id=interaction.id if interaction else None,
    )
    
    # Send confirmation message
    await job_queries.enqueue_job(
        db,
        job_type=JobType.SEND_MESSAGE,
        payload={
            "to": proposal.whatsapp_user_id,
            "text": f"Saved contact: {contact.name}" + (f" at {contact.company}" if contact.company else ""),
        },
    )
    
    return {
        "success": True,
        "message": "Contact saved",
        "proposal_id": proposal.id,
        "contact_id": contact.id,
    }


async def _handle_edit(db: AsyncSession, proposal) -> dict:
    """
    Handle edit request - for now, just acknowledge.
    Full edit flow would require multi-turn conversation.
    """
    # Mark as edited (user will need to re-submit)
    await proposal_queries.update_proposal_data(
        db,
        proposal.id,
        proposal.extracted_data,  # Keep same data for now
    )
    
    # Send edit instructions
    await job_queries.enqueue_job(
        db,
        job_type=JobType.SEND_MESSAGE,
        payload={
            "to": proposal.whatsapp_user_id,
            "text": "Please send a new voice note or message with the corrected information.",
        },
    )
    
    return {
        "success": True,
        "message": "Please resend with corrections",
        "proposal_id": proposal.id,
    }


async def _handle_reject(db: AsyncSession, proposal) -> dict:
    """
    Reject/cancel a proposal.
    """
    await proposal_queries.reject_proposal(db, proposal.id)
    
    await job_queries.enqueue_job(
        db,
        job_type=JobType.SEND_MESSAGE,
        payload={
            "to": proposal.whatsapp_user_id,
            "text": "Entry cancelled.",
        },
    )
    
    return {
        "success": True,
        "message": "Cancelled",
        "proposal_id": proposal.id,
    }
