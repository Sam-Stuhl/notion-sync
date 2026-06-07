from fastapi import APIRouter, BackgroundTasks, Body, Header, HTTPException

from src.clients.canvas import CanvasClient
from src.clients.notion import NotionClient
from src.clients import notion_props
from src.config import settings
from src.operations.assignments import sync_assignments, sync_assignments_for_course

router = APIRouter()

def _run_sync_assignments():
    canvas = CanvasClient()
    notion = NotionClient()
    sync_assignments(canvas, notion)

def _run_sync_assignments_for_course(course_id: str):
    canvas = CanvasClient()
    notion = NotionClient()
    sync_assignments_for_course(canvas, notion, course_id)

@router.post("/sync-assignments")
async def handle_sync_assignment(
    background_tasks: BackgroundTasks,
    authorization: str = Header()
):
    if authorization != f"Bearer {settings.webhook_secret}":
        raise HTTPException(status_code=401)

    background_tasks.add_task(_run_sync_assignments)
    return {"status": "queued"}

@router.post("/sync-assignments-for-course")
async def handle_sync_assignment_for_course(
    background_tasks: BackgroundTasks,
    body: dict = Body(...),
    authorization: str = Header()
):
    if authorization != f"Bearer {settings.webhook_secret}":
        raise HTTPException(status_code=401)

    external_id = notion_props.read_rich_text(body["data"]["properties"], "External ID")
    background_tasks.add_task(_run_sync_assignments_for_course, external_id)
    return {"status": "queued"}
