import pathlib
import uuid
from datetime import datetime, timezone

import httpx
import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import require_user
from src.auth.sessions import verify_session_token
from src.db.models import SyncRun, User
from src.db.repositories import (
    create_sis_integration,
    create_sync_run,
    get_notion_integration,
    get_sis_integration_by_id,
    get_workspace_config,
    list_recent_sync_runs,
    list_sis_integrations,
    soft_delete_sis_integration,
    update_sis_integration,
)
from src.db.session import get_session
from src.web.services import SERVICES, SERVICES_BY_ID

router = APIRouter()
templates = Jinja2Templates(directory=str(pathlib.Path(__file__).parent / "templates"))

# Make the service registry available in all templates without passing explicitly
templates.env.globals["services"] = SERVICES
templates.env.globals["services_by_id"] = SERVICES_BY_ID


# ─── Jinja filters ────────────────────────────────────────────────────────────

def relative_time(dt: datetime | None) -> str:
    if not dt:
        return "never"
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        return f"{seconds // 60} min ago"
    elif seconds < 86400:
        return f"{seconds // 3600}h ago"
    elif seconds < 172800:
        t = dt.strftime("%I:%M %p").lstrip("0").lower()
        return f"yesterday at {t}"
    elif seconds < 604800:
        return dt.strftime("%b %d").replace(" 0", " ")
    else:
        return dt.strftime("%b %d, %Y").replace(" 0", " ")


def format_description(run: SyncRun) -> str:
    summary = run.summary or {}
    op = run.operation or "sync"
    if run.status == "pending":
        return "Syncing…"
    if run.status == "failed":
        return "Sync failed"

    courses = summary.get("courses", [])
    assignments = summary.get("assignments", [])

    parts = []
    if assignments:
        n = len(assignments)
        n_new = sum(1 for a in assignments if a.get("action") == "created")
        label = f"{n} assignment{'s' if n != 1 else ''}"
        if n_new:
            label += f" ({n_new} new)"
        parts.append(label)
    if courses:
        n = len(courses)
        n_new = sum(1 for c in courses if c.get("action") == "created")
        label = f"{n} course{'s' if n != 1 else ''}"
        if n_new:
            label += f" ({n_new} new)"
        parts.append(label)
    if parts:
        return "Synced " + " and ".join(parts)

    # New summary format present but nothing written — everything was unchanged
    if "courses" in summary or "assignments" in summary:
        return "Everything up to date"

    # Old run without summary data
    if op == "refresh":
        return "Refreshed workspace"
    if op == "sync_courses":
        return "Synced courses"
    if op == "sync_assignments":
        return "Synced assignments"
    return op.replace("_", " ").capitalize()


templates.env.filters["relative_time"] = relative_time
templates.env.filters["format_description"] = format_description


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _validate_canvas(base_url: str, token: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{base_url}/api/v1/users/self",
                headers={"Authorization": f"Bearer {token}"},
            )
            return r.status_code == 200
    except Exception:
        return False


async def _validate_credentials(service_id: str, base_url: str, token: str) -> bool:
    if service_id == "canvas":
        return await _validate_canvas(base_url, token)
    return False


def _status_info(integrations, recent_runs: list[SyncRun]) -> dict | None:
    if not integrations:
        return None
    error_integrations = [i for i in integrations if i.last_validation_error]
    if error_integrations:
        svc = SERVICES_BY_ID.get(error_integrations[0].service)
        name = svc.name if svc else "Integration"
        return {"type": "warning", "message": f"{name} token may have expired. Re-connect to fix."}
    recent_failed = [r for r in recent_runs[:3] if r.status == "failed"]
    if recent_failed:
        return {"type": "warning", "message": "Last sync encountered an error."}
    completed = [r for r in recent_runs if r.status == "success"]
    if completed:
        return {"type": "success", "message": f"Everything connected. Last synced {relative_time(completed[0].started_at)}."}
    return {"type": "neutral", "message": "Ready to sync."}


