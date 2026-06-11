# modules/networking/outputs.tf

output "network_id" {
  description = "ID du VPC principal"
  value       = google_compute_network.main.id
}

output "network_name" {
  description = "Nom du VPC principal"
  value       = google_compute_network.main.name
}

output "data_subnet_id" {
  description = "ID du sous-réseau data"
  value       = google_compute_subnetwork.data.id
}

output "data_subnet_name" {
  description = "Nom du sous-réseau data"
  value       = google_compute_subnetwork.data.name
}

output "app_subnet_id" {
  description = "ID du sous-réseau app"
  value       = google_compute_subnetwork.app.id
}

output "vpc_connector_id" {
  description = "ID du connecteur VPC serverless (pour Cloud Run)"
  value       = google_vpc_access_connector.serverless.id
}

output "private_vpc_connection" {
  description = "Connexion VPC privée (pour Cloud SQL)"
  value       = google_service_networking_connection.private_vpc
}
