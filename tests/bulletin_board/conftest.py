import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bulletin_board.database.models import Base, AgentProfile, Post, Comment


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create a test database session"""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_agents(test_session):
    """Create mock agent profiles"""
    agents = [
        AgentProfile(
            agent_id="test_claude_1",
            display_name="TestClaude1",
            agent_software="claude_code",
            role_description="Test Claude agent 1",
            context_instructions="Be helpful",
            is_active=True
        ),
        AgentProfile(
            agent_id="test_gemini_1",
            display_name="TestGemini1",
            agent_software="gemini_cli",
            role_description="Test Gemini agent 1",
            context_instructions="Be analytical",
            is_active=True
        ),
    ]
    
    for agent in agents:
        test_session.add(agent)
    test_session.commit()
    
    return agents


@pytest.fixture
def mock_posts(test_session):
    """Create mock posts for testing"""
    posts = [
        Post(
            external_id="github_1",
            source="favorites",
            title="Test GitHub Favorite",
            content="This is a test favorite from GitHub",
            url="https://github.com/test/repo",
            metadata={"stars": 100},
            created_at=datetime.utcnow() - timedelta(hours=2)
        ),
        Post(
            external_id="news_1",
            source="news",
            title="Breaking Tech News",
            content="Amazing new technology announced",
            url="https://technews.com/article1",
            metadata={"author": "Tech Writer"},
            created_at=datetime.utcnow() - timedelta(hours=12)
        ),
        Post(
            external_id="old_post",
            source="news",
            title="Old News",
            content="This news is too old",
            url="https://oldnews.com/article",
            metadata={},
            created_at=datetime.utcnow() - timedelta(hours=48)  # Too old
        ),
    ]
    
    for post in posts:
        test_session.add(post)
    test_session.commit()
    
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
            "metadata": {"language": "Python"}
        },
        {
            "id": "fav_2",
            "title": "Cool Tool",
            "content": "A cool tool for developers",
            "url": "https://github.com/cool/tool",
            "created_at": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
            "metadata": {"stars": 500}
        }
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
                "content": "Full article content here..."
            },
            {
                "source": {"id": "ars-technica", "name": "Ars Technica"},
                "author": "John Smith",
                "title": "New Programming Language Released",
                "description": "A new language that changes everything",
                "url": "https://arstechnica.com/new-language",
                "publishedAt": (datetime.utcnow() - timedelta(hours=3)).isoformat() + "Z",
                "content": "Detailed article content..."
            }
        ]
    }