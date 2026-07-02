import hmac
import secrets

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.notion_oauth import auth_url, exchange_code
from src.auth.sessions import create_session_token
from src.config import settings
from src.db.repositories import (
    create_user,
    find_notion_integration_by_workspace_id,
    get_user_by_id,
    upsert_notion_integration,
)
from src.db.session import get_session

router = APIRouter(prefix="/auth")


_STATE_COOKIE = "ns_oauth_state"


@router.get("/login")
async def login():
    state = secrets.token_urlsafe(32)
    response = RedirectResponse(url=auth_url(state), status_code=302)
    response.set_cookie(
        _STATE_COOKIE,
        state,
        httponly=True,
        secure=settings.app_base_url.startswith("https"),
        samesite="lax",
        max_age=600,
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session")
    return response


@router.get("/callback")
async def callback(
    request: Request,
    db: AsyncSession = Depends(get_session),
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    if error or not code:
        return RedirectResponse(url="/", status_code=302)

    expected_state = request.cookies.get(_STATE_COOKIE)
    if not state or not expected_state or not hmac.compare_digest(state, expected_state):
        return RedirectResponse(url="/", status_code=302)

    try:
        token_data = await exchange_code(code)
    except httpx.HTTPStatusError:
        return RedirectResponse(url="/", status_code=302)

    access_token = token_data["access_token"]
    workspace_id = token_data["workspace_id"]
    workspace_name = token_data.get("workspace_name")
    workspace_icon = token_data.get("workspace_icon")
    bot_id = token_data.get("bot_id")

    owner_user = token_data.get("owner", {}).get("user", {})
    email = owner_user.get("person", {}).get("email", "")
    display_name = owner_user.get("name")
    avatar_url = owner_user.get("avatar_url")

    existing_integration = await find_notion_integration_by_workspace_id(db, workspace_id)
    user = await get_user_by_id(db, existing_integration.user_id) if existing_integration else None
    if not user:
        user = await create_user(db, email=email, display_name=display_name, avatar_url=avatar_url)

    await upsert_notion_integration(
        db,
        user_id=user.id,
        workspace_id=workspace_id,
        workspace_name=workspace_name,
        workspace_icon=workspace_icon,
        bot_id=bot_id,
        access_token=access_token,
    )

    await db.commit()

    session_token = create_session_token(str(user.id))
    secure = settings.app_base_url.startswith("https")

    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        "session",
        session_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=90 * 24 * 3600,
    )
    response.delete_cookie(_STATE_COOKIE)
    return response
