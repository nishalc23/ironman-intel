import logging
from pathlib import Path
from garminconnect import Garmin, GarminConnectAuthenticationError

logger = logging.getLogger(__name__)

TOKEN_DIR = Path(".garmin_tokens")

DISCIPLINE_MAP = {
    "swimming": "swimming",
    "pool_swimming": "swimming",
    "open_water_swimming": "swimming",
    "cycling": "cycling",
    "road_biking": "cycling",
    "indoor_cycling": "cycling",
    "virtual_ride": "cycling",
    "running": "running",
    "trail_running": "running",
    "track_running": "running",
    "treadmill_running": "running",
}


class GarminClient:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.client = self._authenticate()

    def _authenticate(self) -> Garmin:
        client = Garmin(self.email, self.password)

        TOKEN_DIR.mkdir(exist_ok=True)
        token_path = TOKEN_DIR / "session"

        if token_path.exists():
            try:
                client.login(str(token_path))
                logger.info("Logged in with saved Garmin session tokens")
                return client
            except GarminConnectAuthenticationError:
                logger.warning("Saved tokens expired, re-authenticating")

        client.login()
        client.garth.dump(str(token_path))
        logger.info("Authenticated with Garmin and saved session tokens")
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
