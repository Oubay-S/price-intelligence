/**
 * WebSocket message shapes.
 *
 * The backend fans out two channels:
 *  - `/ws/live-prices`     — public, every price event
 *  - `/ws/alerts/{userId}` — per-user, gated by an access JWT query param
 *
 * Both deliver JSON text frames. The exact payload is whatever
 * `alert_service.process_price_event` broadcasts; `PriceEventBroadcast`
 * is the expected shape.
 */
import { PriceDropAlert } from './alert.model';

export interface PriceEventBroadcast {
  canonical_product_id: string;
  product_name: string;
  site: string;
  price_before?: number | null;
  price_after: number;
  currency: string;
  drop_pct?: number | null;
  in_stock: boolean;
  scraped_at: string;
}

/** Connection lifecycle state surfaced by WebSocketService. */
export type WsStatus = 'connecting' | 'open' | 'closed' | 'error';

/** Discriminated wrapper the service emits to subscribers. */
export type WsMessage =
  | { kind: 'status'; status: WsStatus }
  | { kind: 'price-event'; data: PriceEventBroadcast }
  | { kind: 'alert'; data: PriceDropAlert }
  | { kind: 'raw'; data: unknown };
