/**
 * Analytics dashboard models — mirror the FastAPI `/analytics/*` responses,
 * which in turn mirror the Data Analyst's dashboard JSON exports.
 *
 * Every list endpoint wraps its rows in an envelope with `generated_at` so the
 * UI can show how fresh the analysis is.
 */

export interface AnalyticsEnvelope<T> {
  generated_at: string | null;
  data: T;
}

export interface AnalyticsKpis {
  total_products: number;
  total_stores: number;
  total_categories: number;
  average_price: number;
  median_price: number;
  minimum_price: number;
  maximum_price: number;
  average_discount: number;
  first_scrape: string | null;
  last_scrape: string | null;
}

export interface StorePriceStat {
  store: string;
  products: number;
  average_price: number;
  median_price: number;
  min_price: number;
  max_price: number;
  std_price: number;
}

export interface CategoryPriceStat {
  category: string;
  products: number;
  average_price: number;
  median_price: number;
  min_price: number;
  max_price: number;
  std_price: number;
}

export interface TimeSeriesPoint {
  scraped_date: string;
  store: string;
  products: number;
  average_price: number;
  median_price: number;
}

export interface HeatmapCell {
  store: string;
  category: string;
  products: number;
  median_price: number;
  average_price: number;
}

export interface TopDiscount {
  store: string;
  category: string;
  name: string;
  price: number;
  discount: number;
  stars: number;
}

export interface Recommendation {
  priorite: string;
  recommandation: string;
  justification: string;
}

export type KpisResponse = AnalyticsEnvelope<AnalyticsKpis>;
export type PriceByStoreResponse = AnalyticsEnvelope<StorePriceStat[]>;
export type PriceByCategoryResponse = AnalyticsEnvelope<CategoryPriceStat[]>;
export type TimeSeriesResponse = AnalyticsEnvelope<TimeSeriesPoint[]>;
export type HeatmapResponse = AnalyticsEnvelope<HeatmapCell[]>;
export type TopDiscountsResponse = AnalyticsEnvelope<TopDiscount[]>;
export type RecommendationsResponse = AnalyticsEnvelope<Recommendation[]>;
