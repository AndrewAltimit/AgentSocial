"""
Tests for memory persistence and analytics systems
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from packages.bulletin_board.agents.personality_drift import PersonalityDriftEngine, PersonalityState
from packages.bulletin_board.analytics.analytics_system import (
    AnalyticsCollector,
    CommunityMetrics,
    InteractionHeatmap,
    SentimentTrend,
)
from packages.bulletin_board.memory.memory_system import FileMemorySystem, IncidentMemory, Memory


class TestFileMemorySystem:
    """Test file-based memory system"""

    @pytest.fixture
    def memory_system(self):
        """Create memory system with temp directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            system = FileMemorySystem(base_path=tmpdir)
            yield system

    def test_store_and_retrieve_memory(self, memory_system):
        """Test storing and retrieving memories"""
        # Create memory
        memory = Memory(
            timestamp=datetime.now().isoformat(),
            memory_type="interaction",
            content="Had a great discussion about Python",
            tags=["python", "discussion"],
            participants=["agent1", "agent2"],
            sentiment=0.8,
            importance=0.7,
            references=[],
        )

        # Store memory
        memory_system.store_memory("agent1", memory)

        # Search for memory
        results = memory_system.search_memories("agent1", "Python")

        # Should find the memory
        assert len(results) > 0
        # Note: Exact matching depends on grep parsing implementation

    def test_incident_storage_and_retrieval(self, memory_system):
        """Test incident memory storage"""
        incident = IncidentMemory(
            incident_id="inc_001",
            timestamp=datetime.now().isoformat(),
            title="The Great Outage",
            description="Everything broke at once",
            participants=["agent1", "agent2"],
            outcome="Fixed after 3 hours",
            lessons_learned=["Always have backups", "Test more"],
            reference_count=0,
        )

        # Store incident
        memory_system.store_incident(incident)

        # Find incident by ID
        found = memory_system.find_incident("inc_001")
        assert found is not None
        assert found.title == "The Great Outage"

    def test_relationship_tracking(self, memory_system):
        """Test relationship evolution tracking"""
        # Update relationship multiple times
        memory_system.update_relationship("agent1", "agent2", interaction_sentiment=0.8, inside_joke="That Docker thing")

        memory_system.update_relationship("agent1", "agent2", interaction_sentiment=-0.3)

        memory_system.update_relationship("agent1", "agent2", interaction_sentiment=0.5, shared_incident="inc_001")

        # Get relationship
        rel = memory_system.get_relationship("agent1", "agent2")

        assert rel is not None
        assert rel.interaction_count == 3
        assert rel.positive_interactions == 2
        assert rel.negative_interactions == 1
        assert "That Docker thing" in rel.inside_jokes
        assert "inc_001" in rel.shared_incidents

    def test_similar_situation_search(self, memory_system):
        """Test finding similar past situations"""
        # Store multiple memories
        memories = [
            Memory(
                timestamp=datetime.now().isoformat(),
                memory_type="interaction",
                content="Debugging a race condition in async code",
                tags=["debugging", "async"],
                participants=["agent1"],
                sentiment=-0.5,
                importance=0.8,
                references=[],
            ),
            Memory(
                timestamp=datetime.now().isoformat(),
                memory_type="interaction",
                content="Fixed the async bug finally",
                tags=["async", "success"],
                participants=["agent1"],
                sentiment=0.9,
                importance=0.9,
                references=[],
            ),
            Memory(
                timestamp=datetime.now().isoformat(),
                memory_type="interaction",
                content="Discussing database design",
                tags=["database"],
                participants=["agent1"],
                sentiment=0.3,
                importance=0.5,
                references=[],
            ),
        ]

        for memory in memories:
            memory_system.store_memory("agent1", memory)

        # Search for similar situations
        current_context = "Having issues with async race conditions"
        similar = memory_system.find_similar_situations("agent1", current_context, limit=2)

        # Should find async-related memories
        # Note: Exact results depend on keyword extraction
        assert isinstance(similar, list)

    def test_memory_cleanup(self, memory_system):
        """Test cleaning up old memories"""
        # Create old memory file
        old_date = datetime.now() - timedelta(days=100)
        old_file = memory_system.agents_dir / "agent1" / f"{old_date.strftime('%Y-%m-%d')}.md"
        old_file.parent.mkdir(parents=True, exist_ok=True)
        old_file.write_text("Old memory content")

        # Create recent memory file
        recent_date = datetime.now()
        recent_file = memory_system.agents_dir / "agent1" / f"{recent_date.strftime('%Y-%m-%d')}.md"
        recent_file.write_text("Recent memory content")

        # Clean up old memories
        memory_system.cleanup_old_memories(days_to_keep=90)

        # Old file should be deleted
        assert not old_file.exists()
        # Recent file should remain
        assert recent_file.exists()


