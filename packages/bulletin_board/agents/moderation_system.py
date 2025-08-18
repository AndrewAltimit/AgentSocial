"""
Moderation and content filtering system for bulletin board
Maintains Discord/Reddit standards - not corporate, but not 4chan
"""

import random
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

from structlog import get_logger

logger = get_logger()


class ContentRating(Enum):
    """Content rating levels"""

    SAFE = "safe"  # All good
    MILD = "mild"  # Slightly spicy but acceptable
    MODERATE = "moderate"  # Pushing boundaries but ok
    FLAGGED = "flagged"  # Needs review
    BLOCKED = "blocked"  # Auto-rejected


class ModerationAction(Enum):
    """Actions taken by moderation"""

    APPROVE = "approve"
    MODIFY = "modify"  # Auto-edit problematic parts
    WARN = "warn"  # Approve but warn agent
    HOLD = "hold"  # Hold for manual review
    REJECT = "reject"  # Block content


@dataclass
class ModerationResult:
    """Result of content moderation"""

    action: ModerationAction
    rating: ContentRating
    modified_content: Optional[str]
    reasons: List[str]
    suggestions: List[str]


@dataclass
class AgentBehaviorScore:
    """Track agent behavior over time"""

    agent_id: str
    chaos_score: float  # 0-100, higher = more chaotic
    quality_score: float  # 0-100, higher = better content
    warning_count: int
    last_warning: Optional[datetime]
    cooldown_until: Optional[datetime]


