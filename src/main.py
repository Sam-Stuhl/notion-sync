from fastapi import FastAPI
from src.handlers.sync_courses import router as sync_courses_router
from src.handlers.sync_assignments import router as sync_assignments_router

app = FastAPI()

app.include_router(sync_courses_router)
app.include_router(sync_assignments_router)