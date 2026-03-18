# API: Web interface endpoints

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config import get_settings
from src.db import get_db
from src.db.models import Contact
from src.db.queries import contacts as contact_queries
from src.db.queries import interactions as interaction_queries
from src.db.queries import proposals as proposal_queries
from src.db.queries import search as search_queries
from src.db.queries import tasks as task_queries
from src.schemas.contacts import ContactCreate, ContactUpdate, ExtractedContactData
from src.schemas.interactions import InteractionCreate, InteractionUpdate
from src.schemas.tasks import TaskCreate, TaskUpdate
from src.services.dedup import find_duplicate
from src.services.extraction import extract_contact_data
from src.services.ocr import process_business_card_bytes
from src.services.transcription import transcribe_audio_bytes
from src.utils.dates import parse_relative_date

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api", tags=["web"])

# Security limits
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB


# ============================================================================
# Request/Response models (web.py-specific, not shared with other modules)
# ============================================================================


class TextInput(BaseModel):
    text: str


class ConfirmInput(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    category: str | None = None
    context: str | None = None
    interaction_summary: str | None = None
    follow_up: str | None = None
    follow_up_date: str | None = None


class ProposalConfirmData(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    category: str | None = None
    context: str | None = None
    interaction_summary: str | None = None
    tasks: list[dict] = []  # Array of {title, due_date}


# Input Processing Endpoints


@router.post("/input/text")
async def process_text_input(
    text: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    """Process text input and extract contact information."""
    extracted = await extract_contact_data(text)

    if not extracted or not extracted.name:
        raise HTTPException(status_code=400, detail="Could not extract contact information")

    duplicate = await find_duplicate(db, extracted)

    proposal = await proposal_queries.create_proposal(
        db,
        source_type="text",
        whatsapp_user_id="web",
        extracted_data=extracted.model_dump(),
    )

    # Convert tasks to list of dicts
    tasks = []
    if extracted.tasks:
        tasks = [{"title": t.title, "due_date": t.due_date} for t in extracted.tasks]
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
        }
        if duplicate
        else None,
    }


@router.post("/input/file")
async def process_file_input(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Process uploaded file (voice or image) and extract contact data."""
    # Check content length header for fast rejection
    if file.size and file.size > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    # Read in chunks to enforce limit even without Content-Length header
    chunks = []
    total_size = 0
    while chunk := await file.read(1024 * 1024):  # 1MB chunks
        total_size += len(chunk)
        if total_size > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="File too large (max 10MB)")
        chunks.append(chunk)

    content = b"".join(chunks)
    content_type = file.content_type or ""

    extracted = None
    confidence = None
    source_type = "file"

    if content_type.startswith("audio/"):
        result = await transcribe_audio_bytes(content, file.filename or "audio.ogg")
        extracted = await extract_contact_data(result["text"])
        source_type = "voice"

    elif content_type.startswith("image/"):
        result = await process_business_card_bytes(content)
        extracted = result["extracted"]
        confidence = result["confidence"]
        source_type = "business_card"

    else:
        raise HTTPException(
            status_code=400, detail="Unsupported file type. Use audio or image files."
        )

    if not extracted or not extracted.name:
        raise HTTPException(status_code=400, detail="Could not extract contact data from file")

    duplicate = await find_duplicate(db, extracted, settings.tenant_id)

    proposal = await proposal_queries.create_proposal(
        db,
        source_type=source_type,
        whatsapp_user_id="web",
        extracted_data=extracted.model_dump(),
        confidence_score=confidence,
    )

    return {
        "id": proposal.id,
        "extracted_data": extracted.model_dump(),
        "confidence_score": confidence,
        "duplicate_contact": {
            "id": duplicate.id,
            "name": duplicate.name,
        }
        if duplicate
        else None,
    }


# Proposal Endpoints


@router.get("/proposals/{proposal_id}")
async def get_proposal(
    proposal_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a proposal by ID."""
    proposal = await proposal_queries.get_proposal_by_id(db, proposal_id)
    if not proposal or proposal.tenant_id != settings.tenant_id:
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
    proposal = await proposal_queries.get_proposal_by_id(db, proposal_id)
    if not proposal or proposal.tenant_id != settings.tenant_id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    extracted = ExtractedContactData(**proposal.extracted_data)
    duplicate = await find_duplicate(db, extracted)

    if duplicate:
        contact = duplicate
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
        )

    interaction = None
    if data.interaction_summary:
        interaction = await interaction_queries.create_interaction(
            db,
            contact_id=contact.id,
            interaction_type="note",
            summary=data.interaction_summary,
            occurred_at=datetime.now(UTC),
        )

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
            )
            created_tasks.append(task)

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
    if not proposal or proposal.tenant_id != settings.tenant_id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    await proposal_queries.reject_proposal(db, proposal_id)
    return {"success": True}


