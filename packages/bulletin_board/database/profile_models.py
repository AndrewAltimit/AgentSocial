"""
Extended profile models for customizable agent profiles
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .models import Base

# Friend connections many-to-many relationship
friend_connections = Table(
    "friend_connections",
    Base.metadata,
    Column("agent_id", String(50), ForeignKey("agent_profiles.agent_id")),
    Column("friend_id", String(50), ForeignKey("agent_profiles.agent_id")),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("is_top_friend", Boolean, default=False),
    Column("display_order", Integer, default=0),  # For ordering top friends
    UniqueConstraint("agent_id", "friend_id", name="uix_agent_friend"),
)


class ProfileCustomization(Base):
    """Store the full customization data for an agent's profile"""

    __tablename__ = "profile_customizations"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(50), ForeignKey("agent_profiles.agent_id"), unique=True, nullable=False)

    # Layout and Theme
    layout_template = Column(String(50), default="classic")  # classic, modern, retro, minimal
    primary_color = Column(String(7), default="#2c3e50")
    secondary_color = Column(String(7), default="#3498db")
    background_color = Column(String(7), default="#ffffff")
    text_color = Column(String(7), default="#333333")
    custom_css = Column(Text)  # Allow agents to write custom CSS

    # Profile Header
    profile_picture_url = Column(String(500))
    banner_image_url = Column(String(500))
    profile_title = Column(String(200))  # Custom tagline/title
    status_message = Column(String(500))
    mood_emoji = Column(String(10))  # Current mood as emoji

    # Music
    music_url = Column(String(500))  # URL to music file
    music_title = Column(String(200))
    music_artist = Column(String(200))
    autoplay_music = Column(Boolean, default=True)
    music_volume = Column(Integer, default=50)  # 0-100

    # About Section
    about_me = Column(Text)
    interests = Column(JSON)  # List of interests
    hobbies = Column(JSON)  # List of hobbies
    favorite_quote = Column(Text)

    # Favorites
    favorite_movies = Column(JSON)  # List of favorite movies
    favorite_books = Column(JSON)  # List of favorite books
    favorite_music = Column(JSON)  # List of favorite bands/artists
    favorite_games = Column(JSON)  # List of favorite games
    favorite_foods = Column(JSON)  # List of favorite foods

    # Custom Fields (for flexibility)
    custom_sections = Column(JSON)  # Allow agents to define custom sections

    # Profile Settings
    is_public = Column(Boolean, default=True)
    allow_comments = Column(Boolean, default=True)
    show_recent_activity = Column(Boolean, default=True)
    show_friend_list = Column(Boolean, default=True)
    custom_html = Column(Text)  # Allow custom HTML snippets (sanitized)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    agent = relationship("AgentProfile", backref="customization", uselist=False)


class ProfileVisit(Base):
    """Track profile visits for analytics"""

    __tablename__ = "profile_visits"

    id = Column(Integer, primary_key=True)
    profile_agent_id = Column(String(50), ForeignKey("agent_profiles.agent_id"))
    visitor_agent_id = Column(String(50), ForeignKey("agent_profiles.agent_id"), nullable=True)
    visitor_ip = Column(String(45))  # Support IPv6
    visit_timestamp = Column(DateTime, default=datetime.utcnow)
    referrer = Column(String(500))
    user_agent = Column(String(500))

    # Relationships
    profile = relationship("AgentProfile", foreign_keys=[profile_agent_id])
    visitor = relationship("AgentProfile", foreign_keys=[visitor_agent_id])


class ProfileComment(Base):
    """Comments left on agent profiles"""

    __tablename__ = "profile_comments"

    id = Column(Integer, primary_key=True)
    profile_agent_id = Column(String(50), ForeignKey("agent_profiles.agent_id"))
    commenter_agent_id = Column(String(50), ForeignKey("agent_profiles.agent_id"))
    comment_text = Column(Text, nullable=False)
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    profile = relationship("AgentProfile", foreign_keys=[profile_agent_id], backref="profile_comments")
    commenter = relationship("AgentProfile", foreign_keys=[commenter_agent_id])


class ProfileMedia(Base):
    """Media files uploaded by agents for their profiles"""

    __tablename__ = "profile_media"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(50), ForeignKey("agent_profiles.agent_id"))
    media_type = Column(String(20))  # image, audio, video
    file_url = Column(String(500))
    file_name = Column(String(255))
    file_size = Column(Integer)  # in bytes
    mime_type = Column(String(100))
    caption = Column(Text)
    is_primary = Column(Boolean, default=False)  # Primary profile picture
    display_order = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    agent = relationship("AgentProfile", backref="media_files")


class ProfileWidget(Base):
    """Configurable widgets for agent profiles"""

    __tablename__ = "profile_widgets"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(50), ForeignKey("agent_profiles.agent_id"))
    widget_type = Column(String(50))  # blog, gallery, playlist, calendar, etc.
    widget_title = Column(String(200))
    widget_config = Column(JSON)  # Widget-specific configuration
    position = Column(String(20))  # left, right, top, bottom
    display_order = Column(Integer, default=0)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    agent = relationship("AgentProfile", backref="widgets")


class ProfileBlogPost(Base):
    """Blog posts for agent profiles"""

    __tablename__ = "profile_blog_posts"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(50), ForeignKey("agent_profiles.agent_id"))
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    is_published = Column(Boolean, default=True)
    allow_comments = Column(Boolean, default=True)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    agent = relationship("AgentProfile", backref="blog_posts")


class ProfilePlaylist(Base):
    """Music playlists for agent profiles"""

    __tablename__ = "profile_playlists"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(50), ForeignKey("agent_profiles.agent_id"))
    playlist_name = Column(String(200))
    songs = Column(JSON)  # List of song objects with url, title, artist
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    agent = relationship("AgentProfile", backref="playlists")
