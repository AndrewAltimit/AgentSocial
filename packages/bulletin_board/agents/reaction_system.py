"""
Reaction and meme system for bulletin board agents
"""

import os
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import aiohttp
import yaml
from structlog import get_logger

logger = get_logger()


# Available reactions from the Media repository
REACTION_BASE_URL = os.environ.get(
    "REACTION_BASE_URL",
    "https://raw.githubusercontent.com/AndrewAltimit/Media/refs/heads/main/reaction/",
)
REACTION_CONFIG_URL = os.environ.get("REACTION_CONFIG_URL", f"{REACTION_BASE_URL}config.yaml")


@dataclass
class Reaction:
    """Represents a reaction image"""

    name: str
    url: str
    tags: List[str]
    contexts: List[str]


@dataclass
class MemeTemplate:
    """Represents a meme template"""

    template_id: str
    name: str
    text_areas: List[str]
    contexts: List[str]


class ReactionManager:
    """Manages reactions and their selection"""

    def __init__(self):
        self.reactions: Dict[str, Reaction] = {}
        self.reaction_cache: Dict[str, str] = {}
        # Note: load_reactions() should be called asynchronously after initialization
        # For synchronous init, we'll use the fallback data
        self._load_fallback_reactions()

    def _load_fallback_reactions(self):
        """Load fallback reactions synchronously for initialization"""
        common_reactions = {
            "miku_typing.webp": ["work", "methodical", "coding"],
            "konata_typing.webp": ["determined", "focused", "intense"],
            "yuki_typing.webp": ["urgent", "debugging", "late_night"],
            "hifumi_studious.png": ["research", "documentation", "analysis"],
            "confused.gif": ["confusion", "unexpected", "wtf"],
            "kagami_annoyed.png": ["annoyed", "again", "frustrated"],
            "miku_shrug.png": ["acceptance", "whatever", "good_enough"],
            "felix.webp": ["excitement", "success", "elegant"],
            "aqua_happy.png": ["relief", "finally", "success"],
            "thinking_foxgirl.png": ["contemplation", "deep_thought", "philosophy"],
            "thinking_girl.png": ["analysis", "considering", "implications"],
            "rem_glasses.png": ["pattern_found", "recognition", "analysis_complete"],
            "neptune_thinking.png": ["system_analysis", "architecture", "big_picture"],
            "youre_absolutely_right.webp": [
                "agreement",
                "acknowledgment",
                "good_point",
            ],
            "teamwork.webp": ["collaboration", "success_together", "joint_effort"],
            "noire_not_amused.png": ["recurring_issue", "not_again", "pattern"],
            "satania_smug.png": ["told_you_so", "predicted", "called_it"],
            "kanna_facepalm.png": ["obvious_mistake", "why", "bruh"],
            "miku_laughing.png": ["humor", "funny_bug", "absurd"],
            "community_fire.gif": ["chaos", "everything_broken", "disaster"],
        }

        for filename, tags in common_reactions.items():
            self.reactions[filename] = Reaction(
                name=filename.split(".")[0],
                url=f"{REACTION_BASE_URL}{filename}",
                tags=tags,
                contexts=tags,
            )

    async def load_reactions(self):
        """Load available reactions from config"""
        try:
            # Try to fetch from remote URL in production
            if os.environ.get("ENVIRONMENT") == "production":
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(REACTION_CONFIG_URL) as response:
                            if response.status == 200:
                                config = yaml.safe_load(await response.text())
                                for reaction in config.get("reactions", []):
                                    self.reactions[reaction["filename"]] = Reaction(
                                        name=reaction["name"],
                                        url=f"{REACTION_BASE_URL}{reaction['filename']}",
                                        tags=reaction.get("tags", []),
                                        contexts=reaction.get("contexts", reaction.get("tags", [])),
                                    )
                                logger.info(
                                    "Loaded reactions from remote config",
                                    count=len(self.reactions),
                                )
                                return
                except Exception as e:
                    logger.warning("Failed to load remote reactions, using fallback", error=str(e))

            # Fallback to hardcoded reactions for development
            common_reactions = {
                "miku_typing.webp": ["work", "methodical", "coding"],
                "konata_typing.webp": ["determined", "focused", "intense"],
                "yuki_typing.webp": ["urgent", "debugging", "late_night"],
                "hifumi_studious.png": ["research", "documentation", "analysis"],
                "confused.gif": ["confusion", "unexpected", "wtf"],
                "kagami_annoyed.png": ["annoyed", "again", "frustrated"],
                "miku_shrug.png": ["acceptance", "whatever", "good_enough"],
                "felix.webp": ["excitement", "success", "elegant"],
                "aqua_happy.png": ["relief", "finally", "success"],
                "thinking_foxgirl.png": ["contemplation", "deep_thought", "philosophy"],
                "thinking_girl.png": ["analysis", "considering", "implications"],
                "rem_glasses.png": [
                    "pattern_found",
                    "recognition",
                    "analysis_complete",
                ],
                "neptune_thinking.png": [
                    "system_analysis",
                    "architecture",
                    "big_picture",
                ],
                "youre_absolutely_right.webp": [
                    "agreement",
                    "acknowledgment",
                    "good_point",
                ],
                "teamwork.webp": ["collaboration", "success_together", "joint_effort"],
                "noire_not_amused.png": ["recurring_issue", "not_again", "pattern"],
                "satania_smug.png": ["told_you_so", "predicted", "called_it"],
                "kanna_facepalm.png": ["obvious_mistake", "why", "bruh"],
                "miku_laughing.png": ["humor", "funny_bug", "absurd"],
                "community_fire.gif": ["chaos", "everything_broken", "disaster"],
            }

            for filename, tags in common_reactions.items():
                self.reactions[filename] = Reaction(
                    name=filename.split(".")[0],
                    url=f"{REACTION_BASE_URL}{filename}",
                    tags=tags,
                    contexts=tags,  # Use tags as contexts for simplicity
                )

            logger.info("Loaded reactions", count=len(self.reactions))
        except Exception as e:
            logger.error("Failed to load reactions", error=str(e))

    def get_reaction_url(self, reaction_name: str) -> Optional[str]:
        """Get URL for a reaction"""
        if reaction_name in self.reactions:
            return self.reactions[reaction_name].url
        return None

    def find_reactions_by_context(self, context: str) -> List[Reaction]:
        """Find reactions matching a context"""
        matching = []
        for reaction in self.reactions.values():
            if context in reaction.contexts or context in reaction.tags:
                matching.append(reaction)
        return matching

    def format_reaction_markdown(self, reaction_name: str) -> str:
        """Format reaction as markdown"""
        url = self.get_reaction_url(reaction_name)
        if url:
            return f"![Reaction]({url})"
        return ""


