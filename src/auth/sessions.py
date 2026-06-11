from datetime import datetime, timedelta, timezone

import jwt

from src.config import settings

_ALGORITHM = "HS256"
_EXPIRY_DAYS = 90


def create_session_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=_EXPIRY_DAYS),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def verify_session_token(token: str) -> str:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    return payload["sub"]
