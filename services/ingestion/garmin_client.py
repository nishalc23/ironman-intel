import os
import json
import logging
from pathlib import Path
from garminconnect import Garmin, GarminConnectAuthenticationError

logger = logging.getLogger(__name__)

# /app only exists inside the container. Outside it that path is unwritable,
# so authentication died before it started. Overridable, with a repo-local
# default that works when running the API directly.
TOKEN_DIR = Path(os.environ.get("GARMIN_TOKEN_DIR")
                 or (Path(__file__).resolve().parents[2] / ".garmin_tokens"))

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

        # If running on Render/cloud, seed tokens from env var (always overwrite to stay fresh)
        tokens_env = os.environ.get("GARMIN_TOKENS_JSON") or os.environ.get("garmin_tokens.json")
        if tokens_env:
            try:
                combined = json.loads(tokens_env)
                # garth's Client.dump()/load() expect two separate files:
                # oauth1_token.json and oauth2_token.json, each holding the
                # dataclass fields directly (not wrapped/combined).
                oauth1 = combined.pop("oauth1_token.json", None)
                oauth2 = combined  # whatever remains is the oauth2 token fields

                if oauth1 is not None:
                    (token_path / "oauth1_token.json").write_text(json.dumps(oauth1, indent=4))
                if oauth2:
                    (token_path / "oauth2_token.json").write_text(json.dumps(oauth2, indent=4))

                logger.info("Seeded Garmin tokens from environment variable (split into oauth1/oauth2 files)")
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("Failed to parse GARMIN_TOKENS_JSON env var as combined token JSON: %s", e)

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
