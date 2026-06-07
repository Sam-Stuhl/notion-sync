from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from src.clients.canvas import CanvasClient
from src.clients.notion import NotionClient
from src.config import settings
from src.operations.courses import sync_courses

router = APIRouter()

def _run(term: str | None):
    canvas = CanvasClient()
    notion = NotionClient()
    sync_courses(canvas, notion, term=term)

@router.post("/sync-courses")
async def handle_sync_courses(
    background_tasks: BackgroundTasks,
    authorization: str = Header()
):
    if authorization != f"Bearer {settings.webhook_secret}":
        raise HTTPException(status_code=401)

    background_tasks.add_task(_run, term=None)
    return {"status": "queued"}
