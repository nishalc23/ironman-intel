"""
Multi-tenancy tests.

Before auth existed every route called db.query(Athlete).first(), so the API
returned athlete row one to anyone who asked. These tests pin the property
that replaced it: an athlete sees their own data and never anyone else's.
"""
import os
import tempfile

import pytest

os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production")
os.environ.setdefault("GARMIN_ENC_KEY", "test-encryption-key")

_db_file = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file.name}"

from fastapi.testclient import TestClient  # noqa: E402

from db.database import create_tables, get_engine  # noqa: E402
from db.models import Base  # noqa: E402
from services.api.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    Base.metadata.drop_all(bind=get_engine())
    create_tables()
    with TestClient(app) as c:
        yield c


def register(client, email, password="correct-horse-battery"):
    r = client.post("/api/auth/signup", json={"email": email, "password": password,
                                              "display_name": email.split("@")[0]})
    assert r.status_code == 201, r.text
    return r.json()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestSignupAndLogin:
    def test_signup_returns_a_usable_token(self, client):
        data = register(client, "alice@example.com")
        assert data["athlete_id"] > 0
        r = client.get("/api/auth/me", headers=auth(data["access_token"]))
        assert r.status_code == 200
        assert r.json()["email"] == "alice@example.com"

    def test_duplicate_email_is_rejected(self, client):
        register(client, "dupe@example.com")
        r = client.post("/api/auth/signup", json={"email": "dupe@example.com",
                                                  "password": "another-password"})
        assert r.status_code == 409

    def test_login_with_correct_password_succeeds(self, client):
        register(client, "bob@example.com", "bobs-real-password")
        r = client.post("/api/auth/login", json={"email": "bob@example.com",
                                                 "password": "bobs-real-password"})
        assert r.status_code == 200
        assert r.json()["access_token"]

    def test_login_with_wrong_password_fails(self, client):
        register(client, "carol@example.com", "carols-password")
        r = client.post("/api/auth/login", json={"email": "carol@example.com",
                                                 "password": "wrong"})
        assert r.status_code == 401

    def test_unknown_email_and_wrong_password_give_the_same_error(self, client):
        register(client, "dave@example.com", "daves-password")
        wrong = client.post("/api/auth/login", json={"email": "dave@example.com",
                                                     "password": "nope"})
        missing = client.post("/api/auth/login", json={"email": "ghost@example.com",
                                                       "password": "nope"})
        # Identical responses, so the endpoint cannot be used to discover
        # which email addresses have accounts.
        assert wrong.status_code == missing.status_code == 401
        assert wrong.json() == missing.json()

    def test_password_is_never_stored_in_plaintext(self, client):
        from sqlalchemy import text
        register(client, "erin@example.com", "erins-secret-password")
        with get_engine().connect() as conn:
            row = conn.execute(
                text("SELECT password_hash FROM athletes WHERE email = 'erin@example.com'")
            ).one()
        assert "erins-secret-password" not in row[0]
        assert row[0].startswith("$2")  # bcrypt


