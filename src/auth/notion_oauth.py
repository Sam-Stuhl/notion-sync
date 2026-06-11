import base64
from urllib.parse import urlencode

import httpx

from src.config import settings

_AUTHORIZE_URL = "https://api.notion.com/v1/oauth/authorize"
_TOKEN_URL = "https://api.notion.com/v1/oauth/token"


def _redirect_uri() -> str:
    return f"{settings.app_base_url}/auth/callback"


def auth_url() -> str:
    params = {
        "client_id": settings.notion_oauth_client_id,
        "response_type": "code",
        "owner": "user",
        "redirect_uri": _redirect_uri(),
    }
    return f"{_AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    credentials = base64.b64encode(
        f"{settings.notion_oauth_client_id}:{settings.notion_oauth_client_secret}".encode()
    ).decode()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            _TOKEN_URL,
            headers={"Authorization": f"Basic {credentials}"},
            json={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": _redirect_uri(),
            },
        )
        response.raise_for_status()
        return response.json()
