import os
import sys

sys.path.insert(0, "/app")

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import create_tables
from services.api.routes import metrics, activities, plan, gym, sync

app = FastAPI(title="Ironman Intel API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics.router,    prefix="/api/metrics",    tags=["metrics"])
app.include_router(activities.router, prefix="/api/activities", tags=["activities"])
app.include_router(plan.router,       prefix="/api/plan",       tags=["plan"])
app.include_router(gym.router,        prefix="/api/gym",        tags=["gym"])
app.include_router(sync.router,       prefix="/api/sync",       tags=["sync"])


@app.on_event("startup")
def on_startup():
    create_tables()


@app.get("/health")
def health():
    return {"status": "ok"}
