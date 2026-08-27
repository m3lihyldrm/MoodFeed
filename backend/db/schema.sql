-- ==============================================================================
-- MoodFeed PostgreSQL Schema
-- Tables: users, user_preferences, interaction_logs
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. USERS
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
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
    muted_sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. INTERACTION LOGS
CREATE TABLE IF NOT EXISTS interaction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(64) NOT NULL,
    event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
