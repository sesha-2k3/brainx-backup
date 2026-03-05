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
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base


# Enums
class ProposalStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    EDITED = "edited"
    REJECTED = "rejected"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# Models
class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(50), nullable=False, default="default")
    
    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Classification
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # investor, client, friend
    tags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=list)
    
    # Notes and context
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # How we met, etc.

    # Stay in touch reminder
    reminder_frequency: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # weekly, every_3_days, every_2_weeks, monthly
    last_contacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_reminder_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Full-text search
    search_vector: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    interactions: Mapped[list["Interaction"]] = relationship(back_populates="contact", cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship(back_populates="contact", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_contacts_tenant", "tenant_id"),
        Index("idx_contacts_email", "email"),
        Index("idx_contacts_phone", "phone"),
    )


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    contact_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(50), nullable=False, default="default")
    
    # Content
    interaction_type: Mapped[str] = mapped_column(String(50), nullable=False)  # meeting, call, email, note
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    raw_transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadata
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Full-text search
    search_vector: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    contact: Mapped["Contact"] = relationship(back_populates="interactions")

    __table_args__ = (
        Index("idx_interactions_contact", "contact_id"),
        Index("idx_interactions_tenant", "tenant_id"),
        Index("idx_interactions_occurred", "occurred_at"),
    )


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(50), nullable=False, default="default")
    
    # Source info
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # voice, text, image
    source_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    whatsapp_user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Extracted data
    extracted_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Status
    status: Mapped[ProposalStatus] = mapped_column(Enum(ProposalStatus), default=ProposalStatus.PENDING)
    
    # After confirmation
    contact_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("contacts.id"), nullable=True)
    interaction_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("interactions.id"), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_proposals_tenant_status", "tenant_id", "status"),
        Index("idx_proposals_user", "whatsapp_user_id"),
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    contact_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(50), nullable=False, default="default")
    
    # Task details
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Scheduling
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Status
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.PENDING)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    contact: Mapped[Optional["Contact"]] = relationship(back_populates="tasks")

    __table_args__ = (
        Index("idx_tasks_tenant_status", "tenant_id", "status"),
        Index("idx_tasks_due", "due_date"),
        Index("idx_tasks_reminder", "reminder_at", "reminder_sent"),
    )
    