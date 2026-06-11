# modules/composer/outputs.tf

output "environment_id" {
  description = "ID de l'environnement Composer"
  value       = google_composer_environment.main.id
}

output "airflow_uri" {
  description = "URL du webserver Airflow"
  value       = google_composer_environment.main.config[0].airflow_uri
}

output "dag_gcs_prefix" {
  description = "Préfixe GCS pour les DAGs"
  value       = google_composer_environment.main.config[0].dag_gcs_prefix
}

output "gke_cluster" {
  description = "Cluster GKE utilisé par Composer"
  value       = google_composer_environment.main.config[0].gke_cluster
}
