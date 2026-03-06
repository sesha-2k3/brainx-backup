# Queries: Task CRUD and scheduling operations

from datetime import datetime
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Task, TaskStatus


async def create_task(
    db: AsyncSession,
    *,
    title: str,
    contact_id: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[datetime] = None,
    reminder_at: Optional[datetime] = None,
    tenant_id: str = "default",
) -> Task:
    task = Task(
        tenant_id=tenant_id,
        contact_id=contact_id,
        title=title,
        description=description,
        due_date=due_date,
        reminder_at=reminder_at,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    await db.flush()
    return task


async def get_task_by_id(db: AsyncSession, task_id: str) -> Optional[Task]:
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def complete_task(db: AsyncSession, task_id: str) -> Optional[Task]:
    task = await get_task_by_id(db, task_id)
    if not task:
        return None
    
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.utcnow()
    await db.flush()
    return task


async def cancel_task(db: AsyncSession, task_id: str) -> Optional[Task]:
    task = await get_task_by_id(db, task_id)
    if not task:
        return None
    
    task.status = TaskStatus.CANCELLED
    await db.flush()
    return task


async def list_pending_tasks(
    db: AsyncSession,
    tenant_id: str = "default",
    contact_id: Optional[str] = None,
    limit: int = 50,
) -> list[Task]:
    query = select(Task).where(
        Task.tenant_id == tenant_id,
        Task.status == TaskStatus.PENDING,
    )
    if contact_id:
        query = query.where(Task.contact_id == contact_id)
    query = query.order_by(Task.due_date.asc().nullslast(), Task.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def list_tasks_due_by(
    db: AsyncSession,
    due_by: datetime,
    tenant_id: str = "default",
) -> list[Task]:
    """Get all pending tasks due by a certain date."""
    result = await db.execute(
        select(Task)
        .where(
            Task.tenant_id == tenant_id,
            Task.status == TaskStatus.PENDING,
            Task.due_date <= due_by,
        )
        .order_by(Task.due_date.asc())
    )
    return list(result.scalars().all())


async def get_due_reminders(
    db: AsyncSession,
    as_of: datetime,
    tenant_id: str = "default",
) -> list[Task]:
    """Get tasks with unsent reminders that are now due."""
    result = await db.execute(
        select(Task)
        .where(
            Task.tenant_id == tenant_id,
            Task.status == TaskStatus.PENDING,
            Task.reminder_at <= as_of,
            Task.reminder_sent == False,
        )
        .order_by(Task.reminder_at.asc())
    )
    return list(result.scalars().all())


async def mark_reminder_sent(db: AsyncSession, task_id: str) -> Optional[Task]:
    task = await get_task_by_id(db, task_id)
    if not task:
        return None
    
    task.reminder_sent = True
    await db.flush()
    return task


async def list_tasks_for_contact(
    db: AsyncSession,
    contact_id: str,
    include_completed: bool = False,
    limit: int = 20,
) -> list[Task]:
    query = select(Task).where(Task.contact_id == contact_id)
    if not include_completed:
        query = query.where(Task.status == TaskStatus.PENDING)
    query = query.order_by(Task.due_date.asc().nullslast()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())

async def update_task(
    db: AsyncSession,
    task_id: str,
    **kwargs,
) -> Optional[Task]:
    """Update a task with given fields."""
    task = await db.get(Task, task_id)
    if not task:
        return None
    
    for key, value in kwargs.items():
        if hasattr(task, key):
            setattr(task, key, value)
    
    await db.flush()
    return task