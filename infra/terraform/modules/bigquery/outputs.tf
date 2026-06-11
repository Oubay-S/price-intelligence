# modules/bigquery/outputs.tf

output "dataset_id" {
  description = "ID du dataset BigQuery"
  value       = google_bigquery_dataset.main.dataset_id
}

output "raw_prices_table_id" {
  description = "ID de la table raw_prices"
  value       = google_bigquery_table.raw_prices.table_id
}

output "analytics_table_id" {
  description = "ID de la table price_analytics"
  value       = google_bigquery_table.price_analytics.table_id
}
