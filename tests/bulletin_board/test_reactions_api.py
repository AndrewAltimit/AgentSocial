"""Tests for the reactions API endpoint"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests


class TestReactionsAPI:
    """Test the reactions API endpoint with mocked external dependencies"""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear any existing cache before each test"""
        cache_dir = Path(tempfile.gettempdir()) / "agentsocial_cache"
        cache_file = cache_dir / "reactions_cache.json"
        if cache_file.exists():
            cache_file.unlink()
        yield
        # Cleanup after test
        if cache_file.exists():
            cache_file.unlink()

    def test_reactions_successful_fetch(self, client):
        """Test successful fetch of reactions from remote YAML"""
        mock_yaml_content = """
        reactions:
          - name: happy
            file: happy.webp
            category: emotions
          - name: typing
            file: typing.webp
            category: working
        """

        with patch("packages.bulletin_board.app.app.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_yaml_content
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            response = client.get("/api/reactions")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert "reactions" in data
            assert "base_url" in data
            assert len(data["reactions"]) == 2
            assert data["reactions"][0]["name"] == "happy"
            assert data["reactions"][0]["file"] == "happy.webp"
            assert data["reactions"][0]["category"] == "emotions"

    def test_reactions_cache_hit(self, client):
        """Test that cache is used on second request"""
        mock_yaml_content = """
        reactions:
          - name: cached
            file: cached.webp
            category: test
        """

        with patch("packages.bulletin_board.app.app.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_yaml_content
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            # First request - should fetch from remote
            response1 = client.get("/api/reactions")
            assert response1.status_code == 200
            assert mock_get.call_count == 1

            # Second request - should use cache
            response2 = client.get("/api/reactions")
            assert response2.status_code == 200
            assert mock_get.call_count == 1  # Should not increase

            # Both responses should be identical
            assert response1.data == response2.data

    def test_reactions_network_error_fallback(self, client):
        """Test fallback when network request fails"""
        with patch("packages.bulletin_board.app.app.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Network error")

            response = client.get("/api/reactions")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert "reactions" in data
            assert "base_url" in data
            # Should have fallback reactions
            assert len(data["reactions"]) > 0
            assert any(r["name"] == "typing" for r in data["reactions"])

    def test_reactions_yaml_parse_error_fallback(self, client):
        """Test fallback when YAML parsing fails"""
        with patch("packages.bulletin_board.app.app.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "invalid: yaml: content: {["
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            response = client.get("/api/reactions")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert "reactions" in data
            assert "base_url" in data
            # Should have fallback reactions
            assert len(data["reactions"]) > 0

    def test_reactions_http_error_fallback(self, client):
        """Test fallback when HTTP request returns error status"""
        with patch("packages.bulletin_board.app.app.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
            mock_get.return_value = mock_response

            response = client.get("/api/reactions")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert "reactions" in data
            # Should have fallback reactions
            assert len(data["reactions"]) > 0

    def test_add_reaction_endpoint(self, client, test_db_session, mock_posts):
        """Test the atomic reaction addition endpoint"""
        from packages.bulletin_board.database.models import Comment

        # Add a comment to react to
        comment = Comment(post_id=mock_posts[0].id, agent_id="test_claude_1", content="Test comment")
        test_db_session.add(comment)
        test_db_session.commit()

        # Test adding a reaction
        response = client.post(
            f"/api/comment/{comment.id}/react",
            json={"reaction": "happy.webp"},
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["id"] == comment.id
        assert "[reaction:happy.webp]" in data["content"]

        # Verify reaction was persisted
        test_db_session.refresh(comment)
        assert "[reaction:happy.webp]" in comment.content

    def test_add_reaction_duplicate_prevention(self, client, test_db_session, mock_posts):
        """Test that duplicate reactions are not added"""
        from packages.bulletin_board.database.models import Comment

        # Add a comment with an existing reaction
        comment = Comment(
            post_id=mock_posts[0].id,
            agent_id="test_claude_1",
            content="Test comment [reaction:happy.webp]",
        )
        test_db_session.add(comment)
        test_db_session.commit()

        # Try to add the same reaction again
        response = client.post(
            f"/api/comment/{comment.id}/react",
            json={"reaction": "happy.webp"},
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        # Should still have only one instance of the reaction
        assert data["content"].count("[reaction:happy.webp]") == 1

    def test_add_reaction_nonexistent_comment(self, client):
        """Test adding reaction to nonexistent comment returns 404"""
        response = client.post(
            "/api/comment/9999/react",
            json={"reaction": "happy.webp"},
        )
        assert response.status_code == 404

    def test_add_reaction_missing_field(self, client):
        """Test that missing reaction field returns 400"""
        response = client.post(
            "/api/comment/1/react",
            json={},
        )
        assert response.status_code == 400
