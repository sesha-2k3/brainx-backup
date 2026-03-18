# Database: Tenant-aware async sessions
#
# How it works:
#   1. TenantMixin marks which models are tenant-scoped
#   2. TenantSession carries a tenant_id
#   3. do_orm_execute event auto-appends WHERE tenant_id = :id to every SELECT
#   4. before_flush event auto-sets tenant_id on every new object
#
# Developers can't forget the filter — it's enforced at the infrastructure level.
# Query functions no longer need to accept or filter by tenant_id.

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, ORMExecuteState, Session

from src.config import get_settings

settings = get_settings()

# Engine (dialect-aware: skip pool args for SQLite)

_engine_kwargs: dict = {
    "echo": settings.is_development,
}

if not settings.database_url.startswith("sqlite"):
    _engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_size": 5,
            "max_overflow": 10,
        }
    )

engine = create_async_engine(settings.database_url, **_engine_kwargs)


# Base and TenantMixin


class Base(DeclarativeBase):
    pass


class TenantMixin:
    """
    Marker mixin for models that belong to a tenant.

    Any model with a `tenant_id` column should inherit from this
    so the auto-filter and auto-stamp logic knows to act on it.

    Usage in models.py:
        class Contact(TenantMixin, Base):
            __tablename__ = "contacts"
            tenant_id: Mapped[str] = mapped_column(...)
            ...
    """

    pass


# TenantSession: sync session carries the tenant_id, async session wraps it


class TenantSyncSession(Session):
    """Sync session that carries tenant_id. Events attach here."""

    tenant_id: str = "default"


class TenantSession(AsyncSession):
    """
    Async session that passes tenant_id down to the sync session.
    All event logic lives on TenantSyncSession.
    """

    def __init__(self, tenant_id: str, **kwargs):
        kwargs.setdefault("sync_session_class", TenantSyncSession)
        super().__init__(**kwargs)
        self.sync_session.tenant_id = tenant_id


# Event: auto-filter SELECTs


@event.listens_for(TenantSyncSession, "do_orm_execute")
def _add_tenant_filter(execute_state: ORMExecuteState):
    if not execute_state.is_select:
        return

    tenant_id = execute_state.session.tenant_id

    # column_descriptions is a list of dicts with "entity" key
    tenant_entities = [
        col["entity"]
        for col in execute_state.statement.column_descriptions
        if col.get("entity") is not None
        and isinstance(col["entity"], type)
        and issubclass(col["entity"], TenantMixin)
    ]

    if not tenant_entities:
        return

    execute_state.statement = execute_state.statement.options(
        *[_tenant_criteria(entity, tenant_id) for entity in tenant_entities]
    )


def _tenant_criteria(model_class, tenant_id: str):
    """Build a with_loader_criteria option for a tenant-scoped model."""
    from sqlalchemy.orm import with_loader_criteria

    return with_loader_criteria(
        model_class,
        lambda cls: cls.tenant_id == tenant_id,
        include_aliases=True,
    )


# Event: auto-stamp INSERTs


@event.listens_for(TenantSyncSession, "before_flush")
def _stamp_tenant_id(session, flush_context, instances):
    tenant_id = session.tenant_id

    for obj in session.new:
        if isinstance(obj, TenantMixin) and not getattr(obj, "tenant_id", None):
            obj.tenant_id = tenant_id


# Session factories


def _tenant_session_factory(tenant_id: str) -> async_sessionmaker:
    """Create a session factory bound to a specific tenant."""
    return async_sessionmaker(
        engine,
        class_=TenantSession,
        expire_on_commit=False,
        autoflush=False,
        tenant_id=tenant_id,  # Passed to TenantSession.__init__
    )


# Keep the plain session factory for non-tenant operations (migrations, health checks)


async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# Dependency injection


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Tenant-scoped database session for API endpoints.

    Reads tenant_id from settings. Every query automatically
    filters by this tenant. Every new object gets it stamped.
    """
    tenant_id = settings.tenant_id
    factory = _tenant_session_factory(tenant_id)

    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_unscoped() -> AsyncGenerator[AsyncSession, None]:
    """
    Unscoped session for operations that don't need tenant isolation
    (health checks, migrations, admin queries).
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Lifecycle


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()
