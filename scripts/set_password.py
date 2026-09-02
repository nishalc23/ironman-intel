"""Set an athlete's password.

Registration is closed, so this is how you recover or rotate a login. The
password is read with getpass, which keeps it out of your shell history, out
of the process list, and off the screen.

    DATABASE_URL=<prod url> .venv/bin/python scripts/set_password.py you@example.com

With no DATABASE_URL it edits the local SQLite file.
"""
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import get_db  # noqa: E402
from db.models import Athlete  # noqa: E402
from services.api.auth import hash_password  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    email = sys.argv[1]
    first = getpass.getpass("New password: ")
    if len(first) < 8:
        print("Too short — use at least 8 characters.", file=sys.stderr)
        return 1
    if first != getpass.getpass("Again: "):
        print("They did not match.", file=sys.stderr)
        return 1

    with get_db() as db:
        athlete = db.query(Athlete).filter(Athlete.email == email).first()
        if athlete is None:
            known = [a.email for a in db.query(Athlete).all()]
            print(f"No athlete with email {email!r}.", file=sys.stderr)
            print(f"Registered: {known or 'none — the database is empty'}", file=sys.stderr)
            return 1
        athlete.password_hash = hash_password(first)

    print(f"Password updated for {email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
