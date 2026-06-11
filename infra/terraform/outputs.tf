# =============================================================
# outputs.tf — Valeurs de sortie après déploiement
# =============================================================
# Ces valeurs sont affichées après `terraform apply` et peuvent
# être utilisées pour configurer les autres services.
# =============================================================

# ─── URLS D'ACCÈS ───

output "frontend_url" {
  description = "🌐 URL d'accès au frontend Angular"
  value       = module.frontend_cdn.frontend_url
}

output "backend_url" {
  description = "🔌 URL de l'API Backend (Cloud Run)"
  value       = module.cloud_run.service_url
}

output "airflow_url" {
  description = "🔄 URL du webserver Airflow (Cloud Composer)"
  value       = module.composer.airflow_uri
}

# ─── INFRASTRUCTURE DATA ───

output "bigtable_instance" {
  description = "📊 Nom de l'instance Bigtable"
  value       = module.bigtable.instance_name
}

output "bigquery_dataset" {
  description = "📈 ID du dataset BigQuery"
  value       = module.bigquery.dataset_id
}

output "cloudsql_airflow_ip" {
  description = "🗄️ IP privée Cloud SQL Airflow"
  value       = module.cloud_sql.airflow_private_ip
  sensitive   = true
}

output "cloudsql_app_ip" {
  description = "🗄️ IP privée Cloud SQL App"
  value       = module.cloud_sql.app_private_ip
  sensitive   = true
}

output "redis_url" {
  description = "⚡ URL de connexion Redis (Memorystore)"
  value       = module.redis.redis_url
  sensitive   = true
}

# ─── CI/CD ───

output "artifact_registry_url" {
  description = "🐳 URL du registre d'images Docker"
  value       = module.iam.artifact_registry_url
}

output "dag_gcs_prefix" {
  description = "📂 Chemin GCS pour uploader les DAGs"
  value       = module.composer.dag_gcs_prefix
}

# ─── RÉSEAU ───

output "cdn_ip_address" {
  description = "🌍 Adresse IP publique du Load Balancer"
  value       = module.frontend_cdn.cdn_ip_address
}

output "vpc_name" {
  description = "🔒 Nom du VPC"
  value       = module.networking.network_name
}
