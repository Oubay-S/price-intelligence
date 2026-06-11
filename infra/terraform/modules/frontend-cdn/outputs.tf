# modules/frontend-cdn/outputs.tf

output "bucket_name" {
  description = "Nom du bucket GCS frontend"
  value       = google_storage_bucket.frontend.name
}

output "bucket_url" {
  description = "URL du bucket"
  value       = google_storage_bucket.frontend.url
}

output "cdn_ip_address" {
  description = "Adresse IP publique du Load Balancer"
  value       = google_compute_global_address.frontend.address
}

output "frontend_url" {
  description = "URL d'accès au frontend"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "http://${google_compute_global_address.frontend.address}"
}
