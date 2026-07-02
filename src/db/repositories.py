import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import SISIntegration, NotionIntegration, SyncRun, User, WorkspaceConfig, Widget
from .encryption import encrypt


async def find_user_by_root_page_id(session: AsyncSession, page_id: str) -> User | None:
    normalized = page_id.replace("-", "")
    result = await session.execute(
        select(User)
        .join(WorkspaceConfig, WorkspaceConfig.user_id == User.id)
        .where(WorkspaceConfig.root_page_id == normalized)
        .where(User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def find_user_by_workspace_id(session: AsyncSession, workspace_id: str) -> User | None:
    result = await session.execute(
        select(User)
        .join(NotionIntegration, NotionIntegration.user_id == User.id)
        .where(NotionIntegration.workspace_id == workspace_id)
        .where(NotionIntegration.revoked_at.is_(None))
        .where(User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_notion_integration(session: AsyncSession, user_id: uuid.UUID) -> NotionIntegration | None:
    result = await session.execute(
        select(NotionIntegration)
        .where(NotionIntegration.user_id == user_id)
        .where(NotionIntegration.revoked_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_sis_integration(session: AsyncSession, user_id: uuid.UUID) -> SISIntegration | None:
    result = await session.execute(
        select(SISIntegration)
        .where(SISIntegration.user_id == user_id)
        .where(SISIntegration.is_active.is_(True))
        .where(SISIntegration.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_external_integration(session: AsyncSession, user_id: uuid.UUID, service: str) -> SISIntegration | None:
    result = await session.execute(
        select(SISIntegration)
        .where(SISIntegration.user_id == user_id)
        .where(SISIntegration.service == service)
        .where(SISIntegration.is_active.is_(True))
        .where(SISIntegration.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_workspace_config(session: AsyncSession, user_id: uuid.UUID) -> WorkspaceConfig | None:
    result = await session.execute(
        select(WorkspaceConfig)
        .where(WorkspaceConfig.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await session.execute(
        select(User)
        .where(User.id == user_id)
        .where(User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    email: str,
    display_name: str | None,
    avatar_url: str | None,
) -> User:
    user = User(email=email, display_name=display_name, avatar_url=avatar_url)
    session.add(user)
    await session.flush()
    return user


async def list_sis_integrations(
    session: AsyncSession, user_id: uuid.UUID, service: str | None = None
) -> list[SISIntegration]:
    q = (
        select(SISIntegration)
        .where(SISIntegration.user_id == user_id)
    )
    if service:
        q = q.where(SISIntegration.service == service)
    result = await session.execute(
        q
        .where(SISIntegration.is_active.is_(True))
        .where(SISIntegration.deleted_at.is_(None))
        .order_by(SISIntegration.created_at)
    )
    return list(result.scalars().all())


async def get_sis_integration_by_id(
    session: AsyncSession, integration_id: uuid.UUID, user_id: uuid.UUID
) -> SISIntegration | None:
    result = await session.execute(
        select(SISIntegration)
        .where(SISIntegration.id == integration_id)
        .where(SISIntegration.user_id == user_id)
        .where(SISIntegration.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create_sis_integration(
    session: AsyncSession,
    user_id: uuid.UUID,
    service: str,
    base_url: str,
    access_token: str,
    display_name: str | None = None,
) -> SISIntegration:
    integration = SISIntegration(
        user_id=user_id,
        service=service,
        base_url=base_url,
        access_token_encrypted=encrypt(access_token),
        display_name=display_name,
        is_active=True,
    )
    session.add(integration)
    await session.flush()
    return integration


async def update_sis_integration(
    session: AsyncSession,
    integration: SISIntegration,
    base_url: str,
    access_token: str | None,
    display_name: str | None,
) -> None:
    integration.base_url = base_url
    integration.display_name = display_name
    if access_token:
        integration.access_token_encrypted = encrypt(access_token)
    await session.flush()


async def soft_delete_sis_integration(
    session: AsyncSession, integration: SISIntegration
) -> None:
    from datetime import datetime, timezone
    integration.deleted_at = datetime.now(timezone.utc)
    integration.is_active = False
    await session.flush()


async def get_widget(session: AsyncSession, widget_id: uuid.UUID) -> Widget | None:
    result = await session.execute(
        select(Widget)
        .where(Widget.id == widget_id)
        .where(Widget.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def list_widgets(session: AsyncSession, user_id: uuid.UUID) -> list[Widget]:
    result = await session.execute(
        select(Widget)
        .where(Widget.user_id == user_id)
        .where(Widget.deleted_at.is_(None))
        .order_by(Widget.created_at)
    )
    return list(result.scalars().all())


async def create_widget(
    session: AsyncSession,
    user_id: uuid.UUID,
    type: str,
    config: dict,
    name: str | None = None,
) -> Widget:
    widget = Widget(user_id=user_id, type=type, config=config, name=name)
    session.add(widget)
    await session.flush()
    return widget


async def upsert_notion_integration(
    session: AsyncSession,
    user_id: uuid.UUID,
    workspace_id: str,
    workspace_name: str | None,
    workspace_icon: str | None,
    bot_id: str | None,
    access_token: str,
) -> NotionIntegration:
    result = await session.execute(
        select(NotionIntegration).where(NotionIntegration.workspace_id == workspace_id)
    )
    integration = result.scalar_one_or_none()
    encrypted = encrypt(access_token)
    if integration:
        integration.workspace_name = workspace_name
        integration.workspace_icon = workspace_icon
        integration.bot_id = bot_id
        integration.access_token_encrypted = encrypted
        integration.revoked_at = None
    else:
        integration = NotionIntegration(
            user_id=user_id,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            workspace_icon=workspace_icon,
            bot_id=bot_id,
            access_token_encrypted=encrypted,
        )
        session.add(integration)
    await session.flush()
    return integration


async def find_notion_integration_by_workspace_id(
    session: AsyncSession, workspace_id: str
) -> NotionIntegration | None:
    result = await session.execute(
        select(NotionIntegration).where(NotionIntegration.workspace_id == workspace_id)
    )
    return result.scalar_one_or_none()


async def list_recent_sync_runs(
    session: AsyncSession, user_id: uuid.UUID, limit: int = 10
) -> list[SyncRun]:
    result = await session.execute(
        select(SyncRun)
        .where(SyncRun.user_id == user_id)
        .order_by(SyncRun.started_at.desc().nullslast())
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_sync_run(
    session: AsyncSession,
    user_id: uuid.UUID,
    operation: str,
    triggered_by: str,
    sis_integration_id: uuid.UUID | None = None,
) -> SyncRun:
    from datetime import datetime, timezone
    run = SyncRun(
        user_id=user_id,
        sis_integration_id=sis_integration_id,
        operation=operation,
        triggered_by=triggered_by,
        status="pending",
        started_at=datetime.now(timezone.utc),
    )
    session.add(run)
    await session.flush()
    return run
