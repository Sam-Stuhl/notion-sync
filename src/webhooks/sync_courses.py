from fastapi import APIRouter, BackgroundTasks

from src.clients import notion_props
from src.webhooks.common import (
    WebhookPayload,
    authorize_webhook,
    build_context,
    record_sync_run,
    source_label,
)
from src.operations.courses import sync_courses, _read_title

router = APIRouter()


async def _run_sync_courses(workspace_id: str, triggered_by: str = "notion") -> None:
    async with record_sync_run(workspace_id, "sync_courses", triggered_by) as collector:
        context = await build_context(workspace_id)
        results = sync_courses(context)
        collector["summary"] = {
            "courses": [
                {
                    "title": _read_title(r["page"], "Course Name"),
                    "action": "created" if r.get("was_created") else "updated",
                }
                for r in results
            ]
        }


@router.post("/sync-courses")
async def handle_sync_courses(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
):
    if await authorize_webhook(payload.data.id, "sync_courses") == "skipped":
        return {"status": "skipped"}

    background_tasks.add_task(_run_sync_courses, payload.data.id, source_label(payload.source.type))
    return {"status": "queued"}
