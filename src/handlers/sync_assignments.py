from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from src.clients import notion_props
from src.config import settings
from src.handlers.common import WebhookPayload, build_context
from src.operations.assignments import sync_assignments, sync_assignments_for_course

router = APIRouter()


async def _run_sync_assignments(workspace_id: str) -> None:
    context = await build_context(workspace_id)
    sync_assignments(context)


async def _run_sync_assignments_for_course(workspace_id: str, course_id: str) -> None:
    context = await build_context(workspace_id)
    sync_assignments_for_course(context, course_id)


@router.post("/sync-assignments")
async def handle_sync_assignments(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    authorization: str = Header(),
):
    if authorization != f"Bearer {settings.webhook_secret}":
        raise HTTPException(status_code=401)

    background_tasks.add_task(_run_sync_assignments, payload.data.id)
    return {"status": "queued"}


@router.post("/sync-assignments-for-course")
async def handle_sync_assignments_for_course(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    authorization: str = Header(),
):
    if authorization != f"Bearer {settings.webhook_secret}":
        raise HTTPException(status_code=401)

    course_id = notion_props.read_rich_text(payload.data.properties, "External ID")
    background_tasks.add_task(_run_sync_assignments_for_course, payload.data.id, course_id)
    return {"status": "queued"}
