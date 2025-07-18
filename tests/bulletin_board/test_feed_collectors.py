import os
import sys

# Add project root to path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from bulletin_board.agents.feed_collector import (
    GitHubFavoritesCollector,
    NewsCollector,
    run_collectors,
)
from bulletin_board.database.models import Post


class TestGitHubFavoritesCollector:
    """Test GitHub favorites collector"""

    @pytest.mark.asyncio
    async def test_fetch_and_store_success(self, test_session, mock_github_response):
        """Test successful fetch and store of GitHub favorites"""
        collector = GitHubFavoritesCollector(test_session)

        # Mock the GitHub API call
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(
                return_value=json.dumps(mock_github_response)
            )

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            # Set mock token
            with patch.object(collector, "token", "mock_token"):
                count = await collector.fetch_and_store()

        assert count == 2

        # Verify posts were stored
        posts = test_session.query(Post).filter_by(source="favorites").all()
        assert len(posts) == 2
        assert posts[0].title == "Awesome Project"
        assert posts[1].title == "Cool Tool"

    @pytest.mark.asyncio
    async def test_fetch_with_api_error(self, test_session):
        """Test handling of GitHub API errors"""
        collector = GitHubFavoritesCollector(test_session)

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 404

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            count = await collector.fetch_and_store()

        assert count == 0

    @pytest.mark.asyncio
    async def test_duplicate_favorites_ignored(
        self, test_session, mock_github_response
    ):
        """Test that duplicate favorites are not added"""
        collector = GitHubFavoritesCollector(test_session)

        # Add one favorite manually
        existing_post = Post(
            external_id="fav_1",
            source="favorites",
            title="Existing",
            content="Already exists",
            created_at=datetime.utcnow(),
        )
        test_session.add(existing_post)
        test_session.commit()

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(
                return_value=json.dumps(mock_github_response)
            )

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            with patch.object(collector, "token", "mock_token"):
                count = await collector.fetch_and_store()

        # Only one new favorite should be added
        assert count == 1
        posts = test_session.query(Post).filter_by(source="favorites").all()
        assert len(posts) == 2


class TestNewsCollector:
    """Test news collector"""

    @pytest.mark.asyncio
    async def test_fetch_and_store_success(self, test_session, mock_news_response):
        """Test successful fetch and store of news articles"""
        collector = NewsCollector(test_session)

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_news_response)

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            with patch.object(collector, "api_key", "mock_api_key"):
                count = await collector.fetch_and_store()

        assert count == 2

        # Verify articles were stored
        posts = test_session.query(Post).filter_by(source="news").all()
        assert len(posts) == 2
        assert posts[0].title == "AI Breakthrough Announced"
        assert posts[1].metadata["author"] == "John Smith"

    @pytest.mark.asyncio
    async def test_no_api_key(self, test_session):
        """Test behavior when no API key is configured"""
        collector = NewsCollector(test_session)

        with patch.object(collector, "api_key", ""):
            count = await collector.fetch_and_store()

        assert count == 0

    @pytest.mark.asyncio
    async def test_news_api_error(self, test_session):
        """Test handling of News API errors"""
        collector = NewsCollector(test_session)

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 401  # Unauthorized

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            with patch.object(collector, "api_key", "invalid_key"):
                count = await collector.fetch_and_store()

        assert count == 0


class TestRunCollectors:
    """Test the main collectors runner"""

    @pytest.mark.asyncio
    async def test_run_all_collectors(
        self, test_engine, mock_github_response, mock_news_response
    ):
        """Test running both collectors together"""

        with patch(
            "bulletin_board.agents.feed_collector.get_session"
        ) as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value = mock_session

            # Mock both collectors
            with patch.object(
                GitHubFavoritesCollector, "fetch_and_store", return_value=2
            ) as mock_github:
                with patch.object(
                    NewsCollector, "fetch_and_store", return_value=3
                ) as mock_news:
                    await run_collectors(test_engine)

            mock_github.assert_called_once()
            mock_news.assert_called_once()
            mock_session.close.assert_called_once()
