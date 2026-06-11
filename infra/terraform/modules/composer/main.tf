# =============================================================
# modules/composer/main.tf — Cloud Composer v2 (Airflow managé)
# =============================================================
# Équivalent GCP des services docker-compose :
#   - airflow-webserver
#   - airflow-scheduler
#   - airflow-init
#
# Cloud Composer gère automatiquement :
#   ✅ Le webserver, le scheduler, les workers
#   ✅ La base de données metadata (plus besoin de postgres Airflow)
#   ✅ Les mises à jour et le scaling
# =============================================================

resource "google_composer_environment" "main" {
  name    = "price-intel-composer"
  region  = var.region
  project = var.project_id

  config {
    # Taille de l'environnement
    environment_size = var.environment_size

    software_config {
      image_version = var.image_version

      # Packages Python supplémentaires (même que docker-compose _PIP_ADDITIONAL_REQUIREMENTS)
      pypi_packages = {
        "google-cloud-bigtable"    = ">=2.0.0"
        "google-cloud-bigquery"    = ">=3.0.0"
        "beautifulsoup4"           = ">=4.12.0"
        "requests"                 = ">=2.31.0"
        "selenium"                 = ">=4.15.0"
        "webdriver-manager"        = ">=4.0.0"
        "undetected-chromedriver"  = ">=3.5.0"
        "dbt-bigquery"             = ">=1.8.0"
      }

      # Variables d'environnement Airflow (même que docker-compose)
      env_variables = {
        GOOGLE_CLOUD_PROJECT  = var.project_id
        BIGTABLE_INSTANCE_ID  = var.bigtable_instance_name
        GCP_PROJECT_ID        = var.project_id
        AIRFLOW__CORE__LOAD_EXAMPLES = "false"
      }

      # Configuration Airflow (même que docker-compose)
      airflow_config_overrides = {
        "core-dags_are_paused_at_creation" = "true"
        "core-load_examples"               = "false"
        "api-auth_backends"                = "airflow.api.auth.backend.basic_auth"
      }
    }

    node_config {
      network         = var.network_id
      subnetwork      = var.data_subnet_id
      service_account = var.service_account_email

      ip_allocation_policy {
        cluster_secondary_range_name  = "composer-pods"
        services_secondary_range_name = "composer-services"
      }
    }

    # Configuration du webserver
    workloads_config {
      scheduler {
        cpu        = 1
        memory_gb  = 2
        storage_gb = 1
        count      = 1
      }

      web_server {
        cpu        = 1
        memory_gb  = 2
        storage_gb = 1
      }

      worker {
        cpu        = 1
        memory_gb  = 2
        storage_gb = 1
        min_count  = 1
        max_count  = 3
      }
    }

    # Accès privé uniquement (sécurité)
    private_environment_config {
      enable_private_endpoint = false # true en prod (accès uniquement via VPN)
    }
  }

  labels = {
    component   = "orchestration"
    service     = "composer"
    environment = var.environment
  }
}
