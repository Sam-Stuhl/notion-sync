from fastapi import APIRouter, BackgroundTasks

from src.webhooks.common import (
    WebhookPayload,
    authorize_webhook,
    build_context,
    record_sync_run,
    source_label,
)
from src.operations.courses import sync_courses_and_assignments
from src.operations.semesters import get_current_semester, reconcile_semester_status, update_view_filters

router = APIRouter()


async def _do_refresh(workspace_id: str) -> dict:
    context = await build_context(workspace_id)

    current_semester_id = get_current_semester(context)
    if current_semester_id:
        reconcile_semester_status(context, current_semester_id)
        update_view_filters(context, current_semester_id)

    return sync_courses_and_assignments(context, current_semester_id)


async def _run_refresh(workspace_id: str, triggered_by: str = "notion") -> None:
    async with record_sync_run(workspace_id, "refresh", triggered_by) as collector:
        collector["summary"] = await _do_refresh(workspace_id)


@router.post("/refresh")
async def refresh(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
):
    if await authorize_webhook(payload.data.id, "refresh") == "skipped":
        return {"status": "skipped"}

    background_tasks.add_task(_run_refresh, payload.data.id, source_label(payload.source.type))
    return {"status": "queued"}
