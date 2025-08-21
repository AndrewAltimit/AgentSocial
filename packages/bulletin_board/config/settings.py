import os
from functools import lru_cache
from typing import Any, Dict


class SettingsMeta(type):
    """Metaclass to handle attribute access on Settings class"""

    def __getattr__(cls, name: str) -> Any:
        """Lazy load configuration values on attribute access"""
        cls._ensure_initialized()
        if name in cls._config_cache:
            return cls._config_cache[name]
        raise AttributeError(f"'{cls.__name__}' has no attribute '{name}'")


class Settings(metaclass=SettingsMeta):
    """Application settings with lazy loading to prevent startup crashes"""

    _initialized = False
    _config_cache: Dict[str, Any] = {}

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Initialize configuration on first access"""
        if not cls._initialized:
            cls._load_config()
            cls._initialized = True

    @classmethod
    def _load_config(cls) -> None:
        """Load all configuration from environment variables"""
        try:
            # Database
            cls._config_cache["DATABASE_URL"] = os.getenv(
                "DATABASE_URL",
                "postgresql://bulletin:bulletin@postgres:5432/bulletin_board",
            )

            # GitHub Feed Settings
            cls._config_cache["GITHUB_FEED_REPO"] = os.getenv("GITHUB_FEED_REPO", "AndrewAltimit/AgentSocialFeed")
            cls._config_cache["GITHUB_FEED_BRANCH"] = os.getenv("GITHUB_FEED_BRANCH", "main")
            cls._config_cache["GITHUB_FEED_PATH"] = os.getenv("GITHUB_FEED_PATH", "favorites.json")
            cls._config_cache["GITHUB_TOKEN"] = os.getenv("GITHUB_READ_TOKEN", "")

            # News Collector Settings
            cls._config_cache["NEWS_API_KEY"] = os.getenv("NEWS_API_KEY", "")
            cls._config_cache["NEWS_SOURCES"] = os.getenv("NEWS_SOURCES", "techcrunch,ars-technica,hacker-news").split(",")
            cls._config_cache["NEWS_FETCH_INTERVAL"] = int(os.getenv("NEWS_FETCH_INTERVAL", "3600"))

            # Agent Settings
            cls._config_cache["AGENT_ANALYSIS_CUTOFF_HOURS"] = int(os.getenv("AGENT_ANALYSIS_CUTOFF_HOURS", "24"))

            # Web App Settings
            cls._config_cache["APP_HOST"] = os.getenv("APP_HOST", "0.0.0.0")
            cls._config_cache["APP_PORT"] = int(os.getenv("APP_PORT", "8080"))
            cls._config_cache["APP_DEBUG"] = os.getenv("APP_DEBUG", "False").lower() == "true"

            # Agent connectivity settings
            cls._config_cache["BULLETIN_BOARD_URL"] = os.getenv("BULLETIN_BOARD_URL", "http://bulletin-web:8080")

            # Security
            cls._config_cache["INTERNAL_NETWORK_ONLY"] = os.getenv("INTERNAL_NETWORK_ONLY", "True").lower() == "true"
            cls._config_cache["ALLOWED_AGENT_IPS"] = os.getenv("ALLOWED_AGENT_IPS", "172.20.0.0/16").split(",")

            # Logging
            cls._config_cache["LOG_LEVEL"] = os.getenv("LOG_LEVEL", "INFO")
            cls._config_cache["LOG_FORMAT"] = os.getenv("LOG_FORMAT", "json")

            # Reaction System
            cls._config_cache["REACTION_CONFIG_URL"] = os.getenv(
                "REACTION_CONFIG_URL",
                "https://raw.githubusercontent.com/AndrewAltimit/Media/refs/heads/main/reaction/config.yaml",
            )
        except Exception as e:
            # Provide sensible defaults on configuration error
            import sys

            print(f"Warning: Error loading configuration: {e}", file=sys.stderr)
            cls._config_cache = cls._get_default_config()

    @classmethod
    def _get_default_config(cls) -> Dict[str, Any]:
        """Return default configuration when environment loading fails"""
        return {
            "DATABASE_URL": ("postgresql://bulletin:bulletin@" "postgres:5432/bulletin_board"),
            "GITHUB_FEED_REPO": "AndrewAltimit/AgentSocialFeed",
            "GITHUB_FEED_BRANCH": "main",
            "GITHUB_FEED_PATH": "favorites.json",
            "GITHUB_TOKEN": "",
            "NEWS_API_KEY": "",
            "NEWS_SOURCES": ["techcrunch", "ars-technica", "hacker-news"],
            "NEWS_FETCH_INTERVAL": 3600,
            "AGENT_ANALYSIS_CUTOFF_HOURS": 24,
            "APP_HOST": "0.0.0.0",
            "APP_PORT": 8080,
            "APP_DEBUG": False,
            "BULLETIN_BOARD_URL": "http://bulletin-web:8080",
            "INTERNAL_NETWORK_ONLY": True,
            "ALLOWED_AGENT_IPS": ["172.20.0.0/16"],
            "LOG_LEVEL": "INFO",
            "LOG_FORMAT": "json",
            "REACTION_CONFIG_URL": (
                "https://raw.githubusercontent.com/AndrewAltimit/" "Media/refs/heads/main/reaction/config.yaml"
            ),
        }

    @classmethod
    @lru_cache(maxsize=1)
    def get_config(cls) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        cls._ensure_initialized()
        return cls._config_cache.copy()
