import uuid

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.sessions import verify_session_token
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
