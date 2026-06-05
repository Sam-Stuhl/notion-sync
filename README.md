# notion-sync

A FastAPI server that receives webhook calls from Notion database buttons, fetches data from external academic systems (Canvas, and eventually other SIS platforms), and writes it back into Notion — idempotently.

## What it does

Notion database buttons trigger HTTP webhooks. This server receives those webhooks, runs a sync operation in the background (Notion times out at 25s, so the endpoint returns immediately), and populates Notion databases with data fetched from external sources.

Current operations:
- **Discover Courses** — pulls active course enrollments from Canvas and upserts them into a Notion Courses database

Planned:
- **Sync All** — discover courses + sync assignments for each
- **Refresh Calendar** — pull calendar events into a Notion calendar database
- **Activate Semester** — initialize a semester and link courses to it

## Architecture

Three layers with strict separation:

```
handlers/    ← thin FastAPI endpoints (~15 lines each)
operations/  ← business logic; no HTTP, no FastAPI
clients/     ← API wrappers; translate raw responses into common dataclasses
```

**clients/** contains domain-blind wrappers. `notion.py` wraps the Notion API. `canvas.py` implements `ExternalClient`, an ABC defined in `external_client.py`. All SIS clients return common dataclasses (`ExternalCourse`, `ExternalAssignment`, etc.) so operations are SIS-agnostic. Adding a new SIS means implementing `ExternalClient` — operations don't change.

**operations/** takes instantiated clients and primitive args, does the sync work, returns results. No framework imports.

**handlers/** receives the webhook, verifies auth, schedules the operation as a `BackgroundTask`, returns `{"status": "queued"}`.

## Idempotency design

Every synced row in Notion has two properties: `Source` (select: `Canvas`, `Google Calendar`, `Manual`, etc.) and `External ID` (text). Together they're a composite primary key.

`NotionClient.upsert_by_source(ds_id, source, external_id, properties)` queries by this key: updates if one match, creates if none, raises if multiple. Clicking a Notion sync button twice never creates duplicates.

## Dev setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and fill in:

```
CANVAS_URL=https://canvas.instructure.com
CANVAS_ACCESS_TOKEN=...

NOTION_ACCESS_TOKEN=secret_...
NOTION_COURSES_DB_ID=...
NOTION_TASKS_DB_ID=...
NOTION_SEMESTERS_DB_ID=...
NOTION_COURSES_DS_ID=...   # data source IDs (Notion internal API)
NOTION_TASKS_DS_ID=...
NOTION_SEMESTERS_DS_ID=...

WEBHOOK_SECRET=...         # any secret string; Notion buttons send it as a Bearer token
```

Run the dev server:

```bash
uvicorn src.main:app --reload
```

## Deployment (Fly.io)

```bash
fly launch          # first time only
fly secrets set CANVAS_ACCESS_TOKEN=... NOTION_ACCESS_TOKEN=... # etc.
fly deploy
```

The app needs to be reachable from the public internet so Notion can POST to it.

## Connecting a Notion button

1. Open the Notion database you want to add a button to.
2. Add a **Button** property.
3. Set the button action to **Webhook → POST** with:
   - URL: `https://<your-fly-app>.fly.dev/<endpoint>` (e.g. `/discover-courses`)
   - Header: `Authorization: Bearer <WEBHOOK_SECRET>`
   - Body: any JSON you want passed as the webhook payload (can be empty `{}`)
4. Click the button — the server responds with `{"status": "queued"}` and runs the sync in the background.

## Adding a new SIS

1. Implement `ExternalClient` in `src/clients/your_sis.py` — fill in `source_name`, `get_active_courses`, and `get_assignments`.
2. Wire it into the relevant handler in place of (or alongside) `CanvasClient`.

Operations and Notion logic don't need to change.
