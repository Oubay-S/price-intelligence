# modules/iam/outputs.tf

output "composer_service_account_email" {
  description = "Email du service account Composer"
  value       = google_service_account.composer.email
}

output "backend_service_account_email" {
  description = "Email du service account Backend"
  value       = google_service_account.backend.email
}

output "dbt_service_account_email" {
  description = "Email du service account dbt"
  value       = google_service_account.dbt.email
}

output "cicd_service_account_email" {
  description = "Email du service account CI/CD"
  value       = google_service_account.cicd.email
}

output "cicd_service_account_key" {
  description = "Clé du service account CI/CD (pour GitHub Actions)"
  value       = google_service_account_key.cicd_key.private_key
  sensitive   = true
}

output "artifact_registry_url" {
  description = "URL du registre d'images Docker"
  value       = "${google_artifact_registry_repository.docker.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}