# Contact Endpoints


@router.get("/contacts")
async def list_contacts(
    category: str | None = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List contacts with optional category filter."""
    contacts = await contact_queries.list_contacts(
        db,
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
                "last_contacted_at": c.last_contacted_at.isoformat()
                if c.last_contacted_at
                else None,
            }
            for c in contacts
        ]
    }


@router.get("/contacts/due-reminders")
async def get_due_reminders(
    db: AsyncSession = Depends(get_db),
):
    """Get contacts that are due for a catch-up."""
    contacts = await contact_queries.get_contacts_due_for_reminder(db)

    return {
        "contacts": [
            {
                "id": c.id,
                "name": c.name,
                "company": c.company,
                "reminder_frequency": c.reminder_frequency,
                "next_reminder_at": c.next_reminder_at.isoformat() if c.next_reminder_at else None,
                "last_contacted_at": c.last_contacted_at.isoformat()
                if c.last_contacted_at
                else None,
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
    )

    return {
        "success": True,
        "contact": {
            "id": contact.id,
            "name": contact.name,
        },
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

    # Clear proposal references
    await db.execute(
        text("UPDATE proposals SET interaction_id = NULL WHERE contact_id = :contact_id"),
        {"contact_id": contact_id},
    )
    await db.execute(
        text("UPDATE proposals SET contact_id = NULL WHERE contact_id = :contact_id"),
        {"contact_id": contact_id},
    )

    # Delete related records
    await db.execute(
        text("DELETE FROM tasks WHERE contact_id = :contact_id"), {"contact_id": contact_id}
    )
    await db.execute(
        text("DELETE FROM interactions WHERE contact_id = :contact_id"), {"contact_id": contact_id}
    )

    await db.delete(contact)
    await db.flush()

    return {"success": True}


@router.post("/contacts/{contact_id}/set-reminder")
async def set_contact_reminder(
    contact_id: str,
    frequency: str = Query(..., pattern="^(weekly|every_3_days|every_2_weeks|monthly|none)$"),
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
        "next_reminder_at": contact.next_reminder_at.isoformat()
        if contact.next_reminder_at
        else None,
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

    contact.last_contacted_at = datetime.now(UTC)

    if contact.reminder_frequency:
        contact.next_reminder_at = contact_queries.calculate_next_reminder(
            contact.reminder_frequency, contact.last_contacted_at
        )

    await db.flush()

    return {"success": True}


# Task Endpoints


@router.get("/tasks")
async def list_tasks(
    include_completed: bool = False,
    contact_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List tasks."""
    if contact_id:
        tasks = await task_queries.list_tasks_for_contact(
            db, contact_id, include_completed=include_completed
        )
    else:
        tasks = await task_queries.list_pending_tasks(db, limit=100)

    return {
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "status": task.status,
                "contact_id": task.contact_id,
                "contact_name": task.contact.name if task.contact else None,
            }
            for task in tasks
        ]
    }


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
    task = await task_queries.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await task_queries.complete_task(db, task_id)
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


# Interaction Endpoints


@router.post("/interactions")
async def create_interaction(
    data: InteractionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new interaction."""
    contact = await contact_queries.get_contact_by_id(db, data.contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    occurred_at = datetime.now(UTC)
    if data.occurred_at:
        occurred_at = datetime.fromisoformat(data.occurred_at)

    interaction = await interaction_queries.create_interaction(
        db,
        contact_id=data.contact_id,
        interaction_type=data.interaction_type,
        summary=data.summary,
        occurred_at=occurred_at,
    )

    return {
        "success": True,
        "interaction": {
            "id": interaction.id,
            "interaction_type": interaction.interaction_type,
            "summary": interaction.summary,
            "occurred_at": interaction.occurred_at.isoformat(),
        },
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


# Search Endpoint


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """Semantic search across contacts using LLM."""
    from src.services.semantic_search import semantic_search_with_explanation

    result = await db.execute(
        select(Contact)
        .options(selectinload(Contact.interactions))
        .where(Contact.tenant_id == settings.tenant_id)
        .order_by(Contact.created_at.desc())
        .limit(100)
    )
    all_contacts = list(result.scalars().all())

    contacts_data = [
        {
            "id": c.id,
            "name": c.name,
            "company": c.company,
            "role": c.role,
            "category": c.category,
            "notes": c.notes,
            "context": c.context,
            "interactions": "; ".join([i.summary for i in c.interactions])
            if c.interactions
            else None,
        }
        for c in all_contacts
    ]

    search_result = await semantic_search_with_explanation(q, contacts_data)

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
