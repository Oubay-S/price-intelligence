-- ============================================================
-- PriceRadar — PostgreSQL schema
-- Application & user management database
-- Run order: extensions → types → tables → indexes → triggers
-- ============================================================


-- ============================================================
-- 1. EXTENSIONS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- uuid_generate_v4()
CREATE EXTENSION IF NOT EXISTS "pgcrypto";        -- gen_random_uuid(), crypt()
CREATE EXTENSION IF NOT EXISTS "citext";          -- case-insensitive email type


-- ============================================================
-- 2. CUSTOM TYPES
-- ============================================================

CREATE TYPE user_role AS ENUM ('user', 'admin');

CREATE TYPE alert_type AS ENUM (
    'price_drop',
    'back_in_stock',
    'buy_soon',
    'price_rise'
);

CREATE TYPE audit_action AS ENUM (
    'user_register',
    'user_login',
    'user_logout',
    'user_ban',
    'user_unban',
    'watchlist_add',
    'watchlist_remove',
    'watchlist_threshold_update',
    'alert_read',
    'alert_dismiss',
    'compare_save',
    'compare_delete',
    'preferences_update',
    'password_change',
    'token_revoke'
);


-- ============================================================
-- 3. TABLES
-- ============================================================


-- ------------------------------------------------------------
-- 3.1  users
-- Core identity table. One row per registered account.
-- ------------------------------------------------------------

CREATE TABLE users (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    email               CITEXT          NOT NULL,
    hashed_password     VARCHAR(255)    NOT NULL,
    full_name           VARCHAR(120),
    role                user_role       NOT NULL DEFAULT 'user',
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    email_verified      BOOLEAN         NOT NULL DEFAULT FALSE,

    -- timestamps
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    last_login_at       TIMESTAMPTZ,

    -- constraints
    CONSTRAINT users_email_unique UNIQUE (email),
    CONSTRAINT users_email_format CHECK (email ~* '^[^@]+@[^@]+\.[^@]+$')
);




-- ------------------------------------------------------------
-- 3.2  sessions
-- One row per active login. Supports multi-device login and
-- per-session revocation (instant logout from a single device).
-- ------------------------------------------------------------

CREATE TABLE sessions (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID            NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash      VARCHAR(255)    NOT NULL,   -- SHA-256 of the JWT, never raw token
    ip_address      INET,
    user_agent      TEXT,
    is_revoked      BOOLEAN         NOT NULL DEFAULT FALSE,
    expires_at      TIMESTAMPTZ     NOT NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT sessions_token_hash_unique UNIQUE (token_hash)
);



-- ------------------------------------------------------------
-- 3.3  refresh_tokens
-- Each session can have one active refresh token at a time.
-- is_used prevents replay: token is marked used on first use,
-- a new one is issued immediately.
-- ------------------------------------------------------------

CREATE TABLE refresh_tokens (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID            NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    session_id      UUID            NOT NULL REFERENCES sessions (id) ON DELETE CASCADE,
    token_hash      VARCHAR(255)    NOT NULL,
    is_used         BOOLEAN         NOT NULL DEFAULT FALSE,
    expires_at      TIMESTAMPTZ     NOT NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT refresh_tokens_token_hash_unique UNIQUE (token_hash)
);




-- ------------------------------------------------------------
-- 3.4  user_preferences
-- One-to-one with users. Created automatically on registration
-- with sensible defaults. Controls catalog defaults and
-- notification settings per user.
-- ------------------------------------------------------------

CREATE TABLE user_preferences (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID            NOT NULL REFERENCES users (id) ON DELETE CASCADE,

    -- display defaults
    default_currency        VARCHAR(3)      NOT NULL DEFAULT 'USD',
    default_category        VARCHAR(60),                            -- e.g. 'strength_nutrition'
    preferred_sites         TEXT[],                                 -- e.g. ARRAY['iherb.com','myprotein.com']

    -- alert defaults (per-product threshold overrides this)
    global_alert_threshold  NUMERIC(5,2)    NOT NULL DEFAULT 10.00  -- percentage drop to trigger alert
                            CHECK (global_alert_threshold > 0 AND global_alert_threshold <= 100),

    -- notification channels
    email_notifications     BOOLEAN         NOT NULL DEFAULT TRUE,
    push_notifications      BOOLEAN         NOT NULL DEFAULT FALSE,

    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT user_preferences_user_id_unique UNIQUE (user_id)
);