async def _run_sync_with_tracking(root_page_id: str, run_id: uuid.UUID) -> None:
    from sqlalchemy import select as sa_select
    from src.db.session import AsyncSessionLocal
    from src.webhooks.refresh import _do_refresh

    async with AsyncSessionLocal() as session:
        result = await session.execute(sa_select(SyncRun).where(SyncRun.id == run_id))
        run = result.scalar_one_or_none()
        if not run:
            return
        try:
            run.summary = await _do_refresh(root_page_id)
            run.status = "success"
            run.completed_at = datetime.now(timezone.utc)
            if run.started_at:
                run.duration_ms = int((run.completed_at - run.started_at).total_seconds() * 1000)
        except Exception as e:
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)
            run.error_type = type(e).__name__
            run.error_message = str(e)
        await session.commit()


def _section_response(request, integrations, extra_headers: dict | None = None):
    response = templates.TemplateResponse(
        request=request,
        name="integrations_section.html",
        context={"integrations": integrations},
    )
    for k, v in (extra_headers or {}).items():
        response.headers[k] = v
    return response


# ─── Page routes ──────────────────────────────────────────────────────────────

@router.get("/")
async def index(request: Request):
    token = request.cookies.get("session")
    if token:
        try:
            verify_session_token(token)
            return RedirectResponse("/dashboard", status_code=302)
        except jwt.InvalidTokenError:
            pass
    return templates.TemplateResponse(request=request, name="index.html")


@router.get("/dashboard")
async def dashboard(
    request: Request,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_session),
):
    notion = await get_notion_integration(db, user.id)
    integrations = await list_sis_integrations(db, user.id)
    recent_runs = await list_recent_sync_runs(db, user.id)
    status = _status_info(integrations, recent_runs)
    has_pending = any(r.status == "pending" for r in recent_runs)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
            "notion": notion,
            "integrations": integrations,
            "recent_runs": recent_runs,
            "status": status,
            "polling": has_pending,
        },
    )


@router.get("/logs")
async def logs_page(
    request: Request,
    user: User = Depends(require_user),
    lines: int = 200,
):
    import pathlib
    log_file = pathlib.Path("logs/notion-sync.log")
    log_lines: list[str] = []
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            log_lines = f.readlines()[-lines:]
    return templates.TemplateResponse(
        request=request,
        name="logs_page.html",
        context={"user": user, "log_lines": log_lines},
    )


@router.get("/activity")
async def activity_page(
    request: Request,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_session),
):
    recent_runs = await list_recent_sync_runs(db, user.id, limit=100)
    return templates.TemplateResponse(
        request=request,
        name="activity_page.html",
        context={"user": user, "recent_runs": recent_runs},
    )


@router.get("/dashboard/activity")
async def dashboard_activity(
    request: Request,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_session),
):
    recent_runs = await list_recent_sync_runs(db, user.id)
    has_pending = any(r.status == "pending" for r in recent_runs)
    return templates.TemplateResponse(
        request=request,
        name="activity_feed.html",
        context={"recent_runs": recent_runs, "polling": has_pending},
    )


# ─── Sync now ─────────────────────────────────────────────────────────────────

@router.post("/sync/now")
async def sync_now(
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_session),
):
    workspace_config = await get_workspace_config(db, user.id)
    if not workspace_config or not workspace_config.root_page_id:
        recent_runs = await list_recent_sync_runs(db, user.id)
        response = templates.TemplateResponse(
            request=request,
            name="activity_feed.html",
            context={"recent_runs": recent_runs, "polling": False, "sync_error": "Workspace not configured yet."},
        )
        response.headers["HX-Retarget"] = "#activity-feed"
        response.headers["HX-Reswap"] = "outerHTML"
        return response

    run = await create_sync_run(db, user_id=user.id, operation="refresh", triggered_by="button")
    await db.commit()
    background_tasks.add_task(_run_sync_with_tracking, workspace_config.root_page_id, run.id)

    recent_runs = await list_recent_sync_runs(db, user.id)
    response = templates.TemplateResponse(
        request=request,
        name="activity_feed.html",
        context={"recent_runs": recent_runs, "polling": True},
    )
    response.headers["HX-Retarget"] = "#activity-feed"
    response.headers["HX-Reswap"] = "outerHTML"
    return response


# ─── Integration modal content ────────────────────────────────────────────────

@router.get("/integrations/new")
async def integrations_picker(request: Request, _: User = Depends(require_user)):
    return templates.TemplateResponse(
        request=request, name="integrations/picker.html"
    )


