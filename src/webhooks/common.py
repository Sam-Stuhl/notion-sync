from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from src.clients.canvas import CanvasClient  # noqa: F401 — registers "canvas" in SIS registry
from src.clients.notion import NotionClient
from src.clients.sis_client import build
from src.db.encryption import decrypt
from src.db.models import SyncRun
from src.db.repositories import (
    find_user_by_root_page_id,
    get_notion_integration,
    get_sis_integration,
    get_workspace_config,
)
from src.db.session import AsyncSessionLocal
from src.models import SyncContext
from src.template.config import TemplateSettings


class NotionWebhookSource(BaseModel):
    type: str
    automation_id: str
    action_id: str
    event_id: str
    user_id: str
    attempt: int


class NotionWebhookPage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    properties: dict = {}


class WebhookPayload(BaseModel):
    source: NotionWebhookSource
    data: NotionWebhookPage


_SOURCE_LABELS: dict[str, str] = {
    "automation": "Notion Automation",
    "user": "Notion",
    "api": "API",
}


def source_label(source_type: str) -> str:
    return _SOURCE_LABELS.get(source_type, source_type)


# A webhook is authorized purely by proving it targets a real tenant: the page
# id in the payload must resolve to a user. There is no shared secret (buttons
# can't carry a per-user one). Rate limiting bounds abuse of that open trigger.
_RATE_LIMIT_WINDOW = timedelta(seconds=10)


async def authorize_webhook(page_id: str, operation: str, *, rate_limit: bool = True) -> str:
    """Authorize a webhook by page ownership.

    Returns "ok" to proceed, or "skipped" if an identical sync for this tenant
    ran within the rate-limit window. Raises 404 if the page maps to no user
    (so we don't reveal whether a given page id is registered).
    """
    async with AsyncSessionLocal() as session:
        user = await find_user_by_root_page_id(session, page_id)
        if not user:
            raise HTTPException(status_code=404)
        if rate_limit:
            cutoff = datetime.now(timezone.utc) - _RATE_LIMIT_WINDOW
            recent = await session.execute(
                select(SyncRun.id)
                .where(SyncRun.user_id == user.id)
                .where(SyncRun.operation == operation)
                .where(SyncRun.started_at >= cutoff)
                .limit(1)
            )
            if recent.first():
                return "skipped"
    return "ok"


@asynccontextmanager
async def record_sync_run(page_id: str, operation: str, triggered_by: str = "notion"):
    run_id = None
    started = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        user = await find_user_by_root_page_id(session, page_id)
        if user:
            run = SyncRun(
                user_id=user.id,
                operation=operation,
                triggered_by=triggered_by,
                status="pending",
                started_at=started,
            )
            session.add(run)
            await session.commit()
            run_id = run.id

    collector: dict = {}
    try:
        yield collector
        if run_id:
            completed = datetime.now(timezone.utc)
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(SyncRun).where(SyncRun.id == run_id))
                run = result.scalar_one_or_none()
                if run:
                    run.status = "success"
                    run.completed_at = completed
                    run.duration_ms = int((completed - started).total_seconds() * 1000)
                    run.summary = collector.get("summary")
                    await session.commit()
    except Exception as e:
        if run_id:
            completed = datetime.now(timezone.utc)
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(SyncRun).where(SyncRun.id == run_id))
                run = result.scalar_one_or_none()
                if run:
                    run.status = "failed"
                    run.completed_at = completed
                    run.error_type = type(e).__name__
                    run.error_message = str(e)
                    run.summary = collector.get("summary")
                    await session.commit()
        raise


async def build_context(page_id: str) -> SyncContext:
    """Look up a user by their root page ID and return a fully assembled SyncContext.

    Raises:
        ValueError: if no user is found for the given page_id.
    """
    async with AsyncSessionLocal() as session:
        user = await find_user_by_root_page_id(session, page_id)
        if not user:
            raise ValueError(f"No user found for page_id: {page_id}")
        notion_integration = await get_notion_integration(session, user.id)
        sis_integration = await get_sis_integration(session, user.id)
        workspace_config = await get_workspace_config(session, user.id)

    notion = NotionClient(token=decrypt(notion_integration.access_token_encrypted))
    external = build(
        sis_integration.service,
        sis_integration.base_url,
        decrypt(sis_integration.access_token_encrypted),
    )
    return SyncContext(
        external=external,
        notion=notion,
        workspace=TemplateSettings(**workspace_config.discovered_ids),
    )
