"""Async test fixtures for bulletin board tests"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
import aiohttp
from aiohttp import web


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_aiohttp_session():
    """Mock aiohttp ClientSession for testing"""
    mock_session = AsyncMock(spec=aiohttp.ClientSession)
    
    # Create a mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={})
    mock_response.text = AsyncMock(return_value="")
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    
    # Configure session methods
    mock_session.get = AsyncMock(return_value=mock_response)
    mock_session.post = AsyncMock(return_value=mock_response)
    mock_session.close = AsyncMock()
    
    return mock_session


@pytest.fixture
def mock_async_context_manager():
    """Helper to create async context managers for testing"""
    def _create_async_cm(return_value=None):
        class AsyncContextManager:
            async def __aenter__(self):
                return return_value or self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        
        return AsyncContextManager()
    
    return _create_async_cm


@pytest.fixture
async def test_news_api_response():
    """Mock News API response"""
    return {
        "status": "ok",
        "totalResults": 2,
        "articles": [
            {
                "source": {"id": "techcrunch", "name": "TechCrunch"},
                "author": "Test Author",
                "title": "Test Tech News",
                "description": "Test description",
                "url": "https://techcrunch.com/test",
                "publishedAt": "2024-01-01T12:00:00Z",
                "content": "Test content"
            }
        ]
    }


@pytest.fixture
async def test_github_api_response():
    """Mock GitHub API response"""
    return [
        {
            "id": 123,
            "name": "test-repo",
            "full_name": "user/test-repo",
            "description": "Test repository",
            "html_url": "https://github.com/user/test-repo",
            "stargazers_count": 100,
            "language": "Python",
            "created_at": "2024-01-01T12:00:00Z"
        }
    ]


@pytest.fixture
def async_mock_response():
    """Create a mock async response"""
    def _create_response(json_data=None, text_data=None, status=200):
        response = AsyncMock()
        response.status = status
        response.json = AsyncMock(return_value=json_data or {})
        response.text = AsyncMock(return_value=text_data or "")
        return response
    
    return _create_response