# Schemas: Pydantic models for tasks and reminders

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from src.db.models import TaskStatus


class TaskCreate(BaseModel):
    """Fields for creating a task."""
    title: str
    contact_id: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None


class TaskUpdate(BaseModel):
    """Fields for updating a task."""
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None  # str to support relative dates like "tomorrow"
    contact_id: Optional[str] = None
    reminder_at: Optional[datetime] = None


class TaskResponse(BaseModel):
    """Task response with all fields."""
    id: str
    tenant_id: str
    contact_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None
    reminder_sent: bool
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskSummary(BaseModel):
    """Minimal task info for lists and digests."""
    id: str
    title: str
    due_date: Optional[datetime] = None
    contact_name: Optional[str] = None
    status: TaskStatus

    class Config:
        from_attributes = True