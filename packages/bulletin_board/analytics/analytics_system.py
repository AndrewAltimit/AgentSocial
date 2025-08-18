"""
Analytics system for bulletin board community insights
Uses file-based storage with efficient grep/glob operations
"""

import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from structlog import get_logger  # noqa: E402

logger = get_logger()


@dataclass
class CommunityMetrics:
    """Overall community health metrics"""

    total_posts: int
    total_comments: int
    active_agents: int
    average_sentiment: float
    chaos_level: float
    engagement_rate: float
    peak_hours: List[int]
    trending_topics: List[Tuple[str, int]]


@dataclass
class AgentMetrics:
    """Individual agent performance metrics"""

    agent_id: str
    posts_created: int
    comments_made: int
    reactions_given: int
    memes_generated: int
    average_sentiment: float
    response_time_avg: float  # seconds
    engagement_score: float
    chaos_contribution: float
    favorite_topics: List[str]
    interaction_partners: List[Tuple[str, int]]


@dataclass
class InteractionHeatmap:
    """Agent interaction patterns"""

    timestamp: str
    interactions: Dict[str, Dict[str, float]]  # agent -> agent -> strength
    clusters: List[List[str]]  # detected agent clusters


@dataclass
class SentimentTrend:
    """Community sentiment over time"""

    timestamps: List[str]
    sentiment_values: List[float]
    moving_average: List[float]
    volatility: float
    trend_direction: str  # rising, falling, stable


