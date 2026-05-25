/**
 * Domain enums — mirror of `backend/app/models/enums.py`.
 *
 * Modelled as string-literal union types plus `const` value arrays so the
 * frontend can both type-check and iterate (e.g. to render filter options).
 */

// Only categories that exist in the scraped BigQuery data. Mirror of
// backend SupplementCategory enum; the raw↔enum bridge is in
// backend services/bigquery.py. Dropped nutrition/endurance/wearables/
// combat-protection — they returned no products.
export const SUPPLEMENT_CATEGORIES = [
  'strength_home_gym',
  'team_football',
  'team_basketball',
  'team_volleyball',
  'team_racket',
  'combat_boxing_mma',
] as const;
export type SupplementCategory = (typeof SUPPLEMENT_CATEGORIES)[number];

export const NUTRITION_SUBCATEGORIES = [
  'whey_protein',
  'creatine',
  'pre_workout',
  'amino_acids',
  'mass_gainer',
  'vitamins',
  'energy_gel',
  'electrolytes',
] as const;
export type NutritionSubcategory = (typeof NUTRITION_SUBCATEGORIES)[number];

export type PriceTrend = 'rising' | 'falling' | 'stable';

export type BrandTier = 'premium' | 'mid' | 'budget';

export type AlertType = 'price_drop' | 'back_in_stock' | 'buy_soon' | 'price_rise';

export const SORT_OPTIONS = [
  'scraped_at_desc',
  'price_asc',
  'price_desc',
  'rating_desc',
  'discount_desc',
  'price_per_serving_asc',
] as const;
export type SortOption = (typeof SORT_OPTIONS)[number];

/** Human-readable labels for the category enum — used in filter UIs. */
export const CATEGORY_LABELS: Record<SupplementCategory, string> = {
  strength_home_gym: 'Gym',
  team_football: 'Football',
  team_basketball: 'Basketball',
  team_volleyball: 'Volleyball',
  team_racket: 'Racket Sports',
  combat_boxing_mma: 'Combat Sports',
};

export const SORT_LABELS: Record<SortOption, string> = {
  scraped_at_desc: 'Newest first',
  price_asc: 'Lowest price',
  price_desc: 'Highest price',
  rating_desc: 'Highest rated',
  discount_desc: 'Biggest discount',
  price_per_serving_asc: 'Best value / serving',
};
