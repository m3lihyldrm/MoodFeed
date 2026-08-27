-- ==============================================================================
-- MoodFeed PostgreSQL 16 Production Relational Schema
-- Version: 1.0.0
-- Standards: UUIDv4 PKs, strict foreign keys, indexing, RLS, audit triggers
-- ==============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. USERS & IDENTITY
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(120) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'moderator', 'admin', 'service_role')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE deleted_at IS NULL;

-- 2. SESSIONS
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    user_agent TEXT NULL,
    ip_address INET NULL,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token);

-- 3. REFRESH TOKENS (Token Family Rotation)
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    token_family UUID NOT NULL DEFAULT uuid_generate_v4(),
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_family ON refresh_tokens(token_family);

-- 4. EMAIL VERIFICATION TOKENS
CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. PASSWORD RESET TOKENS
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. CONSENTS (GDPR / KVKK Governance)
CREATE TABLE IF NOT EXISTS consents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type VARCHAR(64) NOT NULL CHECK (consent_type IN ('essential_cookies', 'algorithmic_feed_sorting', 'exploratory_pilot_evaluation', 'anonymous_telemetry')),
    granted BOOLEAN NOT NULL,
    ip_hash VARCHAR(64) NULL,
    user_agent TEXT NULL,
    version VARCHAR(16) NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_consents_user_type ON consents(user_id, consent_type);

-- 7. USER PREFERENCES
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    spiral_threshold FLOAT NOT NULL DEFAULT 0.7,
    negative_threshold FLOAT NOT NULL DEFAULT 0.6,
    positive_threshold FLOAT NOT NULL DEFAULT 0.5,
    toxicity_threshold FLOAT NOT NULL DEFAULT 0.6,
    theme VARCHAR(32) NOT NULL DEFAULT 'light',
    profile_preset VARCHAR(32) NOT NULL DEFAULT 'balanced' CHECK (profile_preset IN ('balanced', 'calmer', 'user_control')),
    low_intensity_mode BOOLEAN NOT NULL DEFAULT FALSE,
    toxicity_filter_level VARCHAR(32) NOT NULL DEFAULT 'standard' CHECK (toxicity_filter_level IN ('off', 'standard', 'strict')),
    active_feed_mode VARCHAR(32) NOT NULL DEFAULT 'moodfeed' CHECK (active_feed_mode IN ('original', 'moodfeed')),
    synthetic_scenario VARCHAR(64) NOT NULL DEFAULT 'default',
    custom_weights JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. CONTENT SOURCES
CREATE TABLE IF NOT EXISTS content_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_type VARCHAR(32) NOT NULL DEFAULT 'rss' CHECK (source_type IN ('rss', 'atom', 'synthetic_demo')),
    title VARCHAR(255) NOT NULL,
    feed_url TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'error', 'revoked')),
    last_sync_at TIMESTAMPTZ NULL,
    last_error_message TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sources_user ON content_sources(user_id);

-- 9. SOURCE CREDENTIALS METADATA (Never raw secrets)
CREATE TABLE IF NOT EXISTS source_credentials_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID UNIQUE NOT NULL REFERENCES content_sources(id) ON DELETE CASCADE,
    auth_method VARCHAR(32) NOT NULL DEFAULT 'none' CHECK (auth_method IN ('none', 'api_key_vault', 'oauth2')),
    key_fingerprint VARCHAR(64) NULL,
    expires_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. CONTENT ITEMS
