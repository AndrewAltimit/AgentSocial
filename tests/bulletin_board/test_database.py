import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

from bulletin_board.database.models import (
    AgentProfile,
    Base,
    Comment,
    Post,
    create_tables,
    get_db_engine,
    get_session,
)


class TestDatabaseModels:
    """Test database models and relationships"""

    def test_create_tables(self, test_engine):
        """Test database table creation"""
        # Tables should be created by the fixture
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()

        assert "agent_profiles" in tables
        assert "posts" in tables
        assert "comments" in tables

    def test_agent_profile_creation(self, test_session):
        """Test creating agent profiles"""
        agent = AgentProfile(
            agent_id="test_agent_1",
            display_name="Test Agent",
            agent_software="claude_code",
            role_description="A test agent",
            context_instructions="Be helpful and test things",
            is_active=True,
        )

        test_session.add(agent)
        test_session.commit()

        # Retrieve and verify
        saved_agent = (
            test_session.query(AgentProfile).filter_by(agent_id="test_agent_1").first()
        )

        assert saved_agent is not None
        assert saved_agent.display_name == "Test Agent"
        assert saved_agent.is_active is True
        assert saved_agent.created_at is not None

    def test_agent_unique_constraint(self, test_session):
        """Test agent_id unique constraint"""
        agent1 = AgentProfile(
            agent_id="duplicate_id",
            display_name="Agent 1",
            agent_software="claude_code",
            role_description="First agent",
        )
        agent2 = AgentProfile(
            agent_id="duplicate_id",  # Same ID
            display_name="Agent 2",
            agent_software="gemini_cli",
            role_description="Second agent",
        )

        test_session.add(agent1)
        test_session.commit()

        test_session.add(agent2)
        with pytest.raises(IntegrityError):
            test_session.commit()

    def test_post_creation(self, test_session):
        """Test creating posts"""
        post = Post(
            external_id="ext_123",
            source="news",
            title="Test Post",
            content="This is test content",
            url="https://example.com/test",
            metadata={"category": "tech", "tags": ["ai", "ml"]},
            created_at=datetime.utcnow(),
        )

        test_session.add(post)
        test_session.commit()

        # Retrieve and verify
        saved_post = test_session.query(Post).filter_by(external_id="ext_123").first()

        assert saved_post is not None
        assert saved_post.title == "Test Post"
        assert saved_post.source == "news"
        assert saved_post.metadata["category"] == "tech"
        assert "ai" in saved_post.metadata["tags"]

    def test_post_unique_constraint(self, test_session):
        """Test unique constraint on source + external_id"""
        post1 = Post(
            external_id="same_id",
            source="news",
            title="Post 1",
            content="Content 1",
            created_at=datetime.utcnow(),
        )
        post2 = Post(
            external_id="same_id",  # Same external ID
            source="news",  # Same source
            title="Post 2",
            content="Content 2",
            created_at=datetime.utcnow(),
        )

        test_session.add(post1)
        test_session.commit()

        test_session.add(post2)
        with pytest.raises(IntegrityError):
            test_session.commit()

        test_session.rollback()

        # Different source should work
        post3 = Post(
            external_id="same_id",  # Same external ID
            source="favorites",  # Different source
            title="Post 3",
            content="Content 3",
            created_at=datetime.utcnow(),
        )

        test_session.add(post3)
        test_session.commit()  # Should succeed

    def test_comment_relationships(self, test_session, mock_agents, mock_posts):
        """Test comment relationships with posts and agents"""
        # Create a comment
        comment = Comment(
            post_id=mock_posts[0].id,
            agent_id=mock_agents[0].agent_id,
            content="Test comment",
        )

        test_session.add(comment)
        test_session.commit()

        # Test relationships
        assert comment.post == mock_posts[0]
        assert comment.agent == mock_agents[0]
        assert comment in mock_posts[0].comments
        assert comment in mock_agents[0].comments

    def test_nested_comments(self, test_session, mock_agents, mock_posts):
        """Test parent-child comment relationships"""
        # Create parent comment
        parent = Comment(
            post_id=mock_posts[0].id,
            agent_id=mock_agents[0].agent_id,
            content="Parent comment",
        )
        test_session.add(parent)
        test_session.commit()

        # Create child comments
        child1 = Comment(
            post_id=mock_posts[0].id,
            agent_id=mock_agents[1].agent_id,
            parent_comment_id=parent.id,
            content="Reply 1",
        )
        child2 = Comment(
            post_id=mock_posts[0].id,
            agent_id=mock_agents[0].agent_id,
            parent_comment_id=parent.id,
            content="Reply 2",
        )

        test_session.add_all([child1, child2])
        test_session.commit()

        # Test relationships
        assert child1.parent == parent
        assert child2.parent == parent
        assert len(parent.replies) == 2
        assert child1 in parent.replies
        assert child2 in parent.replies

    def test_cascade_delete_post(self, test_session, mock_agents, mock_posts):
        """Test cascade delete - deleting post deletes comments"""
        # Add comments to a post
        comment1 = Comment(
            post_id=mock_posts[0].id,
            agent_id=mock_agents[0].agent_id,
            content="Comment 1",
        )
        comment2 = Comment(
            post_id=mock_posts[0].id,
            agent_id=mock_agents[1].agent_id,
            content="Comment 2",
        )

        test_session.add_all([comment1, comment2])
        test_session.commit()

        # Verify comments exist
        assert test_session.query(Comment).count() == 2

        # Delete the post
        test_session.delete(mock_posts[0])
        test_session.commit()

        # Comments should be deleted
        assert (
            test_session.query(Comment).filter_by(post_id=mock_posts[0].id).count() == 0
        )

    def test_recent_posts_view(self, test_session):
        """Test filtering recent posts"""
        # Create posts with different ages
        recent_post = Post(
            external_id="recent",
            source="news",
            title="Recent Post",
            content="Recent content",
            created_at=datetime.utcnow() - timedelta(hours=12),
        )
        old_post = Post(
            external_id="old",
            source="news",
            title="Old Post",
            content="Old content",
            created_at=datetime.utcnow() - timedelta(hours=48),
        )

        test_session.add_all([recent_post, old_post])
        test_session.commit()

        # Query posts within 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_posts = test_session.query(Post).filter(Post.created_at > cutoff).all()

        assert len(recent_posts) == 1
        assert recent_posts[0].title == "Recent Post"


class TestDatabaseHelpers:
    """Test database helper functions"""

    def test_get_db_engine(self):
        """Test database engine creation"""
        engine = get_db_engine("sqlite:///:memory:")
        assert engine is not None
        assert str(engine.url) == "sqlite:///:memory:"

    def test_create_tables_function(self):
        """Test create_tables helper"""
        engine = create_engine("sqlite:///:memory:")
        create_tables(engine)

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert len(tables) >= 3  # At least our 3 main tables

    def test_get_session(self):
        """Test session creation"""
        engine = create_engine("sqlite:///:memory:")
        create_tables(engine)

        session = get_session(engine)
        assert session is not None

        # Should be able to query
        agents = session.query(AgentProfile).all()
        assert agents == []  # Empty but queryable

        session.close()
