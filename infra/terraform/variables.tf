# =============================================================
# variables.tf — Variables d'entrée de l'infrastructure
# =============================================================

# ─────────────────────────────────────────────
# PROJET & LOCALISATION
# ─────────────────────────────────────────────

variable "project_id" {
  description = "ID du projet Google Cloud"
  type        = string
}

variable "region" {
  description = "Région GCP principale"
  type        = string
  default     = "europe-west1"
}

variable "zone" {
  description = "Zone GCP principale"
  type        = string
  default     = "europe-west1-b"
}

variable "environment" {
  description = "Environnement de déploiement (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "L'environnement doit être 'dev', 'staging' ou 'prod'."
  }
}

# ─────────────────────────────────────────────
# NETWORKING
# ─────────────────────────────────────────────

variable "vpc_name" {
  description = "Nom du VPC principal"
  type        = string
  default     = "price-intel-vpc"
}

# ─────────────────────────────────────────────
# BIGTABLE
# ─────────────────────────────────────────────

variable "bigtable_instance_name" {
  description = "Nom de l'instance Bigtable"
  type        = string
  default     = "price-intel-instance"
}

variable "bigtable_num_nodes" {
  description = "Nombre de nœuds Bigtable (min 1 pour prod, 0 = development mode)"
  type        = number
  default     = 1
}

variable "bigtable_storage_type" {
  description = "Type de stockage Bigtable (SSD ou HDD)"
  type        = string
  default     = "SSD"

  validation {
    condition     = contains(["SSD", "HDD"], var.bigtable_storage_type)
    error_message = "Le type de stockage doit être 'SSD' ou 'HDD'."
  }
}

# ─────────────────────────────────────────────
# BIGQUERY
# ─────────────────────────────────────────────

variable "bigquery_dataset_id" {
  description = "ID du dataset BigQuery principal"
  type        = string
  default     = "price_intelligence"
}

variable "bigquery_location" {
  description = "Localisation du dataset BigQuery"
  type        = string
  default     = "US"
}

# ─────────────────────────────────────────────
# CLOUD SQL (PostgreSQL)
# ─────────────────────────────────────────────

variable "cloudsql_tier" {
  description = "Tier de la machine Cloud SQL"
  type        = string
  default     = "db-f1-micro"
}

variable "cloudsql_disk_size" {
  description = "Taille du disque Cloud SQL en Go"
  type        = number
  default     = 10
}

variable "airflow_db_name" {
  description = "Nom de la base de données Airflow"
  type        = string
  default     = "airflow"
}

variable "airflow_db_user" {
  description = "Utilisateur de la base de données Airflow"
  type        = string
  default     = "airflow"
}

variable "app_db_name" {
  description = "Nom de la base de données applicative"
  type        = string
  default     = "price_intelligence"
}

variable "app_db_user" {
  description = "Utilisateur de la base de données applicative"
  type        = string
  default     = "app_user"
}

# ─────────────────────────────────────────────
# REDIS (Memorystore)
# ─────────────────────────────────────────────

variable "redis_memory_size_gb" {
  description = "Taille mémoire de l'instance Redis en Go"
  type        = number
  default     = 1
}

variable "redis_version" {
  description = "Version de Redis"
  type        = string
  default     = "REDIS_7_0"
}

# ─────────────────────────────────────────────
# CLOUD COMPOSER (Airflow managé)
# ─────────────────────────────────────────────

variable "composer_image_version" {
  description = "Version de l'image Cloud Composer"
  type        = string
  default     = "composer-2.9.7-airflow-2.9.3"
}

variable "composer_node_count" {
  description = "Nombre de nœuds du cluster Composer"
  type        = number
  default     = 3
}

variable "composer_environment_size" {
  description = "Taille de l'environnement Composer (SMALL, MEDIUM, LARGE)"
  type        = string
  default     = "ENVIRONMENT_SIZE_SMALL"
}

# ─────────────────────────────────────────────
# CLOUD RUN (Backend FastAPI)
# ─────────────────────────────────────────────

variable "backend_image" {
  description = "Image Docker du backend (Artifact Registry)"
  type        = string
  default     = "europe-west1-docker.pkg.dev/price-intelligence-495411/price-intel/backend:latest"
}

variable "backend_cpu" {
  description = "CPU allouée au backend Cloud Run"
  type        = string
  default     = "1"
}

variable "backend_memory" {
  description = "Mémoire allouée au backend Cloud Run"
  type        = string
  default     = "512Mi"
}

variable "backend_min_instances" {
  description = "Nombre minimum d'instances Cloud Run"
  type        = number
  default     = 0
}

variable "backend_max_instances" {
  description = "Nombre maximum d'instances Cloud Run"
  type        = number
  default     = 10
}

# ─────────────────────────────────────────────
# FRONTEND (GCS + CDN)
# ─────────────────────────────────────────────

variable "frontend_bucket_name" {
  description = "Nom du bucket GCS pour le frontend Angular"
  type        = string
  default     = "price-intel-frontend"
}

variable "domain_name" {
  description = "Nom de domaine personnalisé (optionnel)"
  type        = string
  default     = ""
}
