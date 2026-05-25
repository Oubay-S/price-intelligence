/**
 * Alert DTOs — mirror of `backend/app/models/alerts.py`.
 */
import { AlertType, SupplementCategory } from './enums';

/** Price drop detected in the mart — `GET /prices/drops`, also WS-broadcast. */
export interface PriceDropAlert {
  canonical_product_id: string;
  product_name: string;
  image_url?: string | null;
  site: string;
  listing_url: string;
  category: SupplementCategory;

  price_before: number;
  price_after: number;
  currency: string;
  drop_pct: number;
  alert_type: AlertType;

  scraped_at: string;
  detected_at: string;

  price_per_serving_after?: number | null;
  price_per_kg_after?: number | null;
}

export interface AlertsResponse {
  alerts: PriceDropAlert[];
  count: number;
  threshold_pct: number;
  generated_at: string;
}

/** Per-user stored alert — `price_alerts` table. */
export interface UserAlertRecord {
  id: string;
  canonical_product_id: string;
  product_name: string;
  product_image_url?: string | null;
  site: string;
  listing_url: string;
  price_before: number;
  price_after: number;
  drop_pct: number;
  alert_type: AlertType;
  is_read: boolean;
  triggered_at: string;
  read_at?: string | null;
}

export interface UnreadAlertCount {
  user_id: string;
  unread_count: number;
}
