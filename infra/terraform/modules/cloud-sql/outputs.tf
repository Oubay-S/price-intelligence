# modules/cloud-sql/outputs.tf

output "airflow_instance_name" {
  description = "Nom de l'instance Cloud SQL Airflow"
  value       = google_sql_database_instance.airflow.name
}

output "airflow_connection_name" {
  description = "Connection name de l'instance Airflow (pour Cloud SQL Proxy)"
  value       = google_sql_database_instance.airflow.connection_name
}

output "airflow_private_ip" {
  description = "IP privée de l'instance Cloud SQL Airflow"
  value       = google_sql_database_instance.airflow.private_ip_address
}

output "app_instance_name" {
  description = "Nom de l'instance Cloud SQL App"
  value       = google_sql_database_instance.app.name
}

output "app_connection_name" {
  description = "Connection name de l'instance App (pour Cloud SQL Proxy)"
  value       = google_sql_database_instance.app.connection_name
}

output "app_private_ip" {
  description = "IP privée de l'instance Cloud SQL App"
  value       = google_sql_database_instance.app.private_ip_address
}
