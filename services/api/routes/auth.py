"""Signup, login, and Garmin connection for the authenticated athlete."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from db.database import get_db
from db.models import Athlete
from services.api.auth import (
    hash_password,
    verify_password,
    issue_token,
    current_athlete_id,
    load_athlete,
    encrypt_garmin_token,
)

router = APIRouter()


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    athlete_id: int
    display_name: str | None


class MeOut(BaseModel):
    id: int
    email: str
    display_name: str | None
    ftp_watts: int | None
    gym_split: str | None
    garmin_connected: bool


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(body: SignupIn):
    with get_db() as db:
        if db.query(Athlete).filter(Athlete.email == body.email).first():
            raise HTTPException(status.HTTP_409_CONFLICT, "That email is already registered")
        athlete = Athlete(
            email=body.email,
            display_name=body.display_name,
            password_hash=hash_password(body.password),
        )
        db.add(athlete)
        db.flush()
        return TokenOut(
            access_token=issue_token(athlete),
            athlete_id=athlete.id,
            display_name=athlete.display_name,
        )


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn):
    with get_db() as db:
        athlete = db.query(Athlete).filter(Athlete.email == body.email).first()
        # Same message and same work either way, so the response cannot be used
        # to enumerate which emails have accounts.
        if athlete is None or not verify_password(body.password, athlete.password_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
        return TokenOut(
            access_token=issue_token(athlete),
            athlete_id=athlete.id,
            display_name=athlete.display_name,
        )


@router.get("/me", response_model=MeOut)
def me(athlete_id: int = Depends(current_athlete_id)):
    with get_db() as db:
        a = load_athlete(db, athlete_id)
        return MeOut(
            id=a.id,
            email=a.email,
            display_name=a.display_name,
            ftp_watts=a.ftp_watts,
            gym_split=a.gym_split,
            garmin_connected=a.garmin_token_encrypted is not None,
        )


class GarminConnectIn(BaseModel):
    token_json: str


@router.post("/garmin/connect", status_code=status.HTTP_204_NO_CONTENT)
def connect_garmin(body: GarminConnectIn, athlete_id: int = Depends(current_athlete_id)):
    """
    Store this athlete's own Garmin tokens, encrypted at rest.

    Credentials used to live in GARMIN_EMAIL and GARMIN_PASSWORD env vars, which
    meant the whole deployment could only ever sync one person's account.
    """
    with get_db() as db:
        athlete = load_athlete(db, athlete_id)
        athlete.garmin_token_encrypted = encrypt_garmin_token(body.token_json)
        athlete.garmin_connected_at = datetime.utcnow()


@router.delete("/garmin/connect", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_garmin(athlete_id: int = Depends(current_athlete_id)):
    with get_db() as db:
        athlete = load_athlete(db, athlete_id)
        athlete.garmin_token_encrypted = None
        athlete.garmin_connected_at = None
