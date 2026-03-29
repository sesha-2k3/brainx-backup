from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import (
    Base,
    TenantMixin,
    TenantSession,
    _tenant_session_factory,
    async_session_factory,
    close_db,
    engine,
    get_db,
    get_db_unscoped,
    init_db,
)
from src.db.models import (
    Contact,
    Interaction,
    Proposal,
    ProposalStatus,
    Task,
    TaskStatus,
)


def _get_current_user_dep():
    """Lazy import to avoid circular dependency: src.db → src.auth → src.db"""
    from src.auth.dependencies import get_current_user

    return Depends(get_current_user)


async def get_db_for_user(
    current_user=_get_current_user_dep(),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Tenant-scoped DB session isolated to the authenticated user.
    Each user's data is fully separate — their user ID is used as tenant_id.
    Drop-in replacement for get_db() on all protected routes.
    """
    factory = _tenant_session_factory(current_user.id)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


__all__ = [
    "Base",
    "Contact",
    "Interaction",
    "Proposal",
    "ProposalStatus",
    "Task",
    "TaskStatus",
    "TenantMixin",
    "TenantSession",
    "async_session_factory",
    "close_db",
    "engine",
    "get_db",
    "get_db_for_user",
    "get_db_unscoped",
    "init_db",
]
