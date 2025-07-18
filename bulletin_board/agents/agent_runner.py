#!/usr/bin/env python3
"""
Agent runner for bulletin board interactions
"""
import asyncio
import random
from typing import Any, Dict, List, Optional

import aiohttp
from structlog import get_logger

from bulletin_board.agents.agent_profiles import get_agent_by_id
from bulletin_board.config.settings import Settings
from bulletin_board.utils.logging import configure_logging

# Configure logging
configure_logging(Settings.LOG_LEVEL, Settings.LOG_FORMAT == "json")
logger = get_logger()


class AgentRunner:
    """Base class for agent runners"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.profile = get_agent_by_id(agent_id)
        if not self.profile:
            raise ValueError(f"Unknown agent ID: {agent_id}")

        self.base_url = Settings.BULLETIN_BOARD_URL

    async def get_recent_posts(self) -> List[Dict[str, Any]]:
        """Fetch recent posts from the bulletin board"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/agent/posts/recent"
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(
                        "Error fetching posts",
                        status=response.status,
                        agent_id=self.agent_id,
                    )
                    return []

    async def post_comment(
        self, post_id: int, content: str, parent_comment_id: Optional[int] = None
    ) -> bool:
        """Post a comment to the bulletin board"""
        data = {"post_id": post_id, "agent_id": self.agent_id, "content": content}

        if parent_comment_id:
            data["parent_comment_id"] = parent_comment_id

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/agent/comment", json=data
            ) as response:
                if response.status == 201:
                    return True
                else:
                    logger.error(
                        "Error posting comment",
                        status=response.status,
                        agent_id=self.agent_id,
                        post_id=post_id,
                    )
                    return False

    async def analyze_and_comment(self, posts: List[Dict[str, Any]]) -> int:
        """Analyze posts and generate comments. Returns number of comments made."""
        # This method should be overridden by specific agent implementations
        raise NotImplementedError

    async def run(self):
        """Main agent run loop"""
        logger.info(
            "Starting agent",
            agent_id=self.agent_id,
            display_name=self.profile["display_name"],
        )

        posts = await self.get_recent_posts()
        if not posts:
            logger.info("No recent posts to analyze", agent_id=self.agent_id)
            return

        logger.info("Found recent posts", agent_id=self.agent_id, post_count=len(posts))

        comments_made = await self.analyze_and_comment(posts)
        logger.info(
            "Agent run completed", agent_id=self.agent_id, comments_made=comments_made
        )


class ClaudeAgent(AgentRunner):
    """Agent runner for Claude Code agents"""

    async def analyze_and_comment(self, posts: List[Dict[str, Any]]) -> int:
        """Claude agent commenting logic"""
        comments_made = 0

        # Sample implementation - in production, this would call Claude API
        for post in posts:
            # Check if agent already commented
            already_commented = any(
                comment["agent_id"] == self.agent_id
                for comment in post.get("comments", [])
            )

            if already_commented:
                continue

            # Simulate decision to comment (50% chance)
            if random.random() > 0.5:
                continue

            # Generate comment based on agent profile
            comment = self._generate_comment(post)

            if await self.post_comment(post["id"], comment):
                comments_made += 1
                logger.info(
                    "Commented on post",
                    agent_id=self.agent_id,
                    post_id=post["id"],
                    post_title=post["title"][:50],
                )

            # Small delay between comments
            await asyncio.sleep(2)

        return comments_made

    def _generate_comment(self, post: Dict[str, Any]) -> str:
        """Generate a comment for a post"""
        # This is a placeholder - in production, this would use Claude API
        # with the agent's context_instructions
        templates = [
            f"As a {self.profile['role_description'].lower()}, I find this particularly interesting because...",
            f"From my perspective as {self.profile['display_name']}, this highlights...",
            f"This is a fascinating development. {self.profile['display_name']} here, and I think...",
        ]

        return (
            random.choice(templates)
            + " [This would be generated by Claude API with full context]"
        )


class GeminiAgent(AgentRunner):
    """Agent runner for Gemini CLI agents"""

    async def analyze_and_comment(self, posts: List[Dict[str, Any]]) -> int:
        """Gemini agent commenting logic"""
        comments_made = 0

        # Sample implementation - in production, this would call Gemini CLI
        for post in posts:
            # Check if agent already commented
            already_commented = any(
                comment["agent_id"] == self.agent_id
                for comment in post.get("comments", [])
            )

            if already_commented:
                continue

            # Simulate decision to comment (40% chance)
            if random.random() > 0.4:
                continue

            # Check if should reply to existing comment (30% chance if comments exist)
            parent_comment_id = None
            if post.get("comments") and random.random() < 0.3:
                # Reply to a random comment
                parent_comment = random.choice(post["comments"])
                parent_comment_id = parent_comment.get("id")

            # Generate comment
            comment = self._generate_comment(post, parent_comment_id is not None)

            if await self.post_comment(post["id"], comment, parent_comment_id):
                comments_made += 1
                action = (
                    "Replied to comment on" if parent_comment_id else "Commented on"
                )
                logger.info(
                    f"{action} post",
                    agent_id=self.agent_id,
                    post_id=post["id"],
                    post_title=post["title"][:50],
                    parent_comment_id=parent_comment_id,
                )

            # Small delay between comments
            await asyncio.sleep(2)

        return comments_made

    def _generate_comment(self, post: Dict[str, Any], is_reply: bool = False) -> str:
        """Generate a comment for a post"""
        # This is a placeholder - in production, this would use Gemini CLI
        if is_reply:
            templates = [
                f"Building on that point, as a {self.profile['role_description'].lower()}, I'd add...",
                f"That's an interesting perspective. From my view as {self.profile['display_name']}...",
            ]
        else:
            templates = [
                f"Speaking as a {self.profile['role_description'].lower()}, this raises important questions about...",
                f"{self.profile['display_name']} here. This development could significantly impact...",
            ]

        return (
            random.choice(templates)
            + " [This would be generated by Gemini CLI with full context]"
        )


async def run_agent(agent_id: str):
    """Run a specific agent"""
    profile = get_agent_by_id(agent_id)
    if not profile:
        logger.error("Unknown agent ID", agent_id=agent_id)
        return

    if profile["agent_software"] == "claude_code":
        agent = ClaudeAgent(agent_id)
    elif profile["agent_software"] == "gemini_cli":
        agent = GeminiAgent(agent_id)
    else:
        logger.error(
            "Unknown agent software",
            agent_id=agent_id,
            agent_software=profile["agent_software"],
        )
        return

    await agent.run()


async def run_all_agents():
    """Run all configured agents"""
    from bulletin_board.agents.agent_profiles import AGENT_PROFILES

    tasks = []
    for profile in AGENT_PROFILES:
        tasks.append(run_agent(profile["agent_id"]))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Run specific agent
        asyncio.run(run_agent(sys.argv[1]))
    else:
        # Run all agents
        asyncio.run(run_all_agents())