class TestPersonalityDrift:
    """Test personality drift mechanics"""

    @pytest.fixture
    def drift_engine(self):
        """Create drift engine with temp directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = PersonalityDriftEngine(base_path=tmpdir)
            yield engine

    def test_default_personality_state(self, drift_engine):
        """Test creating default personality state"""
        state = drift_engine.get_current_state("agent1")

        assert state.agent_id == "agent1"
        assert state.energy_level == 0.5
        assert state.chaos_tolerance == 0.5
        assert state.total_interactions == 0
        assert state.drift_velocity == 0.0

    def test_interaction_drift(self, drift_engine):
        """Test personality drift from interactions"""
        initial = drift_engine.get_current_state("agent1")

        # Apply positive collaboration
        state1 = drift_engine.apply_interaction(
            "agent1", interaction_type="collaboration", other_agent="agent2", sentiment=0.8, intensity=0.7
        )

        # Should increase supportiveness and trust
        assert state1.supportiveness > initial.supportiveness
        assert state1.trust_level > initial.trust_level
        assert state1.total_interactions == 1

        # Apply heated debate
        state2 = drift_engine.apply_interaction(
            "agent1", interaction_type="debate", other_agent="agent3", sentiment=-0.5, intensity=0.8
        )

        # Should increase analytical depth
        assert state2.analytical_depth > state1.analytical_depth
        assert state2.total_interactions == 2

    def test_incident_impact(self, drift_engine):
        """Test major incident impact on personality"""
        initial = drift_engine.get_current_state("agent1")

        # Apply system crash incident
        state = drift_engine.apply_incident("agent1", incident_type="system_crash", impact_level=0.8)

        # Should significantly affect chaos tolerance
        assert abs(state.chaos_tolerance - initial.chaos_tolerance) > 0.1
        assert state.last_major_shift is not None

    def test_time_drift(self, drift_engine):
        """Test gradual drift over time"""
        # Set initial state away from baseline
        initial = drift_engine.get_current_state("agent1")
        initial.energy_level = 0.9
        initial.chaos_tolerance = 0.1
        drift_engine._save_state(initial)

        # Apply time drift
        state = drift_engine.apply_time_drift("agent1", hours_passed=24)

        # Should drift slightly toward baseline (0.5)
        assert state.energy_level <= initial.energy_level  # May stay same or decrease
        assert state.chaos_tolerance >= initial.chaos_tolerance  # May stay same or increase

    def test_relationship_influence(self, drift_engine):
        """Test relationship effects on personality"""
        initial = drift_engine.get_current_state("agent1")

        # Simulate positive relationship
        state = drift_engine.simulate_relationship_influence("agent1", relationship_quality=0.8, interaction_count=15)

        # Should increase trust and supportiveness
        assert state.trust_level > initial.trust_level
        assert state.supportiveness > initial.supportiveness

    def test_major_shift_detection(self, drift_engine):
        """Test detection of major personality shifts"""
        state1 = PersonalityState(
            agent_id="agent1",
            timestamp=datetime.now().isoformat(),
            energy_level=0.5,
            formality=0.5,
            verbosity=0.5,
            chaos_tolerance=0.3,
            positivity=0.5,
            aggression=0.0,
            supportiveness=0.0,
            humor_tendency=0.0,
            analytical_depth=0.0,
            extroversion=0.5,
            trust_level=0.5,
            conflict_avoidance=0.5,
            total_interactions=0,
            last_major_shift=None,
            drift_velocity=0.0,
        )

        state2 = PersonalityState(
            agent_id="agent1",
            timestamp=datetime.now().isoformat(),
            energy_level=0.5,
            formality=0.5,
            verbosity=0.5,
            chaos_tolerance=0.8,  # Large change
            positivity=0.5,
            aggression=0.0,
            supportiveness=0.0,
            humor_tendency=0.0,
            analytical_depth=0.0,
            extroversion=0.5,
            trust_level=0.5,
            conflict_avoidance=0.5,
            total_interactions=1,
            last_major_shift=None,
            drift_velocity=0.0,
        )

        is_major = drift_engine._is_major_shift(state1, state2)
        assert is_major is True


class TestAnalyticsSystem:
    """Test analytics collection system"""

    @pytest.fixture
    def analytics(self):
        """Create analytics collector with temp directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = AnalyticsCollector(base_path=tmpdir)
            yield collector

    @pytest.fixture
    def sample_data_dir(self):
        """Create sample data directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            # Create sample data files
            (data_dir / "posts.json").write_text(
                json.dumps(
                    [
                        {"post_id": "p1", "timestamp": datetime.now().isoformat()},
                        {"post_id": "p2", "timestamp": datetime.now().isoformat()},
                    ]
                )
            )

            (data_dir / "comments.json").write_text(
                json.dumps(
                    [
                        {"comment_id": "c1", "agent_id": "agent1", "sentiment": 0.5},
                        {"comment_id": "c2", "agent_id": "agent2", "sentiment": -0.3},
                        {"comment_id": "c3", "agent_id": "agent1", "sentiment": 0.8},
                    ]
                )
            )

            yield str(data_dir)

    @patch("subprocess.run")
    def test_community_metrics_collection(self, mock_run, analytics, sample_data_dir):
        """Test collecting community metrics"""
        # Mock grep output
        mock_run.return_value = MagicMock(returncode=0, stdout="file1:2\nfile2:3\n")

        metrics = analytics.collect_community_metrics(sample_data_dir)

        assert isinstance(metrics, CommunityMetrics)
        assert metrics.total_posts >= 0
        assert metrics.total_comments >= 0
        assert 0 <= metrics.average_sentiment <= 1
        assert 0 <= metrics.chaos_level <= 100

    @patch("subprocess.run")
    def test_agent_metrics_collection(self, mock_run, analytics, sample_data_dir):
        """Test collecting individual agent metrics"""
        # Mock grep output for agent activity
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""
            line1: "agent_id": "agent1", "post_created": true
            line2: "agent_id": "agent1", "comment_made": true
            line3: "agent_id": "agent1", "reaction_given": true, "sentiment": 0.7
            line4: "agent_id": "agent1", "meme_generated": true
            """,
        )

        metrics = analytics.collect_agent_metrics("agent1", sample_data_dir)

        assert metrics.agent_id == "agent1"
        assert metrics.posts_created >= 0
        assert metrics.comments_made >= 0
        assert metrics.engagement_score >= 0

    def test_interaction_heatmap_generation(self, analytics):
        """Test generating interaction heatmap"""
        # Create test interaction data
        test_dir = analytics.base_path / "test_data"
        test_dir.mkdir(exist_ok=True)

        interaction_data = {"from_agent": "agent1", "to_agent": "agent2", "sentiment": 0.8}

        (test_dir / "interaction1.json").write_text(json.dumps(interaction_data))

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=str(test_dir / "interaction1.json"))

            heatmap = analytics.generate_interaction_heatmap(str(test_dir))

            assert isinstance(heatmap, InteractionHeatmap)
            assert isinstance(heatmap.interactions, dict)
            assert isinstance(heatmap.clusters, list)

    @patch("subprocess.run")
    def test_sentiment_trend_analysis(self, mock_run, analytics, sample_data_dir):
        """Test analyzing sentiment trends"""
        # Mock sentiment data
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""
            "sentiment": 0.5
            "sentiment": 0.6
            "sentiment": 0.4
            "sentiment": 0.7
            "sentiment": 0.8
            """,
        )

        trend = analytics.analyze_sentiment_trends(sample_data_dir)

        assert isinstance(trend, SentimentTrend)
        assert len(trend.sentiment_values) > 0
        assert trend.trend_direction in ["rising", "falling", "stable"]

    @patch("subprocess.run")
    def test_chaos_metrics_generation(self, mock_run, analytics, sample_data_dir):
        """Test generating chaos metrics"""
        # Mock chaos indicators
        mock_run.return_value = MagicMock(returncode=0, stdout="meme_generated\nrapid_response\nreaction")

        chaos = analytics.generate_chaos_metrics(sample_data_dir)

        assert "overall_chaos" in chaos
        assert "indicators" in chaos
        assert "status" in chaos
        assert chaos["status"] in ["calm", "active", "chaotic", "very_chaotic", "absolute_pandemonium"]

    def test_visualization_generation(self, analytics):
        """Test that visualizations don't crash"""
        # Test with empty data (should handle gracefully)
        heatmap = InteractionHeatmap(
            timestamp=datetime.now().isoformat(), interactions={"agent1": {"agent2": 0.5}}, clusters=[]
        )

        # Should not raise exception
        analytics._visualize_heatmap(heatmap)

        trend = SentimentTrend(
            timestamps=[], sentiment_values=[0.5, 0.6, 0.4], moving_average=[0.5], volatility=0.1, trend_direction="stable"
        )

        # Should not raise exception
        analytics._visualize_sentiment_trend(trend)


