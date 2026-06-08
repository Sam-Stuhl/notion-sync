"""
seed_self.py — one-time script to insert yourself as user #1 in the database.

How it works:
  Reads credentials from .env (via settings), fetches workspace metadata from
  the Notion API, encrypts all tokens with Fernet, then inserts four rows in a
  single transaction: User, NotionIntegration, SISIntegration (canvas),
  and WorkspaceConfig (seeded from template_settings).

  The script is idempotent — if a user with the given email already exists it
  prints a message and exits cleanly without inserting duplicates.

Usage:
  python -m scripts.seed_self <your-email> [display-name]

  Example:
    python -m scripts.seed_self sam@example.com "Sam Stuhl"
"""
import asyncio
import dataclasses
import sys

from notion_client import Client
from sqlalchemy import select

from src.config import settings
from src.db.encryption import encrypt
from src.db.models import SISIntegration, NotionIntegration, User, WorkspaceConfig
from src.db.session import AsyncSessionLocal
from src.template.config import template_settings


def _fetch_notion_workspace() -> dict:
    """Fetch workspace metadata from the Notion API using the token in settings.

    Returns:
        dict: workspace_id, workspace_name, and bot_id.
    """
    client = Client(auth=settings.notion_access_token)
    me = client.users.me()
    bot = me["bot"]
    return {
        "workspace_id": bot["workspace_id"],
        "workspace_name": bot["workspace_name"],
        "bot_id": me["id"],
    }


async def seed(email: str, display_name: str | None) -> None:
    """Insert the four DB rows that represent a fully configured user.

    Checks for an existing user with the same email first — exits cleanly if
    one is found so the script is safe to re-run.
    """
    workspace = _fetch_notion_workspace()

    async with AsyncSessionLocal() as session:
        async with session.begin():
            existing = await session.scalar(select(User).where(User.email == email))
            if existing:
                print(f"User already exists: {existing.id} ({existing.email})")
                return

            user = User(email=email, display_name=display_name)
            session.add(user)
            await session.flush()

            notion_integration = NotionIntegration(
                user_id=user.id,
                workspace_id=workspace["workspace_id"],
                workspace_name=workspace["workspace_name"],
                bot_id=workspace["bot_id"],
                access_token_encrypted=encrypt(settings.notion_access_token),
            )
            session.add(notion_integration)
            await session.flush()

            canvas_integration = SISIntegration(
                user_id=user.id,
                service="canvas",
                display_name="Canvas (NJIT)",
                base_url=settings.canvas_url,
                access_token_encrypted=encrypt(settings.canvas_access_token),
                is_active=True,
            )
            session.add(canvas_integration)

            workspace_config = WorkspaceConfig(
                user_id=user.id,
                notion_integration_id=notion_integration.id,
                root_page_id=template_settings.root_page_id,
                template_version="1.0",
                discovered_ids=dataclasses.asdict(template_settings),
                discovery_status="complete",
            )
            session.add(workspace_config)

    print(f"Seeded user: {user.id}")
    print(f"  email:        {email}")
    print(f"  workspace_id: {workspace['workspace_id']}")
    print(f"  workspace:    {workspace['workspace_name']}")
    print(f"  canvas url:   {settings.canvas_url}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.seed_self <email> [display-name]")
        sys.exit(1)

    email = sys.argv[1]
    display_name = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(seed(email, display_name))
