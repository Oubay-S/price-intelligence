# =============================================================
# modules/iam/main.tf — Service Accounts & IAM Roles
# =============================================================
# Principe du moindre privilège : chaque composant dispose
# d'un service account dédié avec uniquement les rôles nécessaires.
# =============================================================

# ─────────────────────────────────────────────
# SERVICE ACCOUNT — Airflow / Cloud Composer
# Rôle : orchestrer les DAGs, accéder à Bigtable et BigQuery
# ─────────────────────────────────────────────

resource "google_service_account" "composer" {
  account_id   = "price-intel-composer"
  display_name = "Price Intelligence — Cloud Composer"
  description  = "Service account pour l'orchestration Airflow (DAGs, scraping, export)"
  project      = var.project_id
}

resource "google_project_iam_member" "composer_roles" {
  for_each = toset([
    "roles/composer.worker",              # Exécuter les DAGs
    "roles/bigtable.user",                # Lire/écrire dans Bigtable
    "roles/bigquery.dataEditor",          # Écrire dans BigQuery
    "roles/bigquery.jobUser",             # Lancer des jobs BigQuery
    "roles/storage.objectViewer",         # Lire les fichiers GCS (DAGs)
    "roles/logging.logWriter",            # Écrire les logs
    "roles/monitoring.metricWriter",      # Écrire les métriques
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.composer.email}"
}

# ─────────────────────────────────────────────
# SERVICE ACCOUNT — Backend (Cloud Run)
# Rôle : servir l'API, accéder à Bigtable, BigQuery, Cloud SQL
# ─────────────────────────────────────────────

resource "google_service_account" "backend" {
  account_id   = "price-intel-backend"
  display_name = "Price Intelligence — Backend API"
  description  = "Service account pour l'API FastAPI (Cloud Run)"
  project      = var.project_id
}

resource "google_project_iam_member" "backend_roles" {
  for_each = toset([
    "roles/bigtable.reader",              # Lire Bigtable (données de prix)
    "roles/bigquery.dataViewer",          # Lire BigQuery (analytics)
    "roles/bigquery.jobUser",             # Lancer des jobs BigQuery
    "roles/cloudsql.client",              # Se connecter à Cloud SQL
    "roles/secretmanager.secretAccessor", # Lire les secrets (JWT key)
    "roles/logging.logWriter",            # Écrire les logs
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# ─────────────────────────────────────────────
# SERVICE ACCOUNT — dbt (transformations BigQuery)
# Rôle : créer et modifier les modèles dbt dans BigQuery
# ─────────────────────────────────────────────

resource "google_service_account" "dbt" {
  account_id   = "price-intel-dbt"
  display_name = "Price Intelligence — dbt Transformations"
  description  = "Service account pour les transformations dbt sur BigQuery"
  project      = var.project_id
}

resource "google_project_iam_member" "dbt_roles" {
  for_each = toset([
    "roles/bigquery.dataEditor",          # Créer/modifier les tables dbt
    "roles/bigquery.jobUser",             # Lancer des jobs SQL
    "roles/bigquery.dataViewer",          # Lire les sources
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.dbt.email}"
}

# ─────────────────────────────────────────────
# SERVICE ACCOUNT — CI/CD (GitHub Actions)
# Rôle : déployer les images Docker et mettre à jour les services
# ─────────────────────────────────────────────

resource "google_service_account" "cicd" {
  account_id   = "price-intel-cicd"
  display_name = "Price Intelligence — CI/CD Pipeline"
  description  = "Service account pour GitHub Actions (build & deploy)"
  project      = var.project_id
}

resource "google_project_iam_member" "cicd_roles" {
  for_each = toset([
    "roles/artifactregistry.writer",      # Push les images Docker
    "roles/run.admin",                    # Déployer sur Cloud Run
    "roles/iam.serviceAccountUser",       # Utiliser les service accounts
    "roles/storage.objectAdmin",          # Upload le frontend sur GCS
    "roles/composer.admin",              # Mettre à jour les DAGs Composer
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cicd.email}"
}

# Clé pour GitHub Actions (Workload Identity Federation recommandé en prod)
resource "google_service_account_key" "cicd_key" {
  service_account_id = google_service_account.cicd.name
}

# ─────────────────────────────────────────────
# ARTIFACT REGISTRY — Stockage des images Docker
# ─────────────────────────────────────────────

resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = "price-intel"
  format        = "DOCKER"
  description   = "Images Docker de la plateforme Price Intelligence"
  project       = var.project_id

  cleanup_policies {
    id     = "keep-last-5"
    action = "KEEP"

    most_recent_versions {
      keep_count = 5
    }
  }
}

# ─────────────────────────────────────────────
# APIS GCP — Activer les APIs requises
# ─────────────────────────────────────────────

resource "google_project_service" "apis" {
  for_each = toset([
    "bigtable.googleapis.com",
    "bigtableadmin.googleapis.com",
    "bigquery.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "composer.googleapis.com",
    "run.googleapis.com",
    "compute.googleapis.com",
    "vpcaccess.googleapis.com",
    "servicenetworking.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
  ])

  project = var.project_id
  service = each.value

  disable_dependent_services = false
  disable_on_destroy         = false
}
