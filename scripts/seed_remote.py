"""Create the schema on a fresh database and copy the local SQLite rows into it.

Used to rebuild production after Render's free Postgres expires.

    SOURCE_URL=sqlite:///./local.sqlite \
    DATABASE_URL='<external Postgres URL>' \
    .venv/bin/python scripts/seed_remote.py

Refuses to touch a database that already has athletes unless --force is
passed, so a mistyped URL cannot quietly overwrite live data.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from db.models import Base, Athlete  # noqa: E402

# Importing these registers the rest of the tables on Base.metadata. Without
# them create_all writes a partial schema and the app fails on first query.
import db.session_completion_model  # noqa: E402,F401
import db.sleep_model  # noqa: E402,F401
import db.weekly_plan_model  # noqa: E402,F401

# Ordered so a row's parents exist before it does.
TABLE_ORDER = [
    "athletes",
    "activities",
    "activity_streams",
    "daily_metrics",
    "sleep_logs",
    "gym_workouts",
    "session_completions",
    "weekly_adaptive_plans",
    "predictions",
]


def main() -> int:
    force = "--force" in sys.argv
    source_url = os.getenv("SOURCE_URL", "sqlite:///./local.sqlite")
    target_url = os.environ.get("DATABASE_URL")
    if not target_url:
        print(__doc__, file=sys.stderr)
        return 2

    source = create_engine(source_url)
    target = create_engine(target_url)

    print("Creating the schema…")
    Base.metadata.create_all(bind=target)

    TargetSession = sessionmaker(bind=target)
    with TargetSession() as check:
        existing = check.query(Athlete).count()
    if existing and not force:
        print(f"Target already holds {existing} athlete(s). Pass --force to overwrite.",
              file=sys.stderr)
        return 1

    with source.connect() as src, target.begin() as dst:
        for name in TABLE_ORDER:
            table = Base.metadata.tables.get(name)
            if table is None:
                continue
            rows = [dict(r._mapping) for r in src.execute(table.select())]
            if not rows:
                print(f"  {name}: empty")
                continue
            dst.execute(table.delete())
            dst.execute(table.insert(), rows)
            print(f"  {name}: {len(rows)} rows")

    # Postgres sequences do not advance when ids are supplied explicitly, so the
    # next insert would collide with a copied row. SQLite has no such problem.
    if target.dialect.name == "postgresql":
        with target.begin() as dst:
            for name in TABLE_ORDER:
                table = Base.metadata.tables.get(name)
                if table is None or "id" not in table.c:
                    continue
                dst.exec_driver_sql(
                    f"SELECT setval(pg_get_serial_sequence('{name}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {name}), 1))"
                )
        print("Reset id sequences.")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
