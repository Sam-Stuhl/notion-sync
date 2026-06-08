from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from src.config import settings
from src.handlers.common import WebhookPayload, build_context
from src.operations.courses import sync_courses
from src.operations.semesters import get_current_semester, reconcile_semester_status, update_view_filters

router = APIRouter()


async def _run_refresh(workspace_id: str) -> None:
    context = await build_context(workspace_id)

    current_semester_id = get_current_semester(context)
    if current_semester_id:
        reconcile_semester_status(context, current_semester_id)
        update_view_filters(context, current_semester_id)

    sync_courses(context, current_semester_id)


@router.post("/refresh")
async def refresh(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    authorization: str = Header(),
):
    if authorization != f"Bearer {settings.webhook_secret}":
        raise HTTPException(status_code=401)

    background_tasks.add_task(_run_refresh, payload.data.id)
    return {"status": "queued"}
