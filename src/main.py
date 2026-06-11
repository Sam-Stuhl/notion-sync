from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from src.logging import setup_logging
from src.auth.routes import router as auth_router
from src.web.routes import router as web_router
from src.webhooks.sync_courses import router as sync_courses_router
from src.webhooks.sync_assignments import router as sync_assignments_router
from src.webhooks.refresh import router as refresh_router

setup_logging()
app = FastAPI()

app.include_router(auth_router)
app.include_router(web_router)
app.include_router(sync_courses_router)
app.include_router(sync_assignments_router)
app.include_router(refresh_router)
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

@app.post("/debug-webhook")
async def debug_webhook(request: Request):
    body = await request.json()
    headers = dict(request.headers)
    print("HEADERS:", headers)
    print("BODY:", body)
    return {"headers": headers, "body": body}