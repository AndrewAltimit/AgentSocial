from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from packages.bulletin_board.database.models import AgentProfile, Post

# Import all fixtures from the fixtures module
from tests.bulletin_board.fixtures import *  # noqa: F403, F401

# test_engine and test_session are now imported from fixtures.py


# Create aliases for backward compatibility
@pytest.fixture
def test_engine(test_db_engine):
    """Alias for test_db_engine for backward compatibility"""
    return test_db_engine


@pytest.fixture
def test_session(test_db_session):
    """Alias for test_db_session for backward compatibility"""
    return test_db_session


@pytest.fixture
def mock_agent_profiles():
    """Mock agent profiles for testing"""
    profiles = [
        {
            "agent_id": "test_claude_1",
            "display_name": "TestClaude1",
            "agent_software": "claude_code",
            "role_description": "Test Claude agent 1",
            "context_instructions": "Be helpful",
        },
        {
            "agent_id": "test_gemini_1",
            "display_name": "TestGemini1",
            "agent_software": "gemini_cli",
            "role_description": "Test Gemini agent 1",
            "context_instructions": "Be analytical",
        },
    ]

    # Patch the AGENT_PROFILES at module level
    with patch("packages.bulletin_board.agents.agent_profiles.AGENT_PROFILES", profiles):
        with patch("packages.bulletin_board.agents.agent_runner.get_agent_by_id") as mock_get:
            # Make get_agent_by_id return the correct profile
            def get_by_id(agent_id):
                for p in profiles:
                    if p["agent_id"] == agent_id:
                        return p
                return None

            mock_get.side_effect = get_by_id
            yield profiles


@pytest.fixture
def mock_agents(test_db_session, mock_agent_profiles):
    """Create mock agent profiles"""
    agents = [
        AgentProfile(
            agent_id="test_claude_1",
            display_name="TestClaude1",
            agent_software="claude_code",
            role_description="Test Claude agent 1",
            context_instructions="Be helpful",
            is_active=True,
        ),
        AgentProfile(
            agent_id="test_gemini_1",
            display_name="TestGemini1",
            agent_software="gemini_cli",
            role_description="Test Gemini agent 1",
            context_instructions="Be analytical",
            is_active=True,
        ),
    ]

    for agent in agents:
        test_db_session.add(agent)
    test_db_session.commit()

    return agents


@pytest.fixture
def mock_posts(test_db_session):
    """Create mock posts for testing"""
    posts = [
        Post(
            external_id="github_1",
            source="favorites",
            title="Test GitHub Favorite",
            content="This is a test favorite from GitHub",
            url="https://github.com/test/repo",
            metadata={"stars": 100},
            created_at=datetime.utcnow() - timedelta(hours=2),
        ),
        Post(
            external_id="news_1",
            source="news",
            title="Breaking Tech News",
            content="Amazing new technology announced",
            url="https://technews.com/article1",
            metadata={"author": "Tech Writer"},
            created_at=datetime.utcnow() - timedelta(hours=12),
        ),
        Post(
            external_id="old_post",
            source="news",
            title="Old News",
            content="This news is too old",
            url="https://oldnews.com/article",
            metadata={},
            created_at=datetime.utcnow() - timedelta(hours=48),  # Too old
        ),
    ]

    for post in posts:
        test_db_session.add(post)
    test_db_session.commit()

    return posts


@pytest.fixture
def mock_github_response():
    """Mock GitHub API response for favorites"""
    return [
        {
            "id": "fav_1",
            "title": "Awesome Project",
            "content": "This project is amazing for AI development",
            "url": "https://github.com/awesome/project",
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {"language": "Python"},
        },
        {
            "id": "fav_2",
            "title": "Cool Tool",
            "content": "A cool tool for developers",
            "url": "https://github.com/cool/tool",
            "created_at": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
            "metadata": {"stars": 500},
        },
    ]


@pytest.fixture
def mock_news_response():
    """Mock News API response"""
    return {
        "status": "ok",
        "totalResults": 2,
        "articles": [
            {
                "source": {"id": "techcrunch", "name": "TechCrunch"},
                "author": "Jane Doe",
                "title": "AI Breakthrough Announced",
                "description": "Major breakthrough in AI technology",
                "url": "https://techcrunch.com/ai-breakthrough",
                "publishedAt": datetime.utcnow().isoformat() + "Z",
                "content": "Full article content here...",
            },
            {
                "source": {"id": "ars-technica", "name": "Ars Technica"},
                "author": "John Smith",
                "title": "New Programming Language Released",
                "description": "A new language that changes everything",
                "url": "https://arstechnica.com/new-language",
                "publishedAt": (datetime.utcnow() - timedelta(hours=3)).isoformat() + "Z",
                "content": "Detailed article content...",
            },
        ],
    }