-- ------------------------------------------------------------
-- 3.5  watchlist_items
-- Products a user is monitoring. canonical_product_id links
-- to the BigQuery mart — NOT a local FK (cross-database join
-- happens in the FastAPI service layer).
-- ------------------------------------------------------------

CREATE TABLE watchlist_items (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID            NOT NULL REFERENCES users (id) ON DELETE CASCADE,

    -- BigQuery reference (no FK — cross-database)
    canonical_product_id    VARCHAR(64)     NOT NULL,   -- SHA-256 hash from dbt staging
    product_title           TEXT    NOT NULL,   -- cached at add-time to avoid BQ call
    product_image_url       TEXT,                       -- cached thumbnail
    category                VARCHAR(60),                -- e.g. 'strength_nutrition'
    subcategory             VARCHAR(60),                -- e.g. 'whey_protein'

    -- alert configuration
    alert_threshold_pct     NUMERIC(5,2)                -- NULL = use global_alert_threshold
                            CHECK (alert_threshold_pct IS NULL
                                OR (alert_threshold_pct > 0 AND alert_threshold_pct <= 100)),
    target_price            NUMERIC(12,4)               -- absolute-price floor; NULL = unset
                            CHECK (target_price IS NULL OR target_price > 0),
    alert_enabled           BOOLEAN         NOT NULL DEFAULT TRUE,
    preferred_site          VARCHAR(100),               -- NULL = alert on any site

    -- tracking
    added_at                TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    last_alerted_at         TIMESTAMPTZ,                -- prevents alert spam — checked before firing

    CONSTRAINT watchlist_items_user_product_unique
        UNIQUE (user_id, canonical_product_id)
);




-- ------------------------------------------------------------
-- 3.6  price_alerts
-- Historical log of every alert fired. Drives the unread
-- count badge, notification history, and admin monitoring.
-- Values are snapshotted at alert time — prices keep changing.
-- ------------------------------------------------------------

CREATE TABLE price_alerts (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID            NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    watchlist_item_id       UUID            REFERENCES watchlist_items (id) ON DELETE SET NULL,

    -- product snapshot (denormalised — prices change, history must not)
    canonical_product_id    VARCHAR(64)     NOT NULL,
    product_title           VARCHAR(300)    NOT NULL,
    product_image_url       TEXT,
    site                    VARCHAR(100)    NOT NULL,
    listing_url             TEXT            NOT NULL,

    -- price snapshot
    price_before            NUMERIC(12,4)   NOT NULL,
    price_after             NUMERIC(12,4)   NOT NULL,
    currency                VARCHAR(3)      NOT NULL DEFAULT 'USD',
    drop_pct                NUMERIC(6,2)    NOT NULL,   -- positive = price fell

    -- alert metadata
    alert_type              alert_type      NOT NULL DEFAULT 'price_drop',

    -- read state
    is_read                 BOOLEAN         NOT NULL DEFAULT FALSE,
    triggered_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    read_at                 TIMESTAMPTZ,

    CONSTRAINT price_alerts_drop_pct_positive
        CHECK (drop_pct > 0)
);



-- ------------------------------------------------------------
-- 3.7  compare_sessions
-- Persists user-created comparison selections across page
-- refreshes. Unauthenticated compare state stays in localStorage
-- only — user_id is NOT NULL here (requires login to save).
-- ------------------------------------------------------------

CREATE TABLE compare_sessions (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID            NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    product_ids     VARCHAR(64)[]   NOT NULL                -- array of canonical_product_ids (max 4)
                    CHECK (cardinality(product_ids) BETWEEN 1 AND 4),
    label           VARCHAR(120),                           -- user-defined name e.g. "Whey options March"
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW() + INTERVAL '30 days'
);




