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

        # Try loading saved tokens first (skips re-auth on repeat syncs)
        if token_path.exists():
            try:
                client.login(str(token_path))
                logger.info("Logged in with saved Garmin session tokens")
                return client
            except Exception:
                logger.warning("Saved tokens expired or invalid, re-authenticating")

        client.login()
        logger.info("Authenticated with Garmin Connect")

        # Persist tokens so future syncs don't re-login (garth API varies by version)
        try:
            client.garth.dump(str(token_path))
            logger.info("Session tokens saved for future syncs")
        except AttributeError:
            # Older garminconnect versions don't expose garth directly — try garth import
            try:
                import garth
                garth.save(str(token_path))
                logger.info("Session tokens saved via garth directly")
            except Exception:
                logger.info("Token persistence unavailable — will re-authenticate each sync")

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
