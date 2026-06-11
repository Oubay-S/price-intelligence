# =============================================================
# modules/bigquery/main.tf — BigQuery (Data Warehouse analytique)
# =============================================================
# Dataset et tables BigQuery utilisés par dbt pour les
# transformations SQL et par le dashboard pour l'analyse.
#
# Le profil dbt (profiles.yml) pointe vers :
#   project: price-intelligence-495411
#   dataset: price_intelligence
# =============================================================

resource "google_bigquery_dataset" "main" {
  dataset_id    = var.dataset_id
  friendly_name = "Price Intelligence — Data Warehouse"
  description   = "Dataset principal contenant les données transformées par dbt (staging, intermediate, mart)"
  location      = var.location
  project       = var.project_id

  # Expiration par défaut des tables temporaires (30 jours)
  default_table_expiration_ms = var.environment == "dev" ? 2592000000 : null

  # Contrôle d'accès au niveau du dataset
  access {
    role          = "OWNER"
    special_group = "projectOwners"
  }

  access {
    role          = "READER"
    special_group = "projectReaders"
  }

  # Accès pour le service account dbt/Airflow
  access {
    role          = "WRITER"
    user_by_email = var.dbt_service_account_email
  }

  labels = {
    component   = "analytics"
    managed_by  = "terraform"
    environment = var.environment
  }
}

# ─────────────────────────────────────────────
# TABLE : raw_prices (données brutes depuis Bigtable → BigQuery)
# Alimentée par le script bigtable_to_bigquery.py
# ─────────────────────────────────────────────

resource "google_bigquery_table" "raw_prices" {
  dataset_id          = google_bigquery_dataset.main.dataset_id
  table_id            = "raw_prices"
  description         = "Données brutes de prix exportées depuis Bigtable"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "scrape_date"
  }

  clustering = ["source", "category"]

  schema = jsonencode([
    {
      name        = "product_id"
      type        = "STRING"
      mode        = "REQUIRED"
      description = "Identifiant unique du produit"
    },
    {
      name        = "product_name"
      type        = "STRING"
      mode        = "REQUIRED"
      description = "Nom du produit"
    },
    {
      name        = "price"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Prix actuel du produit"
    },
    {
      name        = "original_price"
      type        = "FLOAT64"
      mode        = "NULLABLE"
      description = "Prix original avant réduction"
    },
    {
      name        = "currency"
      type        = "STRING"
      mode        = "NULLABLE"
      description = "Devise du prix (EUR, USD, MAD...)"
    },
    {
      name        = "source"
      type        = "STRING"
      mode        = "REQUIRED"
      description = "Source du scraping (ebay, jumia, walmart, sport-direct)"
    },
    {
      name        = "category"
      type        = "STRING"
      mode        = "NULLABLE"
      description = "Catégorie du produit"
    },
    {
      name        = "url"
      type        = "STRING"
      mode        = "NULLABLE"
      description = "URL de la page produit"
    },
    {
      name        = "scrape_date"
      type        = "DATE"
      mode        = "REQUIRED"
      description = "Date du scraping"
    },
    {
      name        = "scrape_timestamp"
      type        = "TIMESTAMP"
      mode        = "REQUIRED"
      description = "Horodatage précis du scraping"
    },
    {
      name        = "availability"
      type        = "STRING"
      mode        = "NULLABLE"
      description = "Disponibilité du produit (in_stock, out_of_stock)"
    }
  ])

  labels = {
    layer = "raw"
  }
}

# ─────────────────────────────────────────────
# TABLE : price_analytics (résultats d'analyse statistique)
# Alimentée par data-analysis/upload_analysis_to_bigquery.py
# ─────────────────────────────────────────────

resource "google_bigquery_table" "price_analytics" {
  dataset_id          = google_bigquery_dataset.main.dataset_id
  table_id            = "price_analytics"
  description         = "Résultats d'analyse statistique (EDA) — moyennes, médianes, écarts-types par source et catégorie"
  deletion_protection = false

  schema = jsonencode([
    {
      name        = "source"
      type        = "STRING"
      mode        = "REQUIRED"
      description = "Source du scraping"
    },
    {
      name        = "category"
      type        = "STRING"
      mode        = "REQUIRED"
      description = "Catégorie de produit"
    },
    {
      name        = "avg_price"
      type        = "FLOAT64"
      mode        = "NULLABLE"
      description = "Prix moyen"
    },
    {
      name        = "median_price"
      type        = "FLOAT64"
      mode        = "NULLABLE"
      description = "Prix médian"
    },
    {
      name        = "std_price"
      type        = "FLOAT64"
      mode        = "NULLABLE"
      description = "Écart-type des prix"
    },
    {
      name        = "min_price"
      type        = "FLOAT64"
      mode        = "NULLABLE"
      description = "Prix minimum"
    },
    {
      name        = "max_price"
      type        = "FLOAT64"
      mode        = "NULLABLE"
      description = "Prix maximum"
    },
    {
      name        = "product_count"
      type        = "INT64"
      mode        = "NULLABLE"
      description = "Nombre de produits"
    },
    {
      name        = "analysis_date"
      type        = "DATE"
      mode        = "REQUIRED"
      description = "Date de l'analyse"
    }
  ])

  labels = {
    layer = "analytics"
  }
}
