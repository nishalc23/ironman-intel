import logging
from pathlib import Path
from garminconnect import Garmin, GarminConnectAuthenticationError

logger = logging.getLogger(__name__)

TOKEN_DIR = Path(".garmin_tokens")

DISCIPLINE_MAP = {
    # Swimming
    "swimming": "swimming",
    "pool_swimming": "swimming",
    "open_water_swimming": "swimming",
    "lap_swimming": "swimming",
    # Cycling
    "cycling": "cycling",
    "road_biking": "cycling",
    "indoor_cycling": "cycling",
    "virtual_ride": "cycling",
    "gravel_cycling": "cycling",
    # Running
    "running": "running",
    "trail_running": "running",
    "track_running": "running",
    "treadmill_running": "running",
    "street_running": "running",
    "indoor_running": "running",
}


class GarminClient:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.client = self._authenticate()

    def _authenticate(self) -> Garmin:
        TOKEN_DIR.mkdir(exist_ok=True)
        token_path = TOKEN_DIR / "session"

        # prompt_mfa is only invoked if running interactively and Garmin demands 2FA.
        # In headless sync, there's no TTY so this won't be called; saved tokens are used.
        client = Garmin(
            self.email,
            self.password,
            prompt_mfa=lambda: input("Enter your Garmin MFA code: ").strip(),
        )

        # login(tokenstore=...) handles everything:
        #   1. Loads saved tokens from the path if they exist
        #   2. Falls back to fresh login (email/password) if tokens are missing/expired
        #   3. Auto-saves new tokens to the path on successful fresh login
        client.login(tokenstore=str(token_path))
        logger.info("Logged in to Garmin Connect (tokens: %s)", token_path)

        return client

    def get_activities(self, limit: int = 100) -> list[dict]:
        return self.client.get_activities(0, limit)

    def get_activity_details(self, activity_id: int) -> dict:
        return self.client.get_activity_details(activity_id)

    def get_heart_rate_data(self, date_str: str) -> dict:
        """Daily heart rate stats — used for resting HR trend."""
        return self.client.get_heart_rates(date_str)

    def get_hrv_data(self, date_str: str) -> dict:
        """HRV (Heart Rate Variability) — key overtraining signal."""
        return self.client.get_hrv_data(date_str)

    @staticmethod
    def map_discipline(type_key: str) -> str:
        return DISCIPLINE_MAP.get(type_key, "other")
