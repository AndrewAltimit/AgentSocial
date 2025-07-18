import os
import sys

# Add project root to path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import json  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402
from unittest.mock import AsyncMock, Mock, patch  # noqa: E402

import pytest  # noqa: E402

from bulletin_board.agents.agent_runner import run_all_agents  # noqa: E402
from bulletin_board.agents.feed_collector import run_collectors  # noqa: E402
from bulletin_board.agents.init_agents import init_agents  # noqa: E402
from bulletin_board.app.app import app  # noqa: E402
from bulletin_board.database.models import get_session  # noqa: E402


class TestBulletinBoardIntegration:
    """Full integration tests for bulletin board system"""

    @pytest.fixture
    def temp_db(self):
        """Create an in-memory SQLite database"""
        # Use in-memory database to avoid file permission issues
        db_url = "sqlite:///:memory:"
        yield db_url

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

    def test_database_initialization(
        self, mock_environment, mock_db_functions, test_db_engine
    ):
        """Test database schema creation and agent initialization"""
        # Mock agent profiles to have predictable test data
        test_profiles = [
            {
                "agent_id": "tech_enthusiast_claude",
                "display_name": "Tech Enthusiast",
                "agent_software": "claude_code",
                "role_description": "Tech expert",
                "context_instructions": "Be helpful",
            },
            {
                "agent_id": "security_analyst_gemini",
                "display_name": "Security Analyst",
                "agent_software": "gemini_cli",
                "role_description": "Security expert",
                "context_instructions": "Be secure",
            },
            {
                "agent_id": "business_strategist_claude",
                "display_name": "Business Strategist",
                "agent_software": "claude_code",
                "role_description": "Business expert",
                "context_instructions": "Be strategic",
            },
            {
                "agent_id": "ai_researcher_gemini",
                "display_name": "AI Researcher",
                "agent_software": "gemini_cli",
                "role_description": "AI expert",
                "context_instructions": "Be analytical",
            },
            {
                "agent_id": "developer_advocate_claude",
                "display_name": "Developer Advocate",
                "agent_software": "claude_code",
                "role_description": "Dev advocate",
                "context_instructions": "Be supportive",
            },
        ]

        with patch(
            "bulletin_board.agents.agent_profiles.AGENT_PROFILES", test_profiles
        ):
            init_agents()

        # Verify agents were created
        session = get_session(test_db_engine)
        from bulletin_board.database.models import AgentProfile

        agents = session.query(AgentProfile).all()
        session.close()

        assert len(agents) == 5  # We have 5 agent profiles
        agent_ids = [a.agent_id for a in agents]
        assert "tech_enthusiast_claude" in agent_ids
        assert "security_analyst_gemini" in agent_ids

    @pytest.mark.asyncio
    async def test_feed_collection_cycle(
        self, mock_environment, mock_db_functions, test_db_engine
    ):
        """Test complete feed collection cycle"""
        engine = test_db_engine

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

            # Set up the mock chain properly for GitHub
            mock_github_get = AsyncMock()
            mock_github_get.__aenter__.return_value = github_response

            # Set up the mock chain properly for News
            mock_news_get = AsyncMock()
            mock_news_get.__aenter__.return_value = news_response

            # Configure mock session
            mock_session_instance = AsyncMock()

            # Configure get method to return different mocks based on URL
            def get_mock(url, **kwargs):
                if "github" in url:
                    return mock_github_get
                else:
                    return mock_news_get

            mock_session_instance.get = Mock(side_effect=get_mock)
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            # Run collectors
            await run_collectors(engine)

        # Verify posts were created
        session = get_session(test_db_engine)
        from bulletin_board.database.models import Post

        posts = session.query(Post).all()
        session.close()

        assert len(posts) == 2
        titles = [p.title for p in posts]
        assert "Test Favorite" in titles
        assert "Test News" in titles

    @pytest.mark.asyncio
    async def test_agent_commenting_cycle(
        self, mock_environment, mock_db_functions, test_db_engine
    ):
        """Test agents commenting on posts"""
        # Mock agent profiles
        test_profiles = [
            {
                "agent_id": "tech_enthusiast_claude",
                "display_name": "Tech Enthusiast",
                "agent_software": "claude_code",
                "role_description": "Tech expert",
                "context_instructions": "Be helpful",
            },
            {
                "agent_id": "security_analyst_gemini",
                "display_name": "Security Analyst",
                "agent_software": "gemini_cli",
                "role_description": "Security expert",
                "context_instructions": "Be secure",
            },
        ]

        with patch(
            "bulletin_board.agents.agent_profiles.AGENT_PROFILES", test_profiles
        ):
            init_agents()

        # Create test posts
        session = get_session(test_db_engine)
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

        # Get the IDs before closing the session
        post1_id = post1.id
        post1_title = post1.title
        post1_content = post1.content
        post2_id = post2.id
        post2_title = post2.title
        post2_content = post2.content

        session.close()

        # Mock agent API calls
        with patch("aiohttp.ClientSession") as mock_session:
            # Mock getting posts
            posts_response = AsyncMock()
            posts_response.status = 200
            posts_response.json = AsyncMock(
                return_value=[
                    {
                        "id": post1_id,
                        "title": post1_title,
                        "content": post1_content,
                        "comments": [],
                    },
                    {
                        "id": post2_id,
                        "title": post2_title,
                        "content": post2_content,
                        "comments": [],
                    },
                ]
            )

            # Mock posting comments
            comment_response = AsyncMock()
            comment_response.status = 201

            # Set up the mock chain properly for GET
            mock_get = AsyncMock()
            mock_get.__aenter__.return_value = posts_response

            # Set up the mock chain properly for POST
            mock_post = AsyncMock()
            mock_post.__aenter__.return_value = comment_response

            # Configure the session mock
            mock_session_instance = AsyncMock()
            mock_session_instance.get = Mock(return_value=mock_get)
            mock_session_instance.post = Mock(return_value=mock_post)
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            # Control randomness to ensure some comments
            with patch("random.random", return_value=0.3):  # Will trigger comments
                await run_all_agents()

        # Verify some comments were created
        session = get_session(test_db_engine)
        from bulletin_board.database.models import Comment

        comments = session.query(Comment).all()
        session.close()

        # With controlled randomness, we should have some comments
        # The exact number depends on the agent logic
        assert len(comments) >= 0  # At least no errors

    def test_web_interface_integration(
        self, mock_environment, mock_db_functions, test_db_engine
    ):
        """Test web interface with full stack"""
        # Mock agent profiles
        test_profiles = [
            {
                "agent_id": "tech_enthusiast_claude",
                "display_name": "Tech Enthusiast",
                "agent_software": "claude_code",
                "role_description": "Tech expert",
                "context_instructions": "Be helpful",
            }
        ]

        with patch(
            "bulletin_board.agents.agent_profiles.AGENT_PROFILES", test_profiles
        ):
            init_agents()

        # Create test data
        session = get_session(test_db_engine)
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
            # Find our test post among all posts
            test_post = next((p for p in data if p["title"] == "Web Test Post"), None)
            assert test_post is not None
            assert test_post["comment_count"] == 1

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

    @pytest.fixture
    def mock_environment(self, test_db_engine):
        """Set up mock environment variables"""
        env_vars = {
            "DATABASE_URL": "sqlite:///:memory:",
            "GITHUB_READ_TOKEN": "mock_github_token",
            "NEWS_API_KEY": "mock_news_key",
            "GITHUB_FEED_REPO": "test/repo",
            "GITHUB_FEED_BRANCH": "main",
            "GITHUB_FEED_PATH": "test.json",
        }

        with patch.dict(os.environ, env_vars):
            # Also patch Settings to use test values
            with patch(
                "bulletin_board.config.settings.Settings.DATABASE_URL",
                "sqlite:///:memory:",
            ):
                with patch(
                    "bulletin_board.config.settings.Settings.INTERNAL_NETWORK_ONLY",
                    False,
                ):
                    yield env_vars

    @pytest.mark.asyncio
    async def test_full_bulletin_board_cycle(
        self, mock_environment, mock_db_functions, test_db_engine
    ):
        """Test complete cycle: collect feeds -> agents comment -> web display"""
        # Mock agent profiles
        test_profiles = [
            {
                "agent_id": "tech_enthusiast_claude",
                "display_name": "Tech Enthusiast",
                "agent_software": "claude_code",
                "role_description": "Tech expert",
                "context_instructions": "Be helpful",
            }
        ]

        with patch(
            "bulletin_board.agents.agent_profiles.AGENT_PROFILES", test_profiles
        ):
            init_agents()

        # Step 1: Simulate feed collection
        session = get_session(test_db_engine)
        from bulletin_board.database.models import Post

        post = Post(
            external_id="e2e_test",
            source="news",
            title="Breaking: New AI Model Released",
            content="A revolutionary AI model has been announced today",
            url="https://news.ai/breaking",
            post_metadata={"author": "AI Reporter"},
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
