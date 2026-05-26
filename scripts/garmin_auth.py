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

print(f"\nLogging in as {email}...")
client = Garmin(email, password)

try:
    client.login()
except Exception as e:
    if "MFA" in str(e) or "2FA" in str(e) or "factor" in str(e).lower():
        code = input("Enter your Garmin MFA code: ").strip()
        client.login(mfa_code=code)
    else:
        raise

token_path = Path(".garmin_tokens/session")
token_path.parent.mkdir(exist_ok=True)

try:
    client.garth.dump(str(token_path))
    print(f"\nTokens saved to {token_path}")
    print("Future syncs will use these tokens — no login needed.")
except AttributeError:
    print("\nAuthenticated successfully (token persistence not available in this version).")

print("Done!")
