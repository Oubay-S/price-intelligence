-- ============================================================
-- Migration 001 — watchlist target_price + combined unread view
-- ============================================================
-- Apply against an already-initialised PriceIntelligence DB:
--   docker-compose exec postgres-app \
--     psql -U postgres -d PriceIntelligence \
--     -f /docker-entrypoint-initdb.d/migrations/001_watchlist_target_price_and_views.sql
--
-- Or from the host with the venv:
--   psql "$DATABASE_URL" -f backend/sql/migrations/001_watchlist_target_price_and_views.sql
--
-- Idempotent: safe to re-run.
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1. watchlist_items.target_price
-- Absolute-price alert. Either alert_threshold_pct (relative
-- drop) or target_price (price floor) may trigger an alert.
-- NULL = not configured for this item.
-- ------------------------------------------------------------

ALTER TABLE watchlist_items
    ADD COLUMN IF NOT EXISTS target_price NUMERIC(12,4)
        CHECK (target_price IS NULL OR target_price > 0);


-- ------------------------------------------------------------
-- 2. v_watchlist_summary — refresh to include target_price
-- ------------------------------------------------------------

DROP VIEW IF EXISTS v_watchlist_summary;
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


-- ------------------------------------------------------------
-- 3. v_watchlist_with_unread — single source for the watchlist
-- page (rows + per-row unread counts) and the navbar badge
-- (sum of unread_alert_count across the user's rows).
-- ------------------------------------------------------------

DROP VIEW IF EXISTS v_watchlist_with_unread;
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

COMMIT;