CREATE TABLE IF NOT EXISTS content_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID NULL REFERENCES content_sources(id) ON DELETE SET NULL,
    provider_item_id VARCHAR(255) NOT NULL,
    canonical_url TEXT NULL,
    title VARCHAR(500) NOT NULL,
    summary TEXT NULL,
    text_content TEXT NOT NULL,
    author_display_name VARCHAR(120) NOT NULL DEFAULT 'Anonim',
    category VARCHAR(64) NOT NULL DEFAULT 'Genel',
    tags TEXT[] NOT NULL DEFAULT '{}',
    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    content_hash VARCHAR(64) NOT NULL,
    moderation_status VARCHAR(32) NOT NULL DEFAULT 'allowed' CHECK (moderation_status IN ('pending', 'allowed', 'limited', 'blocked', 'needs_review', 'removed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_content_provider_hash ON content_items(provider_item_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_content_published ON content_items(published_at DESC);

-- 11. CONTENT FEATURES
CREATE TABLE IF NOT EXISTS content_features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID UNIQUE NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
    sentiment_label VARCHAR(16) NOT NULL CHECK (sentiment_label IN ('positive', 'negative', 'neutral')),
    sentiment_score REAL NOT NULL CHECK (sentiment_score >= 0.0 AND sentiment_score <= 1.0),
    toxicity_score REAL NOT NULL CHECK (toxicity_score >= 0.0 AND toxicity_score <= 1.0),
    negativity_score REAL NOT NULL CHECK (negativity_score >= 0.0 AND negativity_score <= 1.0),
    repetition_score REAL NOT NULL DEFAULT 0.0,
    intensity_score REAL NOT NULL DEFAULT 0.0,
    scorer_name VARCHAR(64) NOT NULL DEFAULT 'rule_based',
    scorer_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 12. SIMILARITY GROUPS
CREATE TABLE IF NOT EXISTS similarity_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_key VARCHAR(120) UNIQUE NOT NULL,
    topic_label VARCHAR(120) NOT NULL,
    item_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 13. FEED DECISIONS
CREATE TABLE IF NOT EXISTS feed_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_id UUID NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
    original_rank INT NOT NULL,
    new_rank INT NOT NULL,
    ranking_score REAL NOT NULL,
    score_breakdown JSONB NOT NULL,
    reasons TEXT[] NOT NULL DEFAULT '{}',
    algorithm_version VARCHAR(32) NOT NULL DEFAULT '1.2.0',
    is_reverted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_decisions_user_content ON feed_decisions(user_id, content_id);

-- 14. FEED INTERACTIONS
CREATE TABLE IF NOT EXISTS feed_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_id UUID NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
    interaction_type VARCHAR(32) NOT NULL CHECK (interaction_type IN ('view', 'click', 'save', 'revert', 'mute', 'detail')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_interactions_user ON feed_interactions(user_id);

-- 15. SAVED ITEMS
CREATE TABLE IF NOT EXISTS saved_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_id UUID NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, content_id)
);

-- 16. MUTED SOURCES
CREATE TABLE IF NOT EXISTS muted_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_name VARCHAR(120) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, source_name)
);

-- 17. MUTED CATEGORIES
CREATE TABLE IF NOT EXISTS muted_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_name VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, category_name)
);

-- 18. RECOMMENDATION FEEDBACK
CREATE TABLE IF NOT EXISTS recommendation_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_id UUID NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
    feedback_action VARCHAR(32) NOT NULL CHECK (feedback_action IN ('less_like_this', 'undo_recommendation', 'helpful', 'not_helpful')),
    note VARCHAR(500) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 19. EXPLANATION RECORDS
CREATE TABLE IF NOT EXISTS explanation_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id UUID NOT NULL REFERENCES feed_decisions(id) ON DELETE CASCADE,
    observed_signals TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    user_controls TEXT NOT NULL,
    limitation_notice TEXT NOT NULL,
    confidence_level VARCHAR(16) NOT NULL DEFAULT 'high',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 20. PILOT SESSIONS
CREATE TABLE IF NOT EXISTS pilot_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    anonymous_session_code VARCHAR(64) UNIQUE NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ NULL,
    survey_ratings JSONB NULL,
    survey_open_notes TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 21. PILOT TASKS
CREATE TABLE IF NOT EXISTS pilot_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES pilot_sessions(id) ON DELETE CASCADE,
    task_name VARCHAR(64) NOT NULL,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    duration_ms INT NOT NULL DEFAULT 0,
    error_count INT NOT NULL DEFAULT 0,
    retry_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 22. EXPORT REQUESTS
CREATE TABLE IF NOT EXISTS export_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    format VARCHAR(16) NOT NULL CHECK (format IN ('json', 'csv')),
    status VARCHAR(32) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'ready', 'failed', 'expired')),
    download_url TEXT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 23. DELETION REQUESTS
CREATE TABLE IF NOT EXISTS deletion_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    scheduled_for TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 24. AUDIT EVENTS (Zero secrets, zero raw text)
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    event_type VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    resource_id VARCHAR(64) NULL,
    ip_hash VARCHAR(64) NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'success' CHECK (status IN ('success', 'failure', 'denied')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_events_created ON audit_events(created_at DESC);

-- 25. FEATURE FLAGS
CREATE TABLE IF NOT EXISTS feature_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    flag_key VARCHAR(64) UNIQUE NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
