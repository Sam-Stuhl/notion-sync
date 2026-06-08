import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import SISIntegration, NotionIntegration, User, WorkspaceConfig


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
