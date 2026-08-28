-- ==============================================================================
-- MoodFeed PostgreSQL Complete Production Schema
-- Tables: users, user_preferences, posts, likes, saves, comments, follows, notifications, interaction_logs, user_interactions
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. USERS
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    username VARCHAR(64) UNIQUE,
    password_hash VARCHAR(255),
    display_name VARCHAR(120),
    full_name VARCHAR(120),
    avatar VARCHAR(255),
    avatar_url VARCHAR(255),
    bio VARCHAR(500),
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_private BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NULL
);

-- 2. USER PREFERENCES
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    spiral_threshold FLOAT NOT NULL DEFAULT 0.7,
    negative_threshold FLOAT NOT NULL DEFAULT 0.6,
    positive_threshold FLOAT NOT NULL DEFAULT 0.5,
    toxicity_threshold FLOAT NOT NULL DEFAULT 0.6,
    theme VARCHAR(32) NOT NULL DEFAULT 'light',
    active_profile VARCHAR(64) NOT NULL DEFAULT 'balanced',
    active_scenario VARCHAR(64) NOT NULL DEFAULT 'default',
    profile_preset VARCHAR(32) NOT NULL DEFAULT 'balanced',
    low_intensity_mode BOOLEAN NOT NULL DEFAULT FALSE,
    muted_sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. POSTS (With Mood AI metrics)
CREATE TABLE IF NOT EXISTS posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content VARCHAR(2000) NOT NULL,
    title VARCHAR(255),
    author VARCHAR(120),
    handle VARCHAR(64),
    category VARCHAR(64) NOT NULL DEFAULT 'Gündem',
    mood_score FLOAT NOT NULL DEFAULT 0.0,
    mood_label VARCHAR(32) NOT NULL DEFAULT 'neutral',
    sentiment_label VARCHAR(32) NOT NULL DEFAULT 'neutral',
    sentiment_score FLOAT NOT NULL DEFAULT 0.5,
    negativity_score FLOAT NOT NULL DEFAULT 0.1,
    toxicity_score FLOAT NOT NULL DEFAULT 0.0,
    repetition_score FLOAT NOT NULL DEFAULT 0.0,
    language VARCHAR(8) NOT NULL DEFAULT 'tr',
    is_published BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. LIKES
CREATE TABLE IF NOT EXISTS likes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_post_like UNIQUE (user_id, post_id)
);

-- 5. SAVES (Bookmarks)
CREATE TABLE IF NOT EXISTS saves (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_post_save UNIQUE (user_id, post_id)
);

-- 6. COMMENTS (Nested Tree + Mood AI)
CREATE TABLE IF NOT EXISTS comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    parent_comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    content VARCHAR(1000) NOT NULL,
    mood_score FLOAT NOT NULL DEFAULT 0.0,
    mood_label VARCHAR(32) NOT NULL DEFAULT 'neutral',
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- 7. FOLLOWS
CREATE TABLE IF NOT EXISTS follows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    follower_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    followed_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_follower_followed UNIQUE (follower_user_id, followed_user_id)
);

-- 8. NOTIFICATIONS
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    actor_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(32) NOT NULL,
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    message VARCHAR(255),
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 9. USER INTERACTIONS
CREATE TABLE IF NOT EXISTS user_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content_id VARCHAR(128) NOT NULL,
    action_type VARCHAR(64) NOT NULL,
    source VARCHAR(128),
    category VARCHAR(64),
    extra_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. INTERACTION LOGS
CREATE TABLE IF NOT EXISTS interaction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(64) NOT NULL,
    event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_mood_label ON posts(mood_label);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id);
CREATE INDEX IF NOT EXISTS idx_comments_parent_id ON comments(parent_comment_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_follows_follower ON follows(follower_user_id);
CREATE INDEX IF NOT EXISTS idx_follows_followed ON follows(followed_user_id);

