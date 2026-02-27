"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central config — all values from env vars with sensible defaults."""
    """Application configuration loaded from environment variables.

    All values are read at import time from the process environment (or a
    ``.env`` file loaded by ``python-dotenv``).  Sensible defaults are
    provided where possible; credentials must be supplied explicitly.
    """
    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "platform_v3")
    DB_USER = os.getenv("DB_USER", "")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    # Anthropic
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    # Web Search
    BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")

    @classmethod
    def db_dsn(cls) -> str:
        """Return a libpq-compatible PostgreSQL connection string."""
        return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
