#!/usr/bin/env python3
"""
Full integration test demonstrating bulletin board functionality with mock data
"""
import json
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bulletin_board.agents.agent_runner import ClaudeAgent  # noqa: E402
from bulletin_board.agents.feed_collector import (  # noqa: E402
    GitHubFavoritesCollector,
    NewsCollector,
)
from bulletin_board.config.settings import Settings  # noqa: E402
from bulletin_board.database.models import (  # noqa: E402
    AgentProfile,
    Comment,
    Post,
    create_tables,
    get_db_engine,
)


@pytest.fixture(scope="function")
def test_db():
    """Create a test database"""
    from sqlalchemy.orm import sessionmaker

    # Use in-memory database to avoid file permission issues
    engine = get_db_engine("sqlite:///:memory:")
    create_tables(engine)

    # Create a new session directly instead of using get_session
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create test agents
    agents = [
        AgentProfile(
            agent_id="test_claude",
            display_name="Test Claude",
            agent_software="claude_code",
            role_description="Test Claude agent",
            context_instructions="Be helpful in testing",
            is_active=True,
        ),
        AgentProfile(
            agent_id="test_gemini",
            display_name="Test Gemini",
            agent_software="gemini_cli",
            role_description="Test Gemini agent",
            context_instructions="Be analytical in testing",
            is_active=True,
        ),
    ]

    for agent in agents:
        session.add(agent)
    session.commit()

    print(f"✅ Created {len(agents)} test agents")

    yield engine, session

    # Cleanup
    session.close()
    engine.dispose()


@pytest.fixture
def session(test_db):
    """Get the test session"""
    engine, session = test_db
    return session


@pytest.mark.asyncio
async def test_feed_collection(session):
    """Test feed collection with mock APIs"""
    print("\n🔄 Testing feed collection...")

    # Mock GitHub response
    mock_github_data = [
        {
            "id": "gh_1",
            "title": "Awesome AI Tool",
            "content": "Revolutionary AI tool for developers",
            "url": "https://github.com/test/ai-tool",
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {"stars": 2500, "language": "Python"},
        }
    ]

    # Mock News response
    mock_news_data = {
        "status": "ok",
        "articles": [
            {
                "title": "AI Breakthrough Changes Everything",
                "description": "Major AI advancement announced today",
                "url": "https://news.test/ai-breakthrough",
                "publishedAt": datetime.utcnow().isoformat() + "Z",
                "source": {"name": "Tech News"},
                "author": "Jane Doe",
            }
        ],
    }

    # Test GitHub collector
    github_collector = GitHubFavoritesCollector(session)
    with patch("aiohttp.ClientSession") as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_github_data))

        # Set up the mock chain properly
        mock_get = AsyncMock()
        mock_get.__aenter__.return_value = mock_response

        # Configure the session mock
        mock_session_instance = AsyncMock()
        mock_session_instance.get = Mock(return_value=mock_get)
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        with patch.object(github_collector, "token", "mock_token"):
            github_count = await github_collector.fetch_and_store()

    print(f"✅ Collected {github_count} GitHub favorites")

    # Test News collector
    news_collector = NewsCollector(session)
    with patch("aiohttp.ClientSession") as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_news_data)

        # Set up the mock chain properly
        mock_get = AsyncMock()
        mock_get.__aenter__.return_value = mock_response

        # Configure the session mock
        mock_session_instance = AsyncMock()
        mock_session_instance.get = Mock(return_value=mock_get)
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        with patch.object(news_collector, "api_key", "mock_api_key"):
            news_count = await news_collector.fetch_and_store()

    print(f"✅ Collected {news_count} news articles")

    # Verify posts in database
    posts = session.query(Post).all()
    print(f"📊 Total posts in database: {len(posts)}")
    for post in posts:
        print(f"   - [{post.source}] {post.title}")


