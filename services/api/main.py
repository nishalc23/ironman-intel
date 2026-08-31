import os
import sys
import asyncio
from datetime import datetime

sys.path.insert(0, "/app")

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import create_tables, get_db, check_connection
from db.models import Athlete
from services.api.routes import metrics, activities, plan, gym, sync, sleep, auth

app = FastAPI(title="Ironman Intel API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "https://nishals-macbook-pro.tail396e25.ts.net",
        "http://nishals-macbook-pro.tail396e25.ts.net",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,       prefix="/api/auth",       tags=["auth"])
app.include_router(metrics.router,    prefix="/api/metrics",    tags=["metrics"])
app.include_router(activities.router, prefix="/api/activities", tags=["activities"])
app.include_router(plan.router,       prefix="/api/plan",       tags=["plan"])
app.include_router(gym.router,        prefix="/api/gym",        tags=["gym"])
app.include_router(sync.router,       prefix="/api/sync",       tags=["sync"])
app.include_router(sleep.router,      prefix="/api/sleep",      tags=["sleep"])


async def _sunday_midnight_scheduler():
    """
    Runs every Sunday at 23:59 — generates next week's adaptive plan.
    Compares actual training data vs static plan and has Claude rewrite the week.
    """
    from services.api.adaptive_planner import generate_adaptive_weekly_plan
    import logging
    log = logging.getLogger("adaptive_scheduler")

    while True:
        now = datetime.now()
        # Sunday = weekday 6, fire at 23:59
        is_sunday = now.weekday() == 6
        is_midnight = now.hour == 23 and now.minute == 59

        if is_sunday and is_midnight:
            log.info("Sunday midnight — generating adaptive plan for next week...")
            try:
                with get_db() as db:
                    athlete = db.query(Athlete).first()
                    if athlete:
                        result = generate_adaptive_weekly_plan(db, athlete)
                        log.info(
                            f"Adaptive plan generated: Week {result.week_number} "
                            f"({result.phase}) | {result.adaptation_notes}"
                        )
                    else:
                        log.warning("No athlete found — skipping adaptive plan generation")
            except Exception as e:
                log.error(f"Adaptive plan generation failed: {e}")
            # Sleep 2 min to avoid double-firing within same minute
            await asyncio.sleep(120)
        else:
            # Check every 30 seconds
            await asyncio.sleep(30)


@app.on_event("startup")
async def on_startup():
    """
    Never raise here. A failure in startup kills the process, and Render then
    restarts it in a loop where nothing answers, including /health. Log the
    problem and come up degraded so the failure is visible.
    """
    import logging
    log = logging.getLogger("startup")
    try:
        create_tables()
    except Exception as e:
        log.error(f"Database unavailable at startup, serving degraded: {e}")
        return
    asyncio.create_task(_sunday_midnight_scheduler())


@app.get("/")
def root():
    return {"status": "ok", "app": "Ironman Intel API"}

@app.get("/health")
def health():
    """Reports degraded rather than failing, so a dead database is diagnosable."""
    ok, error = check_connection()
    return {"status": "ok" if ok else "degraded", "database": ok, "error": error}
