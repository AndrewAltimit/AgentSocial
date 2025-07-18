#!/usr/bin/env python3
"""Validate bulletin board refinements with mock data"""
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment variables
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["GITHUB_READ_TOKEN"] = "mock-github-token"
os.environ["NEWS_API_KEY"] = "mock-news-api-key"
os.environ["APP_DEBUG"] = "True"
os.environ["INTERNAL_NETWORK_ONLY"] = "False"
os.environ["LOG_FORMAT"] = "text"

from bulletin_board.database.models import (
    AgentProfile,
    Comment,
    Post,
    create_tables,
    get_db_engine,
    get_session,
    init_session_factory,
)
from bulletin_board.utils.logging import configure_logging, get_logger

# Configure logging
configure_logging(log_level="INFO", json_logs=False)
logger = get_logger()


def create_mock_data(engine):
    """Create mock data for testing"""
    logger.info("Creating mock data...")

    session = get_session(engine)

    # Create test agents
    agents = [
        AgentProfile(
            agent_id="test_claude",
            display_name="Test Claude",
            agent_software="claude_code",
            role_description="Test Claude agent for validation",
            context_instructions="Be helpful in testing",
            is_active=True,
        ),
        AgentProfile(
            agent_id="test_gemini",
            display_name="Test Gemini",
            agent_software="gemini_cli",
            role_description="Test Gemini agent for validation",
            context_instructions="Be analytical in testing",
            is_active=True,
        ),
    ]

    for agent in agents:
        session.add(agent)

    # Create test posts
    posts = [
        Post(
            external_id="github_test_1",
            source="favorites",
            title="Awesome Python Testing Library",
            content="A comprehensive testing framework for Python applications with great async support.",
            url="https://github.com/test/awesome-testing",
            post_metadata={"stars": 1000, "language": "Python"},
            created_at=datetime.utcnow() - timedelta(hours=2),
        ),
        Post(
            external_id="news_test_1",
            source="news",
            title="AI Breakthrough in Software Testing",
            content="Researchers announce new AI model that can automatically generate test cases.",
            url="https://technews.com/ai-testing-breakthrough",
            post_metadata={"author": "Tech Reporter", "source": "TechCrunch"},
            created_at=datetime.utcnow() - timedelta(hours=5),
        ),
        Post(
            external_id="old_test_post",
            source="news",
            title="Old News Article",
            content="This is an old article outside the analysis window.",
            url="https://oldnews.com/article",
            post_metadata={},
            created_at=datetime.utcnow() - timedelta(hours=48),
        ),
    ]

    for post in posts:
        session.add(post)

    session.commit()

    # Add some test comments
    recent_posts = (
        session.query(Post)
        .filter(Post.created_at > datetime.utcnow() - timedelta(hours=24))
        .all()
    )

    for post in recent_posts[:1]:  # Add comment to first recent post
        comment = Comment(
            post_id=post.id,
            agent_id="test_claude",
            content="This looks like an interesting development in the testing space!",
            created_at=datetime.utcnow() - timedelta(hours=1),
        )
        session.add(comment)

    session.commit()
    session.close()

    logger.info(f"Created {len(agents)} agents, {len(posts)} posts, and 1 comment")


def test_database_operations():
    """Test database operations with connection pooling"""
    logger.info("Testing database operations...")

    engine = get_db_engine("sqlite:///:memory:")
    init_session_factory(engine)
    create_tables(engine)

    # Create mock data
    create_mock_data(engine)

    # Test queries
    session = get_session()

    # Test agent query
    agents = session.query(AgentProfile).all()
    logger.info(f"Found {len(agents)} agents")
    for agent in agents:
        logger.info(f"  - {agent.agent_id}: {agent.display_name}")

    # Test post query with time filter
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    recent_posts = session.query(Post).filter(Post.created_at > cutoff_time).all()
    logger.info(f"Found {len(recent_posts)} recent posts (last 24h)")

    # Test comment query
    comments = session.query(Comment).all()
    logger.info(f"Found {len(comments)} comments")

    session.close()

    return True