class AnalyticsCollector:
    """
    Collects and analyzes bulletin board data
    Stores results as markdown and JSON files
    """

    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = os.environ.get(
                "BULLETIN_BOARD_ANALYTICS_PATH", "/var/lib/bulletin_board/analytics"
            )
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        self.metrics_dir = self.base_path / "metrics"
        self.heatmaps_dir = self.base_path / "heatmaps"
        self.trends_dir = self.base_path / "trends"
        self.reports_dir = self.base_path / "reports"
        self.visualizations_dir = self.base_path / "visualizations"

        for dir_path in [
            self.metrics_dir,
            self.heatmaps_dir,
            self.trends_dir,
            self.reports_dir,
            self.visualizations_dir,
        ]:
            dir_path.mkdir(exist_ok=True)

    def collect_community_metrics(self, data_path: str) -> CommunityMetrics:
        """Collect overall community metrics using grep"""
        try:
            # Count posts
            post_count = self._count_entries(data_path, "post_id")

            # Count comments
            comment_count = self._count_entries(data_path, "comment_id")

            # Count active agents
            active_agents = self._count_unique_agents(data_path)

            # Calculate average sentiment
            avg_sentiment = self._calculate_average_sentiment(data_path)

            # Calculate chaos level
            chaos_level = self._calculate_chaos_level(data_path)

            # Calculate engagement rate
            engagement_rate = comment_count / max(post_count, 1)

            # Find peak hours
            peak_hours = self._find_peak_hours(data_path)

            # Get trending topics
            trending = self._get_trending_topics(data_path)

            metrics = CommunityMetrics(
                total_posts=post_count,
                total_comments=comment_count,
                active_agents=active_agents,
                average_sentiment=avg_sentiment,
                chaos_level=chaos_level,
                engagement_rate=engagement_rate,
                peak_hours=peak_hours,
                trending_topics=trending,
            )

            # Store metrics
            self._store_metrics(metrics, "community")

            return metrics

        except Exception as e:
            logger.error("Failed to collect community metrics", error=str(e))
            return self._empty_community_metrics()

    def collect_agent_metrics(self, agent_id: str, data_path: str) -> AgentMetrics:
        """Collect metrics for individual agent"""
        try:
            # Use grep to find agent activity
            cmd = ["grep", "-r", agent_id, data_path]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                return self._empty_agent_metrics(agent_id)

            lines = result.stdout.split("\n")

            # Count different activities
            posts = len([line for line in lines if "post_created" in line])
            comments = len([line for line in lines if "comment_made" in line])
            reactions = len([line for line in lines if "reaction_given" in line])
            memes = len([line for line in lines if "meme_generated" in line])

            # Calculate sentiment
            sentiments = self._extract_sentiments(lines)
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0

            # Calculate response time
            response_times = self._extract_response_times(lines)
            avg_response = (
                sum(response_times) / len(response_times) if response_times else 0
            )

            # Calculate engagement score
            engagement = (comments + reactions * 0.5 + memes * 2) / max(posts, 1)

            # Calculate chaos contribution
            chaos = self._calculate_agent_chaos(lines)

            # Extract favorite topics
            topics = self._extract_topics(lines)

            # Find interaction partners
            partners = self._find_interaction_partners(lines, agent_id)

            metrics = AgentMetrics(
                agent_id=agent_id,
                posts_created=posts,
                comments_made=comments,
                reactions_given=reactions,
                memes_generated=memes,
                average_sentiment=avg_sentiment,
                response_time_avg=avg_response,
                engagement_score=engagement,
                chaos_contribution=chaos,
                favorite_topics=topics[:5],
                interaction_partners=partners[:10],
            )

            # Store metrics
            self._store_metrics(metrics, f"agent_{agent_id}")

            return metrics

        except Exception as e:
            logger.error(
                "Failed to collect agent metrics", agent_id=agent_id, error=str(e)
            )
            return self._empty_agent_metrics(agent_id)

    def generate_interaction_heatmap(
        self, data_path: str, days_back: int = 7
    ) -> InteractionHeatmap:
        """Generate interaction heatmap between agents"""
        try:
            # Find recent interaction files
            # cutoff = datetime.now() - timedelta(days=days_back)

            # Use find to get recent files
            cmd = [
                "find",
                data_path,
                "-name",
                "*.json",
                "-mtime",
                f"-{days_back}",
                "-exec",
                "grep",
                "-l",
                "interaction",
                "{}",
                ";",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                return self._empty_heatmap()

            files = result.stdout.strip().split("\n")

            # Build interaction matrix
            interactions = defaultdict(lambda: defaultdict(float))

            for file_path in files:
                if not file_path:
                    continue

                with open(file_path, "r") as f:
                    try:
                        data = json.load(f)
                        if "from_agent" in data and "to_agent" in data:
                            weight = data.get("sentiment", 0.5) + 0.5
                            interactions[data["from_agent"]][data["to_agent"]] += weight
                    except json.JSONDecodeError:
                        continue

            # Detect clusters (simple community detection)
            clusters = self._detect_clusters(dict(interactions))

            heatmap = InteractionHeatmap(
                timestamp=datetime.now().isoformat(),
                interactions=dict(interactions),
                clusters=clusters,
            )

            # Store and visualize
            self._store_heatmap(heatmap)
            self._visualize_heatmap(heatmap)

            return heatmap

        except Exception as e:
            logger.error("Failed to generate interaction heatmap", error=str(e))
            return self._empty_heatmap()

    def analyze_sentiment_trends(
        self, data_path: str, days_back: int = 30
    ) -> SentimentTrend:
        """Analyze sentiment trends over time"""
        try:
            # Collect sentiment data points
            cmd = [
                "find",
                data_path,
                "-name",
                "*.json",
                "-mtime",
                f"-{days_back}",
                "-exec",
                "grep",
                "-h",
                "sentiment",
                "{}",
                ";",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                return self._empty_sentiment_trend()

            # Parse sentiment values with timestamps
            sentiment_data = []
            for line in result.stdout.split("\n"):
                if '"sentiment"' in line:
                    try:
                        # Extract sentiment value
                        match = re.search(r'"sentiment":\s*([-\d.]+)', line)
                        if match:
                            sentiment_data.append(float(match.group(1)))
                    except Exception:
                        continue

            if not sentiment_data:
                return self._empty_sentiment_trend()

            # Create time series
            timestamps = [
                (datetime.now() - timedelta(hours=i)).isoformat()
                for i in range(len(sentiment_data))
            ]

            # Calculate moving average
            window = min(24, len(sentiment_data) // 4)
            moving_avg = self._moving_average(sentiment_data, window)

            # Calculate volatility
            volatility = np.std(sentiment_data) if len(sentiment_data) > 1 else 0

            # Determine trend
            if len(moving_avg) > 1:
                recent = sum(moving_avg[-10:]) / min(10, len(moving_avg))
                older = sum(moving_avg[:10]) / min(10, len(moving_avg))
                if recent > older + 0.1:
                    trend = "rising"
                elif recent < older - 0.1:
                    trend = "falling"
                else:
                    trend = "stable"
            else:
                trend = "stable"

            sentiment_trend = SentimentTrend(
                timestamps=timestamps,
                sentiment_values=sentiment_data,
                moving_average=moving_avg,
                volatility=volatility,
                trend_direction=trend,
            )

            # Store and visualize
            self._store_sentiment_trend(sentiment_trend)
            self._visualize_sentiment_trend(sentiment_trend)

            return sentiment_trend

        except Exception as e:
            logger.error("Failed to analyze sentiment trends", error=str(e))
            return self._empty_sentiment_trend()

    def generate_chaos_metrics(self, data_path: str) -> Dict[str, Any]:
        """Generate chaos metrics for the community"""
        try:
            # Find chaos indicators
            chaos_indicators = {
                "rapid_responses": self._count_rapid_responses(data_path),
                "meme_density": self._calculate_meme_density(data_path),
                "reaction_velocity": self._calculate_reaction_velocity(data_path),
                "thread_derailment": self._detect_thread_derailment(data_path),
                "chaos_agents": self._identify_chaos_agents(data_path),
            }

            # Calculate overall chaos score
            chaos_score = sum(
                [
                    chaos_indicators["rapid_responses"] * 0.2,
                    chaos_indicators["meme_density"] * 0.3,
                    chaos_indicators["reaction_velocity"] * 0.2,
                    chaos_indicators["thread_derailment"] * 0.3,
                ]
            )

            chaos_metrics = {
                "timestamp": datetime.now().isoformat(),
                "overall_chaos": chaos_score,
                "indicators": chaos_indicators,
                "status": self._get_chaos_status(chaos_score),
            }

            # Store metrics
            self._store_chaos_metrics(chaos_metrics)

            return chaos_metrics

        except Exception as e:
            logger.error("Failed to generate chaos metrics", error=str(e))
            return {"overall_chaos": 0, "indicators": {}, "status": "calm"}

    def _count_entries(self, path: str, pattern: str) -> int:
        """Count occurrences of pattern using grep"""
        cmd = ["grep", "-r", "-c", pattern, path]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return 0

        # Sum all counts
        total = 0
        for line in result.stdout.split("\n"):
            if ":" in line:
                try:
                    count = int(line.split(":")[-1])
                    total += count
                except (ValueError, AttributeError, KeyError):
                    continue

        return total

    def _count_unique_agents(self, path: str) -> int:
        """Count unique agent IDs"""
        cmd = ["grep", "-r", "-h", "agent_id", path]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return 0

        agents = set()
        for line in result.stdout.split("\n"):
            match = re.search(r'"agent_id":\s*"([^"]+)"', line)
            if match:
                agents.add(match.group(1))

        return len(agents)

    def _calculate_average_sentiment(self, path: str) -> float:
        """Calculate average sentiment from all entries"""
        cmd = ["grep", "-r", "-h", "sentiment", path]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return 0.0

        sentiments = []
        for line in result.stdout.split("\n"):
            match = re.search(r'"sentiment":\s*([-\d.]+)', line)
            if match:
                try:
                    sentiments.append(float(match.group(1)))
                except (ValueError, AttributeError, KeyError):
                    continue

        return sum(sentiments) / len(sentiments) if sentiments else 0.0

    def _calculate_chaos_level(self, path: str) -> float:
        """Calculate overall chaos level"""
        # Count chaos indicators
        memes = self._count_entries(path, "meme_generated")
        rapid = self._count_entries(path, "rapid_response")
        reactions = self._count_entries(path, "reaction")

        total_activity = self._count_entries(path, "agent_id")

        if total_activity == 0:
            return 0.0

        # Calculate chaos as ratio of chaotic activity
        chaos_ratio = (memes * 2 + rapid * 1.5 + reactions) / total_activity

        # Normalize to 0-100 scale
        return min(100, chaos_ratio * 100)

    def _find_peak_hours(self, path: str) -> List[int]:
        """Find peak activity hours"""
        cmd = ["grep", "-r", "-h", "timestamp", path]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return []

        hours = Counter()
        for line in result.stdout.split("\n"):
            match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2})", line)
            if match:
                try:
                    dt = datetime.fromisoformat(match.group(1) + ":00:00")
                    hours[dt.hour] += 1
                except (ValueError, AttributeError, KeyError):
                    continue

        # Return top 3 peak hours
        return [hour for hour, _ in hours.most_common(3)]

    def _get_trending_topics(self, path: str, limit: int = 10) -> List[Tuple[str, int]]:
        """Extract trending topics using keyword frequency"""
        cmd = ["grep", "-r", "-h", "-E", "(topic|keyword|tag)", path]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return []

        topics = Counter()
        for line in result.stdout.split("\n"):
            # Extract words that look like topics
            words = re.findall(r"\b[a-zA-Z]{4,}\b", line.lower())
            for word in words:
                if word not in ["topic", "keyword", "tag", "the", "and", "for"]:
                    topics[word] += 1

        return topics.most_common(limit)

    def _extract_sentiments(self, lines: List[str]) -> List[float]:
        """Extract sentiment values from grep output"""
        sentiments = []
        for line in lines:
            match = re.search(r'"sentiment":\s*([-\d.]+)', line)
            if match:
                try:
                    sentiments.append(float(match.group(1)))
                except (ValueError, AttributeError, KeyError):
                    continue
        return sentiments

    def _extract_response_times(self, lines: List[str]) -> List[float]:
        """Extract response times from activity logs"""
        times = []
        for line in lines:
            match = re.search(r'"response_time":\s*([\d.]+)', line)
            if match:
                try:
                    times.append(float(match.group(1)))
                except (ValueError, AttributeError, KeyError):
                    continue
        return times

    def _calculate_agent_chaos(self, lines: List[str]) -> float:
        """Calculate chaos contribution for an agent"""
        chaos_count = 0
        total_count = len(lines)

        for line in lines:
            if any(
                indicator in line.lower()
                for indicator in ["meme", "rapid", "chaos", "reaction"]
            ):
                chaos_count += 1

        return (chaos_count / max(total_count, 1)) * 100

    def _extract_topics(self, lines: List[str]) -> List[str]:
        """Extract topics from agent activity"""
        topics = Counter()
        for line in lines:
            words = re.findall(r"\b[a-zA-Z]{4,}\b", line.lower())
            for word in words:
                if len(word) > 4 and word not in ["agent", "comment", "post"]:
                    topics[word] += 1

        return [topic for topic, _ in topics.most_common(10)]

    def _find_interaction_partners(
        self, lines: List[str], agent_id: str
    ) -> List[Tuple[str, int]]:
        """Find agents this agent interacts with most"""
        partners = Counter()
        for line in lines:
            # Look for other agent IDs
            agents = re.findall(r'"agent_id":\s*"([^"]+)"', line)
            for other_agent in agents:
                if other_agent != agent_id:
                    partners[other_agent] += 1

        return partners.most_common()

    def _detect_clusters(
        self, interactions: Dict[str, Dict[str, float]]
    ) -> List[List[str]]:
        """Simple community detection for agent clusters"""
        clusters = []
        processed = set()

        for agent in interactions:
            if agent in processed:
                continue

            # Find strongly connected agents
            cluster = [agent]
            processed.add(agent)

            for other in interactions.get(agent, {}):
                if other not in processed:
                    # Check bidirectional strength
                    if interactions.get(other, {}).get(agent, 0) > 0.5:
                        cluster.append(other)
                        processed.add(other)

            if len(cluster) > 1:
                clusters.append(cluster)

        return clusters

    def _moving_average(self, data: List[float], window: int) -> List[float]:
        """Calculate moving average"""
        if len(data) < window:
            return data

        moving_avg = []
        for i in range(len(data) - window + 1):
            avg = sum(data[i : i + window]) / window
            moving_avg.append(avg)

        return moving_avg

    def _count_rapid_responses(self, path: str) -> float:
        """Count rapid response patterns"""
        # Implementation would analyze timestamps
        return self._count_entries(path, "rapid_response") / 100

    def _calculate_meme_density(self, path: str) -> float:
        """Calculate meme density in content"""
        memes = self._count_entries(path, "meme")
        total = self._count_entries(path, "content")
        return (memes / max(total, 1)) * 100

    def _calculate_reaction_velocity(self, path: str) -> float:
        """Calculate reaction velocity"""
        reactions = self._count_entries(path, "reaction")
        # Would need time analysis for true velocity
        return min(100, reactions / 10)

    def _detect_thread_derailment(self, path: str) -> float:
        """Detect thread derailment patterns"""
        # Simplified implementation
        offtopic = self._count_entries(path, "offtopic")
        total = self._count_entries(path, "thread")
        return (offtopic / max(total, 1)) * 100

    def _identify_chaos_agents(self, path: str) -> List[str]:
        """Identify agents contributing most to chaos"""
        cmd = ["grep", "-r", "-h", "chaos_contribution", path]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return []

        chaos_agents = {}
        for line in result.stdout.split("\n"):
            agent_match = re.search(r'"agent_id":\s*"([^"]+)"', line)
            chaos_match = re.search(r'"chaos_contribution":\s*([\d.]+)', line)

            if agent_match and chaos_match:
                agent = agent_match.group(1)
                chaos = float(chaos_match.group(1))
                chaos_agents[agent] = max(chaos_agents.get(agent, 0), chaos)

        # Return top chaos agents
        sorted_agents = sorted(chaos_agents.items(), key=lambda x: x[1], reverse=True)
        return [agent for agent, _ in sorted_agents[:5]]

    def _get_chaos_status(self, score: float) -> str:
        """Get chaos status description"""
        if score < 20:
            return "calm"
        elif score < 40:
            return "active"
        elif score < 60:
            return "chaotic"
        elif score < 80:
            return "very_chaotic"
        else:
            return "absolute_pandemonium"

    def _store_metrics(self, metrics: Any, name: str):
        """Store metrics as JSON and markdown"""
        timestamp = datetime.now().strftime("%Y-%m-%d")

        # Store as JSON
        json_file = self.metrics_dir / f"{name}_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump(
                (
                    asdict(metrics)
                    if hasattr(metrics, "__dataclass_fields__")
                    else metrics
                ),
                f,
                indent=2,
            )

        # Store as markdown for human reading
        md_file = self.metrics_dir / f"{name}_{timestamp}.md"
        with open(md_file, "w") as f:
            f.write(f"# {name.replace('_', ' ').title()} Metrics\n\n")
            f.write(f"**Generated**: {datetime.now().isoformat()}\n\n")

            if hasattr(metrics, "__dataclass_fields__"):
                for field, value in asdict(metrics).items():
                    f.write(f"- **{field}**: {value}\n")
            else:
                for key, value in metrics.items():
                    f.write(f"- **{key}**: {value}\n")

    def _store_heatmap(self, heatmap: InteractionHeatmap):
        """Store interaction heatmap data"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")

        json_file = self.heatmaps_dir / f"heatmap_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump(asdict(heatmap), f, indent=2)

    def _store_sentiment_trend(self, trend: SentimentTrend):
        """Store sentiment trend data"""
        timestamp = datetime.now().strftime("%Y-%m-%d")

        json_file = self.trends_dir / f"sentiment_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump(asdict(trend), f, indent=2)

    def _store_chaos_metrics(self, metrics: Dict[str, Any]):
        """Store chaos metrics"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")

        json_file = self.metrics_dir / f"chaos_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump(metrics, f, indent=2)

    def _visualize_heatmap(self, heatmap: InteractionHeatmap):
        """Create visual representation of interaction heatmap"""
        try:
            agents = list(
                set(
                    list(heatmap.interactions.keys())
                    + [a for d in heatmap.interactions.values() for a in d.keys()]
                )
            )

            if not agents:
                return

            # Create matrix
            n = len(agents)
            matrix = np.zeros((n, n))

            for i, agent1 in enumerate(agents):
                for j, agent2 in enumerate(agents):
                    if (
                        agent1 in heatmap.interactions
                        and agent2 in heatmap.interactions[agent1]
                    ):
                        matrix[i][j] = heatmap.interactions[agent1][agent2]

            # Create plot
            fig, ax = plt.subplots(figsize=(10, 8))
            im = ax.imshow(matrix, cmap="YlOrRd")

            ax.set_xticks(np.arange(n))
            ax.set_yticks(np.arange(n))
            ax.set_xticklabels(agents, rotation=45, ha="right")
            ax.set_yticklabels(agents)

            plt.colorbar(im)
            plt.title("Agent Interaction Heatmap")
            plt.tight_layout()

            # Save
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            plt.savefig(self.visualizations_dir / f"heatmap_{timestamp}.png")
            plt.close()

        except Exception as e:
            logger.error("Failed to visualize heatmap", error=str(e))

    def _visualize_sentiment_trend(self, trend: SentimentTrend):
        """Create sentiment trend visualization"""
        try:
            if not trend.sentiment_values:
                return

            fig, ax = plt.subplots(figsize=(12, 6))

            x = range(len(trend.sentiment_values))

            # Plot raw sentiment
            ax.plot(x, trend.sentiment_values, "b-", alpha=0.3, label="Raw Sentiment")

            # Plot moving average
            if trend.moving_average:
                x_avg = range(len(trend.moving_average))
                ax.plot(
                    x_avg,
                    trend.moving_average,
                    "r-",
                    linewidth=2,
                    label="Moving Average",
                )

            # Add trend indicator
            ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5)

            ax.set_xlabel("Time")
            ax.set_ylabel("Sentiment")
            ax.set_title(f"Community Sentiment Trend ({trend.trend_direction})")
            ax.legend()
            ax.grid(True, alpha=0.3)

            plt.tight_layout()

            # Save
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            plt.savefig(self.visualizations_dir / f"sentiment_{timestamp}.png")
            plt.close()

        except Exception as e:
            logger.error("Failed to visualize sentiment trend", error=str(e))

    def _empty_community_metrics(self) -> CommunityMetrics:
        """Return empty community metrics"""
        return CommunityMetrics(
            total_posts=0,
            total_comments=0,
            active_agents=0,
            average_sentiment=0.0,
            chaos_level=0.0,
            engagement_rate=0.0,
            peak_hours=[],
            trending_topics=[],
        )

    def _empty_agent_metrics(self, agent_id: str) -> AgentMetrics:
        """Return empty agent metrics"""
        return AgentMetrics(
            agent_id=agent_id,
            posts_created=0,
            comments_made=0,
            reactions_given=0,
            memes_generated=0,
            average_sentiment=0.0,
            response_time_avg=0.0,
            engagement_score=0.0,
            chaos_contribution=0.0,
            favorite_topics=[],
            interaction_partners=[],
        )

    def _empty_heatmap(self) -> InteractionHeatmap:
        """Return empty heatmap"""
        return InteractionHeatmap(
            timestamp=datetime.now().isoformat(), interactions={}, clusters=[]
        )

    def _empty_sentiment_trend(self) -> SentimentTrend:
        """Return empty sentiment trend"""
        return SentimentTrend(
            timestamps=[],
            sentiment_values=[],
            moving_average=[],
            volatility=0.0,
            trend_direction="stable",
        )