class TestProtectedRoutes:
    ENDPOINTS = ["/api/metrics/", "/api/activities/", "/api/plan/split", "/api/gym/"]

    @pytest.mark.parametrize("path", ENDPOINTS)
    def test_rejects_request_with_no_token(self, client, path):
        assert client.get(path).status_code == 401

    @pytest.mark.parametrize("path", ENDPOINTS)
    def test_rejects_a_forged_token(self, client, path):
        assert client.get(path, headers=auth("not.a.real.token")).status_code == 401

    def test_token_signed_with_a_different_secret_is_rejected(self, client):
        import jwt
        from datetime import datetime, timedelta, timezone
        forged = jwt.encode(
            {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(days=1)},
            "attacker-secret", algorithm="HS256",
        )
        assert client.get("/api/metrics/", headers=auth(forged)).status_code == 401

    def test_expired_token_is_rejected(self, client):
        import jwt
        from datetime import datetime, timedelta, timezone
        expired = jwt.encode(
            {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
            os.environ["JWT_SECRET"], algorithm="HS256",
        )
        assert client.get("/api/metrics/", headers=auth(expired)).status_code == 401


class TestTenantIsolation:
    def test_two_athletes_see_their_own_identity(self, client):
        a = register(client, "iso-a@example.com")
        b = register(client, "iso-b@example.com")
        assert a["athlete_id"] != b["athlete_id"]

        me_a = client.get("/api/auth/me", headers=auth(a["access_token"])).json()
        me_b = client.get("/api/auth/me", headers=auth(b["access_token"])).json()
        assert me_a["email"] == "iso-a@example.com"
        assert me_b["email"] == "iso-b@example.com"

    def test_metrics_are_scoped_to_the_caller(self, client):
        """
        The regression this suite exists for. A second athlete must not receive
        the first athlete's training history.
        """
        from datetime import date, timedelta
        from db.database import get_db
        from db.models import DailyMetrics

        a = register(client, "scope-a@example.com")
        b = register(client, "scope-b@example.com")

        with get_db() as db:
            db.add(DailyMetrics(athlete_id=a["athlete_id"], date=date.today(),
                                ctl=88.0, atl=60.0, tsb=28.0, daily_tss=120))

        seen_by_a = client.get("/api/metrics/?days=5", headers=auth(a["access_token"])).json()
        seen_by_b = client.get("/api/metrics/?days=5", headers=auth(b["access_token"])).json()

        assert len(seen_by_a["history"]) == 1
        assert seen_by_a["history"][0]["ctl"] == 88.0
        assert seen_by_b["history"] == [], "athlete B must not see athlete A's metrics"

    def test_gym_workouts_are_scoped_to_the_caller(self, client):
        from datetime import date
        from db.database import get_db
        from db.models import GymWorkout

        a = register(client, "gym-a@example.com")
        b = register(client, "gym-b@example.com")

        with get_db() as db:
            db.add(GymWorkout(athlete_id=a["athlete_id"], date=date.today(),
                              duration_minutes=45, exercises=[{"name": "Squat", "sets": []}]))

        seen_by_b = client.get("/api/gym/", headers=auth(b["access_token"]))
        assert seen_by_b.status_code == 200
        assert seen_by_b.json() == [], "athlete B must not see athlete A's gym log"


class TestGarminCredentials:
    def test_garmin_starts_disconnected(self, client):
        a = register(client, "garmin-new@example.com")
        me = client.get("/api/auth/me", headers=auth(a["access_token"])).json()
        assert me["garmin_connected"] is False

    def test_connecting_stores_the_token_encrypted(self, client):
        from sqlalchemy import text
        a = register(client, "garmin-connect@example.com")
        secret = '{"oauth2":"super-secret-garmin-token"}'

        r = client.post("/api/auth/garmin/connect", json={"token_json": secret},
                        headers=auth(a["access_token"]))
        assert r.status_code == 204

        with get_engine().connect() as conn:
            stored = conn.execute(
                text("SELECT garmin_token_encrypted FROM athletes WHERE id = :i"),
                {"i": a["athlete_id"]},
            ).scalar()
        assert stored is not None
        assert "super-secret-garmin-token" not in stored

        from services.api.auth import decrypt_garmin_token
        assert decrypt_garmin_token(stored) == secret

    def test_disconnecting_clears_the_token(self, client):
        a = register(client, "garmin-drop@example.com")
        client.post("/api/auth/garmin/connect", json={"token_json": "{}"},
                    headers=auth(a["access_token"]))
        client.delete("/api/auth/garmin/connect", headers=auth(a["access_token"]))
        me = client.get("/api/auth/me", headers=auth(a["access_token"])).json()
        assert me["garmin_connected"] is False


class TestWeeklyTemplate:
    """The fixed weekly template and its server-side checkmarks."""

    def test_template_matches_the_prescribed_volume(self, client):
        from compute.weekly_template import counts_by_discipline, WEEKLY_TARGETS
        assert counts_by_discipline() == WEEKLY_TARGETS

    def test_session_keys_are_unique(self, client):
        from compute.weekly_template import TEMPLATE
        keys = [s.key for day in TEMPLATE.values() for s in day]
        assert len(keys) == len(set(keys))

    def test_week_returns_seven_days_starting_monday(self, client):
        a = register(client, "week-shape@example.com")
        w = client.get("/api/week/", headers=auth(a["access_token"])).json()
        assert len(w["days"]) == 7
        assert w["days"][0]["day_name"] == "Monday"
        assert w["days"][6]["day_name"] == "Sunday"
        assert w["progress"]["total"] == 12
        assert w["progress"]["completed"] == 0

    def test_checking_a_session_persists(self, client):
        a = register(client, "week-check@example.com")
        r = client.post("/api/week/complete/mon_swim_endurance", headers=auth(a["access_token"]))
        assert r.status_code == 200
        assert r.json()["progress"]["completed"] == 1

        again = client.get("/api/week/", headers=auth(a["access_token"])).json()
        session = again["days"][0]["sessions"][0]
        assert session["key"] == "mon_swim_endurance"
        assert session["completed"] is True
        assert session["completed_at"] is not None

    def test_checking_twice_does_not_double_count(self, client):
        a = register(client, "week-double@example.com")
        h = auth(a["access_token"])
        client.post("/api/week/complete/tue_run_intervals", headers=h)
        r = client.post("/api/week/complete/tue_run_intervals", headers=h)
        assert r.json()["progress"]["completed"] == 1

    def test_unchecking_removes_it(self, client):
        a = register(client, "week-uncheck@example.com")
        h = auth(a["access_token"])
        client.post("/api/week/complete/sat_brick", headers=h)
        r = client.delete("/api/week/complete/sat_brick", headers=h)
        assert r.json()["progress"]["completed"] == 0

    def test_unchecking_something_never_checked_is_not_an_error(self, client):
        a = register(client, "week-noop@example.com")
        r = client.delete("/api/week/complete/sun_rest", headers=auth(a["access_token"]))
        assert r.status_code == 200

    def test_unknown_session_key_is_rejected(self, client):
        a = register(client, "week-bogus@example.com")
        r = client.post("/api/week/complete/not_a_real_session", headers=auth(a["access_token"]))
        assert r.status_code == 404

    def test_checkmarks_are_scoped_per_athlete(self, client):
        a = register(client, "week-iso-a@example.com")
        b = register(client, "week-iso-b@example.com")
        client.post("/api/week/complete/wed_swim_intervals", headers=auth(a["access_token"]))
        seen_by_b = client.get("/api/week/", headers=auth(b["access_token"])).json()
        assert seen_by_b["progress"]["completed"] == 0

    def test_checkmarks_are_scoped_per_week(self, client):
        from datetime import date, timedelta
        a = register(client, "week-scope@example.com")
        h = auth(a["access_token"])
        client.post("/api/week/complete/fri_bike_intervals", headers=h)
        last_week = (date.today() - timedelta(days=7)).isoformat()
        prior = client.get(f"/api/week/?week_of={last_week}", headers=h).json()
        assert prior["progress"]["completed"] == 0

    def test_requires_authentication(self, client):
        assert client.get("/api/week/").status_code == 401
