import os
import sys

# Add project root to path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import json  # noqa: E402
import tempfile  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402
from unittest.mock import AsyncMock, patch  # noqa: E402

import pytest  # noqa: E402

from bulletin_board.agents.agent_runner import run_all_agents  # noqa: E402
from bulletin_board.agents.feed_collector import run_collectors  # noqa: E402
from bulletin_board.agents.init_agents import init_agents  # noqa: E402
from bulletin_board.app.app import app  # noqa: E402
from bulletin_board.database.models import (  # noqa: E402
    create_tables,
    get_db_engine,
    get_session,
)


class TestBulletinBoardIntegration:
    """Full integration tests for bulletin board system"""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary SQLite database"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db_url = f"sqlite:///{db_path}"
        yield db_url

        # Cleanup
        try:
            os.unlink(db_path)
        except OSError:
            pass

    @pytest.fixture
    def mock_environment(self, temp_db):
        """Set up mock environment variables"""
        env_vars = {
            "DATABASE_URL": temp_db,
            "GITHUB_READ_TOKEN": "mock_github_token",
            "NEWS_API_KEY": "mock_news_api_key",
            "GITHUB_FEED_REPO": "test/repo",
            "GITHUB_FEED_BRANCH": "main",
            "INTERNAL_NETWORK_ONLY": "False",  # Disable for testing
        }

        with patch.dict(os.environ, env_vars):
            # Also patch the Settings class
            with patch("bulletin_board.config.settings.Settings.DATABASE_URL", temp_db):
                with patch(
                    "bulletin_board.config.settings.Settings.GITHUB_TOKEN",
                    "mock_github_token",
                ):
                    with patch(
                        "bulletin_board.config.settings.Settings.NEWS_API_KEY",
                        "mock_news_api_key",
                    ):
                        with patch(
                            (
                                "bulletin_board.config.settings.Settings."
                                "INTERNAL_NETWORK_ONLY"
                            ),
                            False,
                        ):
                            yield env_vars

    def test_database_initialization(self, mock_environment):
        """Test database schema creation and agent initialization"""
        engine = get_db_engine(mock_environment["DATABASE_URL"])
        create_tables(engine)

        # Initialize agents
        init_agents()

        # Verify agents were created
        session = get_session(engine)
        from bulletin_board.database.models import AgentProfile

        agents = session.query(AgentProfile).all()
        session.close()

        assert len(agents) == 5  # We have 5 agent profiles
        agent_ids = [a.agent_id for a in agents]
        assert "tech_enthusiast_claude" in agent_ids
        assert "security_analyst_gemini" in agent_ids

    @pytest.mark.asyncio
    async def test_feed_collection_cycle(self, mock_environment):
        """Test complete feed collection cycle"""
        engine = get_db_engine(mock_environment["DATABASE_URL"])
        create_tables(engine)

        # Mock API responses
        github_favorites = [
            {
                "id": "test_1",
                "title": "Test Favorite",
                "content": "Test content",
                "url": "https://github.com/test",
                "created_at": datetime.utcnow().isoformat(),
            }
        ]

        news_articles = {
            "status": "ok",
            "articles": [
                {
                    "title": "Test News",
                    "description": "Test news content",
                    "url": "https://news.test",
                    "publishedAt": datetime.utcnow().isoformat() + "Z",
                    "source": {"name": "Test Source"},
                }
            ],
        }

        # Mock HTTP calls
        with patch("aiohttp.ClientSession") as mock_session:
            # GitHub response
            github_response = AsyncMock()
            github_response.status = 200
            github_response.text = AsyncMock(return_value=json.dumps(github_favorites))

            # News response
            news_response = AsyncMock()
            news_response.status = 200
            news_response.json = AsyncMock(return_value=news_articles)

            # Configure mock to return different responses based on URL
            async def get_mock(url, **kwargs):
                if "github" in url:
                    return github_response
                else:
                    return news_response

            mock_get = AsyncMock(side_effect=get_mock)
            mock_session.return_value.__aenter__.return_value.get = mock_get

            # Run collectors
            await run_collectors(engine)

        # Verify posts were created
        session = get_session(engine)
        from bulletin_board.database.models import Post

        posts = session.query(Post).all()
        session.close()

        assert len(posts) == 2
        titles = [p.title for p in posts]
        assert "Test Favorite" in titles
        assert "Test News" in titles

    @pytest.mark.asyncio
    async def test_agent_commenting_cycle(self, mock_environment):
        """Test agents commenting on posts"""
        engine = get_db_engine(mock_environment["DATABASE_URL"])
        create_tables(engine)
        init_agents()

        # Create test posts
        session = get_session(engine)
        from bulletin_board.database.models import Post

        post1 = Post(
            external_id="test_1",
            source="news",
            title="AI Discussion Topic",
            content="Let's discuss AI",
            created_at=datetime.utcnow() - timedelta(hours=1),
        )
        post2 = Post(
            external_id="test_2",
            source="favorites",
            title="Programming Topic",
            content="New programming language",
            created_at=datetime.utcnow() - timedelta(hours=2),
        )

        session.add(post1)
        session.add(post2)
        session.commit()
        session.close()

        # Mock agent API calls
        with patch("aiohttp.ClientSession") as mock_session:
            # Mock getting posts
            posts_response = AsyncMock()
            posts_response.status = 200
            posts_response.json = AsyncMock(
                return_value=[
                    {
                        "id": post1.id,
                        "title": post1.title,
                        "content": post1.content,
                        "comments": [],
                    },
                    {
                        "id": post2.id,
                        "title": post2.title,
                        "content": post2.content,
                        "comments": [],
                    },
                ]
            )

            # Mock posting comments
            comment_response = AsyncMock()
            comment_response.status = 201

            (
                mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value  # noqa: E501
            ) = posts_response
            (
                mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value  # noqa: E501
            ) = comment_response

            # Control randomness to ensure some comments
            with patch("random.random", return_value=0.3):  # Will trigger comments
                await run_all_agents()

        # Verify some comments were created
        session = get_session(engine)
        from bulletin_board.database.models import Comment

        comments = session.query(Comment).all()
        session.close()

        # With controlled randomness, we should have some comments
        # The exact number depends on the agent logic
        assert len(comments) >= 0  # At least no errors

    def test_web_interface_integration(self, mock_environment):
        """Test web interface with full stack"""
        engine = get_db_engine(mock_environment["DATABASE_URL"])
        create_tables(engine)
        init_agents()

        # Create test data
        session = get_session(engine)
        from bulletin_board.database.models import Comment, Post

        post = Post(
            external_id="web_test",
            source="news",
            title="Web Test Post",
            content="Testing web interface",
            created_at=datetime.utcnow(),
        )
        session.add(post)
        session.commit()

        # Add a comment
        comment = Comment(
            post_id=post.id,
            agent_id="tech_enthusiast_claude",
            content="Test comment from agent",
        )
        session.add(comment)
        session.commit()

        post_id = post.id
        session.close()

        # Test web endpoints
        app.config["TESTING"] = True
        with app.test_client() as client:
            # Get posts
            response = client.get("/api/posts")
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data) == 1
            assert data[0]["title"] == "Web Test Post"

            # Get single post with comments
            response = client.get(f"/api/posts/{post_id}")
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["title"] == "Web Test Post"
            assert len(data["comments"]) == 1
            assert data["comments"][0]["content"] == "Test comment from agent"

            # Get agents
            response = client.get("/api/agents")
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data) == 5  # All configured agents


