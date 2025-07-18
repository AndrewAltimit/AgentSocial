import os
from typing import Any, Dict


class Settings:
    """Application settings"""

    # Database
    DATABASE_URL = os.getenv(
        "DATABASE_URL", "postgresql://bulletin:bulletin@postgres:5432/bulletin_board"
    )

    # GitHub Feed Settings
    GITHUB_FEED_REPO = os.getenv("GITHUB_FEED_REPO", "AndrewAltimit/AgentSocialFeed")
    GITHUB_FEED_BRANCH = os.getenv("GITHUB_FEED_BRANCH", "main")
    GITHUB_FEED_PATH = os.getenv("GITHUB_FEED_PATH", "favorites.json")
    GITHUB_TOKEN = os.getenv(
        "GITHUB_READ_TOKEN", ""
    )  # Read-only token for private repo

    # News Collector Settings
    NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
    NEWS_SOURCES = os.getenv(
        "NEWS_SOURCES", "techcrunch,ars-technica,hacker-news"
    ).split(",")
    NEWS_FETCH_INTERVAL = int(os.getenv("NEWS_FETCH_INTERVAL", "3600"))  # 1 hour

    # Agent Settings
    AGENT_ANALYSIS_CUTOFF_HOURS = int(os.getenv("AGENT_ANALYSIS_CUTOFF_HOURS", "24"))

    # Web App Settings
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", "8080"))
    APP_DEBUG = os.getenv("APP_DEBUG", "False").lower() == "true"

    # Agent connectivity settings
    BULLETIN_BOARD_URL = os.getenv("BULLETIN_BOARD_URL", "http://bulletin-web:8080")

    # Security
    INTERNAL_NETWORK_ONLY = os.getenv("INTERNAL_NETWORK_ONLY", "True").lower() == "true"
    ALLOWED_AGENT_IPS = os.getenv("ALLOWED_AGENT_IPS", "172.20.0.0/16").split(",")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "json")  # "json" or "text"

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith("_") and not callable(getattr(cls, key))
        }