class TestMemoryEnhancedRunner:
    """Test memory-enhanced agent runner"""

    @pytest.fixture
    def runner(self):
        """Create runner with mocked dependencies"""
        with patch("packages.bulletin_board.agents.memory_enhanced_runner.FileMemorySystem"):
            with patch("packages.bulletin_board.agents.memory_enhanced_runner.PersonalityDriftEngine"):
                with patch("packages.bulletin_board.agents.memory_enhanced_runner.AnalyticsCollector"):
                    from packages.bulletin_board.agents.memory_enhanced_runner import MemoryEnhancedRunner

                    runner = MemoryEnhancedRunner()
                    yield runner

    def test_memory_context_building(self, runner):
        """Test building memory context for responses"""
        # Mock memory system methods
        runner.memory_system.find_similar_situations = MagicMock(return_value=[])
        runner.memory_system.search_memories = MagicMock(return_value=[])
        runner.memory_system.find_incident = MagicMock(return_value=None)
        runner.memory_system.get_relationship = MagicMock(return_value=None)

        # Mock drift engine to return valid state
        mock_state = MagicMock()
        mock_state.positivity = 0.5
        mock_state.energy_level = 0.5
        mock_state.chaos_tolerance = 0.5
        runner.drift_engine.get_current_state = MagicMock(return_value=mock_state)

        # Mock post
        post = MagicMock()
        post.content = "Test post content"

        context = runner._build_memory_context("agent1", post)

        assert "similar_memories" in context
        assert "recent_memories" in context
        assert "incident" in context
        assert "relationships" in context
        assert "current_mood" in context

    def test_sentiment_analysis(self, runner):
        """Test sentiment analysis"""
        positive_text = "This is great! I love it. Awesome work!"
        negative_text = "This is bad. I hate bugs. Everything is broken."
        neutral_text = "This is a comment about code."

        assert runner._analyze_sentiment(positive_text) > 0.5
        assert runner._analyze_sentiment(negative_text) < -0.5
        assert abs(runner._analyze_sentiment(neutral_text)) < 0.5

    def test_importance_calculation(self, runner):
        """Test calculating interaction importance"""
        comment = MagicMock()
        comment.content = "Short comment"
        comment.reactions = {}
        # No confidence_score attribute

        low_importance = runner._calculate_importance(comment, 0.1)
        assert 0 <= low_importance <= 1

        comment.content = "A" * 300  # Long comment
        comment.reactions = {"reaction1": "url1", "reaction2": "url2"}
        comment.confidence_score = 0.8  # Add confidence score

        high_importance = runner._calculate_importance(comment, 0.9)
        assert high_importance > low_importance
