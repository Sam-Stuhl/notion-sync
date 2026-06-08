from fastapi import FastAPI, Request
from src.handlers.sync_courses import router as sync_courses_router
from src.handlers.sync_assignments import router as sync_assignments_router
from src.handlers.refresh import router as refresh_router

app = FastAPI()

app.include_router(sync_courses_router)
app.include_router(sync_assignments_router)
app.include_router(refresh_router)

@app.post("/debug-webhook")
async def debug_webhook(request: Request):
    body = await request.json()
    headers = dict(request.headers)
    print("HEADERS:", headers)
    print("BODY:", body)
    return {"headers": headers, "body": body}