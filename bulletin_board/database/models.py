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
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

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
    """Create database engine"""
    return create_engine(database_url, pool_pre_ping=True)


def create_tables(engine):
    """Create all tables"""
    Base.metadata.create_all(engine)


def get_session(engine):
    """Get database session"""
    Session = sessionmaker(bind=engine)
    return Session()
