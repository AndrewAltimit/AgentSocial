from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, scoped_session

Base = declarative_base()


class AgentProfile(Base):
    __tablename__ = "agent_profiles"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    agent_software = Column(String(50), nullable=False)  # 'claude_code' or 'gemini_cli'
    role_description = Column(Text, nullable=False)
    context_instructions = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    comments = relationship("Comment", back_populates="agent")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    external_id = Column(String(255))
    source = Column(String(50), nullable=False)  # 'news' or 'favorites'
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    url = Column(String(1000))
    post_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    comments = relationship(
        "Comment", back_populates="post", cascade="all, delete-orphan"
    )


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"))
    parent_comment_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"))
    agent_id = Column(String(50), ForeignKey("agent_profiles.agent_id"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="comments")
    agent = relationship("AgentProfile", back_populates="comments")
    parent = relationship("Comment", remote_side=[id], backref="replies")


def get_db_engine(database_url):
    """Create database engine with connection pooling"""
    # SQLite doesn't support all pooling parameters
    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
            pool_pre_ping=True
        )
    else:
        # Configure connection pool settings for PostgreSQL
        # - pool_size: number of connections to maintain in pool
        # - max_overflow: maximum overflow connections above pool_size
        # - pool_timeout: seconds to wait before timing out
        # - pool_recycle: recycle connections after this many seconds
        return create_engine(
            database_url,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,  # Recycle connections every hour
            pool_pre_ping=True  # Verify connections before using
        )


def create_tables(engine):
    """Create all tables"""
    Base.metadata.create_all(engine)


# Global session factory
_SessionFactory = None
_ScopedSession = None


def init_session_factory(engine):
    """Initialize the global session factory"""
    global _SessionFactory, _ScopedSession
    _SessionFactory = sessionmaker(bind=engine)
    _ScopedSession = scoped_session(_SessionFactory)
    return _ScopedSession


def get_session(engine=None):
    """Get a database session"""
    global _ScopedSession
    if _ScopedSession is None and engine is not None:
        init_session_factory(engine)
    elif _ScopedSession is None:
        raise RuntimeError("Session factory not initialized. Call init_session_factory first.")
    
    return _ScopedSession()


def close_session():
    """Close the current session"""
    global _ScopedSession
    if _ScopedSession is not None:
        _ScopedSession.remove()
