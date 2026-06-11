# modules/cloud-run/outputs.tf

output "service_url" {
  description = "URL publique du service Cloud Run"
  value       = google_cloud_run_v2_service.backend.uri
}

output "service_name" {
  description = "Nom du service Cloud Run"
  value       = google_cloud_run_v2_service.backend.name
}