@pytest.mark.asyncio
async def test_agent_commenting(session):
    """Test agent commenting behavior"""
    print("\n💬 Testing agent commenting...")

    # Get posts for agents to comment on
    posts = session.query(Post).all()

    # Mock the agent profile lookup
    mock_agent_profile = AgentProfile(
        agent_id="test_claude",
        display_name="Test Claude",
        agent_software="claude_code",
        role_description="Test Claude agent",
        context_instructions="Be helpful in testing",
    )

    # Mock agent behavior
    with patch(
        "bulletin_board.agents.agent_runner.get_agent_by_id",
        return_value=mock_agent_profile,
    ):
        claude_agent = ClaudeAgent("test_claude")

        # Prepare mock posts data
        mock_posts_data = []
        for post in posts:
            mock_posts_data.append(
                {
                    "id": post.id,
                    "title": post.title,
                    "content": post.content,
                    "source": post.source,
                    "comments": [],
                }
            )

        # Mock API calls
        with patch("aiohttp.ClientSession") as mock_session:
            # Mock getting posts
            get_response = AsyncMock()
            get_response.status = 200
            get_response.json = AsyncMock(return_value=mock_posts_data)

            # Mock posting comments
            post_response = AsyncMock()
            post_response.status = 201

            # Set up the mock chain properly for GET
            mock_get = AsyncMock()
            mock_get.__aenter__.return_value = get_response

            # Set up the mock chain properly for POST
            mock_post = AsyncMock()
            mock_post.__aenter__.return_value = post_response

            # Configure the session mock
            mock_session_instance = AsyncMock()
            mock_session_instance.get = Mock(return_value=mock_get)
            mock_session_instance.post = Mock(return_value=mock_post)
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            # Make agent always comment (override random)
            with patch("random.random", return_value=0.1):
                comments_made = await claude_agent.analyze_and_comment(mock_posts_data)

        print(f"✅ Claude agent made {comments_made} comments")

    # Manually add comments to database for demonstration
    for i, post in enumerate(posts):
        comment = Comment(
            post_id=post.id,
            agent_id="test_claude",
            content=f"This is a thoughtful comment about {post.title}",
        )
        session.add(comment)

    session.commit()

    # Add a reply from Gemini
    first_comment = session.query(Comment).first()
    if first_comment:
        reply = Comment(
            post_id=first_comment.post_id,
            agent_id="test_gemini",
            parent_comment_id=first_comment.id,
            content="I agree with your analysis, and would add...",
        )
        session.add(reply)
        session.commit()
        print("✅ Gemini agent replied to Claude's comment")


def test_web_interface(test_db):
    """Test web interface endpoints"""
    print("\n🌐 Testing web interface...")

    engine, session = test_db

    # Add some test posts for the web interface to display
    from datetime import timedelta

    post1 = Post(
        external_id="web_test_1",
        source="favorites",
        title="Test Favorite for Web",
        content="This is a test favorite post",
        created_at=datetime.utcnow() - timedelta(hours=1),
    )
    post2 = Post(
        external_id="web_test_2",
        source="news",
        title="Test News for Web",
        content="This is a test news post",
        created_at=datetime.utcnow() - timedelta(hours=2),
    )
    session.add(post1)
    session.add(post2)
    session.commit()

    # Add a comment
    comment = Comment(
        post_id=post1.id,
        agent_id="test_claude",
        content="This is a test comment on the web post",
    )
    session.add(comment)
    session.commit()

    post1_id = post1.id

    # Override database URL for Flask app
    original_url = Settings.DATABASE_URL
    Settings.DATABASE_URL = "sqlite:///:memory:"  # Use in-memory for Flask app too

    # Patch the database functions to use our test database
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=engine)

    def get_test_session(engine=None):
        return Session()

    with patch("bulletin_board.database.models.get_db_engine", return_value=engine):
        with patch(
            "bulletin_board.database.models.get_session", side_effect=get_test_session
        ):
            # Import app after patching
            from bulletin_board.app.app import app

            app.config["TESTING"] = True
            with app.test_client() as client:
                # Test getting posts
                response = client.get("/api/posts")
                assert response.status_code == 200
                posts = json.loads(response.data)
                print(f"✅ API returned {len(posts)} posts")

                # Test getting single post with comments
                response = client.get(f"/api/posts/{post1_id}")
                assert response.status_code == 200
                post_data = json.loads(response.data)
                print(
                    f"✅ Retrieved post '{post_data['title']}' with "  # noqa: E501
                    f"{len(post_data['comments'])} comments"
                )

                # Test getting agents
                response = client.get("/api/agents")
                assert response.status_code == 200
                agents = json.loads(response.data)
                print(f"✅ API returned {len(agents)} active agents")

                # Test main page
                response = client.get("/")
                assert response.status_code == 200
                print("✅ Web interface homepage loads successfully")

    # Restore original URL
    Settings.DATABASE_URL = original_url


# Tests can be run with: pytest tests/test_bulletin_board_full.py -v
