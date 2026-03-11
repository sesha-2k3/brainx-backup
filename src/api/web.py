# API: Web interface endpoints

import logging
import os
import tempfile
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from src.config import get_settings
from src.db import get_db
from src.db.models import Contact, Task, TaskStatus
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

class ProposalConfirmData(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    category: Optional[str] = None
    context: Optional[str] = None
    interaction_summary: Optional[str] = None
    tasks: list[dict] = []  # Array of {title, due_date}

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

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    contact_id: Optional[str] = None

class InteractionCreate(BaseModel):
    contact_id: str
    interaction_type: str = "note"
    summary: str
    occurred_at: Optional[str] = None

class InteractionUpdate(BaseModel):
    interaction_type: Optional[str] = None
    summary: Optional[str] = None
    occurred_at: Optional[str] = None

class ContactCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    category: Optional[str] = None
    context: Optional[str] = None
    notes: Optional[str] = None

@router.post("/input/text")
async def process_text_input(
    text: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    """Process text input and extract contact information."""
    # Extract contact data
    extracted = await extract_contact_data(text)
    
    if not extracted or not extracted.name:
        raise HTTPException(status_code=400, detail="Could not extract contact information")
    
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
    
    # Convert tasks to list of dicts
    tasks = []
    if extracted.tasks:
        tasks = [{"title": t.title, "due_date": t.due_date} for t in extracted.tasks]
    # Backward compatibility: if no tasks array but has follow_up
    elif extracted.follow_up:
        tasks = [{"title": extracted.follow_up, "due_date": extracted.follow_up_date}]
    
    return {
        "proposal_id": proposal.id,
        "extracted": {
            "name": extracted.name,
            "email": extracted.email,
            "phone": extracted.phone,
            "company": extracted.company,
            "role": extracted.role,
            "category": extracted.category,
            "context": extracted.context,
            "interaction_summary": extracted.interaction_summary,
            "tasks": tasks,
        },
        "is_duplicate": duplicate is not None,
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
    data: ProposalConfirmData,
    db: AsyncSession = Depends(get_db),
):
    """Confirm a proposal and create/update the contact."""
    from src.utils.dates import parse_relative_date
    
    proposal = await proposal_queries.get_proposal_by_id(db, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Create or update contact
    extracted = ExtractedContactData(**proposal.extracted_data)
    duplicate = await find_duplicate(db, extracted, settings.tenant_id)
    
    if duplicate:
        contact = duplicate
        # Update with new info
        updates = {}
        if data.email and not contact.email:
            updates["email"] = data.email
        if data.phone and not contact.phone:
            updates["phone"] = data.phone
        if data.company and not contact.company:
            updates["company"] = data.company
        if data.role and not contact.role:
            updates["role"] = data.role
        if updates:
            await contact_queries.update_contact(db, contact.id, **updates)
    else:
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
    
    # Create interaction
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
    
    # Create ALL tasks
    created_tasks = []
    for task_data in data.tasks:
        if task_data.get("title"):
            due_date = None
            if task_data.get("due_date"):
                due_date = parse_relative_date(task_data["due_date"])
            
            task = await task_queries.create_task(
                db,
                title=task_data["title"],
                contact_id=contact.id,
                due_date=due_date,
                tenant_id=settings.tenant_id,
            )
            created_tasks.append(task)
    
    # Mark proposal as confirmed
    await proposal_queries.confirm_proposal(
        db,
        proposal_id,
        contact_id=contact.id,
        interaction_id=interaction.id if interaction else None,
    )
    
    return {
        "success": True,
        "contact_id": contact.id,
        "contact_name": contact.name,
        "tasks_created": len(created_tasks),
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

async def list_pending_tasks_with_contacts(
    db: AsyncSession,
    tenant_id: str = "default",
    limit: int = 50,
) -> list[Task]:
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.contact))  # Eager load contacts
        .where(
            Task.tenant_id == tenant_id,
            Task.status == TaskStatus.PENDING,
        )
        .order_by(Task.due_date.asc().nullslast())
        .limit(limit)
    )
    return list(result.scalars().all())

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
        result.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "status": task.status,
            "contact_id": task.contact_id,
            "contact_name": task.contact.name if task.contact else None,
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

@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a task."""
    from src.utils.dates import parse_relative_date
    
    task = await task_queries.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    updates = {}
    if task_data.title is not None:
        updates["title"] = task_data.title
    if task_data.description is not None:
        updates["description"] = task_data.description
    if task_data.due_date is not None:
        if task_data.due_date == "":
            updates["due_date"] = None
        else:
            updates["due_date"] = parse_relative_date(task_data.due_date)
    if task_data.contact_id is not None:
        if task_data.contact_id == "":
            updates["contact_id"] = None
        else:
            updates["contact_id"] = task_data.contact_id
    
    if updates:
        await task_queries.update_task(db, task_id, **updates)
    
    return {"success": True}

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
    """Semantic search across contacts using LLM."""
    from src.services.semantic_search import semantic_search_with_explanation
    from sqlalchemy.orm import selectinload
    
    # Get all contacts WITH their interactions
    result = await db.execute(
        select(Contact)
        .options(selectinload(Contact.interactions))
        .where(Contact.tenant_id == settings.tenant_id)
        .order_by(Contact.created_at.desc())
        .limit(100)
    )
    all_contacts = list(result.scalars().all())
    
    # Convert to dicts for LLM - include interactions!
    contacts_data = [
        {
            "id": c.id,
            "name": c.name,
            "company": c.company,
            "role": c.role,
            "category": c.category,
            "notes": c.notes,
            "context": c.context,
            "interactions": "; ".join([i.summary for i in c.interactions]) if c.interactions else None,
        }
        for c in all_contacts
    ]
    
    # Semantic search using LLM
    search_result = await semantic_search_with_explanation(q, contacts_data)
    
    # Handle both dict and list returns
    if isinstance(search_result, dict):
        matches = search_result.get("matches", [])
        explanation = search_result.get("explanation", "")
    else:
        matches = search_result if search_result else []
        explanation = ""
    
    return {
        "query": q,
        "intent": "semantic_search",
        "explanation": explanation,
        "contacts": matches,
        "interactions": [],
        "tasks": [],
    }

@router.patch("/interactions/{interaction_id}")
async def update_interaction(
    interaction_id: str,
    data: InteractionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an interaction."""
    interaction = await interaction_queries.get_interaction_by_id(db, interaction_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    
    updates = {}
    if data.interaction_type is not None:
        updates["interaction_type"] = data.interaction_type
    if data.summary is not None:
        updates["summary"] = data.summary
    if data.occurred_at is not None:
        updates["occurred_at"] = datetime.fromisoformat(data.occurred_at)
    
    if updates:
        await interaction_queries.update_interaction(db, interaction_id, **updates)
    
    return {"success": True}


@router.delete("/interactions/{interaction_id}")
async def delete_interaction(
    interaction_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete an interaction."""
    interaction = await interaction_queries.get_interaction_by_id(db, interaction_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    
    await interaction_queries.delete_interaction(db, interaction_id)
    return {"success": True}


@router.post("/interactions")
async def create_interaction(
    data: InteractionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new interaction."""
    # Verify contact exists
    contact = await contact_queries.get_contact_by_id(db, data.contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    occurred_at = datetime.utcnow()
    if data.occurred_at:
        occurred_at = datetime.fromisoformat(data.occurred_at)
    
    interaction = await interaction_queries.create_interaction(
        db,
        contact_id=data.contact_id,
        interaction_type=data.interaction_type,
        summary=data.summary,
        occurred_at=occurred_at,
        tenant_id=settings.tenant_id,
    )
    
    return {
        "success": True,
        "interaction": {
            "id": interaction.id,
            "interaction_type": interaction.interaction_type,
            "summary": interaction.summary,
            "occurred_at": interaction.occurred_at.isoformat(),
        }
    }

@router.post("/contacts")
async def create_contact_direct(
    data: ContactCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a contact directly (without extraction)."""
    contact = await contact_queries.create_contact(
        db,
        name=data.name,
        email=data.email,
        phone=data.phone,
        company=data.company,
        role=data.role,
        category=data.category,
        context=data.context,
        notes=data.notes,
        tenant_id=settings.tenant_id,
    )
    
    return {
        "success": True,
        "contact": {
            "id": contact.id,
            "name": contact.name,
        }
    }