-- ------------------------------------------------------------
-- 3.8  email_verification_tokens
-- Short-lived tokens sent to verify a new email address.
-- One active token per user at a time.
-- ------------------------------------------------------------

CREATE TABLE email_verification_tokens (
    id          UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID            NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash  VARCHAR(255)    NOT NULL,
    is_used     BOOLEAN         NOT NULL DEFAULT FALSE,
    expires_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW() + INTERVAL '24 hours',
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT email_verification_tokens_token_hash_unique UNIQUE (token_hash)
);



-- ------------------------------------------------------------
-- 3.9  password_reset_tokens
-- Short-lived tokens for the forgot-password flow.
-- ------------------------------------------------------------

CREATE TABLE password_reset_tokens (
    id          UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID            NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash  VARCHAR(255)    NOT NULL,
    is_used     BOOLEAN         NOT NULL DEFAULT FALSE,
    expires_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW() + INTERVAL '1 hour',
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT password_reset_tokens_token_hash_unique UNIQUE (token_hash)
);



-- ------------------------------------------------------------
-- 3.10  audit_logs
-- Append-only log of all significant user and admin actions.
-- Never updated or deleted — only INSERT allowed.
-- ------------------------------------------------------------

CREATE TABLE audit_logs (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID            REFERENCES users (id) ON DELETE SET NULL, -- NULL for system events
    action          audit_action    NOT NULL,
    entity_type     VARCHAR(50),    -- 'watchlist_item' | 'user' | 'session' | etc.
    entity_id       VARCHAR(100),   -- UUID or canonical_product_id of the affected entity
    ip_address      INET,
    user_agent      TEXT,
    metadata        JSONB,          -- extra context: old/new threshold, ban reason, etc.
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);




-- ============================================================
-- 4. INDEXES
-- Covers all expected query patterns in FastAPI service layer.
-- ============================================================

-- users
CREATE INDEX idx_users_email          ON users (email);
CREATE INDEX idx_users_role           ON users (role);
CREATE INDEX idx_users_is_active      ON users (is_active);
CREATE INDEX idx_users_created_at     ON users (created_at DESC);

-- sessions
CREATE INDEX idx_sessions_user_id     ON sessions (user_id);
CREATE INDEX idx_sessions_token_hash  ON sessions (token_hash);
CREATE INDEX idx_sessions_expires_at  ON sessions (expires_at);
CREATE INDEX idx_sessions_is_revoked  ON sessions (is_revoked) WHERE is_revoked = FALSE;

