# Models: SQLAlchemy ORM definitions for contacts, interactions, proposals, tasks, jobs

import enum
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base, TenantMixin


# Enums
class ProposalStatus(enum.StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    EDITED = "edited"
    REJECTED = "rejected"


class TaskStatus(enum.StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Models


class User(Base):
    """Application user — not tenant-scoped, IS the tenant source."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Contact(TenantMixin, Base):
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Classification
    category: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # investor, client, friend
    tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)

    # Notes and context
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)  # How we met, etc.

    # Stay in touch reminder
    reminder_frequency: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # weekly, every_3_days, every_2_weeks, monthly
    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_reminder_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_contacts_tenant", "tenant_id"),
        Index("idx_contacts_email", "email"),
        Index("idx_contacts_phone", "phone"),
        Index("idx_contacts_tenant_created", "tenant_id", "created_at"),
    )


class Interaction(TenantMixin, Base):
    __tablename__ = "interactions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    contact_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Content
    interaction_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # meeting, call, email, note
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    raw_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    contact: Mapped["Contact"] = relationship(back_populates="interactions")

    __table_args__ = (
        Index("idx_interactions_contact", "contact_id"),
        Index("idx_interactions_tenant", "tenant_id"),
        Index("idx_interactions_occurred", "occurred_at"),
        Index("idx_interactions_tenant_created", "tenant_id", "created_at"),
    )


class Proposal(TenantMixin, Base):
    __tablename__ = "proposals"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Source info
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # voice, text, image
    source_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp_user_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Extracted data
    extracted_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)

    # Status
    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus), default=ProposalStatus.PENDING
    )

    # After confirmation
    contact_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("contacts.id"), nullable=True
    )
    interaction_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("interactions.id"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_proposals_tenant_status", "tenant_id", "status"),
        Index("idx_proposals_user", "whatsapp_user_id"),
    )


class Task(TenantMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    contact_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Task details
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Scheduling
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Status
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.PENDING)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    contact: Mapped[Optional["Contact"]] = relationship(back_populates="tasks")

    __table_args__ = (
        Index("idx_tasks_tenant_status", "tenant_id", "status"),
        Index("idx_tasks_due", "due_date"),
        Index("idx_tasks_reminder", "reminder_at", "reminder_sent"),
    )
