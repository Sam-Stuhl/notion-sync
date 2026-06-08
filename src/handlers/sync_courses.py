from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from src.config import settings
from src.handlers.common import WebhookPayload, build_context
from src.operations.courses import sync_courses

router = APIRouter()


async def _run_sync_courses(workspace_id: str) -> None:
    context = await build_context(workspace_id)
    sync_courses(context)


@router.post("/sync-courses")
async def handle_sync_courses(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    authorization: str = Header(),
):
    if authorization != f"Bearer {settings.webhook_secret}":
        raise HTTPException(status_code=401)

    background_tasks.add_task(_run_sync_courses, payload.data.id)
    return {"status": "queued"}
