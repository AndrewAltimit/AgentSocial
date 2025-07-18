"""Tests for bulletin board web API endpoints"""

import os
import sys

# Add project root to path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import json  # noqa: E402
from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402

from bulletin_board.app.app import app  # noqa: E402
from bulletin_board.database.models import Comment  # noqa: E402


class TestBulletinBoardAPI:
    """Test bulletin board web API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def mock_db_session(self, test_session, mock_agents):
        """Mock database session with test data"""
        with patch("bulletin_board.app.app.get_session", return_value=test_session):
            yield test_session

    def test_index_page(self, client):
        """Test main index page loads"""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Agent Social Bulletin Board" in response.data

    def test_get_recent_posts(self, client, mock_db_session):
        """Test getting recent posts"""
        response = client.get("/api/posts")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data) == 2  # Only 2 posts are recent (not the old one)
        assert data[0]["title"] == "Test GitHub Favorite"
        assert data[1]["title"] == "Breaking Tech News"

    def test_get_single_post(self, client, mock_db_session, mock_posts):
        """Test getting a single post with comments"""
        # Add a comment to the first post
        comment = Comment(
            post_id=mock_posts[0].id, agent_id="test_claude_1", content="Test comment"
        )
        mock_db_session.add(comment)
        mock_db_session.commit()

        response = client.get(f"/api/posts/{mock_posts[0].id}")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["title"] == "Test GitHub Favorite"
        assert len(data["comments"]) == 1
        assert data["comments"][0]["content"] == "Test comment"

    def test_get_nonexistent_post(self, client, mock_db_session):
        """Test getting a post that doesn't exist"""
        response = client.get("/api/posts/9999")
        assert response.status_code == 404

    def test_get_agents(self, client, mock_db_session):
        """Test getting list of active agents"""
        response = client.get("/api/agents")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data) == 2
        assert data[0]["agent_id"] == "test_claude_1"
        assert data[1]["agent_id"] == "test_gemini_1"


class TestAgentEndpoints:
    """Test agent-specific endpoints with access control"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def mock_db_session(self, test_session, mock_agents):
        """Mock database session with test data"""
        with patch("bulletin_board.app.app.get_session", return_value=test_session):
            yield test_session

    def test_agent_recent_posts_internal_only(self, client):
        """Test agent posts endpoint requires internal access"""
        with patch("bulletin_board.app.app.Settings.INTERNAL_NETWORK_ONLY", True):
            # External IP should be blocked
            with patch("flask.request.remote_addr", "8.8.8.8"):
                response = client.get("/api/agent/posts/recent")
                assert response.status_code == 403

    def test_agent_recent_posts_localhost_allowed(self, client, mock_db_session):
        """Test localhost can access agent endpoints"""
        with patch("bulletin_board.app.app.Settings.INTERNAL_NETWORK_ONLY", True):
            with patch("flask.request.remote_addr", "127.0.0.1"):
                response = client.get("/api/agent/posts/recent")
                assert response.status_code == 200

                data = json.loads(response.data)
                assert len(data) == 2  # Recent posts only

    def test_create_comment_success(self, client, mock_db_session, mock_posts):
        """Test creating a comment successfully"""
        with patch("flask.request.remote_addr", "127.0.0.1"):
            response = client.post(
                "/api/agent/comment",
                json={
                    "post_id": mock_posts[0].id,
                    "agent_id": "test_claude_1",
                    "content": "This is a test comment",
                },
            )
            assert response.status_code == 201

            data = json.loads(response.data)
            assert "id" in data
            assert "created_at" in data

            # Verify comment was added
            comments = mock_db_session.query(Comment).all()
            assert len(comments) == 1
            assert comments[0].content == "This is a test comment"

    def test_create_comment_missing_fields(self, client, mock_db_session):
        """Test creating comment with missing fields"""
        with patch("flask.request.remote_addr", "127.0.0.1"):
            response = client.post(
                "/api/agent/comment",
                json={
                    "post_id": 1,
                    # Missing agent_id and content
                },
            )
            assert response.status_code == 400

    def test_create_comment_invalid_agent(self, client, mock_db_session, mock_posts):
        """Test creating comment with invalid agent"""
        with patch("flask.request.remote_addr", "127.0.0.1"):
            response = client.post(
                "/api/agent/comment",
                json={
                    "post_id": mock_posts[0].id,
                    "agent_id": "invalid_agent",
                    "content": "Test",
                },
            )
            assert response.status_code == 403

    def test_create_comment_old_post(self, client, mock_db_session, mock_posts):
        """Test creating comment on post that's too old"""
        with patch("flask.request.remote_addr", "127.0.0.1"):
            response = client.post(
                "/api/agent/comment",
                json={
                    "post_id": mock_posts[2].id,  # Old post
                    "agent_id": "test_claude_1",
                    "content": "Test",
                },
            )
            assert response.status_code == 404

    def test_create_comment_with_parent(self, client, mock_db_session, mock_posts):
        """Test creating a reply comment"""
        # First create a parent comment
        parent = Comment(
            post_id=mock_posts[0].id, agent_id="test_claude_1", content="Parent comment"
        )
        mock_db_session.add(parent)
        mock_db_session.commit()

        with patch("flask.request.remote_addr", "127.0.0.1"):
            response = client.post(
                "/api/agent/comment",
                json={
                    "post_id": mock_posts[0].id,
                    "agent_id": "test_gemini_1",
                    "content": "Reply to parent",
                    "parent_comment_id": parent.id,
                },
            )
            assert response.status_code == 201

            # Verify reply was created
            reply = (
                mock_db_session.query(Comment)
                .filter_by(parent_comment_id=parent.id)
                .first()
            )
            assert reply is not None
            assert reply.content == "Reply to parent"


class TestAccessControl:
    """Test internal network access control"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_allowed_network_access(self, client):
        """Test access from allowed internal networks"""
        with patch("bulletin_board.app.app.Settings.INTERNAL_NETWORK_ONLY", True):
            with patch(
                "bulletin_board.app.app.Settings.ALLOWED_AGENT_IPS", ["172.20.0.0/16"]
            ):
                with patch("flask.request.remote_addr", "172.20.0.50"):
                    response = client.get("/api/agent/posts/recent")
                    assert response.status_code != 403

    def test_blocked_network_access(self, client):
        """Test access blocked from external networks"""
        with patch("bulletin_board.app.app.Settings.INTERNAL_NETWORK_ONLY", True):
            with patch(
                "bulletin_board.app.app.Settings.ALLOWED_AGENT_IPS", ["172.20.0.0/16"]
            ):
                with patch("flask.request.remote_addr", "192.168.1.100"):
                    response = client.post("/api/agent/comment", json={})
                    assert response.status_code == 403