-- refresh_tokens
CREATE INDEX idx_refresh_tokens_user_id    ON refresh_tokens (user_id);
CREATE INDEX idx_refresh_tokens_session_id ON refresh_tokens (session_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens (token_hash);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens (expires_at);

-- user_preferences
CREATE INDEX idx_user_preferences_user_id ON user_preferences (user_id);

-- watchlist_items
CREATE INDEX idx_watchlist_user_id            ON watchlist_items (user_id);
CREATE INDEX idx_watchlist_canonical_id       ON watchlist_items (canonical_product_id);
CREATE INDEX idx_watchlist_alert_enabled      ON watchlist_items (alert_enabled) WHERE alert_enabled = TRUE;
CREATE INDEX idx_watchlist_last_alerted_at    ON watchlist_items (last_alerted_at);
-- composite: used by the alert-firing query (find all users watching a product)
CREATE INDEX idx_watchlist_alert_lookup
    ON watchlist_items (canonical_product_id, alert_enabled, alert_threshold_pct)
    WHERE alert_enabled = TRUE;

-- price_alerts
CREATE INDEX idx_price_alerts_user_id         ON price_alerts (user_id);
CREATE INDEX idx_price_alerts_watchlist_id    ON price_alerts (watchlist_item_id);
CREATE INDEX idx_price_alerts_canonical_id    ON price_alerts (canonical_product_id);
CREATE INDEX idx_price_alerts_triggered_at    ON price_alerts (triggered_at DESC);
CREATE INDEX idx_price_alerts_unread
    ON price_alerts (user_id, triggered_at DESC)
    WHERE is_read = FALSE;

-- compare_sessions
CREATE INDEX idx_compare_sessions_user_id    ON compare_sessions (user_id);
CREATE INDEX idx_compare_sessions_expires_at ON compare_sessions (expires_at);

-- email_verification_tokens
CREATE INDEX idx_email_verify_user_id     ON email_verification_tokens (user_id);
CREATE INDEX idx_email_verify_token_hash  ON email_verification_tokens (token_hash);

-- password_reset_tokens
CREATE INDEX idx_pwd_reset_user_id     ON password_reset_tokens (user_id);
CREATE INDEX idx_pwd_reset_token_hash  ON password_reset_tokens (token_hash);

-- audit_logs
CREATE INDEX idx_audit_logs_user_id     ON audit_logs (user_id);
CREATE INDEX idx_audit_logs_action      ON audit_logs (action);
CREATE INDEX idx_audit_logs_created_at  ON audit_logs (created_at DESC);
CREATE INDEX idx_audit_logs_entity      ON audit_logs (entity_type, entity_id);


-- ============================================================
-- 5. TRIGGERS
-- ============================================================


-- ------------------------------------------------------------
-- 5.1  auto-update updated_at columns
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER trg_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- ------------------------------------------------------------
-- 5.2  auto-create user_preferences row on user INSERT
-- Every new user gets default preferences immediately.
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION trigger_create_user_preferences()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_preferences (user_id)
    VALUES (NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_create_user_preferences
    AFTER INSERT ON users
    FOR EACH ROW EXECUTE FUNCTION trigger_create_user_preferences();


-- ------------------------------------------------------------
-- 5.3  set read_at when is_read flips to TRUE
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION trigger_set_alert_read_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_read = TRUE AND OLD.is_read = FALSE THEN
        NEW.read_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_price_alerts_read_at
    BEFORE UPDATE OF is_read ON price_alerts
    FOR EACH ROW EXECUTE FUNCTION trigger_set_alert_read_at();


-- ------------------------------------------------------------
-- 5.4  block UPDATE and DELETE on audit_logs (append-only)
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION trigger_block_audit_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs is append-only — UPDATE and DELETE are not permitted.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_logs_no_update
    BEFORE UPDATE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION trigger_block_audit_mutation();

CREATE TRIGGER trg_audit_logs_no_delete
    BEFORE DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION trigger_block_audit_mutation();


-- ============================================================
-- 6. ROW LEVEL SECURITY (RLS)
-- Enable so FastAPI can use a low-privilege connection role
-- that can only see its own user's rows.
-- ============================================================

ALTER TABLE watchlist_items      ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_alerts         ENABLE ROW LEVEL SECURITY;
ALTER TABLE compare_sessions     ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences     ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions             ENABLE ROW LEVEL SECURITY;
ALTER TABLE refresh_tokens       ENABLE ROW LEVEL SECURITY;

-- Application role (used by FastAPI connection pool)
-- CREATE ROLE priceradar_app LOGIN PASSWORD 'change_me';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO priceradar_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO priceradar_app;

-- RLS policies — each user only sees their own rows
-- (Uncomment after creating the priceradar_app role)

-- CREATE POLICY watchlist_own_rows ON watchlist_items
--     USING (user_id = current_setting('app.current_user_id')::UUID);

-- CREATE POLICY alerts_own_rows ON price_alerts
--     USING (user_id = current_setting('app.current_user_id')::UUID);

-- CREATE POLICY compare_own_rows ON compare_sessions
--     USING (user_id = current_setting('app.current_user_id')::UUID);

-- CREATE POLICY preferences_own_rows ON user_preferences
--     USING (user_id = current_setting('app.current_user_id')::UUID);


-- ============================================================
-- 7. UTILITY VIEWS
-- ============================================================


-- Active sessions with user info (admin dashboard)
CREATE VIEW v_active_sessions AS
SELECT
    s.id,
    s.user_id,
    u.email,
    u.role,
    s.ip_address,
    s.user_agent,
    s.created_at,
    s.expires_at
FROM sessions s
JOIN users u ON u.id = s.user_id
WHERE s.is_revoked = FALSE
  AND s.expires_at > NOW();



-- Unread alert count per user (NavBar badge)
CREATE VIEW v_unread_alert_counts AS
SELECT
    user_id,
    COUNT(*) AS unread_count
FROM price_alerts
WHERE is_read = FALSE
GROUP BY user_id;

COMMENT ON VIEW v_unread_alert_counts IS 'Unread alert count per user. Consumed by the navbar badge endpoint.';


-- Watchlist with alert configuration summary (watchlist page)
CREATE VIEW v_watchlist_summary AS
SELECT
    w.id,
    w.user_id,
    w.canonical_product_id,
    w.product_title,
    w.product_image_url,
    w.category,
    w.subcategory,
    w.alert_enabled,
    w.preferred_site,
    w.target_price,
    COALESCE(w.alert_threshold_pct, p.global_alert_threshold) AS effective_threshold,
    w.added_at,
    w.last_alerted_at,
    COUNT(a.id) AS total_alerts_fired
FROM watchlist_items w
JOIN user_preferences p ON p.user_id = w.user_id
LEFT JOIN price_alerts a ON a.watchlist_item_id = w.id
GROUP BY w.id, p.global_alert_threshold;


-- Watchlist rows with per-item unread alert count.
-- Single query backs the watchlist page AND the navbar badge
-- (SUM(unread_alert_count) per user).
CREATE VIEW v_watchlist_with_unread AS
SELECT
    w.id,
    w.user_id,
    w.canonical_product_id,
    w.product_title,
    w.product_image_url,
    w.category,
    w.subcategory,
    w.alert_threshold_pct,
    w.target_price,
    w.alert_enabled,
    w.preferred_site,
    w.added_at,
    w.last_alerted_at,
    COALESCE(w.alert_threshold_pct, p.global_alert_threshold) AS effective_threshold,
    COUNT(a.id) FILTER (WHERE a.is_read = FALSE) AS unread_alert_count,
    COUNT(a.id)                                   AS total_alerts_fired
FROM watchlist_items w
JOIN user_preferences p ON p.user_id = w.user_id
LEFT JOIN price_alerts a ON a.watchlist_item_id = w.id
GROUP BY w.id, p.global_alert_threshold;

COMMENT ON VIEW v_watchlist_with_unread IS
    'Watchlist rows with per-item unread alert count. Drives the watchlist page and the navbar badge (SUM(unread_alert_count) per user).';



-- ============================================================
-- 8. CLEANUP FUNCTION
-- Called by Airflow nightly DAG to remove expired rows.
-- ============================================================

CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS void AS $$
BEGIN
    -- Remove expired sessions (cascade deletes their refresh tokens)
    DELETE FROM sessions
    WHERE expires_at < NOW() - INTERVAL '7 days';

    -- Remove expired refresh tokens not already cascade-deleted
    DELETE FROM refresh_tokens
    WHERE expires_at < NOW() - INTERVAL '7 days';

    -- Remove expired email verification tokens
    DELETE FROM email_verification_tokens
    WHERE expires_at < NOW() - INTERVAL '2 days';

    -- Remove expired password reset tokens
    DELETE FROM password_reset_tokens
    WHERE expires_at < NOW() - INTERVAL '2 days';

    -- Remove expired compare sessions
    DELETE FROM compare_sessions
    WHERE expires_at < NOW();

    RAISE NOTICE 'cleanup_expired_tokens completed at %', NOW();
END;
$$ LANGUAGE plpgsql;




-- ============================================================
-- END OF SCHEMA
-- ============================================================