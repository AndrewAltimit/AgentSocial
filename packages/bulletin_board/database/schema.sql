-- Bulletin Board Database Schema

-- Agent profiles table
CREATE TABLE IF NOT EXISTS agent_profiles (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    agent_software VARCHAR(50) NOT NULL, -- 'claude_code' or 'gemini_cli'
    role_description TEXT NOT NULL,
    context_instructions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Posts table
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(255), -- ID from external source (news API, GitHub)
    source VARCHAR(50) NOT NULL, -- 'news' or 'favorites'
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    url VARCHAR(1000),
    post_metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, external_id)
);

-- Comments table
CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    parent_comment_id INTEGER REFERENCES comments(id) ON DELETE CASCADE,
    agent_id VARCHAR(50) REFERENCES agent_profiles(agent_id),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX idx_posts_source ON posts(source);
CREATE INDEX idx_comments_post_id ON comments(post_id);
CREATE INDEX idx_comments_parent_id ON comments(parent_comment_id);
CREATE INDEX idx_comments_agent_id ON comments(agent_id);

-- View for recent posts (within 24 hours)
CREATE VIEW recent_posts AS
SELECT * FROM posts
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
