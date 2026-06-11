# =============================================================
# environments/dev.tfvars — Variables pour l'environnement DEV
# =============================================================
# Utilisé avec : terraform plan -var-file=environments/dev.tfvars
# Coûts minimaux : instances micro, pas de HA, scale to zero
# =============================================================

# ─── Projet ───
project_id  = "price-intelligence-495411"
region      = "europe-west1"
zone        = "europe-west1-b"
environment = "dev"

# ─── Networking ───
vpc_name = "price-intel-vpc-dev"

# ─── Bigtable (mode DEVELOPMENT = gratuit quasi-rien) ───
bigtable_instance_name = "price-intel-dev"
bigtable_num_nodes     = 1
bigtable_storage_type  = "HDD" # HDD moins cher que SSD pour dev

# ─── BigQuery ───
bigquery_dataset_id = "price_intelligence"
bigquery_location   = "US"

# ─── Cloud SQL (instances minimales) ───
cloudsql_tier    = "db-f1-micro"
cloudsql_disk_size = 10

# ─── Redis (minimal) ───
redis_memory_size_gb = 1
redis_version        = "REDIS_7_0"

# ─── Cloud Composer (environnement minimal) ───
composer_image_version    = "composer-2.9.7-airflow-2.9.3"
composer_environment_size = "ENVIRONMENT_SIZE_SMALL"

# ─── Cloud Run (scale to zero en dev) ───
backend_image         = "europe-west1-docker.pkg.dev/price-intelligence-495411/price-intel/backend:latest"
backend_cpu           = "1"
backend_memory        = "512Mi"
backend_min_instances = 0
backend_max_instances = 3

# ─── Frontend ───
frontend_bucket_name = "price-intel-frontend-dev"
domain_name          = "" # Pas de domaine en dev
