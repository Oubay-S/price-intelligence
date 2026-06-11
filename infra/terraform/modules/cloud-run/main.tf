# =============================================================
# modules/cloud-run/main.tf — Cloud Run (Backend FastAPI)
# =============================================================
# Équivalent GCP du service docker-compose : backend
# Déploie l'API FastAPI en tant que service serverless
# avec autoscaling, VPC connector, et variables d'environnement.
# =============================================================

resource "google_cloud_run_v2_service" "backend" {
  name     = "price-intel-backend"
  location = var.region
  project  = var.project_id

  template {
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    # Timeout de requête (5 minutes pour les scraping longs)
    timeout = "300s"

    # Service account dédié
    service_account = var.service_account_email

    # Connecteur VPC pour accéder à Cloud SQL et Redis
    vpc_access {
      connector = var.vpc_connector_id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = var.backend_image

      # Ressources (équivalent des limits docker-compose)
      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
        cpu_idle          = true   # Scale to zero quand pas de trafic
        startup_cpu_boost = true   # Boost au démarrage pour charger l'app
      }

      # Port (identique au docker-compose : 8000)
      ports {
        container_port = 8000
      }

      # ─── Variables d'environnement ───
      # Reproduit exactement les env du docker-compose backend

      # Base de données applicative
      env {
        name  = "DATABASE_URL"
        value = var.database_url
      }

      # Redis
      env {
        name  = "REDIS_URL"
        value = var.redis_url
      }

      # GCP
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      env {
        name  = "BIGTABLE_INSTANCE_ID"
        value = var.bigtable_instance_name
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      # Frontend URL (pour les emails de vérification)
      env {
        name  = "FRONTEND_URL"
        value = var.frontend_url
      }

      # Secret JWT (depuis Secret Manager)
      env {
        name = "SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.jwt_secret.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "ALGORITHM"
        value = "HS256"
      }

      # Health check — Liveness probe (identique au docker-compose)
      liveness_probe {
        http_get {
          path = "/health/live"
          port = 8000
        }
        initial_delay_seconds = 10
        period_seconds        = 30
        timeout_seconds       = 5
        failure_threshold     = 3
      }

      # Startup probe
      startup_probe {
        http_get {
          path = "/health/live"
          port = 8000
        }
        initial_delay_seconds = 5
        period_seconds        = 5
        timeout_seconds       = 5
        failure_threshold     = 10
      }
    }
  }

  # Trafic — 100% vers la dernière révision
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  labels = {
    component   = "app-layer"
    service     = "backend"
    environment = var.environment
  }
}

# ─────────────────────────────────────────────
# SECRET MANAGER — JWT Secret Key
# ─────────────────────────────────────────────

resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "price-intel-jwt-secret"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    component = "security"
  }
}

resource "google_secret_manager_secret_version" "jwt_secret_value" {
  secret      = google_secret_manager_secret.jwt_secret.id
  secret_data = var.jwt_secret
}

# ─────────────────────────────────────────────
# IAM — Autoriser l'accès public (ou restreint) au backend
# ─────────────────────────────────────────────

# En dev : accès public pour les tests
# En prod : accès restreint via Load Balancer + IAP
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  count    = var.environment == "dev" ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
