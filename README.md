# notion-sync

A multi-tenant FastAPI service that syncs academic data from Canvas LMS (and eventually other SIS platforms) into each user's Notion workspace, idempotently.

## What it does

Users sign in with Notion OAuth. The service stores their Notion workspace connection and Canvas credentials (Fernet-encrypted, in Postgres), and gives them a dashboard to manage integrations and trigger syncs. Sync operations pull courses and assignments from Canvas and upsert them into the user's Notion databases.

Syncs are triggered two ways:

- From the web dashboard.
- From buttons inside Notion itself: a database button POSTs a webhook to this server, which authorizes the request by page ownership plus rate limiting, queues the sync as a background task (Notion times out at 25s, so the endpoint returns immediately), and runs it against that user's stored credentials.

## Architecture

Layers with strict separation:

```
src/
  auth/        Notion OAuth flow, JWT sessions, auth middleware
  web/         dashboard UI (Jinja templates): integrations, widgets, activity feed
  webhooks/    endpoints Notion buttons POST to; authorize, queue, return
  operations/  sync business logic; no HTTP, no FastAPI
  clients/     API wrappers; translate raw responses into common dataclasses
  db/          SQLAlchemy models, repositories, token encryption
```

**clients/** contains domain-blind wrappers. `notion.py` wraps the Notion API. `canvas.py` implements `SISClient`, an ABC defined in `sis_client.py`. All SIS clients return common dataclasses (`SISCourse`, `SISAssignment`) so operations are SIS-agnostic. Adding a new SIS means implementing `SISClient`; operations don't change.

**operations/** takes instantiated clients and primitive args, does the sync work, returns results. No framework imports.

**webhooks/** receives the webhook, resolves which user owns the page (`build_context`), rate-limits, schedules the operation as a background task, and returns `{"status": "queued"}`.

## Multi-tenancy and security

- Each user row links to their Notion integration, SIS integrations, and workspace config (see `src/db/models.py`).
- Notion and Canvas tokens are encrypted at rest with Fernet (`src/db/encryption.py`); the key never lives in the database.
- Sessions are JWTs; operator-only pages (like `/logs`) are gated by an admin email allowlist.

## Idempotency design

Every synced row in Notion has two properties: `Source` (select: `Canvas`, `Google Calendar`, `Manual`, etc.) and `External ID` (text). Together they're a composite primary key.

`NotionClient.upsert_by_source(ds_id, source, external_id, properties)` queries by this key: updates if one match, creates if none, raises if multiple. Running the same sync twice never creates duplicates.

## Dev setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and fill in:

```
NOTION_OAUTH_CLIENT_ID=...
NOTION_OAUTH_CLIENT_SECRET=...
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname
ENCRYPTION_KEY=...
JWT_SECRET=...
APP_BASE_URL=http://localhost:8000
```

Run migrations and the dev server:

```bash
alembic upgrade head
uvicorn src.main:app --reload
```

## Deployment (Fly.io)

```bash
fly launch          # first time only
fly secrets set NOTION_OAUTH_CLIENT_ID=... NOTION_OAUTH_CLIENT_SECRET=... DATABASE_URL=... ENCRYPTION_KEY=... JWT_SECRET=...
fly deploy
```

The app needs to be reachable from the public internet so Notion can complete OAuth redirects and POST button webhooks.

## Connecting a Notion button

1. Open the Notion database you want to add a button to.
2. Add a **Button** property with action **Webhook, POST** pointing at the deployed endpoint (e.g. `/sync-courses`).
3. Click the button. The server responds with `{"status": "queued"}` and runs the sync in the background against the credentials of whoever owns that page.

## Adding a new SIS

1. Implement `SISClient` in `src/clients/your_sis.py`: fill in `source_name`, `get_active_courses`, and `get_assignments`.
2. Wire it into the integration picker so users can connect it.

Operations and Notion logic don't need to change.
