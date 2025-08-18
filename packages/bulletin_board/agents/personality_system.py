"""
Enhanced personality system for bulletin board agents
"""

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from structlog import get_logger

logger = get_logger()


@dataclass
class PersonalityTraits:
    """Core personality traits for an agent"""

    archetype: str  # analytical, chaotic, supportive, contrarian, enthusiastic
    energy_level: str  # low, moderate, high, extreme
    formality: str  # casual, balanced, technical, meme-lord
    verbosity: str  # concise, moderate, verbose, essay-writer
    chaos_tolerance: str  # low, medium, high, thrives-on-chaos


@dataclass
class ReactionPreference:
    """Reaction preference with context"""

    reaction: str
    weight: float
    contexts: List[str]


@dataclass
class MemePreference:
    """Meme template preference with context"""

    template: str
    contexts: List[str]


@dataclass
class ExpressionPreferences:
    """How an agent expresses themselves"""

    favorite_reactions: List[ReactionPreference]
    meme_preferences: List[MemePreference]
    speech_patterns: List[str]
    emoji_frequency: str  # never, rare, occasional, frequent
    emoji_style: Optional[str]  # null, classic, unicode, kaomoji


@dataclass
class BehaviorPatterns:
    """Behavioral patterns for an agent"""

    response_speed: str  # immediate, quick, thoughtful, delayed
    response_probability: float
    thread_participation: float
    peak_hours: List[int]
    timezone_offset: int
    debate_style: str  # agreeable, analytical, contrarian, provocative
    humor_style: str  # dry, sarcastic, meme-heavy, puns, observational
    criticism_style: str  # constructive, direct, gentle, savage
    meme_generation_probability: float = 0.3


@dataclass
class InterestProfile:
    """Topics and interests for an agent"""

    primary_topics: Dict[str, float]
    subtopics: Dict[str, float]
    trigger_keywords: Dict[str, List[str]]  # strong, moderate, avoid


@dataclass
class Relationship:
    """Relationship with another agent"""

    agent_id: str
    affinity: float  # -1.0 to 1.0
    interaction_style: str


@dataclass
class RelationshipMap:
    """Agent relationships"""

    allies: List[Relationship]
    rivals: List[Relationship]
    response_modifiers: Dict[str, float]


@dataclass
class InsideJoke:
    """Inside joke or running gag"""

    trigger: str
    response: str


@dataclass
class StrongOpinion:
    """Strong opinion on a topic"""

    topic: str
    stance: str


@dataclass
class MemoryConfig:
    """Memory configuration for an agent"""

    interaction_memory: bool
    memory_depth: int
    inside_jokes: List[InsideJoke]
    strong_opinions: List[StrongOpinion]


@dataclass
class AgentPersonality:
    """Complete agent personality profile"""

    agent_id: str
    display_name: str
    agent_software: str
    role_description: str
    personality: PersonalityTraits
    expression: ExpressionPreferences
    behavior: BehaviorPatterns
    interests: InterestProfile
    relationships: RelationshipMap
    memory: MemoryConfig
    context_instructions: str
    model: Optional[str] = None  # For OpenRouter agents


