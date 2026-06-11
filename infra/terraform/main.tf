# =============================================================
# main.tf — Module Root — Assemblage de l'infrastructure complète
# =============================================================
#
# Ce fichier orchestre tous les modules pour déployer la
# plateforme Price Intelligence sur Google Cloud Platform.
#
# Architecture reproduite depuis docker-compose.yml :
#
# ┌──────────────────────────────────────────────────────────┐
# │  COUCHE APPLICATIVE (app-subnet)                         │
# │  Load Balancer → Frontend CDN (Angular)                  │
# │               → Cloud Run (FastAPI) → Cloud SQL App      │
# │                                     → Memorystore Redis  │
# ├──────────────────────────────────────────────────────────┤
# │  COUCHE DATA (data-subnet)                               │
# │  Cloud Composer (Airflow) → Cloud SQL Airflow            │
# │                            → Cloud Bigtable              │
# │                            → BigQuery                    │
# └──────────────────────────────────────────────────────────┘
#
# =============================================================

# ─────────────────────────────────────────────
# 0. IAM — Service Accounts, APIs, Artifact Registry
# ─────────────────────────────────────────────

module "iam" {
  source = "./modules/iam"

  project_id = var.project_id
  region     = var.region
}

# ─────────────────────────────────────────────
# 1. NETWORKING — VPC, Sous-réseaux, Firewall, NAT
# ─────────────────────────────────────────────

module "networking" {
  source = "./modules/networking"

  vpc_name = var.vpc_name
  region   = var.region

  depends_on = [module.iam]
}

# ─────────────────────────────────────────────
# 2. BIGTABLE — Stockage NoSQL temps réel (données de prix)
# ─────────────────────────────────────────────

module "bigtable" {
  source = "./modules/bigtable"

  instance_name = var.bigtable_instance_name
  zone          = var.zone
  num_nodes     = var.bigtable_num_nodes
  storage_type  = var.bigtable_storage_type
  environment   = var.environment

  depends_on = [module.iam]
}

# ─────────────────────────────────────────────
# 3. BIGQUERY — Data Warehouse analytique (dbt)
# ─────────────────────────────────────────────

module "bigquery" {
  source = "./modules/bigquery"

  project_id                = var.project_id
  dataset_id                = var.bigquery_dataset_id
  location                  = var.bigquery_location
  environment               = var.environment
  dbt_service_account_email = module.iam.dbt_service_account_email

  depends_on = [module.iam]
}

# ─────────────────────────────────────────────
# 4. CLOUD SQL — 2 instances PostgreSQL isolées
#    (Airflow metadata + App data)
# ─────────────────────────────────────────────

module "cloud_sql" {
  source = "./modules/cloud-sql"

  region                 = var.region
  network_id             = module.networking.network_id
  private_vpc_connection = module.networking.private_vpc_connection
  tier                   = var.cloudsql_tier
  disk_size              = var.cloudsql_disk_size
  environment            = var.environment

  # Airflow DB (équivalent du service postgres docker-compose)
  airflow_db_name     = var.airflow_db_name
  airflow_db_user     = var.airflow_db_user
  airflow_db_password = var.airflow_db_password

  # App DB (équivalent du service postgres-app docker-compose)
  app_db_name     = var.app_db_name
  app_db_user     = var.app_db_user
  app_db_password = var.app_db_password

  depends_on = [module.networking]
}

# ─────────────────────────────────────────────
# 5. REDIS — Cache, Sessions, WebSocket pub/sub
# ─────────────────────────────────────────────

module "redis" {
  source = "./modules/redis"

  region         = var.region
  network_id     = module.networking.network_id
  memory_size_gb = var.redis_memory_size_gb
  redis_version  = var.redis_version
  environment    = var.environment

  depends_on = [module.networking]
}

# ─────────────────────────────────────────────
# 6. CLOUD COMPOSER — Airflow managé (orchestration des DAGs)
# ─────────────────────────────────────────────

module "composer" {
  source = "./modules/composer"

  project_id             = var.project_id
  region                 = var.region
  network_id             = module.networking.network_id
  data_subnet_id         = module.networking.data_subnet_id
  service_account_email  = module.iam.composer_service_account_email
  bigtable_instance_name = var.bigtable_instance_name
  image_version          = var.composer_image_version
  environment_size       = var.composer_environment_size
  environment            = var.environment

  depends_on = [module.networking, module.iam, module.cloud_sql]
}

# ─────────────────────────────────────────────
# 7. CLOUD RUN — Backend FastAPI (API REST)
# ─────────────────────────────────────────────

module "cloud_run" {
  source = "./modules/cloud-run"

  project_id            = var.project_id
  region                = var.region
  backend_image         = var.backend_image
  cpu                   = var.backend_cpu
  memory                = var.backend_memory
  min_instances         = var.backend_min_instances
  max_instances         = var.backend_max_instances
  vpc_connector_id      = module.networking.vpc_connector_id
  service_account_email = module.iam.backend_service_account_email
  environment           = var.environment

  # Connexion à Cloud SQL App (via IP privée)
  database_url = "postgresql://${var.app_db_user}:${var.app_db_password}@${module.cloud_sql.app_private_ip}:5432/${var.app_db_name}"

  # Connexion à Redis (via IP privée)
  redis_url = module.redis.redis_url

  # Bigtable
  bigtable_instance_name = var.bigtable_instance_name

  # Frontend URL (pour les emails)
  frontend_url = module.frontend_cdn.frontend_url

  # JWT Secret
  jwt_secret = var.jwt_secret

  depends_on = [module.networking, module.iam, module.cloud_sql, module.redis]
}

# ─────────────────────────────────────────────
# 8. FRONTEND CDN — Angular SPA (GCS + Cloud CDN + Load Balancer)
# ─────────────────────────────────────────────

module "frontend_cdn" {
  source = "./modules/frontend-cdn"

  project_id         = var.project_id
  region             = var.region
  bucket_name        = var.frontend_bucket_name
  domain_name        = var.domain_name
  backend_service_id = module.cloud_run.service_name
  environment        = var.environment

  depends_on = [module.iam]
}