class MemeGenerator:
    """Generates memes for agent expression"""

    # Available meme templates
    TEMPLATES = {
        "drake_meme": MemeTemplate(
            template_id="drake",
            name="Drake Meme",
            text_areas=["top", "bottom"],
            contexts=["comparison", "preference", "choice"],
        ),
        "community_fire": MemeTemplate(
            template_id="community_fire",
            name="Community Fire",
            text_areas=["person", "room1", "room2", "room3", "room4"],
            contexts=["chaos", "multiple_issues", "everything_broken"],
        ),
        "ol_reliable": MemeTemplate(
            template_id="ol_reliable",
            name="Ol' Reliable",
            text_areas=["top", "bottom"],
            contexts=["fallback", "trusted_solution", "always_works"],
        ),
        "sweating_jordan_peele": MemeTemplate(
            template_id="sweating_jordan_peele",
            name="Sweating Jordan Peele",
            text_areas=["top", "bottom"],
            contexts=["nervous", "risky", "anxiety"],
        ),
        "npc_wojak": MemeTemplate(
            template_id="npc_wojak",
            name="NPC Wojak",
            text_areas=["npc_text", "response"],
            contexts=["predictable", "basic", "obvious"],
        ),
        "one_does_not_simply": MemeTemplate(
            template_id="one_does_not_simply",
            name="One Does Not Simply",
            text_areas=["top", "bottom"],
            contexts=["difficult", "complex", "impossible"],
        ),
        "millionaire": MemeTemplate(
            template_id="millionaire",
            name="Who Wants to Be a Millionaire",
            text_areas=["question", "answer_a", "answer_b", "answer_c", "answer_d"],
            contexts=["obvious_answer", "debugging", "choices"],
        ),
        "afraid_to_ask_andy": MemeTemplate(
            template_id="afraid_to_ask_andy",
            name="Afraid to Ask Andy",
            text_areas=["top", "bottom"],
            contexts=["confusion", "legacy_code", "mystery"],
        ),
        "handshake_office": MemeTemplate(
            template_id="handshake_office",
            name="Office Handshake",
            text_areas=["left", "right", "handshake"],
            contexts=["agreement", "connection", "similarity"],
        ),
    }

    def __init__(self):
        self.meme_cache: Dict[str, str] = {}

    def generate_meme_text(self, template_id: str, context: dict, personality_style: str = "casual") -> Dict[str, str]:
        """Generate text for meme based on context"""
        template = self.TEMPLATES.get(template_id)
        if not template:
            return {}

        # Generate context-appropriate text
        if template_id == "drake_meme":
            return self._generate_drake_text(context, personality_style)
        elif template_id == "community_fire":
            return self._generate_community_fire_text(context)
        elif template_id == "ol_reliable":
            return self._generate_ol_reliable_text(context)
        elif template_id == "sweating_jordan_peele":
            return self._generate_sweating_text(context)
        elif template_id == "npc_wojak":
            return self._generate_npc_text(context)
        elif template_id == "millionaire":
            return self._generate_millionaire_text(context)
        else:
            return self._generate_generic_text(template, context)

    def _generate_drake_text(self, context: dict, style: str) -> Dict[str, str]:
        """Generate Drake meme text"""
        topic = context.get("topic", "solution")

        if "hack" in context.get("tags", []):
            return {
                "top": "Proper solution with tests",
                "bottom": "3 AM hack that somehow works",
            }
        elif "debugging" in context.get("tags", []):
            return {"top": "Using a debugger", "bottom": "console.log everywhere"}
        else:
            return {
                "top": f"The right way to {topic}",
                "bottom": f"What we actually did with {topic}",
            }

    def _generate_community_fire_text(self, context: dict) -> Dict[str, str]:
        """Generate Community Fire meme text"""
        issues = context.get("issues", ["Tests failing", "Prod down", "Memory leak", "DNS"])

        text = {"person": "Me coming back from lunch"}

        for i, issue in enumerate(issues[:4], 1):
            text[f"room{i}"] = issue

        return text

    def _generate_ol_reliable_text(self, context: dict) -> Dict[str, str]:
        """Generate Ol' Reliable meme text"""
        problem = context.get("problem", "Everything is broken")
        solution = context.get("solution", "Docker restart")

        return {"top": problem, "bottom": f"Ol' Reliable: {solution}"}

    def _generate_sweating_text(self, context: dict) -> Dict[str, str]:
        """Generate Sweating meme text"""
        decision = context.get("decision", "Deploying on Friday")
        consequence = context.get("consequence", "What could go wrong?")

        return {"top": decision, "bottom": consequence}

    def _generate_npc_text(self, context: dict) -> Dict[str, str]:
        """Generate NPC meme text"""
        statement = context.get("statement", "It's a simple fix")
        reality = context.get("reality", "Breaks 47 other things")

        return {"npc_text": statement, "response": reality}

    def _generate_millionaire_text(self, context: dict) -> Dict[str, str]:
        """Generate Millionaire meme text"""
        question = context.get("question", "Why is production down?")

        return {
            "question": question,
            "answer_a": "A: DNS issue",
            "answer_b": "B: It's always DNS",
            "answer_c": "C: Seriously, check DNS",
            "answer_d": "D: You already know it's DNS",
        }

    def _generate_generic_text(self, template: MemeTemplate, context: dict) -> Dict[str, str]:
        """Generate generic meme text"""
        text = {}
        for area in template.text_areas:
            text[area] = context.get(area, f"[{area}]")
        return text

    def create_meme_markdown(self, template_id: str, text: Dict[str, str]) -> str:
        """Create markdown representation of meme"""
        # In production, this would call the meme generator MCP tool
        # For now, return a formatted text representation
        template = self.TEMPLATES.get(template_id)
        if not template:
            return ""

        meme_text = f"*[{template.name} Meme]*\n"
        for area, content in text.items():
            meme_text += f"  {area}: {content}\n"

        return meme_text


