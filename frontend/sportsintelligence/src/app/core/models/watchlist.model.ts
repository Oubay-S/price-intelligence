/**
 * Watchlist DTOs — mirror of `backend/app/models/watchlist.py`.
 */

/** Body for POST /watchlist/{product_id}. */
export interface WatchlistAdd {
  alert_threshold_pct?: number | null;
  target_price?: number | null;
  alert_enabled: boolean;
  preferred_site?: string | null;
}

/** Body for PATCH /watchlist/{product_id} — all fields optional. */
export interface WatchlistUpdate {
  alert_threshold_pct?: number | null;
  target_price?: number | null;
  alert_enabled?: boolean | null;
  preferred_site?: string | null;
}

export interface WatchlistItemResponse {
  id: string;
  canonical_product_id: string;
  product_title: string;
  product_image_url?: string | null;
  category?: string | null;
  subcategory?: string | null;

  alert_threshold_pct?: number | null;
  target_price?: number | null;
  effective_threshold: number;
  alert_enabled: boolean;
  preferred_site?: string | null;

  added_at: string;
  last_alerted_at?: string | null;

  unread_alert_count: number;
  total_alerts_fired: number;

  current_price?: number | null;
  currency?: string | null;
  in_stock?: boolean | null;
  site?: string | null;
  listing_url?: string | null;
}

export interface WatchlistListResponse {
  items: WatchlistItemResponse[];
  total_count: number;
  page: number;
  limit: number;
  unread_total: number;
}
