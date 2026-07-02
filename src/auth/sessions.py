from datetime import datetime, timedelta, timezone

import jwt

from src.config import settings

_ALGORITHM = "HS256"
_EXPIRY_DAYS = 90
_WIDGET_EDIT_EXPIRY_DAYS = 30


def create_session_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=_EXPIRY_DAYS),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def verify_session_token(token: str) -> str:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    return payload["sub"]


def create_widget_edit_token(widget_id: str, user_id: str) -> str:
    payload = {
        "sub": user_id,
        "wid": widget_id,
        "typ": "widget_edit",
        "exp": datetime.now(timezone.utc) + timedelta(days=_WIDGET_EDIT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def verify_widget_edit_token(token: str) -> tuple[str, str]:
    """Returns (widget_id, user_id). Raises jwt.InvalidTokenError on any problem."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    if payload.get("typ") != "widget_edit":
        raise jwt.InvalidTokenError("wrong token type")
    return payload["wid"], payload["sub"]
