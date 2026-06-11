# =============================================================
# modules/bigtable/main.tf — Cloud Bigtable (NoSQL temps réel)
# =============================================================
# Équivalent GCP du service docker-compose :
#   bigtable-emulator (gcr.io/google.com/cloudsdktool/cloud-sdk)
#
# Stocke les données de prix scrapées en temps réel avec un
# schéma de row key optimisé : {source}#{category}#{product_id}
# =============================================================

resource "google_bigtable_instance" "main" {
  name                = var.instance_name
  deletion_protection = var.environment == "prod" ? true : false

  # En dev, on utilise le mode DEVELOPMENT (1 noeud, pas de SLA, moins cher)
  # En prod, on utilise le mode PRODUCTION (multi-noeud, SLA garanti)
  instance_type = var.environment == "prod" ? "PRODUCTION" : "DEVELOPMENT"

  cluster {
    cluster_id   = "${var.instance_name}-cluster"
    zone         = var.zone
    num_nodes    = var.environment == "prod" ? var.num_nodes : 0
    storage_type = var.storage_type
  }

  labels = {
    component = "data-layer"
    service   = "bigtable"
  }
}

# ─────────────────────────────────────────────
# TABLE PRINCIPALE : prices
# Stocke TOUTES les données de prix scrapées
# ─────────────────────────────────────────────

resource "google_bigtable_table" "prices" {
  name          = "prices"
  instance_name = google_bigtable_instance.main.name

  # Politique de garbage collection :
  # Garder les 100 dernières versions OU les données des 90 derniers jours
  column_family {
    family = "product_info"
  }

  column_family {
    family = "pricing"
  }

  column_family {
    family = "metadata"
  }

  lifecycle {
    prevent_destroy = false
  }
}

# Politique GC pour la famille "pricing" (données de prix)
resource "google_bigtable_gc_policy" "pricing_gc" {
  instance_name = google_bigtable_instance.main.name
  table         = google_bigtable_table.prices.name
  column_family = "pricing"

  max_version {
    number = 100
  }
}

# ─────────────────────────────────────────────
# TABLE : price_history
# Historique agrégé des prix (par jour)
# ─────────────────────────────────────────────

resource "google_bigtable_table" "price_history" {
  name          = "price_history"
  instance_name = google_bigtable_instance.main.name

  column_family {
    family = "daily_stats"
  }

  column_family {
    family = "weekly_stats"
  }

  lifecycle {
    prevent_destroy = false
  }
}
