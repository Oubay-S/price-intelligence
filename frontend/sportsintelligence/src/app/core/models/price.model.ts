/**
 * Price-history + cross-site comparison DTOs.
 * Mirror of `backend/app/models/price.py`.
 */
import { SupplementCategory } from './enums';
import { EquipmentInfo, NutritionInfo } from './product.model';

export interface PricePoint {
  price_usd: number;
  site: string;
  scraped_at: string;
  in_stock: boolean;
  discount_pct?: number | null;
}

export interface PriceHistory {
  canonical_product_id: string;
  product_name: string;
  points: PricePoint[];
  min_price: number;
  max_price: number;
  avg_price: number;
  median_price: number;
  floor_price_30d?: number | null;
}

export interface SitePriceSnapshot {
  site: string;
  price_usd: number;
  original_price?: number | null;
  discount_pct?: number | null;
  listing_url: string;
  in_stock: boolean;
  last_seen: string;
  shipping_cost?: number | null;
  landed_cost?: number | null;
}

export interface ProductComparison {
  canonical_product_id: string;
  product_name: string;
  image_url?: string | null;
  category: SupplementCategory;
  nutrition?: NutritionInfo | null;
  equipment?: EquipmentInfo | null;
  sites_prices: SitePriceSnapshot[];
  best_site: string;
  worst_site: string;
  price_gap_pct: number;
  tags: string[];
}

export interface CompareResponse {
  products: ProductComparison[];
  generated_at: string;
}
