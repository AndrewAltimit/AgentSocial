"""Test configuration for bulletin board system"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TestSettings:
    """Test settings that don't require environment variables"""

    # Database
    DATABASE_URL: str = "sqlite:///:memory:"

    # App configuration
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 5000
    APP_DEBUG: bool = False

    # Agent settings
    AGENT_ANALYSIS_CUTOFF_HOURS: int = 24
    INTERNAL_NETWORK_ONLY: bool = False
    ALLOWED_AGENT_IPS: Optional[List[str]] = None

    # External services (mocked in tests)
    GITHUB_API_URL: str = "https://api.github.com"
    GITHUB_READ_TOKEN: str = "test-token"
    GITHUB_TOKEN: str = "test-token"  # Alias for GITHUB_READ_TOKEN
    NEWS_API_URL: str = "https://newsapi.org/v2"
    NEWS_API_KEY: str = "test-key"

    # GitHub Feed Settings
    GITHUB_FEED_REPO: str = "AndrewAltimit/AgentSocialFeed"
    GITHUB_FEED_BRANCH: str = "main"
    GITHUB_FEED_PATH: str = "favorites.json"

    # News Sources
    NEWS_SOURCES: Optional[List[str]] = None
    NEWS_FETCH_INTERVAL: int = 3600

    # Bulletin board API
    BULLETIN_BOARD_URL: str = "http://localhost:5000"
    BULLETIN_BOARD_API_URL: str = "http://localhost:5000"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    def __post_init__(self):
        if self.ALLOWED_AGENT_IPS is None:
            self.ALLOWED_AGENT_IPS = ["127.0.0.1/32", "10.0.0.0/8"]
        if self.NEWS_SOURCES is None:
            self.NEWS_SOURCES = ["techcrunch", "ars-technica", "hacker-news"]


# Create a singleton instance for tests
test_settings = TestSettings()
