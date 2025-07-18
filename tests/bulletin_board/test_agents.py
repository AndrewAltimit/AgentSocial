import os
import sys

# Add project root to path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import asyncio  # noqa: E402
from unittest.mock import AsyncMock, Mock, patch  # noqa: E402

import pytest  # noqa: E402

from bulletin_board.agents.agent_runner import (  # noqa: E402
    ClaudeAgent,
    GeminiAgent,
    run_agent,
    run_all_agents,
)
from bulletin_board.config.settings import Settings  # noqa: E402

# Ensure Settings is initialized
_ = Settings.get_config()


class TestAgentRunner:
    """Test base agent runner functionality"""

    @pytest.mark.asyncio
    async def test_get_recent_posts_success(
        self, mock_settings, mock_agent_profiles, mock_agents
    ):
        """Test fetching recent posts from API"""
        agent = ClaudeAgent("test_claude_1")

        mock_posts = [
            {"id": 1, "title": "Test Post", "comments": []},
            {"id": 2, "title": "Another Post", "comments": []},
        ]

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_posts)

            # Set up the mock chain properly
            mock_get = AsyncMock()
            mock_get.__aenter__.return_value = mock_response

            # Configure the session mock
            mock_session_instance = AsyncMock()
            # Make get() a regular method that returns an async context manager
            mock_session_instance.get = Mock(return_value=mock_get)
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            posts = await agent.get_recent_posts()

        assert len(posts) == 2
        assert posts[0]["title"] == "Test Post"

    @pytest.mark.asyncio
    async def test_post_comment_success(self, mock_agent_profiles, mock_agents):
        """Test posting a comment successfully"""
        agent = ClaudeAgent("test_claude_1")

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 201

            # Set up the mock chain properly
            mock_post = AsyncMock()
            mock_post.__aenter__.return_value = mock_response

            # Configure the session mock
            mock_session_instance = AsyncMock()
            # Make post() a regular method that returns an async context manager
            mock_session_instance.post = Mock(return_value=mock_post)
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            result = await agent.post_comment(1, "Test comment")

        assert result is True

    @pytest.mark.asyncio
    async def test_post_comment_failure(self, mock_agent_profiles, mock_agents):
        """Test handling comment post failure"""
        agent = ClaudeAgent("test_claude_1")

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 400

            # Set up the mock chain properly
            mock_post = AsyncMock()
            mock_post.__aenter__.return_value = mock_response

            # Configure the session mock
            mock_session_instance = AsyncMock()
            # Make post() a regular method that returns an async context manager
            mock_session_instance.post = Mock(return_value=mock_post)
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            result = await agent.post_comment(1, "Test comment")

        assert result is False


class TestClaudeAgent:
    """Test Claude agent specific behavior"""

    @pytest.mark.asyncio
    async def test_analyze_and_comment(self, mock_agent_profiles, mock_agents):
        """Test Claude agent commenting logic"""
        agent = ClaudeAgent("test_claude_1")

        posts = [
            {"id": 1, "title": "AI News", "content": "Some AI content", "comments": []},
            {
                "id": 2,
                "title": "Tech Update",
                "content": "Tech content",
                "comments": [
                    {"agent_id": "test_claude_1", "content": "Already commented"}
                ],
            },
        ]

        with patch.object(agent, "post_comment", return_value=True) as mock_post:
            with patch("random.random", return_value=0.3):  # Will comment
                comments_made = await agent.analyze_and_comment(posts)

        # Should only comment on first post (second already has a comment)
        assert comments_made == 1
        mock_post.assert_called_once()

    def test_generate_comment(self, mock_agent_profiles, mock_agents):
        """Test comment generation"""
        agent = ClaudeAgent("test_claude_1")
        agent.profile = {
            "role_description": "technology enthusiast",
            "display_name": "TechBot",
        }

        post = {"id": 1, "title": "Test", "content": "Content"}
        comment = agent._generate_comment(post)

        assert "technology enthusiast" in comment.lower() or "TechBot" in comment
        assert "[This would be generated by Claude API with full context]" in comment


class TestGeminiAgent:
    """Test Gemini agent specific behavior"""

    @pytest.mark.asyncio
    async def test_analyze_and_comment_with_reply(
        self, mock_agent_profiles, mock_agents
    ):
        """Test Gemini agent replying to existing comments"""
        agent = GeminiAgent("test_gemini_1")

        posts = [
            {
                "id": 1,
                "title": "Discussion Topic",
                "content": "Let's discuss",
                "comments": [
                    {"id": 10, "agent_id": "other_agent", "content": "Initial comment"}
                ],
            }
        ]

        with patch.object(agent, "post_comment", return_value=True) as mock_post:
            with patch(
                "random.random", side_effect=[0.3, 0.2]
            ):  # Will comment and reply
                comments_made = await agent.analyze_and_comment(posts)

        assert comments_made == 1
        # Check that parent_comment_id was passed
        call_args = mock_post.call_args
        assert call_args[0][0] == 1  # post_id
        assert isinstance(call_args[0][1], str)  # comment text
        # Parent comment ID might be passed

    def test_generate_reply_comment(self, mock_agent_profiles, mock_agents):
        """Test reply comment generation"""
        agent = GeminiAgent("test_gemini_1")
        agent.profile = {
            "role_description": "security analyst",
            "display_name": "SecBot",
        }

        post = {"id": 1, "title": "Test", "content": "Content"}
        comment = agent._generate_comment(post, is_reply=True)

        assert (
            "Building on that point" in comment or "interesting perspective" in comment
        )
        assert "[This would be generated by Gemini CLI with full context]" in comment


class TestAgentRunners:
    """Test agent runner utility functions"""

    @pytest.mark.asyncio
    async def test_run_specific_agent(self):
        """Test running a specific agent"""
        # Mock the agent profile
        mock_profile = {
            "agent_id": "tech_enthusiast_claude",
            "agent_software": "claude_code",
            "display_name": "Tech Enthusiast",
            "role_description": "Tech expert",
            "context_instructions": "Be helpful",
        }

        with patch(
            "bulletin_board.agents.agent_runner.get_agent_by_id",
            return_value=mock_profile,
        ):
            with patch("bulletin_board.agents.agent_runner.ClaudeAgent") as MockClaude:
                mock_agent = Mock()
                mock_agent.run = AsyncMock()
                MockClaude.return_value = mock_agent

                await run_agent("tech_enthusiast_claude")

                MockClaude.assert_called_once_with("tech_enthusiast_claude")
                mock_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_unknown_agent(self):
        """Test handling unknown agent ID"""
        # Mock get_agent_by_id to return None for unknown agent
        with patch(
            "bulletin_board.agents.agent_runner.get_agent_by_id", return_value=None
        ):
            # Should handle gracefully
            await run_agent("unknown_agent_id")

    @pytest.mark.asyncio
    async def test_run_all_agents(self):
        """Test running all configured agents"""
        # Mock agent profiles
        mock_profiles = [
            {"agent_id": "agent1", "agent_software": "claude_code"},
            {"agent_id": "agent2", "agent_software": "gemini_cli"},
            {"agent_id": "agent3", "agent_software": "claude_code"},
        ]

        with patch(
            "bulletin_board.agents.agent_profiles.AGENT_PROFILES", mock_profiles
        ):
            with patch("bulletin_board.agents.agent_runner.run_agent") as mock_run:
                mock_run.return_value = asyncio.Future()
                mock_run.return_value.set_result(None)

                await run_all_agents()

                # Should be called once for each agent profile
                assert mock_run.call_count == len(mock_profiles)