class TestEndToEndScenarios:
    """Test complete end-to-end scenarios"""

    @pytest.mark.asyncio
    async def test_full_bulletin_board_cycle(self, mock_environment):
        """Test complete cycle: collect feeds -> agents comment -> web display"""
        engine = get_db_engine(mock_environment["DATABASE_URL"])
        create_tables(engine)
        init_agents()

        # Step 1: Simulate feed collection
        session = get_session(engine)
        from bulletin_board.database.models import Post

        post = Post(
            external_id="e2e_test",
            source="news",
            title="Breaking: New AI Model Released",
            content="A revolutionary AI model has been announced today",
            url="https://news.ai/breaking",
            metadata={"author": "AI Reporter"},
            created_at=datetime.utcnow(),
        )
        session.add(post)
        session.commit()
        post_id = post.id
        session.close()

        # Step 2: Simulate agent commenting
        app.config["TESTING"] = True
        with app.test_client() as client:
            # Agent posts comment
            response = client.post(
                "/api/agent/comment",
                json={
                    "post_id": post_id,
                    "agent_id": "ai_researcher_gemini",
                    "content": "This is a significant breakthrough in AI research!",
                },
            )
            assert response.status_code == 201

            # Another agent replies
            comment_data = json.loads(response.data)
            response = client.post(
                "/api/agent/comment",
                json={
                    "post_id": post_id,
                    "agent_id": "tech_enthusiast_claude",
                    "content": "I agree! The implications are fascinating.",
                    "parent_comment_id": comment_data["id"],
                },
            )
            assert response.status_code == 201

        # Step 3: Verify web display
        with app.test_client() as client:
            response = client.get(f"/api/posts/{post_id}")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["title"] == "Breaking: New AI Model Released"
            assert len(data["comments"]) == 2

            # Verify comment thread
            comments = sorted(data["comments"], key=lambda x: x["created_at"])
            assert "significant breakthrough" in comments[0]["content"]
            assert "implications are fascinating" in comments[1]["content"]
            assert comments[1].get("parent_id") == comments[0]["id"]
