from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from src.clients import notion_props
from src.config import settings
from src.webhooks.common import WebhookPayload, build_context, record_sync_run, source_label
from src.operations.assignments import sync_assignments_for_course

router = APIRouter()


def _title(page: dict, field: str) -> str:
    try:
        return notion_props.read_title(page["properties"], field) or "Untitled"
    except (KeyError, TypeError):
        return "Untitled"


async def _run_sync_assignments(workspace_id: str, triggered_by: str = "notion") -> None:
    async with record_sync_run(workspace_id, "sync_assignments", triggered_by) as collector:
        context = await build_context(workspace_id)

        existing_tasks = context.notion.get_pages_by_source(
            context.workspace.template_tasks_ds_id,
            context.external.source_name,
        )
        existing_courses = context.notion.get_pages_by_source(
            context.workspace.template_courses_ds_id,
            context.external.source_name,
        )

        items = []
        for course in context.external.get_active_courses():
            course_page = existing_courses.get(course.id)
            if not course_page:
                continue
            course_notion_id = course_page["id"]
            try:
                rel = notion_props.read_relation(course_page["properties"], "Semester")
                semester_notion_id = rel[0] if rel else None
            except (KeyError, TypeError):
                semester_notion_id = None

            for r in sync_assignments_for_course(
                context, course.id, existing_tasks, course_notion_id, semester_notion_id
            ):
                items.append({
                    "title": _title(r["page"], "Task Name"),
                    "course": course.name,
                    "action": "created" if r.get("was_created") else "updated",
                })

        collector["summary"] = {"assignments": items}


async def _run_sync_assignments_for_course(
    workspace_id: str, course_id: str, triggered_by: str = "notion"
) -> None:
    async with record_sync_run(workspace_id, "sync_assignments", triggered_by) as collector:
        context = await build_context(workspace_id)

        existing_tasks = context.notion.get_pages_by_source(
            context.workspace.template_tasks_ds_id,
            context.external.source_name,
        )
        course_page = context.notion.get_page_by_source(
            context.workspace.template_courses_ds_id,
            context.external.source_name,
            course_id,
        )
        if not course_page:
            collector["summary"] = {"assignments": []}
            return

        course_notion_id = course_page["id"]
        try:
            rel = notion_props.read_relation(course_page["properties"], "Semester")
            semester_notion_id = rel[0] if rel else None
        except (KeyError, TypeError):
            semester_notion_id = None

        results = sync_assignments_for_course(
            context, course_id, existing_tasks, course_notion_id, semester_notion_id
        )
        collector["summary"] = {
            "assignments": [
                {
                    "title": _title(r["page"], "Task Name"),
                    "action": "created" if r.get("was_created") else "updated",
                }
                for r in results
            ]
        }


@router.post("/sync-assignments")
async def handle_sync_assignments(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    authorization: str = Header(),
):
    if authorization != f"Bearer {settings.webhook_secret}":
        raise HTTPException(status_code=401)

    background_tasks.add_task(_run_sync_assignments, payload.data.id, source_label(payload.source.type))
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
    background_tasks.add_task(
        _run_sync_assignments_for_course, payload.data.id, course_id, source_label(payload.source.type)
    )
    return {"status": "queued"}
