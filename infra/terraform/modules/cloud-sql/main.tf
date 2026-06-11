# =============================================================
# modules/cloud-sql/main.tf — Cloud SQL for PostgreSQL
# =============================================================
# Reproduit les 2 bases PostgreSQL du docker-compose :
#   1. postgres (port 5433) → metadata Airflow
#   2. postgres-app (port 5432) → données applicatives
#
# En GCP, ces deux bases sont hébergées sur des instances
# Cloud SQL séparées pour l'isolation et la sécurité.
# =============================================================

# Suffixe aléatoire pour éviter les conflits de noms
# (Cloud SQL garde les noms pendant 7 jours après suppression)
resource "random_id" "db_suffix" {
  byte_length = 4
}

# ─────────────────────────────────────────────
# INSTANCE 1 : Cloud SQL pour Airflow (metadata)
# Équivalent docker-compose : service "postgres"
# ─────────────────────────────────────────────

resource "google_sql_database_instance" "airflow" {
  name             = "price-intel-airflow-${random_id.db_suffix.hex}"
  database_version = "POSTGRES_15"
  region           = var.region

  deletion_protection = var.environment == "prod" ? true : false

  settings {
    tier              = var.tier
    disk_size         = var.disk_size
    disk_autoresize   = true
    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = var.network_id
      enable_private_path_for_google_cloud_services = true
    }

    backup_configuration {
      enabled                        = var.environment == "prod" ? true : false
      point_in_time_recovery_enabled = var.environment == "prod" ? true : false
      start_time                     = "03:00"
      location                       = var.region

      backup_retention_settings {
        retained_backups = 7
      }
    }

    maintenance_window {
      day          = 7 # Dimanche
      hour         = 4 # 04h00 UTC
      update_track = "stable"
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }

    user_labels = {
      component = "airflow-metadata"
      service   = "cloud-sql"
    }
  }

  depends_on = [var.private_vpc_connection]
}

resource "google_sql_database" "airflow_db" {
  name     = var.airflow_db_name
  instance = google_sql_database_instance.airflow.name
}

resource "google_sql_user" "airflow_user" {
  name     = var.airflow_db_user
  instance = google_sql_database_instance.airflow.name
  password = var.airflow_db_password
}

# ─────────────────────────────────────────────
# INSTANCE 2 : Cloud SQL pour l'Application (users, watchlist, alerts)
# Équivalent docker-compose : service "postgres-app"
# ─────────────────────────────────────────────

resource "google_sql_database_instance" "app" {
  name             = "price-intel-app-${random_id.db_suffix.hex}"
  database_version = "POSTGRES_15"
  region           = var.region

  deletion_protection = var.environment == "prod" ? true : false

  settings {
    tier              = var.tier
    disk_size         = var.disk_size
    disk_autoresize   = true
    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = var.network_id
      enable_private_path_for_google_cloud_services = true
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = var.environment == "prod" ? true : false
      start_time                     = "04:00"
      location                       = var.region

      backup_retention_settings {
        retained_backups = 7
      }
    }

    database_flags {
      name  = "max_connections"
      value = "200"
    }

    user_labels = {
      component = "app-database"
      service   = "cloud-sql"
    }
  }

  depends_on = [var.private_vpc_connection]
}

resource "google_sql_database" "app_db" {
  name     = var.app_db_name
  instance = google_sql_database_instance.app.name
}

resource "google_sql_user" "app_user" {
  name     = var.app_db_user
  instance = google_sql_database_instance.app.name
  password = var.app_db_password
}
