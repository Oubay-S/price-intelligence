/**
 * Query-param shapes — mirror of `backend/app/models/filters.py`.
 * Passed to ApiService methods and serialised into HttpParams.
 */
import { BrandTier, SortOption, SupplementCategory } from './enums';

/** Query params for `GET /products`. */
export interface ProductFilterParams {
  category?: SupplementCategory;
  subcategory?: string;
  site?: string[];
  brand?: string;
  min_price?: number;
  max_price?: number;
  in_stock?: boolean;
  has_discount?: boolean;
  brand_tier?: BrandTier;
  tags?: string[];
  sort?: SortOption;
  page?: number;
  limit?: number;
}

/** Query params for `GET /prices/{id}/history`. */
export interface PriceHistoryParams {
  start_date?: string;
  end_date?: string;
  site?: string;
  period?: '7d' | '30d' | '90d' | 'all';
}

/** Query params for `GET /prices/drops`. */
export interface PriceDropParams {
  threshold?: number;
  category?: SupplementCategory;
  site?: string;
  limit?: number;
}