@router.get("/integrations/{service_id}/new-form")
async def integration_new_form(
    service_id: str,
    request: Request,
    _: User = Depends(require_user),
):
    service = SERVICES_BY_ID.get(service_id)
    if not service or service.status != "available" or not service.form_template:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request=request,
        name=service.form_template,
        context={"mode": "add", "integration": None, "service": service},
    )


@router.get("/integrations/{integration_id}/edit-form")
async def integration_edit_form(
    integration_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_session),
):
    integration = await get_sis_integration_by_id(db, integration_id, user.id)
    if not integration:
        raise HTTPException(404)
    service = SERVICES_BY_ID.get(integration.service)
    if not service or not service.form_template:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request=request,
        name=service.form_template,
        context={"mode": "edit", "integration": integration, "service": service},
    )


@router.get("/integrations/{integration_id}/delete-confirm")
async def integration_delete_confirm(
    integration_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_session),
):
    integration = await get_sis_integration_by_id(db, integration_id, user.id)
    if not integration:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request=request,
        name="integrations/delete_confirm.html",
        context={"integration": integration},
    )


# ─── Integration mutations ────────────────────────────────────────────────────

@router.post("/integrations/{service_id}")
async def integration_create(
    service_id: str,
    request: Request,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_session),
    base_url: str = Form(...),
    access_token: str = Form(...),
    display_name: str = Form(""),
):
    service = SERVICES_BY_ID.get(service_id)
    if not service or service.status != "available":
        raise HTTPException(404)

    base_url = base_url.rstrip("/")
    if not await _validate_credentials(service_id, base_url, access_token):
        response = templates.TemplateResponse(
            request=request,
            name=service.form_template,
            context={
                "mode": "add",
                "integration": None,
                "service": service,
                "error": f"Could not connect to {service.name}. Check the URL and token.",
                "values": {"base_url": base_url, "display_name": display_name},
            },
        )
        response.headers["HX-Retarget"] = "#integration-modal-content"
        response.headers["HX-Reswap"] = "innerHTML"
        return response

    integration = await create_sis_integration(
        db,
        user_id=user.id,
        service=service_id,
        base_url=base_url,
        access_token=access_token,
        display_name=display_name.strip() or None,
    )
    integration.last_validated_at = datetime.now(timezone.utc)
    await db.commit()

    integrations = await list_sis_integrations(db, user.id)
    return _section_response(request, integrations, {"HX-Trigger": "close-modal"})


@router.put("/integrations/{integration_id}")
async def integration_update(
    integration_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_session),
    base_url: str = Form(...),
    access_token: str = Form(""),
    display_name: str = Form(""),
):
    integration = await get_sis_integration_by_id(db, integration_id, user.id)
    if not integration:
        raise HTTPException(404)
    service = SERVICES_BY_ID.get(integration.service)
    if not service or not service.form_template:
        raise HTTPException(404)

    base_url = base_url.rstrip("/")
    token_to_validate = access_token or None

    if token_to_validate and not await _validate_credentials(integration.service, base_url, token_to_validate):
        response = templates.TemplateResponse(
            request=request,
            name=service.form_template,
            context={
                "mode": "edit",
                "integration": integration,
                "service": service,
                "error": f"Could not connect to {service.name}. Check the URL and token.",
                "values": {"base_url": base_url, "display_name": display_name},
            },
        )
        response.headers["HX-Retarget"] = "#integration-modal-content"
        response.headers["HX-Reswap"] = "innerHTML"
        return response

    await update_sis_integration(
        db,
        integration=integration,
        base_url=base_url,
        access_token=token_to_validate,
        display_name=display_name.strip() or None,
    )
    if token_to_validate:
        integration.last_validated_at = datetime.now(timezone.utc)
        integration.last_validation_error = None
    await db.commit()

    integrations = await list_sis_integrations(db, user.id)
    return _section_response(request, integrations, {"HX-Trigger": "close-modal"})


@router.delete("/integrations/{integration_id}")
async def integration_delete(
    integration_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_session),
):
    integration = await get_sis_integration_by_id(db, integration_id, user.id)
    if not integration:
        raise HTTPException(404)

    await soft_delete_sis_integration(db, integration)
    await db.commit()

    integrations = await list_sis_integrations(db, user.id)
    return _section_response(request, integrations, {"HX-Trigger": "close-modal"})
