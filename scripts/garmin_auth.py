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

token_path = Path(".garmin_tokens/session")
token_path.parent.mkdir(exist_ok=True)

print(f"\nLogging in as {email}...")

# prompt_mfa is called automatically if Garmin requires a 2FA code
client = Garmin(
    email,
    password,
    prompt_mfa=lambda: input("Enter your Garmin MFA code: ").strip(),
)

# login() with tokenstore will:
#   1. Try to load existing tokens from the path
#   2. Fall back to fresh login if tokens are missing/expired
#   3. Auto-save new tokens to the path on successful login
client.login(tokenstore=str(token_path))

print(f"\nSuccess! Tokens saved to {token_path}")
print("Run `make sync` now.")
