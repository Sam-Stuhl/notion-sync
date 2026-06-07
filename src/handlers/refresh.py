from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from src.clients.canvas import CanvasClient
from src.clients.notion import NotionClient
from src.config import settings
from src.operations.courses import sync_courses
from src.operations.semesters import get_current_semester, reconcile_semester_status, update_view_filters

router = APIRouter()

def _run_refresh():
    canvas = CanvasClient()
    notion = NotionClient()
    
    # Semester updating
    current_semester_id = get_current_semester(notion)
    if current_semester_id:
        reconcile_semester_status(notion, current_semester_id)
        update_view_filters(notion, current_semester_id)
    
    # Course and Assignments
    sync_courses(canvas, notion, current_semester_id)
    

@router.post("/refresh")
async def refresh(
    background_tasks: BackgroundTasks,
    authorization: str = Header()
):
    if authorization != f"Bearer {settings.webhook_secret}":
        raise HTTPException(status_code=401)
    
    background_tasks.add_task(_run_refresh)
    return {"status": "queued"}
    
    