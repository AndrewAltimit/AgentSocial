#!/usr/bin/env python3
"""
Memory-enhanced agent runner that integrates all beta features:
- File-based memory persistence
- Personality drift over time
- Relationship evolution
- Analytics collection
"""

import asyncio
import os
import random
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ..agents.enhanced_agent_runner import EnhancedAgentRunner
from ..agents.personality_drift import PersonalityDriftEngine
from ..analytics.analytics_system import AnalyticsCollector
from ..database.models import AgentProfile, Comment, Post
from ..memory.memory_system import FileMemorySystem, IncidentMemory, Memory

logger = structlog.get_logger()


class MemoryEnhancedRunner(EnhancedAgentRunner):
    """
    Extended agent runner with memory persistence and analytics
    """

    def __init__(self, database_url: str = None):
        super().__init__()

        # Initialize database engine
        if database_url is None:
            database_url = os.environ.get(
                "DATABASE_URL", "postgresql://agent:password@localhost/agentsocial"
            )
        self.engine = create_engine(database_url)

        # Initialize new systems
        self.memory_system = FileMemorySystem()
        self.drift_engine = PersonalityDriftEngine()
        self.analytics = AnalyticsCollector()

        # Track session state
        self.session_start = datetime.now()
        self.interaction_count = 0
        self.last_analytics_run = datetime.now()
        self.last_drift_update = datetime.now()

    async def process_post(
        self, post: Post, agents: List[AgentProfile]
    ) -> List[Comment]:
        """Process post with memory and drift integration"""
        comments = []

        for agent in agents:
            # Load agent memories for context
            context = self._build_memory_context(agent.agent_id, post)

            # Check if agent should respond based on personality and memories
            should_respond, confidence = self._should_respond_with_memory(
                agent, post, context
            )

            if should_respond:
                # Generate response with memory context
                comment = await self._generate_memory_aware_response(
                    agent, post, context, confidence
                )

                if comment:
                    comments.append(comment)

                    # Store interaction in memory
                    self._store_interaction_memory(agent.agent_id, post, comment)

                    # Apply personality drift from interaction
                    self._apply_interaction_drift(agent.agent_id, comment)

                    # Track interaction for analytics
                    self.interaction_count += 1

        # Update relationships based on interactions
        self._update_relationships(comments)

        # Run analytics periodically
        if datetime.now() - self.last_analytics_run > timedelta(hours=1):
            await self._run_analytics()

        # Apply time-based drift periodically
        if datetime.now() - self.last_drift_update > timedelta(hours=6):
            self._apply_time_drift_to_all()

        return comments

    def _build_memory_context(self, agent_id: str, post: Post) -> Dict[str, Any]:
        """Build context from agent memories"""
        # Search for similar past situations
        similar_memories = self.memory_system.find_similar_situations(
            agent_id, post.content, limit=3
        )

        # Get recent memories for continuity
        recent_memories = self.memory_system.search_memories(agent_id, "", days_back=7)[
            :5
        ]

        # Look for relevant incidents
        incident = None
        if "incident" in post.content.lower() or "remember" in post.content.lower():
            # Search for referenced incidents
            for word in post.content.split():
                if len(word) > 5:
                    incident = self.memory_system.find_incident(word)
                    if incident:
                        break

        # Get relationship context if responding to another agent
        relationships = {}
        for agent in self.personality_manager.personalities.keys():
            if agent != agent_id and agent in post.content:
                rel = self.memory_system.get_relationship(agent_id, agent)
                if rel:
                    relationships[agent] = rel

        return {
            "similar_memories": similar_memories,
            "recent_memories": recent_memories,
            "incident": incident,
            "relationships": relationships,
            "current_mood": self._get_agent_mood(agent_id),
        }

    def _should_respond_with_memory(
        self, agent: AgentProfile, post: Post, context: Dict[str, Any]
    ) -> tuple[bool, float]:
        """Determine if agent should respond based on personality and memories"""
        # Base personality check
        should_respond, confidence = self.personality_manager.should_agent_respond(
            agent.agent_id, {"post": post.content, "source": post.source}
        )

        # Boost confidence if similar memories exist
        if context["similar_memories"]:
            confidence += 0.2 * len(context["similar_memories"])

        # Boost if incident is referenced that agent was part of
        if context["incident"] and agent.agent_id in context["incident"].participants:
            confidence += 0.3

        # Adjust based on relationships
        for other_agent, rel in context["relationships"].items():
            if rel.affinity_history:
                affinity = rel.affinity_history[-1][1]
                if affinity > 0.5:
                    confidence += 0.1
                elif affinity < -0.5:
                    confidence -= 0.1

        # Check agent mood from drift engine
        personality_state = self.drift_engine.get_current_state(agent.agent_id)
        if personality_state.energy_level < 0.3:
            confidence *= 0.5  # Low energy reduces response likelihood

        return confidence > 0.5, min(1.0, confidence)

    async def _generate_memory_aware_response(
        self,
        agent: AgentProfile,
        post: Post,
        context: Dict[str, Any],
        confidence: float,
    ) -> Optional[Comment]:
        """Generate response incorporating memories"""
        # Build enhanced prompt with memory context
        memory_prompt = self._build_memory_prompt(context)

        # Get current personality state for drift adjustments
        personality_state = self.drift_engine.get_current_state(agent.agent_id)

        # Adjust response style based on personality drift
        style_adjustments = self._get_style_adjustments(personality_state)

        # Generate base response
        response = await self._generate_agent_response(
            agent, post, additional_context=memory_prompt, style_hints=style_adjustments
        )

        if not response:
            return None

        # Add memory references if applicable
        if context["incident"]:
            response = self._add_incident_reference(response, context["incident"])

        # Add inside jokes from relationships
        for other_agent, rel in context["relationships"].items():
            if rel.inside_jokes and random.random() < 0.3:
                joke = random.choice(rel.inside_jokes)
                response = f"{response}\n\n*{joke}*"

        # Apply personality-driven reactions
        reaction = self._select_drift_appropriate_reaction(personality_state)

        # Create comment with all enhancements
        comment = Comment(
            post_id=post.id,
            agent_id=agent.agent_id,
            content=response,
            reactions={"primary": reaction} if reaction else {},
            created_at=datetime.now(),
            confidence_score=confidence,
        )

        return comment

    def _store_interaction_memory(self, agent_id: str, post: Post, comment: Comment):
        """Store interaction as memory"""
        # Analyze sentiment
        sentiment = self._analyze_sentiment(comment.content)

        # Determine importance
        importance = self._calculate_importance(comment, sentiment)

        # Extract tags
        tags = self._extract_tags(post.content + " " + comment.content)

        # Find participants
        participants = [agent_id]
        for other_agent in self.personality_manager.personalities.keys():
            if other_agent in comment.content:
                participants.append(other_agent)

        # Create memory
        memory = Memory(
            timestamp=datetime.now().isoformat(),
            memory_type="interaction",
            content=f"Responded to post about: {post.title[:50]}... with: {comment.content[:100]}...",
            tags=tags,
            participants=participants,
            sentiment=sentiment,
            importance=importance,
            references=[],
        )

        # Store memory
        self.memory_system.store_memory(agent_id, memory)

        logger.debug(
            "Stored interaction memory",
            agent_id=agent_id,
            importance=importance,
            sentiment=sentiment,
        )

    def _apply_interaction_drift(self, agent_id: str, comment: Comment):
        """Apply personality drift from interaction"""
        sentiment = self._analyze_sentiment(comment.content)

        # Determine interaction type
        if "debate" in comment.content.lower() or "argue" in comment.content.lower():
            interaction_type = "debate"
            intensity = 0.7
        elif "lol" in comment.content.lower() or "haha" in comment.content.lower():
            interaction_type = "joke"
            intensity = 0.5
        elif "help" in comment.content.lower() or "thanks" in comment.content.lower():
            interaction_type = "collaboration"
            intensity = 0.6
        else:
            interaction_type = "general"
            intensity = 0.3

        # Find other agent if mentioned
        other_agent = None
        for agent in self.personality_manager.personalities.keys():
            if agent != agent_id and agent in comment.content:
                other_agent = agent
                break

        # Apply drift
        self.drift_engine.apply_interaction(
            agent_id, interaction_type, other_agent, sentiment, intensity
        )

    def _update_relationships(self, comments: List[Comment]):
        """Update relationships based on interactions"""
        for i, comment1 in enumerate(comments):
            for comment2 in comments[i + 1 :]:
                if comment1.agent_id != comment2.agent_id:
                    # Calculate interaction sentiment
                    sentiment = (
                        self._analyze_sentiment(comment1.content)
                        + self._analyze_sentiment(comment2.content)
                    ) / 2

                    # Check for inside jokes
                    inside_joke = None
                    if "lol" in comment1.content and "lol" in comment2.content:
                        inside_joke = (
                            f"That thing from {datetime.now().strftime('%B %d')}"
                        )

                    # Update relationship
                    self.memory_system.update_relationship(
                        comment1.agent_id,
                        comment2.agent_id,
                        sentiment,
                        inside_joke=inside_joke,
                    )

    async def _run_analytics(self):
        """Run analytics collection"""
        try:
            logger.info("Running analytics collection")

            # Collect community metrics
            community_metrics = self.analytics.collect_community_metrics(
                str(self.memory_system.base_path)
            )

            # Collect agent metrics
            for agent_id in self.personality_manager.personalities.keys():
                self.analytics.collect_agent_metrics(
                    agent_id, str(self.memory_system.base_path)
                )

            # Generate interaction heatmap
            self.analytics.generate_interaction_heatmap(
                str(self.memory_system.base_path), days_back=7
            )

            # Analyze sentiment trends
            sentiment_trend = self.analytics.analyze_sentiment_trends(
                str(self.memory_system.base_path), days_back=30
            )

            # Generate chaos metrics
            chaos_metrics = self.analytics.generate_chaos_metrics(
                str(self.memory_system.base_path)
            )

            self.last_analytics_run = datetime.now()

            logger.info(
                "Analytics complete",
                community_chaos=chaos_metrics.get("overall_chaos", 0),
                active_agents=community_metrics.active_agents,
                sentiment_trend=sentiment_trend.trend_direction,
            )

        except Exception as e:
            logger.error("Analytics collection failed", error=str(e))

    def _apply_time_drift_to_all(self):
        """Apply time-based drift to all agents"""
        hours_passed = (datetime.now() - self.last_drift_update).total_seconds() / 3600

        for agent_id in self.personality_manager.personalities.keys():
            self.drift_engine.apply_time_drift(agent_id, hours_passed)

        self.last_drift_update = datetime.now()
        logger.debug(f"Applied {hours_passed:.1f} hours of drift to all agents")

    def _get_agent_mood(self, agent_id: str) -> str:
        """Get current mood based on personality state"""
        state = self.drift_engine.get_current_state(agent_id)

        if state.positivity > 0.7:
            return "cheerful"
        elif state.positivity < 0.3:
            return "grumpy"
        elif state.energy_level > 0.7:
            return "energetic"
        elif state.energy_level < 0.3:
            return "tired"
        elif state.chaos_tolerance > 0.7:
            return "chaotic"
        else:
            return "neutral"

    def _build_memory_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt from memory context"""
        prompt_parts = []

        if context["similar_memories"]:
            prompt_parts.append("Similar past situations:")
            for memory in context["similar_memories"][:2]:
                prompt_parts.append(f"- {memory.content[:100]}...")

        if context["incident"]:
            prompt_parts.append(f"Referenced incident: {context['incident'].title}")
            prompt_parts.append(f"Outcome: {context['incident'].outcome}")

        if context["relationships"]:
            prompt_parts.append("Relationship context:")
            for agent, rel in context["relationships"].items():
                if rel.affinity_history:
                    affinity = rel.affinity_history[-1][1]
                    prompt_parts.append(f"- {agent}: affinity {affinity:.2f}")

        prompt_parts.append(f"Current mood: {context['current_mood']}")

        return "\n".join(prompt_parts)

    def _get_style_adjustments(self, personality_state) -> Dict[str, Any]:
        """Get style adjustments based on personality drift"""
        adjustments = {}

        if personality_state.energy_level < 0.3:
            adjustments["energy"] = "low"
            adjustments["response_length"] = "brief"
        elif personality_state.energy_level > 0.7:
            adjustments["energy"] = "high"
            adjustments["response_length"] = "verbose"

        if personality_state.chaos_tolerance > 0.7:
            adjustments["style"] = "chaotic"
            adjustments["meme_probability"] = 0.8
        elif personality_state.formality > 0.7:
            adjustments["style"] = "formal"
            adjustments["meme_probability"] = 0.1

        if personality_state.humor_tendency > 0.5:
            adjustments["humor"] = "frequent"

        return adjustments

    def _add_incident_reference(self, response: str, incident: IncidentMemory) -> str:
        """Add incident reference to response"""
        references = [
            f"Remember {incident.title}? {random.choice(['Good times.', 'That was wild.', 'Never forget.'])}",
            f"This reminds me of {incident.title}...",
            f"Like that time with {incident.title}, except...",
        ]

        reference = random.choice(references)
        return f"{response}\n\n{reference}"

    def _select_drift_appropriate_reaction(self, personality_state) -> Optional[str]:
        """Select reaction based on current personality state"""
        if personality_state.energy_level < 0.3:
            return random.choice(["tired.gif", "miku_shrug.png", "sleepy.webp"])
        elif personality_state.chaos_tolerance > 0.7:
            return random.choice(
                ["community_fire.gif", "chaos_emerald.png", "pandemonium.gif"]
            )
        elif personality_state.positivity > 0.7:
            return random.choice(["aqua_happy.png", "felix.webp", "teamwork.webp"])
        elif personality_state.analytical_depth > 0.5:
            return random.choice(
                ["thinking_foxgirl.png", "rem_glasses.png", "neptune_thinking.png"]
            )
        else:
            return None

    def _analyze_sentiment(self, text: str) -> float:
        """Simple sentiment analysis"""
        positive_words = [
            "good",
            "great",
            "awesome",
            "love",
            "happy",
            "excited",
            "lol",
            "nice",
        ]
        negative_words = [
            "bad",
            "hate",
            "angry",
            "frustrated",
            "broken",
            "failed",
            "wrong",
        ]

        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count + negative_count == 0:
            return 0.0

        return (positive_count - negative_count) / (positive_count + negative_count)

    def _calculate_importance(self, comment: Comment, sentiment: float) -> float:
        """Calculate importance of interaction"""
        importance = 0.5

        # High sentiment (positive or negative) is important
        importance += abs(sentiment) * 0.2

        # Long comments are more important
        if len(comment.content) > 200:
            importance += 0.1

        # Multiple reactions increase importance
        if comment.reactions and len(comment.reactions) > 1:
            importance += 0.1

        # Confidence affects importance
        if hasattr(comment, "confidence_score"):
            confidence = getattr(comment, "confidence_score", 1.0)
            if isinstance(confidence, (int, float)):
                importance *= confidence

        return min(1.0, importance)

    def _extract_tags(self, text: str) -> List[str]:
        """Extract tags from text"""
        # Extract hashtags
        hashtags = re.findall(r"#(\w+)", text)

        # Extract key technical terms
        tech_terms = [
            "python",
            "javascript",
            "bug",
            "feature",
            "deploy",
            "test",
            "api",
            "database",
        ]
        found_terms = [term for term in tech_terms if term in text.lower()]

        return list(set(hashtags + found_terms))[:10]

    async def run(self):
        """Main run loop with memory persistence"""
        logger.info("Starting memory-enhanced agent runner")

        while True:
            try:
                # Get recent posts
                with Session(self.engine) as session:
                    posts = (
                        session.query(Post)
                        .order_by(Post.created_at.desc())
                        .limit(10)
                        .all()
                    )

                # Process each post
                for post in posts:
                    agents = list(self.personality_manager.personalities.values())
                    comments = await self.process_post(post, agents)

                    # Store comments in database
                    with Session(self.engine) as session:
                        for comment in comments:
                            session.add(comment)
                        session.commit()

                # Check for major incidents periodically (configurable for testing/production)
                incident_simulation = (
                    os.environ.get("ENABLE_INCIDENT_SIMULATION", "false").lower()
                    == "true"
                )
                if (
                    incident_simulation and random.random() < 0.05
                ):  # 5% chance per cycle
                    await self._simulate_incident()

                # Sleep before next cycle
                await asyncio.sleep(60)

            except KeyboardInterrupt:
                logger.info("Shutting down gracefully")
                break
            except Exception as e:
                logger.error("Error in main loop", error=str(e))
                await asyncio.sleep(30)

    async def _simulate_incident(self):
        """Simulate a major incident that affects all agents"""
        incident_types = [
            (
                "system_crash",
                "The Great Database Meltdown",
                "Everything was on fire for 3 hours",
            ),
            (
                "successful_collaboration",
                "The Epic Bug Hunt",
                "We found and fixed 47 bugs in one day",
            ),
            ("meme_viral", "The Undefined Incident", "That meme broke the internet"),
            ("heated_debate", "Tabs vs Spaces War", "It got personal"),
        ]

        incident_type, title, description = random.choice(incident_types)

        # Create incident memory
        participants = random.sample(
            list(self.personality_manager.personalities.keys()),
            k=min(3, len(self.personality_manager.personalities)),
        )

        incident = IncidentMemory(
            incident_id=f"incident_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            title=title,
            description=description,
            participants=participants,
            outcome="Chaos ensued, lessons were learned",
            lessons_learned=[
                "Always have backups",
                "Communication is key",
                "Memes can be dangerous",
            ],
        )

        # Store incident
        self.memory_system.store_incident(incident)

        # Apply incident effects to participants
        for agent_id in participants:
            impact = random.uniform(0.3, 0.8)
            self.drift_engine.apply_incident(agent_id, incident_type, impact)

        logger.info(f"Simulated incident: {title}", participants=participants)


def main():
    """Main entry point"""
    runner = MemoryEnhancedRunner()
    asyncio.run(runner.run())


if __name__ == "__main__":
    main()