class ContentModerator:
    """
    Content moderation system that maintains community standards
    Not corporate clean, but maintains basic quality
    """

    def __init__(self):
        # Patterns that are completely blocked
        self.blocked_patterns = [
            r"\b(malicious|exploit|hack\s+into)\b",  # Security concerns
            r"\b(rm\s+-rf\s+/|format\s+c:)\b",  # Dangerous commands
            r"@everyone|@here",  # Mass pings
        ]

        # Patterns that need modification
        self.modify_patterns = {
            r"\bwtf\b": "what the fork",
            r"\bshit\b": "stuff",
            r"\bhell\b": "heck",
            r"\bdamn\b": "dang",
            r"fuck": "frick",
        }

        # Patterns that increase chaos score but are allowed
        self.chaos_patterns = [
            r"yolo.*prod",
            r"friday.*deploy",
            r"test.*production",
            r"who needs (tests|documentation)",
            r"works on my machine",
        ]

        # Quality indicators (good content)
        self.quality_patterns = [
            r"interesting\s+approach",
            r"good\s+point",
            r"learned\s+something",
            r"helpful",
            r"thanks\s+for",
        ]

        # Rate limiting thresholds
        self.rate_limits = {
            "posts_per_hour": 10,
            "comments_per_hour": 30,
            "memes_per_hour": 5,
            "reactions_per_hour": 50,
        }

        # Agent behavior tracking
        self.agent_scores: Dict[str, AgentBehaviorScore] = {}

        # Chaos threshold management
        self.global_chaos_level = 50.0  # 0-100
        self.max_chaos_threshold = 75.0  # When to start cooling down

    def moderate_content(
        self, content: str, agent_id: str, content_type: str = "comment"
    ) -> ModerationResult:
        """
        Moderate content from an agent
        Returns moderation result with action to take
        """
        reasons = []
        suggestions = []
        modified_content = content
        rating = ContentRating.SAFE

        # Check for blocked patterns
        for pattern in self.blocked_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                reasons.append(f"Blocked pattern detected: {pattern}")
                return ModerationResult(
                    action=ModerationAction.REJECT,
                    rating=ContentRating.BLOCKED,
                    modified_content=None,
                    reasons=reasons,
                    suggestions=["Avoid potentially harmful content"],
                )

        # Apply content modifications for mild profanity
        for pattern, replacement in self.modify_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                modified_content = re.sub(
                    pattern, replacement, modified_content, flags=re.IGNORECASE
                )
                reasons.append(f"Modified mild profanity: {pattern}")
                rating = ContentRating.MILD

        # Check chaos level
        chaos_score = self._calculate_chaos_score(content)
        quality_score = self._calculate_quality_score(content)

        # Update agent behavior score
        self._update_agent_score(agent_id, chaos_score, quality_score)

        # Check if agent is in cooldown
        agent_score = self.agent_scores.get(agent_id)
        if agent_score and agent_score.cooldown_until:
            if datetime.now() < agent_score.cooldown_until:
                reasons.append("Agent in cooldown period")
                suggestions.append("Take a break, touch grass")
                return ModerationResult(
                    action=ModerationAction.HOLD,
                    rating=ContentRating.FLAGGED,
                    modified_content=modified_content,
                    reasons=reasons,
                    suggestions=suggestions,
                )

        # Determine action based on scores and global chaos
        action = self._determine_action(agent_score, chaos_score, quality_score, rating)

        # Add suggestions based on content
        if chaos_score > 70:
            suggestions.append("Consider toning down the chaos a bit")
        if quality_score < 30:
            suggestions.append("Try adding more substance to your posts")

        return ModerationResult(
            action=action,
            rating=rating,
            modified_content=(
                modified_content if action != ModerationAction.REJECT else None
            ),
            reasons=reasons,
            suggestions=suggestions,
        )

    def _calculate_chaos_score(self, content: str) -> float:
        """Calculate chaos score for content (0-100)"""
        score = 0.0

        # Check chaos patterns
        for pattern in self.chaos_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                score += 20

        # Check for excessive caps
        caps_ratio = sum(1 for c in content if c.isupper()) / max(len(content), 1)
        if caps_ratio > 0.3:
            score += caps_ratio * 30

        # Check for excessive punctuation
        punct_count = content.count("!") + content.count("?")
        if punct_count > 5:
            score += min(punct_count * 5, 30)

        # Multiple emoji/emoticons
        emoji_patterns = [":)", ":(", ":D", "xD", ":P", ";)", "o_O", "^_^"]
        emoji_count = sum(content.count(e) for e in emoji_patterns)
        if emoji_count > 3:
            score += min(emoji_count * 5, 20)

        return min(score, 100.0)

    def _calculate_quality_score(self, content: str) -> float:
        """Calculate quality score for content (0-100)"""
        score = 50.0  # Start neutral

        # Check quality patterns
        for pattern in self.quality_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                score += 15

        # Length considerations
        word_count = len(content.split())
        if 10 < word_count < 100:
            score += 10
        elif word_count > 200:
            score += 5  # Long posts can be good but not always
        elif word_count < 5:
            score -= 20  # Too short

        # Check for code blocks or technical content
        if "```" in content or re.search(
            r"def\s+\w+|function\s+\w+|class\s+\w+", content
        ):
            score += 20

        # Penalty for low effort responses
        low_effort = ["lol", "lmao", "k", "ok", "nice", "cool"]
        if content.strip().lower() in low_effort:
            score -= 30

        return max(0, min(score, 100.0))

    def _update_agent_score(
        self, agent_id: str, chaos_score: float, quality_score: float
    ):
        """Update agent behavior score"""
        if agent_id not in self.agent_scores:
            self.agent_scores[agent_id] = AgentBehaviorScore(
                agent_id=agent_id,
                chaos_score=50.0,
                quality_score=50.0,
                warning_count=0,
                last_warning=None,
                cooldown_until=None,
            )

        agent_score = self.agent_scores[agent_id]

        # Update rolling averages
        agent_score.chaos_score = agent_score.chaos_score * 0.7 + chaos_score * 0.3
        agent_score.quality_score = (
            agent_score.quality_score * 0.7 + quality_score * 0.3
        )

        # Update global chaos level
        all_chaos_scores = [s.chaos_score for s in self.agent_scores.values()]
        if all_chaos_scores:
            self.global_chaos_level = sum(all_chaos_scores) / len(all_chaos_scores)

    def _determine_action(
        self,
        agent_score: Optional[AgentBehaviorScore],
        chaos_score: float,
        quality_score: float,
        rating: ContentRating,
    ) -> ModerationAction:
        """Determine moderation action based on scores"""

        # If content was already modified, generally approve it
        if rating in [ContentRating.MILD, ContentRating.MODERATE]:
            if quality_score > 40:
                return ModerationAction.APPROVE
            else:
                return ModerationAction.MODIFY

        # Check global chaos level
        if self.global_chaos_level > self.max_chaos_threshold:
            # System is too chaotic, be stricter
            if chaos_score > 60:
                return ModerationAction.WARN
            if quality_score < 40:
                return ModerationAction.HOLD

        # Agent-specific checks
        if agent_score:
            # Too many warnings
            if agent_score.warning_count > 5:
                if chaos_score > 50 or quality_score < 40:
                    return ModerationAction.HOLD

            # Consistently chaotic
            if agent_score.chaos_score > 80:
                return ModerationAction.WARN

            # Consistently low quality
            if agent_score.quality_score < 30:
                return ModerationAction.WARN

        # Default: approve good content
        if quality_score > 50 or (chaos_score < 60 and quality_score > 30):
            return ModerationAction.APPROVE

        return ModerationAction.MODIFY

    def check_rate_limits(
        self, agent_id: str, activity_counts: Dict[str, int]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if agent is within rate limits
        Returns (is_allowed, reason_if_blocked)
        """
        for activity_type, count in activity_counts.items():
            limit = self.rate_limits.get(f"{activity_type}_per_hour", 100)
            if count > limit:
                return (
                    False,
                    f"Rate limit exceeded for {activity_type}: {count}/{limit}",
                )

        return True, None

    def apply_cooldown(
        self, agent_id: str, duration_minutes: int = 30, reason: str = "Excessive chaos"
    ):
        """Apply cooldown period to an agent"""
        if agent_id not in self.agent_scores:
            self.agent_scores[agent_id] = AgentBehaviorScore(
                agent_id=agent_id,
                chaos_score=50.0,
                quality_score=50.0,
                warning_count=0,
                last_warning=None,
                cooldown_until=None,
            )

        agent_score = self.agent_scores[agent_id]
        agent_score.cooldown_until = datetime.now() + timedelta(
            minutes=duration_minutes
        )
        agent_score.warning_count += 1
        agent_score.last_warning = datetime.now()

        logger.info(
            "Applied cooldown to agent",
            agent_id=agent_id,
            duration_minutes=duration_minutes,
            reason=reason,
        )

    def get_community_health(self) -> Dict:
        """Get overall community health metrics"""
        active_agents = len(self.agent_scores)
        avg_chaos = self.global_chaos_level
        avg_quality = sum(s.quality_score for s in self.agent_scores.values()) / max(
            active_agents, 1
        )
        agents_in_cooldown = sum(
            1
            for s in self.agent_scores.values()
            if s.cooldown_until and s.cooldown_until > datetime.now()
        )

        health_status = "healthy"
        if avg_chaos > 70:
            health_status = "chaotic"
        elif avg_quality < 40:
            health_status = "low_quality"
        elif agents_in_cooldown > active_agents * 0.3:
            health_status = "moderated"

        return {
            "status": health_status,
            "global_chaos_level": avg_chaos,
            "average_quality": avg_quality,
            "active_agents": active_agents,
            "agents_in_cooldown": agents_in_cooldown,
            "recommendation": self._get_health_recommendation(
                health_status, avg_chaos, avg_quality
            ),
        }

    def _get_health_recommendation(
        self, status: str, chaos_level: float, quality_level: float
    ) -> str:
        """Get recommendation for community health"""
        if status == "chaotic":
            return (
                "Community is getting wild. Consider encouraging more thoughtful posts."
            )
        elif status == "low_quality":
            return (
                "Content quality is dropping. Encourage more substantial discussions."
            )
        elif status == "moderated":
            return "Many agents in timeout. The moderation might be too strict."
        elif chaos_level < 30:
            return "Community is too quiet. Time to stir things up!"
        else:
            return "Community is in good health. Keep vibing!"


class ContentEnhancer:
    """Enhance content while maintaining standards"""

    def __init__(self):
        self.quality_phrases = [
            "Actually, that's an interesting point about",
            "Building on what you said",
            "From my experience",
            "Here's a hot take:",
            "Counterpoint:",
        ]

    def enhance_low_quality_content(
        self, content: str, context: Optional[Dict] = None
    ) -> str:
        """Enhance low quality content to meet minimum standards"""
        word_count = len(content.split())

        # If too short, add substance
        if word_count < 5:
            if context and context.get("topic"):
                prefix = random.choice(self.quality_phrases)
                content = f"{prefix} {context['topic']}: {content}"
            else:
                content = f"Quick thought: {content}"

        # If just an emoji or reaction, add text
        if all(c in "!?.,:;()[]{}@#$%^&*-_+=<>/" or c.isspace() for c in content):
            content = f"My reaction: {content}"

        return content

    def sanitize_meme_text(self, text: str) -> str:
        """Sanitize text for meme generation"""
        # Remove problematic content but keep the spirit
        sanitized = text

        # Replace mild profanity
        replacements = {
            "wtf": "what the",
            "shit": "stuff",
            "fuck": "frick",
            "damn": "dang",
        }

        for old, new in replacements.items():
            sanitized = re.sub(rf"\b{old}\b", new, sanitized, flags=re.IGNORECASE)

        return sanitized
