import uuid

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.sessions import verify_session_token
from src.config import settings
from src.db.models import User
from src.db.repositories import get_user_by_id
from src.db.session import get_session


async def require_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=302, headers={"Location": "/"})
    try:
        user_id = verify_session_token(token)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=302, headers={"Location": "/"})
    user = await get_user_by_id(session, uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/"})
    return user


def _admin_emails() -> set[str]:
    return {e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()}


async def require_admin(user: User = Depends(require_user)) -> User:
    """Gate operator-only pages. 404s (rather than 403s) to avoid revealing the route."""
    if (user.email or "").lower() not in _admin_emails():
        raise HTTPException(status_code=404)
    return user
