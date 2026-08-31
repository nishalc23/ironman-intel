"""
Database engine and session management.

The engine is built lazily. Reading DATABASE_URL at import time used to take
the whole service down: a missing variable raised KeyError before uvicorn
could load the app, so Render restarted it forever and no endpoint answered,
not even /health. Now an unconfigured or unreachable database degrades the
service instead of killing it.
"""
import os
import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from db.models import Base
from db.weekly_plan_model import WeeklyAdaptivePlan  # noqa: F401 — registers model with Base
from db.sleep_model import SleepLog                  # noqa: F401 — registers model with Base
from db.session_completion_model import SessionCompletion  # noqa: F401 — registers model with Base

log = logging.getLogger(__name__)

_engine = None
_SessionLocal = None


class DatabaseUnavailable(RuntimeError):
    """Raised when the database is unconfigured or unreachable."""


def get_engine():
    """Build the engine on first use so import never fails."""
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine

    url = os.environ.get("DATABASE_URL")
    if not url:
        raise DatabaseUnavailable(
            "DATABASE_URL is not set. On Render this usually means the free "
            "Postgres instance expired and the fromDatabase reference no "
            "longer resolves; create a new database and redeploy."
        )

    _engine = create_engine(
        url,
        pool_pre_ping=True,   # checks connection is alive before using it from the pool
        pool_size=5,
        max_overflow=10,
    )
    _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine


def get_session_factory():
    if _SessionLocal is None:
        get_engine()
    return _SessionLocal


def create_tables():
    Base.metadata.create_all(bind=get_engine())


def check_connection() -> tuple[bool, str | None]:
    """Ping the database. Used by /health so the service can report degraded."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except DatabaseUnavailable as e:
        return False, str(e)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


@contextmanager
def get_db() -> Session:
    db = get_session_factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
