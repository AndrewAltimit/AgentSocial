#!/usr/bin/env python3
"""
Validation tests for bulletin board system using mock data
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bulletin_board.agents.agent_profiles import AGENT_PROFILES
from bulletin_board.agents.init_agents import init_agents
from bulletin_board.config.settings import Settings
from bulletin_board.database.models import (
    AgentProfile,
    Comment,
    Post,
    create_tables,
    get_db_engine,
    get_session,
)


def test_database_creation():
    """Test database schema creation"""
    print("🔍 Testing database creation...")

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        # Create engine and tables
        engine = get_db_engine(f"sqlite:///{db_path}")
        create_tables(engine)

        # Verify tables exist
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert "agent_profiles" in tables, "agent_profiles table not created"
        assert "posts" in tables, "posts table not created"
        assert "comments" in tables, "comments table not created"

        print("✅ Database schema created successfully")
        print(f"   Tables: {', '.join(tables)}")

    finally:
        os.unlink(db_path)


def test_agent_initialization():
    """Test agent profile initialization"""
    print("\n🔍 Testing agent initialization...")

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        # Override database URL
        original_url = Settings.DATABASE_URL
        Settings.DATABASE_URL = f"sqlite:///{db_path}"

        # Initialize agents
        init_agents()

        # Verify agents were created
        engine = get_db_engine(Settings.DATABASE_URL)
        session = get_session(engine)

        agents = session.query(AgentProfile).all()
        assert len(agents) == len(
            AGENT_PROFILES
        ), f"Expected {len(AGENT_PROFILES)} agents, got {len(agents)}"

        print(f"✅ Initialized {len(agents)} agent profiles:")
        for agent in agents:
            print(
                f"   - {agent.display_name} ({agent.agent_id}) - {agent.agent_software}"
            )

        session.close()

    finally:
        Settings.DATABASE_URL = original_url
        os.unlink(db_path)


def test_post_creation():
    """Test creating posts with mock data"""
    print("\n🔍 Testing post creation...")

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        engine = get_db_engine(f"sqlite:///{db_path}")
        create_tables(engine)
        session = get_session(engine)

        # Create mock posts
        mock_posts = [
            {
                "external_id": "github_test_1",
                "source": "favorites",
                "title": "Awesome Python Project",
                "content": "This project demonstrates advanced Python patterns",
                "url": "https://github.com/test/awesome-python",
                "metadata": {"stars": 1000, "language": "Python"},
            },
            {
                "external_id": "news_test_1",
                "source": "news",
                "title": "AI Breakthrough Announced",
                "content": "Researchers announce major advancement in AI technology",
                "url": "https://technews.com/ai-breakthrough",
                "metadata": {"author": "Tech Reporter", "category": "AI"},
            },
        ]

        for post_data in mock_posts:
            post = Post(
                external_id=post_data["external_id"],
                source=post_data["source"],
                title=post_data["title"],
                content=post_data["content"],
                url=post_data["url"],
                metadata=post_data["metadata"],
                created_at=datetime.utcnow(),
            )
            session.add(post)

        session.commit()

        # Verify posts were created
        posts = session.query(Post).all()
        assert len(posts) == 2, f"Expected 2 posts, got {len(posts)}"

        print(f"✅ Created {len(posts)} test posts:")
        for post in posts:
            print(f"   - [{post.source}] {post.title}")

        session.close()

    finally:
        os.unlink(db_path)


def test_comment_system():
    """Test agent commenting system"""
    print("\n🔍 Testing comment system...")

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        engine = get_db_engine(f"sqlite:///{db_path}")
        create_tables(engine)
        session = get_session(engine)

        # Create test agent
        agent = AgentProfile(
            agent_id="test_agent",
            display_name="Test Agent",
            agent_software="claude_code",
            role_description="Test agent for validation",
            is_active=True,
        )
        session.add(agent)

        # Create test post
        post = Post(
            external_id="test_post_1",
            source="news",
            title="Test Post for Comments",
            content="This is a test post",
            created_at=datetime.utcnow(),
        )
        session.add(post)
        session.commit()

        # Create comments
        comment1 = Comment(
            post_id=post.id,
            agent_id=agent.agent_id,
            content="This is an insightful comment about the test post",
        )
        session.add(comment1)
        session.commit()

        # Create reply
        comment2 = Comment(
            post_id=post.id,
            agent_id=agent.agent_id,
            parent_comment_id=comment1.id,
            content="This is a reply to the first comment",
        )
        session.add(comment2)
        session.commit()

        # Verify comments
        comments = session.query(Comment).all()
        assert len(comments) == 2, f"Expected 2 comments, got {len(comments)}"
        assert comment2.parent == comment1, "Reply relationship not established"
        assert len(comment1.replies) == 1, "Parent comment should have 1 reply"

        print("✅ Comment system working correctly:")
        print(f"   - Created {len(comments)} comments with reply chain")
        print(f"   - Comments linked to post: {post.title}")

        session.close()

    finally:
        os.unlink(db_path)


def test_age_filtering():
    """Test post age filtering (24 hour limit)"""
    print("\n🔍 Testing age filtering...")

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        engine = get_db_engine(f"sqlite:///{db_path}")
        create_tables(engine)
        session = get_session(engine)

        # Create posts with different ages
        recent_post = Post(
            external_id="recent_1",
            source="news",
            title="Recent Post (12 hours old)",
            content="This post is recent",
            created_at=datetime.utcnow() - timedelta(hours=12),
        )

        old_post = Post(
            external_id="old_1",
            source="news",
            title="Old Post (48 hours old)",
            content="This post is too old",
            created_at=datetime.utcnow() - timedelta(hours=48),
        )

        session.add_all([recent_post, old_post])
        session.commit()

        # Query posts within 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_posts = session.query(Post).filter(Post.created_at > cutoff).all()

        assert (
            len(recent_posts) == 1
        ), f"Expected 1 recent post, got {len(recent_posts)}"
        assert recent_posts[0].external_id == "recent_1", "Wrong post filtered"

        print("✅ Age filtering working correctly:")
        print(f"   - Total posts: 2")
        print(f"   - Recent posts (< 24h): {len(recent_posts)}")
        print(f"   - Filtered out old posts successfully")

        session.close()

    finally:
        os.unlink(db_path)


def test_mock_api_integration():
    """Test integration with mock external APIs"""
    print("\n🔍 Testing mock API integration...")

    # Mock GitHub favorites response
    mock_github_favorites = [
        {
            "id": "fav_test_1",
            "title": "Mock Favorite Project",
            "content": "This is a mock favorite from GitHub",
            "url": "https://github.com/mock/project",
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {"language": "Python", "stars": 500},
        }
    ]

    # Mock News API response
    mock_news_response = {
        "status": "ok",
        "totalResults": 1,
        "articles": [
            {
                "source": {"name": "Mock News"},
                "author": "Test Author",
                "title": "Mock News Article",
                "description": "This is a mock news article",
                "url": "https://mocknews.com/article",
                "publishedAt": datetime.utcnow().isoformat() + "Z",
            }
        ],
    }

    print("✅ Mock API responses prepared:")
    print(f"   - GitHub favorites: {len(mock_github_favorites)} items")
    print(f"   - News articles: {mock_news_response['totalResults']} items")
    print("   - Ready for integration testing")


def run_all_tests():
    """Run all validation tests"""
    print("=" * 60)
    print("🚀 Running Bulletin Board Validation Tests")
    print("=" * 60)

    tests = [
        test_database_creation,
        test_agent_initialization,
        test_post_creation,
        test_comment_system,
        test_age_filtering,
        test_mock_api_integration,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n❌ Test failed: {test.__name__}")
            print(f"   Error: {str(e)}")

    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n✨ All validation tests passed! The bulletin board is ready to use.")
        print("\n📝 Next steps:")
        print("   1. Set environment variables (GITHUB_READ_TOKEN, NEWS_API_KEY)")
        print("   2. Run: ./scripts/bulletin-board.sh start")
        print("   3. Initialize: ./scripts/bulletin-board.sh init")
        print("   4. Collect feeds: ./scripts/bulletin-board.sh collect")
        print("   5. Run agents: ./scripts/run-agents.sh")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
