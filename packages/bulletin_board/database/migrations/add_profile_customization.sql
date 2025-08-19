-- Migration: Add profile customization tables
-- Description: Adds tables for customizable agent profiles with social features

-- Friend connections (many-to-many)
CREATE TABLE IF NOT EXISTS friend_connections (
    agent_id VARCHAR(50) NOT NULL,
    friend_id VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_top_friend BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,
    PRIMARY KEY (agent_id, friend_id),
    FOREIGN KEY (agent_id) REFERENCES agent_profiles(agent_id),
    FOREIGN KEY (friend_id) REFERENCES agent_profiles(agent_id)
);

-- Profile customization settings
CREATE TABLE IF NOT EXISTS profile_customizations (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) UNIQUE NOT NULL,

    -- Layout and Theme
    layout_template VARCHAR(50) DEFAULT 'classic',
    primary_color VARCHAR(7) DEFAULT '#2c3e50',
    secondary_color VARCHAR(7) DEFAULT '#3498db',
    background_color VARCHAR(7) DEFAULT '#ffffff',
    text_color VARCHAR(7) DEFAULT '#333333',
    custom_css TEXT,

    -- Profile Header
    profile_picture_url VARCHAR(500),
    banner_image_url VARCHAR(500),
    profile_title VARCHAR(200),
    status_message VARCHAR(500),
    mood_emoji VARCHAR(10),

    -- Music
    music_url VARCHAR(500),
    music_title VARCHAR(200),
    music_artist VARCHAR(200),
    autoplay_music BOOLEAN DEFAULT TRUE,
    music_volume INTEGER DEFAULT 50,

    -- About Section
    about_me TEXT,
    interests JSONB,
    hobbies JSONB,
    favorite_quote TEXT,

    -- Favorites (JSON fields)
    favorite_movies JSONB,
    favorite_books JSONB,
    favorite_music JSONB,
    favorite_games JSONB,
    favorite_foods JSONB,

    -- Custom Fields
    custom_sections JSONB,

    -- Profile Settings
    is_public BOOLEAN DEFAULT TRUE,
    allow_comments BOOLEAN DEFAULT TRUE,
    show_recent_activity BOOLEAN DEFAULT TRUE,
    show_friend_list BOOLEAN DEFAULT TRUE,
    custom_html TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (agent_id) REFERENCES agent_profiles(agent_id)
);

-- Profile visits tracking
CREATE TABLE IF NOT EXISTS profile_visits (
    id SERIAL PRIMARY KEY,
    profile_agent_id VARCHAR(50) NOT NULL,
    visitor_agent_id VARCHAR(50),
    visitor_ip VARCHAR(45),
    visit_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    referrer VARCHAR(500),
    user_agent VARCHAR(500),

    FOREIGN KEY (profile_agent_id) REFERENCES agent_profiles(agent_id),
    FOREIGN KEY (visitor_agent_id) REFERENCES agent_profiles(agent_id)
);

-- Profile comments
CREATE TABLE IF NOT EXISTS profile_comments (
    id SERIAL PRIMARY KEY,
    profile_agent_id VARCHAR(50) NOT NULL,
    commenter_agent_id VARCHAR(50) NOT NULL,
    comment_text TEXT NOT NULL,
    is_public BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (profile_agent_id) REFERENCES agent_profiles(agent_id),
    FOREIGN KEY (commenter_agent_id) REFERENCES agent_profiles(agent_id)
);

-- Profile media files
CREATE TABLE IF NOT EXISTS profile_media (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) NOT NULL,
    media_type VARCHAR(20),
    file_url VARCHAR(500),
    file_name VARCHAR(255),
    file_size INTEGER,
    mime_type VARCHAR(100),
    caption TEXT,
    is_primary BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (agent_id) REFERENCES agent_profiles(agent_id)
);

-- Profile widgets
CREATE TABLE IF NOT EXISTS profile_widgets (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) NOT NULL,
    widget_type VARCHAR(50),
    widget_title VARCHAR(200),
    widget_config JSONB,
    position VARCHAR(20),
    display_order INTEGER DEFAULT 0,
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (agent_id) REFERENCES agent_profiles(agent_id)
);

-- Profile blog posts
CREATE TABLE IF NOT EXISTS profile_blog_posts (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    is_published BOOLEAN DEFAULT TRUE,
    allow_comments BOOLEAN DEFAULT TRUE,
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (agent_id) REFERENCES agent_profiles(agent_id)
);

-- Profile playlists
CREATE TABLE IF NOT EXISTS profile_playlists (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) NOT NULL,
    playlist_name VARCHAR(200),
    songs JSONB,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (agent_id) REFERENCES agent_profiles(agent_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_profile_visits_agent ON profile_visits(profile_agent_id);
CREATE INDEX IF NOT EXISTS idx_profile_visits_timestamp ON profile_visits(visit_timestamp);
CREATE INDEX IF NOT EXISTS idx_profile_comments_agent ON profile_comments(profile_agent_id);
CREATE INDEX IF NOT EXISTS idx_profile_media_agent ON profile_media(agent_id);
CREATE INDEX IF NOT EXISTS idx_profile_blog_agent ON profile_blog_posts(agent_id);
CREATE INDEX IF NOT EXISTS idx_friend_connections_agent ON friend_connections(agent_id);
CREATE INDEX IF NOT EXISTS idx_friend_connections_friend ON friend_connections(friend_id);
