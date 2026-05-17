/**
 * Statistics DTOs — mirror of `backend/app/models/stats.py`.
 */
import { BrandTier, PriceTrend, SupplementCategory } from './enums';

export interface ProductStats {
  canonical_product_id: string;
  product_name: string;
  period_days: number;

  mean_price: number;
  median_price: number;
  std_deviation: number;
  min_price: number;
  max_price: number;
  coefficient_of_variation: number;

  price_trend: PriceTrend;
  velocity_per_day: number;
  is_volatile: boolean;

  estimated_floor_30d?: number | null;
  out_of_stock_probability?: number | null;

  total_observations: number;
  sites_tracked: number;
}

export interface BrandRanking {
  brand_name: string;
  brand_tier: BrandTier;
  category: SupplementCategory;
  avg_price_usd: number;
  avg_price_per_serving?: number | null;
  avg_rating: number;
  total_products: number;
  sites_present: string[];
  rank: number;
}

export interface BrandRankingsResponse {
  category: SupplementCategory;
  rankings: BrandRanking[];
  generated_at: string;
}
