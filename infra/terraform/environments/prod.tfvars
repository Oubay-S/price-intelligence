# =============================================================
# environments/prod.tfvars — Variables pour l'environnement PROD
# =============================================================
# Utilisé avec : terraform plan -var-file=environments/prod.tfvars
# Haute disponibilité, sécurité renforcée, performances optimales
# =============================================================

# ─── Projet ───
project_id  = "price-intelligence-495411"
region      = "europe-west1"
zone        = "europe-west1-b"
environment = "prod"

# ─── Networking ───
vpc_name = "price-intel-vpc-prod"

# ─── Bigtable (mode PRODUCTION = SLA garanti) ───
bigtable_instance_name = "price-intel-prod"
bigtable_num_nodes     = 3
bigtable_storage_type  = "SSD"

# ─── BigQuery ───
bigquery_dataset_id = "price_intelligence"
bigquery_location   = "US"

# ─── Cloud SQL (HA + backups + PITR) ───
cloudsql_tier      = "db-custom-2-4096" # 2 vCPU, 4 Go RAM
cloudsql_disk_size = 50

# ─── Redis (HA — réplication automatique) ───
redis_memory_size_gb = 4
redis_version        = "REDIS_7_0"

# ─── Cloud Composer (capacité production) ───
composer_image_version    = "composer-2.9.7-airflow-2.9.3"
composer_environment_size = "ENVIRONMENT_SIZE_MEDIUM"

# ─── Cloud Run (always-on en prod) ───
backend_image         = "europe-west1-docker.pkg.dev/price-intelligence-495411/price-intel/backend:latest"
backend_cpu           = "2"
backend_memory        = "1Gi"
backend_min_instances = 1  # Toujours au moins 1 instance active
backend_max_instances = 20

# ─── Frontend ───
frontend_bucket_name = "price-intel-frontend-prod"
domain_name          = "price-intelligence.example.com" # Remplacer par le vrai domaine
