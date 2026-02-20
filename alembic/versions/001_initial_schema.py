"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pg_trgm extension for fuzzy search
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    
    # Contacts table
    op.create_table(
        'contacts',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, default='default'),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('company', sa.String(255), nullable=True),
        sa.Column('role', sa.String(255), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('tags', postgresql.JSONB, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('context', sa.Text, nullable=True),
        sa.Column('search_vector', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_contacts_tenant', 'contacts', ['tenant_id'])
    op.create_index('idx_contacts_email', 'contacts', ['email'])
    op.create_index('idx_contacts_phone', 'contacts', ['phone'])
    op.create_index(
        'idx_contacts_name_trgm', 'contacts', ['name'],
        postgresql_using='gin',
        postgresql_ops={'name': 'gin_trgm_ops'}
    )
    
    # Interactions table
    op.create_table(
        'interactions',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('contact_id', postgresql.UUID(as_uuid=False), 
                  sa.ForeignKey('contacts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', sa.String(50), nullable=False, default='default'),
        sa.Column('interaction_type', sa.String(50), nullable=False),
        sa.Column('summary', sa.Text, nullable=False),
        sa.Column('raw_transcript', sa.Text, nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('search_vector', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_interactions_contact', 'interactions', ['contact_id'])
    op.create_index('idx_interactions_tenant', 'interactions', ['tenant_id'])
    op.create_index('idx_interactions_occurred', 'interactions', ['occurred_at'])
    
    # Proposals table
    op.create_table(
        'proposals',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, default='default'),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_message_id', sa.String(255), nullable=True),
        sa.Column('whatsapp_user_id', sa.String(100), nullable=False),
        sa.Column('extra_data', postgresql.JSONB, nullable=False),
        sa.Column('confidence_score', sa.Float, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('contact_id', postgresql.UUID(as_uuid=False), 
                  sa.ForeignKey('contacts.id'), nullable=True),
        sa.Column('interaction_id', postgresql.UUID(as_uuid=False), 
                  sa.ForeignKey('interactions.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_proposals_tenant_status', 'proposals', ['tenant_id', 'status'])
    op.create_index('idx_proposals_user', 'proposals', ['whatsapp_user_id'])
    
    # Tasks table
    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('contact_id', postgresql.UUID(as_uuid=False), 
                  sa.ForeignKey('contacts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, default='default'),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reminder_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reminder_sent', sa.Boolean, default=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_tasks_tenant_status', 'tasks', ['tenant_id', 'status'])
    op.create_index('idx_tasks_due', 'tasks', ['due_date'])
    op.create_index('idx_tasks_reminder', 'tasks', ['reminder_at', 'reminder_sent'])
    
    # Artifacts table
    op.create_table(
        'artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, default='default'),
        sa.Column('proposal_id', postgresql.UUID(as_uuid=False), 
                  sa.ForeignKey('proposals.id'), nullable=True),
        sa.Column('contact_id', postgresql.UUID(as_uuid=False), 
                  sa.ForeignKey('contacts.id'), nullable=True),
        sa.Column('artifact_type', sa.String(50), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('file_size', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_artifacts_proposal', 'artifacts', ['proposal_id'])
    op.create_index('idx_artifacts_contact', 'artifacts', ['contact_id'])
    
    # Jobs table
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('attempts', sa.Integer, default=0),
        sa.Column('max_attempts', sa.Integer, default=3),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('scheduled_for', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'idx_jobs_pending', 'jobs', ['scheduled_for'],
        postgresql_where=sa.text("status = 'pending'")
    )


def downgrade() -> None:
    op.drop_table('jobs')
    op.drop_table('artifacts')
    op.drop_table('tasks')
    op.drop_table('proposals')
    op.drop_table('interactions')
    op.drop_table('contacts')
    op.execute('DROP EXTENSION IF EXISTS pg_trgm')
