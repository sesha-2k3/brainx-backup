# Schemas: Pydantic models for tasks and reminders

from datetime import datetime

from pydantic import BaseModel

from src.db.models import TaskStatus


class TaskCreate(BaseModel):
    """Fields for creating a task."""

    title: str
    contact_id: str | None = None
    description: str | None = None
    due_date: datetime | None = None
    reminder_at: datetime | None = None


class TaskUpdate(BaseModel):
    """Fields for updating a task."""

    title: str | None = None
    description: str | None = None
    due_date: str | None = None  # str to support relative dates like "tomorrow"
    contact_id: str | None = None
    reminder_at: datetime | None = None


class TaskResponse(BaseModel):
    """Task response with all fields."""

    id: str
    tenant_id: str
    contact_id: str | None = None
    title: str
    description: str | None = None
    due_date: datetime | None = None
    reminder_at: datetime | None = None
    reminder_sent: bool
    status: TaskStatus
    created_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class TaskSummary(BaseModel):
    """Minimal task info for lists and digests."""

    id: str
    title: str
    due_date: datetime | None = None
    contact_name: str | None = None
    status: TaskStatus

    class Config:
        from_attributes = True
