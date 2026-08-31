"""
Authentication and per-athlete scoping.

Every route used to call db.query(Athlete).first(), which meant the API served
row one to whoever asked. That made the app single-tenant no matter how many
people signed up. Routes now depend on current_athlete, which resolves the
athlete from a signed token, so one athlete can never read another's data.
"""
import os
import base64
import hashlib
import logging
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import bcrypt
from sqlalchemy.orm import Session

from db.models import Athlete

log = logging.getLogger(__name__)

TOKEN_TTL_DAYS = 30
ALGORITHM = "HS256"

_bearer = HTTPBearer(auto_error=False)


def _secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        # Refuse to sign tokens with a default. A predictable secret means
        # anyone can mint a token for any athlete.
        raise RuntimeError("JWT_SECRET is not set; refusing to issue tokens")
    return secret


def _prepare(password: str) -> bytes:
    """
    bcrypt silently truncates anything past 72 bytes, which would make a long
    passphrase no stronger than its first 72 bytes. Hashing to a fixed-width
    digest first means the whole password contributes.
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(_prepare(password), password_hash.encode())
    except ValueError:
        return False


def issue_token(athlete: Athlete) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(athlete.id),
        "email": athlete.email,
        "iat": now,
        "exp": now + timedelta(days=TOKEN_TTL_DAYS),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_token(token: str) -> int:
    """Return the athlete id, or raise 401. Never trust the body without verifying."""
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
        return int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired, sign in again")
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")


def athlete_from_token(db: Session, credentials: HTTPAuthorizationCredentials | None) -> Athlete:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    athlete_id = decode_token(credentials.credentials)
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if athlete is None:
        # The token is validly signed but the athlete is gone. Treat as 401,
        # not 404, so a deleted account cannot be probed.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account no longer exists")
    return athlete


def current_athlete_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> int:
    """
    Resolve the athlete id from the bearer token without touching the database.

    Routes open their own session via get_db(), so taking the id here and
    loading inside that session avoids attaching the object to a session that
    is about to close.
    """
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return decode_token(credentials.credentials)


def load_athlete(db: Session, athlete_id: int) -> Athlete:
    """Load the authenticated athlete inside a route's own session."""
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if athlete is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account no longer exists")
    return athlete


# --- Garmin credential encryption -------------------------------------------------

def _fernet() -> Fernet:
    key = os.environ.get("GARMIN_ENC_KEY")
    if not key:
        raise RuntimeError("GARMIN_ENC_KEY is not set; refusing to store credentials")
    # Accept either a raw Fernet key or any passphrase, derived to 32 bytes.
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError):
        derived = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
        return Fernet(derived)


def encrypt_garmin_token(token_json: str) -> str:
    return _fernet().encrypt(token_json.encode()).decode()


def decrypt_garmin_token(blob: str | None) -> str | None:
    if not blob:
        return None
    try:
        return _fernet().decrypt(blob.encode()).decode()
    except InvalidToken:
        # Key rotated or row corrupted. Surface as "not connected" rather than
        # a 500, so the athlete is prompted to reconnect Garmin.
        log.warning("Could not decrypt stored Garmin token; athlete must reconnect")
        return None
