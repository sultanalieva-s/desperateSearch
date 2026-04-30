"""
config.py — All environment variables and constants.
Copy .env.example → .env and fill in your keys.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent


@dataclass
class Settings:
    # ── Required ─────────────────────────────────────────────────────────────
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # ── Optional platform credentials ────────────────────────────────────────
    HH_CLIENT_ID: str     = os.getenv("HH_CLIENT_ID", "")
    HH_CLIENT_SECRET: str = os.getenv("HH_CLIENT_SECRET", "")
    HH_ACCESS_TOKEN: str  = os.getenv("HH_ACCESS_TOKEN", "")   # OAuth2 bearer

    LINKEDIN_EMAIL: str    = os.getenv("LINKEDIN_EMAIL", "")
    LINKEDIN_PASSWORD: str = os.getenv("LINKEDIN_PASSWORD", "")

    GLASSDOOR_EMAIL: str    = os.getenv("GLASSDOOR_EMAIL", "")
    GLASSDOOR_PASSWORD: str = os.getenv("GLASSDOOR_PASSWORD", "")

    DJINNI_EMAIL: str    = os.getenv("DJINNI_EMAIL", "")
    DJINNI_PASSWORD: str = os.getenv("DJINNI_PASSWORD", "")

    # Telegram channel usernames/IDs to scan (comma-separated)
    TG_JOB_CHANNELS: list[str] = field(default_factory=lambda: [
        c.strip() for c in os.getenv("TG_JOB_CHANNELS", "").split(",") if c.strip()
    ])

    # ── Paths ─────────────────────────────────────────────────────────────────
    STORAGE_DIR: Path = BASE_DIR / "storage"
    CV_DIR: Path      = BASE_DIR / "storage" / "cvs"
    DB_PATH: Path     = BASE_DIR / "storage" / "jobs.db"

    # ── Scan interval (seconds) ───────────────────────────────────────────────
    SCAN_INTERVAL: int = int(os.getenv("SCAN_INTERVAL", "1800"))   # 30 min default

    # ── Claude model ──────────────────────────────────────────────────────────
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    COVER_LETTER_MAX_TOKENS: int = 800

    def validate(self) -> None:
        missing = [k for k in ("TELEGRAM_TOKEN", "ANTHROPIC_API_KEY") if not getattr(self, k)]
        if missing:
            raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")

    def ensure_dirs(self) -> None:
        self.STORAGE_DIR.mkdir(exist_ok=True)
        self.CV_DIR.mkdir(exist_ok=True)


settings = Settings()
settings.ensure_dirs()
