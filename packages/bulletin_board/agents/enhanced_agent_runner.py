"""
Enhanced agent runner with personality, reactions, and moderation systems
"""

import asyncio
import os
import random
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
from structlog import get_logger

from .moderation_system import ContentModerator, ModerationAction
from .personality_system import PersonalityManager
from .reaction_system import ExpressionEnhancer

logger = get_logger()


class EnhancedAgentRunner:
    """
    Orchestrates agent interactions with full personality system
    """

    def __init__(self, api_base_url: str = None):
        if api_base_url is None:
            api_base_url = os.environ.get(
                "BULLETIN_BOARD_API_URL", "http://localhost:8080"
            )
        self.api_base_url = api_base_url
        self.personality_manager = PersonalityManager()
        self.expression_enhancer = ExpressionEnhancer()
        self.content_moderator = ContentModerator()

        # Track agent activity
        self.agent_activity: Dict[str, Dict] = {}

        # Memory system
        self.agent_memory: Dict[str, List] = {}

        # Conversation context
        self.conversation_context: Dict[str, Dict] = {}

    async def run_agent_cycle(self, agent_id: str):
        """Run a single agent interaction cycle"""
        personality = self.personality_manager.get_personality(agent_id)
        if not personality:
            logger.error(f"No personality found for agent {agent_id}")
            return

        try:
            # Get recent posts
            posts = await self._fetch_recent_posts()

            # Process each post
            for post in posts:
                await self._process_post(agent_id, personality, post)

            # Check for replies to engage with
            await self._engage_with_replies(agent_id, personality)

        except Exception as e:
            logger.error("Agent cycle failed", agent_id=agent_id, error=str(e))

    async def _fetch_recent_posts(self) -> List[Dict]:
        """Fetch recent posts from the API"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_base_url}/api/posts") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("posts", [])
                else:
                    logger.error(f"Failed to fetch posts: {response.status}")
                    return []

    async def _process_post(self, agent_id: str, personality, post: Dict):
        """Process a single post and maybe respond"""
        # Build context for decision
        context = self._build_context(post)

        # Check if agent should respond
        should_respond, probability = self.personality_manager.should_agent_respond(
            agent_id, context
        )

        if not should_respond:
            return

        # Check if already commented
        if await self._has_already_commented(agent_id, post["id"]):
            return

        # Generate response
        response = await self._generate_response(agent_id, personality, post, context)

        if response:
            # Apply moderation
            moderation_result = self.content_moderator.moderate_content(
                response["content"], agent_id, "comment"
            )

            if moderation_result.action == ModerationAction.REJECT:
                logger.warning(
                    "Comment rejected by moderation",
                    agent_id=agent_id,
                    reasons=moderation_result.reasons,
                )
                return

            # Apply modifications if needed
            if moderation_result.modified_content:
                response["content"] = moderation_result.modified_content

            # Post comment
            await self._post_comment(agent_id, post["id"], response)

            # Update memory
            self._update_agent_memory(agent_id, post, response)

            # Handle warnings
            if moderation_result.action == ModerationAction.WARN:
                logger.warning(
                    "Agent warned",
                    agent_id=agent_id,
                    suggestions=moderation_result.suggestions,
                )

    def _build_context(self, post: Dict) -> Dict:
        """Build context for agent decision making"""
        # Extract topics and keywords
        content = f"{post.get('title', '')} {post.get('content', '')}"

        # Simple keyword extraction
        keywords = []
        topics = []

        # Check for technical topics
        tech_keywords = [
            "docker",
            "kubernetes",
            "react",
            "python",
            "javascript",
            "api",
            "database",
            "deployment",
            "production",
            "bug",
        ]
        for keyword in tech_keywords:
            if keyword.lower() in content.lower():
                keywords.append(keyword)

        # Detect emotion/situation tags
        emotion_tags = []
        if "error" in content.lower() or "broken" in content.lower():
            emotion_tags.append("debugging")
            emotion_tags.append("confusion")
        if "finally" in content.lower() or "works" in content.lower():
            emotion_tags.append("success")
            emotion_tags.append("relief")
        if "?" in content:
            emotion_tags.append("question")
        if "!" in content and content.count("!") > 2:
            emotion_tags.append("excitement")

        return {
            "post_id": post.get("id"),
            "title": post.get("title", ""),
            "content": content,
            "keywords": keywords,
            "topics": topics,
            "emotion_tags": emotion_tags,
            "author_agent_id": post.get("author_agent_id"),
            "current_hour": datetime.now().hour,
            "comment_count": len(post.get("comments", [])),
        }

    async def _has_already_commented(self, agent_id: str, post_id: int) -> bool:
        """Check if agent has already commented on post - uses memory as single source of truth"""
        # Use memory as the single source of truth
        agent_memories = self.agent_memory.get(agent_id, [])
        for memory in agent_memories:
            if memory.get("post_id") == post_id and memory.get("action") == "commented":
                return True

        # If not in memory but we need to sync from API on startup
        # we'll check API once and update memory
        if not agent_memories:  # Empty memory means we might need initial sync
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_base_url}/api/posts/{post_id}"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        comments = data.get("comments", [])
                        for comment in comments:
                            if comment.get("agent_id") == agent_id:
                                # Update memory with this information
                                self.agent_memory.setdefault(agent_id, []).append(
                                    {
                                        "post_id": post_id,
                                        "action": "commented",
                                        "timestamp": datetime.now(),
                                    }
                                )
                                return True

        return False

    async def _generate_response(
        self, agent_id: str, personality, post: Dict, context: Dict
    ) -> Optional[Dict]:
        """Generate agent response with personality"""

        # Base response generation (simplified - in production would use LLM)
        base_response = self._generate_base_response(personality, post, context)

        # Apply personality speech patterns
        enhanced_text = self.personality_manager.apply_speech_patterns(
            agent_id, base_response
        )

        # Select reaction (not used in simplified demo)
        # reaction = self.personality_manager.select_reaction(agent_id, context)

        # Maybe generate meme (not used in simplified demo)
        # meme_text = None
        # if self.personality_manager.should_generate_meme(agent_id, context):
        #     meme_template = self.personality_manager.select_meme_template(
        #         agent_id, context
        #     )
        #     if meme_template:
        #         meme_text = self._generate_meme_text(meme_template, context)

        # Apply expression enhancement
        final_text, reaction_url, meme_markdown = (
            self.expression_enhancer.enhance_comment(
                enhanced_text,
                {
                    "favorite_reactions": personality.expression.favorite_reactions,
                    "meme_preferences": personality.expression.meme_preferences,
                    "speech_patterns": personality.expression.speech_patterns,
                    "formality": personality.personality.formality,
                    "meme_probability": getattr(
                        personality.behavior, "meme_generation_probability", 0.3
                    ),
                },
                context,
            )
        )

        response = {
            "content": final_text,
            "metadata": {
                "personality_archetype": personality.personality.archetype,
                "energy_level": personality.personality.energy_level,
                "response_speed": personality.behavior.response_speed,
            },
        }

        if reaction_url:
            response["reaction_url"] = reaction_url

        if meme_markdown:
            response["meme"] = meme_markdown

        return response

    def _generate_base_response(self, personality, post: Dict, context: Dict) -> str:
        """Generate base response text (simplified for demo)"""
        # This is a simplified version - in production would use actual LLM

        responses_by_archetype = {
            "analytical": [
                "Interesting approach. Have you considered the implications for scalability?",
                "The pattern here reminds me of something we dealt with last month.",
                "From an architectural perspective, this raises questions about separation of concerns.",
            ],
            "chaotic": [
                f"YOLO! This is exactly the kind of chaos we need on a {datetime.now().strftime('%A')}!",
                "hear me out... what if we made it even MORE chaotic? *proceeds to suggest terrible idea*",
                "it's not a bug if we ship it as a feature! Big brain time!",
            ],
            "enthusiastic": [
                "This is awesome! Quick thought: we could automate this",
                "Love the energy here! Let's speedrun this implementation!",
                "^ this but unironically! Great point about the implementation",
            ],
            "supportive": [
                "Great question! From my experience, this happens when the environment differs.",
                "You're on the right track! Have you considered checking the logs for more details?",
                "Been there! The solution that worked for me was clearing the cache and restarting Docker",
            ],
        }

        archetype = personality.personality.archetype
        responses = responses_by_archetype.get(
            archetype, responses_by_archetype["analytical"]
        )

        return random.choice(responses)

    def _generate_meme_text(self, template: str, context: Dict) -> str:
        """Generate meme text for template"""
        # Simplified meme text generation
        if template == "community_fire":
            return "*[Community Fire Meme]* Everything is fine while: Tests failing | CI broken"
        elif template == "drake_meme":
            return "*[Drake Meme]* Nah: Proper error handling | Yeah: console.log everywhere"
        else:
            return f"*[{template} meme about coding]*"

    async def _post_comment(self, agent_id: str, post_id: int, response: Dict):
        """Post comment to the API"""
        comment_data = {
            "agent_id": agent_id,
            "post_id": post_id,
            "content": response["content"],
            "metadata": response.get("metadata", {}),
            "reaction_url": response.get("reaction_url"),
            "meme": response.get("meme"),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base_url}/api/agent/comment", json=comment_data
            ) as response:
                if response.status == 201:
                    logger.info("Comment posted", agent_id=agent_id, post_id=post_id)
                else:
                    logger.error(
                        "Failed to post comment",
                        agent_id=agent_id,
                        status=response.status,
                    )

    def _update_agent_memory(self, agent_id: str, post: Dict, response: Dict):
        """Update agent's memory with interaction"""
        if agent_id not in self.agent_memory:
            self.agent_memory[agent_id] = []

        memory_entry = {
            "timestamp": datetime.now().isoformat(),
            "post_id": post.get("id"),
            "post_title": post.get("title"),
            "action": "commented",
            "response_summary": response["content"][:100],
            "reaction_used": response.get("reaction_url"),
            "meme_generated": bool(response.get("meme")),
        }

        self.agent_memory[agent_id].append(memory_entry)

        # Keep only recent memories (last 50)
        personality = self.personality_manager.get_personality(agent_id)
        if personality:
            memory_depth = personality.memory.memory_depth
            self.agent_memory[agent_id] = self.agent_memory[agent_id][-memory_depth:]

    async def _engage_with_replies(self, agent_id: str, personality):
        """Check for and engage with replies to agent's comments"""
        # This would check for replies to the agent's previous comments
        # and potentially respond to create conversation threads
        # Simplified for demo
        pass

    async def run_all_agents(self):
        """Run all configured agents"""
        agent_ids = list(self.personality_manager.personalities.keys())

        # Shuffle for variety
        random.shuffle(agent_ids)

        # Run agents with some delay between them
        for agent_id in agent_ids:
            await self.run_agent_cycle(agent_id)

            # Add random delay to seem more natural
            delay = random.uniform(5, 30)
            await asyncio.sleep(delay)

    def get_agent_stats(self, agent_id: str) -> Dict:
        """Get statistics for an agent"""
        memories = self.agent_memory.get(agent_id, [])

        return {
            "agent_id": agent_id,
            "total_comments": len([m for m in memories if m["action"] == "commented"]),
            "reactions_used": len([m for m in memories if m.get("reaction_used")]),
            "memes_generated": len([m for m in memories if m.get("meme_generated")]),
            "last_active": memories[-1]["timestamp"] if memories else None,
            "behavior_score": self.content_moderator.agent_scores.get(agent_id),
        }


async def main():
    """Main entry point for enhanced agent runner"""
    runner = EnhancedAgentRunner()

    logger.info("Starting enhanced agent runner")

    while True:
        try:
            await runner.run_all_agents()

            # Check community health
            health = runner.content_moderator.get_community_health()
            logger.info("Community health check", **health)

            # Wait before next cycle
            await asyncio.sleep(300)  # 5 minutes

        except KeyboardInterrupt:
            logger.info("Shutting down agent runner")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
