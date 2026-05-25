/**
 * Product catalog DTOs — mirror of `backend/app/models/product.py`.
 */
import { BrandTier, PriceTrend, SupplementCategory } from './enums';

export interface PriceInfo {
  current: number;
  original?: number | null;
  currency_raw: string;
  per_serving?: number | null;
  per_100g?: number | null;
  per_kg?: number | null;
  discount_pct?: number | null;
  trend: PriceTrend;
  velocity_per_day?: number | null;
}

export interface NutritionInfo {
  protein_g?: number | null;
  calories?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
  sugar_g?: number | null;
  sodium_mg?: number | null;
  caffeine_mg?: number | null;
  creatine_type?: string | null;
  bcaa_ratio?: string | null;
  serving_size_g?: number | null;
  total_servings?: number | null;
  total_weight_g?: number | null;
}

export interface EquipmentInfo {
  weight_kg?: number | null;
  max_load_kg?: number | null;
  material?: string | null;
  adjustable?: boolean | null;
  size?: string | null;
  gender?: string | null;
  oz_weight?: number | null;
  glove_type?: string | null;
  stud_type?: string | null;
  racket_weight_g?: number | null;
  grip_size?: string | null;
  drop_mm?: number | null;
  shoe_weight_g?: number | null;
  stack_height_mm?: number | null;
  carbon_plate?: boolean | null;
  battery_life_h?: number | null;
  resistance_level?: string | null;
}

export interface RatingsInfo {
  score: number;
  count: number;
  composite_score?: number | null;
}

export interface BrandInfo {
  brand_id: string;
  name: string;
  logo_url?: string | null;
  country?: string | null;
  tier: BrandTier;
  verified: boolean;
}

/** Full product shape returned by `GET /products/{id}`. */
export interface ProductResponse {
  canonical_product_id: string;
  name: string;
  site: string;
  listing_url: string;
  category: SupplementCategory;
  subcategory?: string | null;
  brand_raw: string;
  in_stock: boolean;

  brand?: BrandInfo | null;
  flavour?: string | null;
  image_url?: string | null;

  pricing: PriceInfo;
  nutrition?: NutritionInfo | null;
  equipment?: EquipmentInfo | null;
  ratings?: RatingsInfo | null;

  certifications: string[];
  tags: string[];
  purpose_tags: string[];
  brand_tier: BrandTier;

  scraped_at: string;
  data_quality_score?: number | null;
}

/** Trending product — `GET /products/trending`. */
export interface TrendingProduct {
  canonical_product_id: string;
  product_name: string;
  image_url?: string | null;
  category: SupplementCategory;
  brand_raw: string;
  brand_tier: BrandTier;
  current_price: number;
  drop_pct?: number | null;
  price_trend: PriceTrend;
  best_site: string;
  listing_url: string;
  rating_score?: number | null;
  tags: string[];
  rank: number;
}

export interface TrendingResponse {
  products: TrendingProduct[];
  period: string;
  generated_at: string;
}

/** Leaner shape — `GET /products/search`. */
export interface SearchResult {
  canonical_product_id: string;
  product_name: string;
  brand_raw: string;
  category: SupplementCategory;
  image_url?: string | null;
  current_price: number;
  discount_pct?: number | null;
  price_trend: PriceTrend;
  rating_score?: number | null;
  best_site: string;
  listing_url: string;
  tags: string[];
  relevance_score?: number | null;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
  total: number;
  generated_at: string;
}

/** Paginated list — `GET /products`. */
export interface PaginatedProducts {
  items: ProductResponse[];
  total_count: number;
  page: number;
  limit: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}