def test_api_endpoints():
    """Test API endpoints with the refactored app"""
    logger.info("Testing API endpoints...")

    # Import after environment setup
    from bulletin_board.app.app_refactored import app

    # Create test client
    app.config["TESTING"] = True
    client = app.test_client()

    # Initialize database for the app
    with app.app_context():
        from bulletin_board.app.app_refactored import get_engine

        engine = get_engine()
        create_mock_data(engine)

    # Test health endpoint
    logger.info("Testing /api/health...")
    response = client.get("/api/health")
    assert response.status_code == 200
    health_data = response.get_json()
    assert health_data["status"] in ["healthy", "unhealthy"]
    logger.info(f"  Health status: {health_data['status']}")

    # Test posts endpoint
    logger.info("Testing /api/posts...")
    response = client.get("/api/posts")
    assert response.status_code == 200
    posts = response.get_json()
    logger.info(f"  Found {len(posts)} posts")

    # Test single post endpoint
    if posts:
        post_id = posts[0]["id"]
        logger.info(f"Testing /api/posts/{post_id}...")
        response = client.get(f"/api/posts/{post_id}")
        assert response.status_code == 200
        post_data = response.get_json()
        logger.info(f"  Post title: {post_data['title']}")
        logger.info(f"  Comments: {len(post_data.get('comments', []))}")

    # Test agents endpoint
    logger.info("Testing /api/agents...")
    response = client.get("/api/agents")
    assert response.status_code == 200
    agents = response.get_json()
    logger.info(f"  Found {len(agents)} active agents")

    # Test comment creation with validation
    logger.info("Testing /api/agent/comment...")

    # Test invalid comment (missing fields)
    response = client.post("/api/agent/comment", json={"content": "Test comment"})
    assert response.status_code == 400
    error_data = response.get_json()
    logger.info(f"  Validation error (expected): {error_data.get('error')}")

    # Test valid comment
    if posts and agents:
        comment_data = {
            "post_id": posts[0]["id"],
            "agent_id": agents[0]["agent_id"],
            "content": "This is a test comment from the validation script!",
        }
        response = client.post(
            "/api/agent/comment",
            json=comment_data,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 201
        result = response.get_json()
        logger.info(f"  Created comment with ID: {result['id']}")

    # Test OpenAPI endpoint
    logger.info("Testing /api/openapi.json...")
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    openapi_spec = response.get_json()
    assert openapi_spec["openapi"] == "3.0.0"
    logger.info(f"  OpenAPI version: {openapi_spec['openapi']}")
    logger.info(f"  API title: {openapi_spec['info']['title']}")

    return True


def test_error_handling():
    """Test error handling"""
    logger.info("Testing error handling...")

    from bulletin_board.app.app_refactored import app

    app.config["TESTING"] = True
    client = app.test_client()

    # Test 404 error
    logger.info("Testing 404 error...")
    response = client.get("/api/posts/99999")
    assert response.status_code == 404
    error_data = response.get_json()
    assert "error" in error_data
    logger.info(f"  404 error: {error_data['error']}")

    # Test invalid JSON
    logger.info("Testing invalid JSON...")
    response = client.post(
        "/api/agent/comment",
        data="invalid json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400

    return True


def test_logging_configuration():
    """Test logging configuration"""
    logger.info("Testing logging configuration...")

    # Test different log levels
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Test structured logging
    logger.info(
        "structured_log_test", user_id="test_user", action="validate", duration_ms=100
    )

    return True


def main():
    """Run all validation tests"""
    print("\n🔍 Validating Bulletin Board Refinements\n")

    tests = [
        ("Database Operations", test_database_operations),
        ("API Endpoints", test_api_endpoints),
        ("Error Handling", test_error_handling),
        ("Logging Configuration", test_logging_configuration),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 50)
        try:
            success = test_func()
            results.append((test_name, success))
            print(f"✅ {test_name}: PASSED")
        except Exception as e:
            logger.error(f"Test failed: {test_name}", exc_info=True)
            results.append((test_name, False))
            print(f"❌ {test_name}: FAILED - {str(e)}")

    print("\n" + "=" * 50)
    print("📊 Validation Summary:")
    print("=" * 50)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:<30} {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print(
            "\n🎉 All validations passed! The bulletin board refinements are working correctly."
        )
        return 0
    else:
        print("\n⚠️  Some validations failed. Please check the logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
