from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
SESSION_FILE = DATA_DIR / "instagram_session.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class Settings:
    instagram_username: str | None = os.getenv("INSTAGRAM_USERNAME")
    instagram_password: str | None = os.getenv("INSTAGRAM_PASSWORD")
    instagram_profile_url: str | None = os.getenv("INSTAGRAM_PROFILE_URL")
    max_posts: int = int(os.getenv("MAX_POSTS", 10))
    headless_mode: bool = os.getenv("HEADLESS_MODE", "false").lower() == "true"
    exclude_pinned: bool = os.getenv("EXCLUDE_PINNED", "false").lower() == "true"