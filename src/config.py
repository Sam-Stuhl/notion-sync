from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # --- Required in the live (multi-tenant) request path ---
    # The deployed service cannot boot or serve without these.
    notion_oauth_client_id: str
    notion_oauth_client_secret: str
    jwt_secret: str
    webhook_secret: str
    database_url: str
    encryption_key: str
    app_base_url: str

    # --- Optional: legacy single-tenant / dev-and-script-only ---
    # In production, per-tenant Canvas/Notion credentials and workspace IDs come
    # from the database (see src/webhooks/common.py:build_context). These globals
    # are only read as fallbacks by the client constructors and by scripts/ and
    # __main__ dev blocks, so the deployed service does not need them set.
    canvas_url: str | None = None
    canvas_access_token: str | None = None
    notion_access_token: str | None = None

    notion_courses_db_id: str | None = None
    notion_tasks_db_id: str | None = None
    notion_semesters_db_id: str | None = None
    notion_courses_ds_id: str | None = None
    notion_tasks_ds_id: str | None = None
    notion_semesters_ds_id: str | None = None

    log_level: str = "INFO"

    # Comma-separated emails allowed to view operator-only pages (e.g. /logs).
    # Empty = nobody; the pages 404 for everyone until set.
    admin_emails: str = ""

settings = Settings()  # raises on startup only if a *required* field is missing
