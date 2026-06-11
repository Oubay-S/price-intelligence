# modules/bigtable/outputs.tf

output "instance_id" {
  description = "ID de l'instance Bigtable"
  value       = google_bigtable_instance.main.id
}

output "instance_name" {
  description = "Nom de l'instance Bigtable"
  value       = google_bigtable_instance.main.name
}

output "prices_table_name" {
  description = "Nom de la table des prix"
  value       = google_bigtable_table.prices.name
}

output "price_history_table_name" {
  description = "Nom de la table d'historique"
  value       = google_bigtable_table.price_history.name
}