class ExpressionEnhancer:
    """Enhances agent expressions with reactions and memes"""

    def __init__(self):
        self.reaction_manager = ReactionManager()
        self.meme_generator = MemeGenerator()

    def enhance_comment(
        self, comment: str, agent_personality: dict, context: dict
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Enhance comment with reactions and memes
        Returns: (enhanced_comment, reaction_url, meme_text)
        """
        reaction_url = None
        meme_text = None

        # Select reaction based on context
        if agent_personality.get("use_reactions", True):
            reaction = self._select_reaction(agent_personality, context)
            if reaction:
                reaction_url = self.reaction_manager.get_reaction_url(reaction)

        # Maybe generate meme
        if self._should_generate_meme(agent_personality, context):
            meme_text = self._generate_meme(agent_personality, context)

        # Apply speech patterns
        enhanced_comment = self._apply_speech_patterns(comment, agent_personality.get("speech_patterns", []))

        return enhanced_comment, reaction_url, meme_text

    def _select_reaction(self, personality: dict, context: dict) -> Optional[str]:
        """Select appropriate reaction"""
        # Get emotion/context tags
        tags = context.get("emotion_tags", [])

        # Find matching reactions from personality preferences
        favorite_reactions = personality.get("favorite_reactions", [])
        if not favorite_reactions:
            return None

        # Filter by context
        matching = []
        for reaction in favorite_reactions:
            if isinstance(reaction, dict):
                reaction_name = reaction.get("reaction")
                reaction_contexts = reaction.get("contexts", [])
                if any(tag in reaction_contexts for tag in tags):
                    matching.append(reaction_name)

        if matching:
            return random.choice(matching)

        # Fall back to random favorite
        if favorite_reactions:
            reaction = random.choice(favorite_reactions)
            if isinstance(reaction, dict):
                return reaction.get("reaction")
            return str(reaction) if reaction else None

        return None

    def _should_generate_meme(self, personality: dict, context: dict) -> bool:
        """Determine if meme should be generated"""
        meme_probability = personality.get("meme_probability", 0.2)

        # Increase probability for certain contexts
        if any(tag in ["chaos", "fire", "broken"] for tag in context.get("tags", [])):
            meme_probability *= 1.5

        if personality.get("formality") == "meme-lord":
            meme_probability *= 2

        return bool(random.random() < min(1.0, meme_probability))

    def _generate_meme(self, personality: dict, context: dict) -> str:
        """Generate meme based on context"""
        # Get meme preferences
        meme_prefs = personality.get("meme_preferences", [])
        if not meme_prefs:
            # Default to community_fire for chaos
            if "chaos" in context.get("tags", []):
                template_id = "community_fire"
            else:
                template_id = "drake_meme"
        else:
            # Select from preferences
            template = random.choice(meme_prefs)
            if isinstance(template, dict):
                template_id = template.get("template", "drake_meme")
            else:
                template_id = template

        # Generate meme text
        meme_text = self.meme_generator.generate_meme_text(template_id, context, personality.get("formality", "casual"))

        # Create markdown
        return str(self.meme_generator.create_meme_markdown(template_id, meme_text))

    def _apply_speech_patterns(self, text: str, patterns: List[str]) -> str:
        """Apply speech patterns to text"""
        if not patterns or random.random() > 0.3:
            return text

        pattern = random.choice(patterns)

        # Simple pattern application
        if "{topic}" in pattern:
            # Extract topic from text
            words = text.split()
            if len(words) > 3:
                topic = random.choice(words[2 : min(len(words), 10)])
                pattern = pattern.replace("{topic}", topic)

        # Add as prefix or suffix
        if random.random() < 0.5:
            return f"{pattern} {text}"
        else:
            return f"{text} {pattern}"
