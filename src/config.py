from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    canvas_url: str
    canvas_access_token: str
    
    notion_access_token: str
    notion_courses_db_id: str
    notion_tasks_db_id: str
    notion_semesters_db_id: str
    notion_courses_ds_id: str
    notion_tasks_ds_id: str
    notion_semesters_ds_id: str
    webhook_secret: str
    
    database_url: str
    encryption_key: str

    notion_oauth_client_id: str
    notion_oauth_client_secret: str
    jwt_secret: str
    
    app_base_url: str

    log_level: str = "INFO"

settings = Settings()  # raises on startup if anything's missing