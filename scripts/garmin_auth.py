"""
Run this once to authenticate with Garmin and save session tokens.
Handles MFA interactively.

Usage (inside Docker):
    docker compose run --rm -it ingestion python scripts/garmin_auth.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, "/app")

from dotenv import load_dotenv
load_dotenv()

from garminconnect import Garmin

email    = os.environ.get("GARMIN_EMAIL")    or input("Garmin email: ")
password = os.environ.get("GARMIN_PASSWORD") or input("Garmin password: ")

token_path = Path("/app/.garmin_tokens/session")
token_path.mkdir(parents=True, exist_ok=True)

print(f"\nLogging in as {email}...")

client = Garmin(
    email,
    password,
    prompt_mfa=lambda: input("Enter your Garmin MFA code: ").strip(),
)

# login(tokenstore=path) will:
#   1. Try to load existing tokens — silently falls back to fresh login if missing
#   2. Do fresh OAuth login (prompts MFA if needed)
#   3. Auto-save new tokens to path
client.login(tokenstore=str(token_path))

print(f"\nSuccess! Tokens saved to {token_path}")
print("Run `make sync` now.")