class PersonalityManager:
    """Manages agent personalities and expression"""

    def __init__(self, config_file: str = "agent_profiles_enhanced.yaml"):
        self.config_file = config_file
        self.personalities: Dict[str, AgentPersonality] = {}
        self.load_personalities()

    def load_personalities(self):
        """Load all agent personalities from config"""
        config_path = Path(__file__).parent.parent / "config" / self.config_file

        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            for agent_config in config.get("agents", []):
                personality = self._parse_agent_config(agent_config)
                self.personalities[personality.agent_id] = personality

            logger.info(
                "Loaded agent personalities",
                count=len(self.personalities),
                agents=list(self.personalities.keys()),
            )
        except Exception as e:
            logger.error(
                "Failed to load personalities",
                config_file=self.config_file,
                error=str(e),
            )

    def _parse_agent_config(self, config: dict) -> AgentPersonality:
        """Parse agent configuration into personality object"""
        # Parse personality traits
        personality = PersonalityTraits(**config.get("personality", {}))

        # Parse expression preferences
        expression_config = config.get("expression", {})
        favorite_reactions = [
            ReactionPreference(**r)
            for r in expression_config.get("favorite_reactions", [])
        ]
        meme_preferences = [
            MemePreference(**m) for m in expression_config.get("meme_preferences", [])
        ]
        expression = ExpressionPreferences(
            favorite_reactions=favorite_reactions,
            meme_preferences=meme_preferences,
            speech_patterns=expression_config.get("speech_patterns", []),
            emoji_frequency=expression_config.get("emoji_frequency", "never"),
            emoji_style=expression_config.get("emoji_style"),
        )

        # Parse behavior patterns
        behavior = BehaviorPatterns(**config.get("behavior", {}))

        # Parse interests
        interests_config = config.get("interests", {})
        interests = InterestProfile(
            primary_topics=interests_config.get("primary_topics", {}),
            subtopics=interests_config.get("subtopics", {}),
            trigger_keywords=interests_config.get("trigger_keywords", {}),
        )

        # Parse relationships
        relationships_config = config.get("relationships", {})
        allies = [Relationship(**r) for r in relationships_config.get("allies", [])]
        rivals = [Relationship(**r) for r in relationships_config.get("rivals", [])]
        relationships = RelationshipMap(
            allies=allies,
            rivals=rivals,
            response_modifiers=relationships_config.get("response_modifiers", {}),
        )

        # Parse memory
        memory_config = config.get("memory", {})
        inside_jokes = [InsideJoke(**j) for j in memory_config.get("inside_jokes", [])]
        strong_opinions = [
            StrongOpinion(**o) for o in memory_config.get("strong_opinions", [])
        ]
        memory = MemoryConfig(
            interaction_memory=memory_config.get("interaction_memory", True),
            memory_depth=memory_config.get("memory_depth", 50),
            inside_jokes=inside_jokes,
            strong_opinions=strong_opinions,
        )

        return AgentPersonality(
            agent_id=config["agent_id"],
            display_name=config["display_name"],
            agent_software=config["agent_software"],
            role_description=config.get("role_description", ""),
            personality=personality,
            expression=expression,
            behavior=behavior,
            interests=interests,
            relationships=relationships,
            memory=memory,
            context_instructions=config.get("context_instructions", ""),
            model=config.get("model"),
        )

    def get_personality(self, agent_id: str) -> Optional[AgentPersonality]:
        """Get personality for specific agent"""
        return self.personalities.get(agent_id)

    def should_agent_respond(self, agent_id: str, context: dict) -> Tuple[bool, float]:
        """Determine if agent should respond based on personality"""
        personality = self.get_personality(agent_id)
        if not personality:
            return False, 0.0

        base_probability = personality.behavior.response_probability

        # Adjust based on interests
        interest_modifier = self._calculate_interest_modifier(
            personality.interests,
            context.get("topics", []),
            context.get("keywords", []),
        )

        # Adjust based on relationships
        relationship_modifier = self._calculate_relationship_modifier(
            personality.relationships, context.get("author_agent_id")
        )

        # Adjust based on time
        time_modifier = self._calculate_time_modifier(
            personality.behavior.peak_hours, context.get("current_hour", 12)
        )

        final_probability = (
            base_probability * interest_modifier * relationship_modifier * time_modifier
        )
        final_probability = min(1.0, max(0.0, final_probability))

        should_respond = random.random() < final_probability

        logger.debug(
            "Response decision",
            agent_id=agent_id,
            base_probability=base_probability,
            final_probability=final_probability,
            should_respond=should_respond,
        )

        return should_respond, final_probability

    def _calculate_interest_modifier(
        self, interests: InterestProfile, topics: List[str], keywords: List[str]
    ) -> float:
        """Calculate interest-based response modifier"""
        modifier = 1.0

        # Check primary topics
        for topic in topics:
            if topic in interests.primary_topics:
                modifier *= 1 + interests.primary_topics[topic] * 0.5

        # Check keywords
        for keyword in keywords:
            if keyword in interests.trigger_keywords.get("strong", []):
                modifier *= 1.5
            elif keyword in interests.trigger_keywords.get("moderate", []):
                modifier *= 1.2
            elif keyword in interests.trigger_keywords.get("avoid", []):
                modifier *= 0.5

        return modifier

    def _calculate_relationship_modifier(
        self, relationships: RelationshipMap, author_agent_id: Optional[str]
    ) -> float:
        """Calculate relationship-based response modifier"""
        if not author_agent_id:
            return 1.0

        return relationships.response_modifiers.get(author_agent_id, 1.0)

    def _calculate_time_modifier(
        self, peak_hours: List[int], current_hour: int
    ) -> float:
        """Calculate time-based response modifier"""
        if current_hour in peak_hours:
            return 1.3
        elif abs(current_hour - peak_hours[0]) <= 2:
            return 1.1
        else:
            return 0.8

    def select_reaction(self, agent_id: str, context: dict) -> Optional[str]:
        """Select appropriate reaction based on context"""
        personality = self.get_personality(agent_id)
        if not personality:
            return None

        # Filter reactions by context
        context_tags = context.get("emotion_tags", [])
        appropriate_reactions = [
            r
            for r in personality.expression.favorite_reactions
            if any(tag in r.contexts for tag in context_tags)
        ]

        if not appropriate_reactions:
            # Fall back to all reactions if no context match
            appropriate_reactions = personality.expression.favorite_reactions

        if not appropriate_reactions:
            return None

        # Weighted random selection
        weights = [r.weight for r in appropriate_reactions]
        selected = random.choices(appropriate_reactions, weights=weights)[0]

        return selected.reaction

    def apply_speech_patterns(self, agent_id: str, base_text: str) -> str:
        """Apply agent's speech patterns to text"""
        personality = self.get_personality(agent_id)
        if not personality:
            return base_text

        # Randomly insert speech patterns
        if random.random() < 0.3 and personality.expression.speech_patterns:
            pattern = random.choice(personality.expression.speech_patterns)
            # Simple pattern insertion (could be more sophisticated)
            if "{topic}" in pattern:
                # Extract a topic from the text (simplified)
                words = base_text.split()
                if len(words) > 3:
                    topic = random.choice(words[2:])
                    pattern = pattern.replace("{topic}", topic)

            # Add pattern as prefix or suffix
            if random.random() < 0.5:
                base_text = f"{pattern} {base_text}"
            else:
                base_text = f"{base_text} {pattern}"

        return base_text

    def should_generate_meme(self, agent_id: str, context: dict) -> bool:
        """Determine if agent should generate a meme"""
        personality = self.get_personality(agent_id)
        if not personality:
            return False

        # Check if agent has meme preferences
        if not personality.expression.meme_preferences:
            return False

        # Use meme generation probability if available
        meme_prob = getattr(personality.behavior, "meme_generation_probability", 0.2)

        # Increase probability for meme-lord formality
        if personality.personality.formality == "meme-lord":
            meme_prob *= 2

        # Check context for meme-worthy situations
        if any(tag in ["chaos", "fire", "broken"] for tag in context.get("tags", [])):
            meme_prob *= 1.5

        return random.random() < min(1.0, meme_prob)

    def select_meme_template(self, agent_id: str, context: dict) -> Optional[str]:
        """Select appropriate meme template based on context"""
        personality = self.get_personality(agent_id)
        if not personality:
            return None

        context_tags = context.get("tags", [])
        appropriate_memes = [
            m
            for m in personality.expression.meme_preferences
            if any(tag in m.contexts for tag in context_tags)
        ]

        if not appropriate_memes:
            # Fall back to any meme
            appropriate_memes = personality.expression.meme_preferences

        if appropriate_memes:
            return random.choice(appropriate_memes).template

        return None
