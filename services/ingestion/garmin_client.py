import os
import json
import logging
from pathlib import Path
from garminconnect import Garmin, GarminConnectAuthenticationError

logger = logging.getLogger(__name__)

TOKEN_DIR = Path("/app/.garmin_tokens")

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
        token_path = TOKEN_DIR / "session"
        token_path.mkdir(parents=True, exist_ok=True)

        # If running on Render/cloud, seed tokens from env var
        tokens_env = os.environ.get("garmin_tokens.json") or os.environ.get("GARMIN_TOKENS_JSON")
        if tokens_env:
            token_file = token_path / "garmin_tokens.json"
            if not token_file.exists():
                token_file.write_text(tokens_env)
                logger.info("Seeded Garmin tokens from environment variable")

        client = Garmin(
            self.email,
            self.password,
            prompt_mfa=lambda: input("Enter your Garmin MFA code: ").strip(),
        )

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

    def get_sleep_data(self, date_str: str) -> dict:
        """Sleep data for a given date — score, stages, HRV, body battery."""
        try:
            return self.client.get_sleep_data(date_str)
        except Exception:
            return {}

    def get_body_battery(self, date_str: str) -> list:
        """Body battery levels throughout the day."""
        try:
            return self.client.get_body_battery(date_str)
        except Exception:
            return []

    @staticmethod
    def map_discipline(type_key: str) -> str:
        return DISCIPLINE_MAP.get(type_key, "other")
