from pydantic import BaseModel, ConfigDict

from src.clients.canvas import CanvasClient  # registers "canvas" in SIS registry
from src.clients.notion import NotionClient
from src.clients.sis_client import build
from src.db.encryption import decrypt
from src.db.repositories import find_user_by_root_page_id, get_notion_integration, get_sis_integration, get_workspace_config
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
