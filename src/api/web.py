# API: Web interface endpoints

import logging
import os
import tempfile
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.config import get_settings
from src.db import get_db
from src.db.queries import contacts as contact_queries
from src.db.queries import interactions as interaction_queries
from src.db.queries import proposals as proposal_queries
from src.db.queries import search as search_queries
from src.db.queries import tasks as task_queries
from src.schemas.contacts import ExtractedContactData
from src.services.dedup import find_duplicate
from src.services.extraction import extract_contact_data
from src.services.ocr import process_business_card_bytes
from src.services.query_parser import parse_query
from src.services.transcription import transcribe_audio_bytes
from src.utils.dates import parse_relative_date

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api", tags=["web"])


# Request/Response models
class TextInput(BaseModel):
    text: str


class ConfirmInput(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    category: Optional[str] = None
    context: Optional[str] = None
    interaction_summary: Optional[str] = None
    follow_up: Optional[str] = None
    follow_up_date: Optional[str] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    context: Optional[str] = None
    reminder_frequency: Optional[str] = None # For reminders.


class TaskCreate(BaseModel):
    title: str
    contact_id: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None


# Input processing endpoints
@router.post("/input/text")
async def process_text_input(
    data: TextInput,
    db: AsyncSession = Depends(get_db),
):
    """Process text input and extract contact data."""
    if not data.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")
    
    # Extract contact data using LLM
    extracted = await extract_contact_data(data.text)
    
    if not extracted.name:
        raise HTTPException(status_code=400, detail="Could not extract contact name from text")
    
    # Check for duplicate
    duplicate = await find_duplicate(db, extracted, settings.tenant_id)
    
    # Create proposal
    proposal = await proposal_queries.create_proposal(
        db,
        source_type="text",
        whatsapp_user_id="web",
        extracted_data=extracted.model_dump(),
        tenant_id=settings.tenant_id,
    )
    
    return {
        "id": proposal.id,
        "extracted_data": extracted.model_dump(),
        "duplicate_contact": {
            "id": duplicate.id,
            "name": duplicate.name,
        } if duplicate else None,
    }


@router.post("/input/file")
async def process_file_input(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Process uploaded file (voice or image) and extract contact data."""
    content = await file.read()
    content_type = file.content_type or ""
    
    extracted = None
    confidence = None
    source_type = "file"
    
    if content_type.startswith("audio/"):
        # Transcribe audio
        result = await transcribe_audio_bytes(content, file.filename or "audio.ogg")
        extracted = await extract_contact_data(result["text"])
        source_type = "voice"
    
    elif content_type.startswith("image/"):
        # OCR for business card
        result = await process_business_card_bytes(content)
        extracted = result["extracted"]
        confidence = result["confidence"]
        source_type = "business_card"
    
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use audio or image files.")
    
    if not extracted or not extracted.name:
        raise HTTPException(status_code=400, detail="Could not extract contact data from file")
    
    # Check for duplicate
    duplicate = await find_duplicate(db, extracted, settings.tenant_id)
    
    # Create proposal
    proposal = await proposal_queries.create_proposal(
        db,
        source_type=source_type,
        whatsapp_user_id="web",
        extracted_data=extracted.model_dump(),
        confidence_score=confidence,
        tenant_id=settings.tenant_id,
    )
    
    return {
        "id": proposal.id,
        "extracted_data": extracted.model_dump(),
        "confidence_score": confidence,
        "duplicate_contact": {
            "id": duplicate.id,
            "name": duplicate.name,
        } if duplicate else None,
    }


# Proposal endpoints
@router.get("/proposals/{proposal_id}")
async def get_proposal(
    proposal_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a proposal by ID."""
    proposal = await proposal_queries.get_proposal_by_id(db, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return {
        "id": proposal.id,
        "extracted_data": proposal.extracted_data,
        "confidence_score": proposal.confidence_score,
        "status": proposal.status,
    }


@router.post("/proposals/{proposal_id}/confirm")
async def confirm_proposal(
    proposal_id: str,
    data: ConfirmInput,
    db: AsyncSession = Depends(get_db),
):
    """Confirm a proposal and create/update contact."""
    proposal = await proposal_queries.get_proposal_by_id(db, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    extracted = ExtractedContactData(**data.model_dump())
    
    # Check for duplicate
    duplicate = await find_duplicate(db, extracted, settings.tenant_id)
    
    if duplicate:
        # Update existing contact
        updates = {}
        if data.email and not duplicate.email:
            updates["email"] = data.email
        if data.phone and not duplicate.phone:
            updates["phone"] = data.phone
        if data.company and not duplicate.company:
            updates["company"] = data.company
        if data.role and not duplicate.role:
            updates["role"] = data.role
        if data.category and not duplicate.category:
            updates["category"] = data.category
        if data.context:
            existing = duplicate.context or ""
            if data.context not in existing:
                updates["context"] = f"{existing}\n{data.context}".strip()
        
        if updates:
            await contact_queries.update_contact(db, duplicate.id, **updates)
        
        contact = duplicate
    else:
        # Create new contact
        contact = await contact_queries.create_contact(
            db,
            name=data.name,
            email=data.email,
            phone=data.phone,
            company=data.company,
            role=data.role,
            category=data.category,
            context=data.context,
            tenant_id=settings.tenant_id,
        )
    
    # Create interaction if summary provided
    interaction = None
    if data.interaction_summary:
        interaction = await interaction_queries.create_interaction(
            db,
            contact_id=contact.id,
            interaction_type="note",
            summary=data.interaction_summary,
            occurred_at=datetime.utcnow(),
            tenant_id=settings.tenant_id,
        )
    
    # Create task if follow-up provided
    if data.follow_up:
        due_date = None
        if data.follow_up_date:
            due_date = parse_relative_date(data.follow_up_date)
        
        await task_queries.create_task(
            db,
            title=data.follow_up,
            contact_id=contact.id,
            due_date=due_date,
            tenant_id=settings.tenant_id,
        )
    
    # Mark proposal confirmed
    await proposal_queries.confirm_proposal(
        db,
        proposal.id,
        contact_id=contact.id,
        interaction_id=interaction.id if interaction else None,
    )
    
    return {
        "success": True,
        "contact": {
            "id": contact.id,
            "name": contact.name,
            "company": contact.company,
        },
    }


@router.delete("/proposals/{proposal_id}")
async def reject_proposal(
    proposal_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Reject/cancel a proposal."""
    proposal = await proposal_queries.get_proposal_by_id(db, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    await proposal_queries.reject_proposal(db, proposal_id)
    return {"success": True}


# Contact endpoints
@router.get("/contacts")
async def list_contacts(
    category: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List contacts with optional category filter."""
    contacts = await contact_queries.list_contacts(
        db,
        tenant_id=settings.tenant_id,
        category=category,
        limit=limit,
        offset=offset,
    )
    
    return {
        "contacts": [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "company": c.company,
                "role": c.role,
                "category": c.category,
                "reminder_frequency": c.reminder_frequency,
                "next_reminder_at": c.next_reminder_at.isoformat() if c.next_reminder_at else None,
                "last_contacted_at": c.last_contacted_at.isoformat() if c.last_contacted_at else None,
            }
            for c in contacts
        ]
    }

@router.get("/contacts/due-reminders")
async def get_due_reminders(
    db: AsyncSession = Depends(get_db),
):
    """Get contacts that are due for a catch-up."""
    contacts = await contact_queries.get_contacts_due_for_reminder(db, settings.tenant_id)
    
    return {
        "contacts": [
            {
                "id": c.id,
                "name": c.name,
                "company": c.company,
                "reminder_frequency": c.reminder_frequency,
                "next_reminder_at": c.next_reminder_at.isoformat() if c.next_reminder_at else None,
                "last_contacted_at": c.last_contacted_at.isoformat() if c.last_contacted_at else None,
            }
            for c in contacts
        ]
    }

@router.get("/contacts/{contact_id}")
async def get_contact(
    contact_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a contact with their interactions."""
    result = await search_queries.get_contact_with_interactions(db, contact_id)
    if not result:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    contact = result["contact"]
    interactions = result["interactions"]
    
    return {
        "contact": {
            "id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "phone": contact.phone,
            "company": contact.company,
            "role": contact.role,
            "category": contact.category,
            "notes": contact.notes,
            "context": contact.context,
            "created_at": contact.created_at.isoformat(),
            "updated_at": contact.updated_at.isoformat(),
        },
        "interactions": [
            {
                "id": i.id,
                "interaction_type": i.interaction_type,
                "summary": i.summary,
                "occurred_at": i.occurred_at.isoformat(),
            }
            for i in interactions
        ],
    }


@router.patch("/contacts/{contact_id}")
async def update_contact(
    contact_id: str,
    data: ContactUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a contact."""
    contact = await contact_queries.get_contact_by_id(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if updates:
        contact = await contact_queries.update_contact(db, contact_id, **updates)
    
    return {
        "contact": {
            "id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "phone": contact.phone,
            "company": contact.company,
            "role": contact.role,
            "category": contact.category,
            "notes": contact.notes,
            "context": contact.context,
        }
    }


@router.delete("/contacts/{contact_id}")
async def delete_contact(
    contact_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a contact and all related data."""
    contact = await contact_queries.get_contact_by_id(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # 1. Clear proposal references to interactions (set to NULL)
    await db.execute(
        text("UPDATE proposals SET interaction_id = NULL WHERE contact_id = :contact_id"),
        {"contact_id": contact_id}
    )
    
    # 2. Clear proposal references to contact
    await db.execute(
        text("UPDATE proposals SET contact_id = NULL WHERE contact_id = :contact_id"),
        {"contact_id": contact_id}
    )
    
    # 3. Delete related tasks
    await db.execute(
        text("DELETE FROM tasks WHERE contact_id = :contact_id"),
        {"contact_id": contact_id}
    )
    
    # 4. Delete related artifacts
    await db.execute(
        text("DELETE FROM artifacts WHERE contact_id = :contact_id"),
        {"contact_id": contact_id}
    )
    
    # 5. Delete related interactions
    await db.execute(
        text("DELETE FROM interactions WHERE contact_id = :contact_id"),
        {"contact_id": contact_id}
    )
    
    # 6. Now delete the contact
    await db.delete(contact)
    await db.flush()
    
    return {"success": True}

@router.post("/contacts/{contact_id}/set-reminder")
async def set_contact_reminder(
    contact_id: str,
    frequency: str = Query(..., regex="^(weekly|every_3_days|every_2_weeks|monthly|none)$"),
    db: AsyncSession = Depends(get_db),
):
    """Set stay-in-touch reminder frequency for a contact."""
    contact = await contact_queries.get_contact_by_id(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    if frequency == "none":
        contact.reminder_frequency = None
        contact.next_reminder_at = None
    else:
        contact.reminder_frequency = frequency
        contact.next_reminder_at = contact_queries.calculate_next_reminder(frequency)
    
    await db.flush()
    
    return {
        "success": True,
        "contact_id": contact_id,
        "reminder_frequency": contact.reminder_frequency,
        "next_reminder_at": contact.next_reminder_at.isoformat() if contact.next_reminder_at else None,
    }

@router.post("/contacts/{contact_id}/mark-contacted")
async def mark_contact_contacted(
    contact_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Mark a contact as contacted and reset their reminder."""
    contact = await contact_queries.get_contact_by_id(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    contact.last_contacted_at = datetime.utcnow()
    
    if contact.reminder_frequency:
        contact.next_reminder_at = contact_queries.calculate_next_reminder(
            contact.reminder_frequency, 
            contact.last_contacted_at
        )
    
    await db.flush()
    
    return {"success": True}


# Task endpoints
@router.get("/tasks")
async def list_tasks(
    include_completed: bool = False,
    contact_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List tasks."""
    if contact_id:
        tasks = await task_queries.list_tasks_for_contact(
            db, contact_id, include_completed=include_completed
        )
    else:
        tasks = await task_queries.list_pending_tasks(
            db, tenant_id=settings.tenant_id, limit=100
        )
    
    # Get contact names
    result = []
    for task in tasks:
        contact_name = None
        if task.contact_id:
            contact = await contact_queries.get_contact_by_id(db, task.contact_id)
            if contact:
                contact_name = contact.name
        
        result.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "status": task.status,
            "contact_id": task.contact_id,
            "contact_name": contact_name,
        })
    
    return {"tasks": result}


@router.post("/tasks")
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new task."""
    task = await task_queries.create_task(
        db,
        title=data.title,
        contact_id=data.contact_id,
        description=data.description,
        due_date=data.due_date,
        tenant_id=settings.tenant_id,
    )
    
    return {
        "task": {
            "id": task.id,
            "title": task.title,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "status": task.status,
        }
    }


@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Mark a task as completed."""
    task = await task_queries.complete_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"success": True}


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a task."""
    task = await task_queries.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await task_queries.cancel_task(db, task_id)
    return {"success": True}


# Search endpoint
@router.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """Natural language search across contacts, interactions, and tasks."""
    # Parse the query using LLM
    parsed = await parse_query(q)
    intent = parsed.get("intent", "fts_search")
    filters = parsed.get("filters", {})
    
    contacts = []
    interactions = []
    tasks = []
    
    if intent == "contact_lookup":
        name = filters.get("name", q)
        contacts = await contact_queries.search_contacts_by_name(
            db, name, settings.tenant_id
        )
    
    elif intent == "filtered_list":
        category = filters.get("category")
        since = None
        if "date_range" in filters and "start" in filters["date_range"]:
            try:
                since = datetime.fromisoformat(filters["date_range"]["start"])
            except:
                pass
        
        contacts = await search_queries.get_contacts_by_category(
            db, category, settings.tenant_id, since
        )
    
    elif intent == "task_query":
        due_by = filters.get("due_by")
        if due_by:
            try:
                due_date = datetime.fromisoformat(due_by)
                tasks = await task_queries.list_tasks_due_by(db, due_date, settings.tenant_id)
            except:
                tasks = await task_queries.list_pending_tasks(db, settings.tenant_id)
        else:
            tasks = await task_queries.list_pending_tasks(db, settings.tenant_id)
    
    elif intent == "interaction_search":
        company = filters.get("company")
        if company:
            interactions = await search_queries.get_interactions_by_company(
                db, company, settings.tenant_id
            )
        else:
            query_text = filters.get("query_text", q)
            interactions = await interaction_queries.search_interactions(
                db, query_text, settings.tenant_id
            )
    
    else:  # fts_search
        results = await search_queries.search_all(db, q, settings.tenant_id)
        contacts = results["contacts"]
        interactions = results["interactions"]
    
    # Format response
    return {
        "query": q,
        "intent": intent,
        "contacts": [
            {
                "id": c.id,
                "name": c.name,
                "company": c.company,
                "role": c.role,
                "category": c.category,
            }
            for c in contacts
        ],
        "interactions": [
            {
                "id": i.id,
                "contact_id": i.contact_id,
                "contact_name": (await contact_queries.get_contact_by_id(db, i.contact_id)).name if i.contact_id else None,
                "summary": i.summary,
                "occurred_at": i.occurred_at.isoformat(),
            }
            for i in interactions
        ],
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "contact_name": (await contact_queries.get_contact_by_id(db, t.contact_id)).name if t.contact_id else None,
            }
            for t in tasks
        ],
    }
