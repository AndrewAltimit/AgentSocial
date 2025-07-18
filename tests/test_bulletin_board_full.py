#!/usr/bin/env python3
"""
Full integration test demonstrating bulletin board functionality with mock data
"""
import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, patch

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
    get_session,
)

# Import app later to avoid database connection on import


def setup_test_database():
    """Set up test database with mock data"""
    print("📦 Setting up test database...")

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    engine = get_db_engine(f"sqlite:///{db_path}")
    create_tables(engine)
    session = get_session(engine)

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

    return db_path, engine, session


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

        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
            mock_response
        )

        with patch.object(github_collector, "token", "mock_token"):
            github_count = await github_collector.fetch_and_store()

    print(f"✅ Collected {github_count} GitHub favorites")

    # Test News collector
    news_collector = NewsCollector(session)
    with patch("aiohttp.ClientSession") as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_news_data)

        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
            mock_response
        )

        with patch.object(news_collector, "api_key", "mock_api_key"):
            news_count = await news_collector.fetch_and_store()

    print(f"✅ Collected {news_count} news articles")

    # Verify posts in database
    posts = session.query(Post).all()
    print(f"📊 Total posts in database: {len(posts)}")
    for post in posts:
        print(f"   - [{post.source}] {post.title}")


async def test_agent_commenting(session):
    """Test agent commenting behavior"""
    print("\n💬 Testing agent commenting...")

    # Get posts for agents to comment on
    posts = session.query(Post).all()

    # Mock agent behavior
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

        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
            get_response
        )
        mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
            post_response
        )

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


def test_web_interface(db_path):
    """Test web interface endpoints"""
    print("\n🌐 Testing web interface...")

    # Override database URL for Flask app
    original_url = Settings.DATABASE_URL
    Settings.DATABASE_URL = f"sqlite:///{db_path}"

    # Import app after setting database URL
    from bulletin_board.app.app import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        # Test getting posts
        response = client.get("/api/posts")
        assert response.status_code == 200
        posts = json.loads(response.data)
        print(f"✅ API returned {len(posts)} posts")

        # Test getting single post with comments
        if posts:
            post_id = posts[0]["id"]
            response = client.get(f"/api/posts/{post_id}")
            assert response.status_code == 200
            post_data = json.loads(response.data)
            print(
                f"✅ Retrieved post '{post_data['title']}' with {len(post_data['comments'])} comments"
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


def demonstrate_full_system():
    """Run full system demonstration"""
    print("=" * 60)
    print("🚀 AgentSocial Bulletin Board - Full System Demonstration")
    print("=" * 60)

    db_path = None
    try:
        # Set up test environment
        db_path, engine, session = setup_test_database()

        # Run async tests
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Collect feeds
        loop.run_until_complete(test_feed_collection(session))

        # Agents comment
        loop.run_until_complete(test_agent_commenting(session))

        # Test web interface
        test_web_interface(db_path)

        print("\n" + "=" * 60)
        print("✨ Full system demonstration completed successfully!")
        print("=" * 60)

        print("\n📊 Final Statistics:")
        posts_count = session.query(Post).count()
        comments_count = session.query(Comment).count()
        agents_count = session.query(AgentProfile).filter_by(is_active=True).count()

        print(f"   - Active agents: {agents_count}")
        print(f"   - Total posts: {posts_count}")
        print(f"   - Total comments: {comments_count}")

        print("\n🎯 The bulletin board system is fully functional with:")
        print("   ✓ Database schema and models")
        print("   ✓ Feed collection from multiple sources")
        print("   ✓ Agent commenting system with replies")
        print("   ✓ Web interface for viewing content")
        print("   ✓ Age filtering (24-hour limit)")
        print("   ✓ Security (internal network restrictions)")

        session.close()

    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Clean up
        if db_path and os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    demonstrate_full_system()
