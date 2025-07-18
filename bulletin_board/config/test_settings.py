"""Test configuration for bulletin board system"""

import os
from dataclasses import dataclass


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
    ALLOWED_AGENT_IPS: list = None

    # External services (mocked in tests)
    GITHUB_API_URL: str = "https://api.github.com"
    GITHUB_READ_TOKEN: str = "test-token"
    NEWS_API_URL: str = "https://newsapi.org/v2"
    NEWS_API_KEY: str = "test-key"

    # Bulletin board API
    BULLETIN_BOARD_API_URL: str = "http://localhost:5000"

    def __post_init__(self):
        if self.ALLOWED_AGENT_IPS is None:
            self.ALLOWED_AGENT_IPS = ["127.0.0.1/32", "10.0.0.0/8"]


# Create a singleton instance for tests
test_settings = TestSettings()
