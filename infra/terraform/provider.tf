# =============================================================
# provider.tf — Configuration du provider Google Cloud Platform
# =============================================================

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone

  # Labels par défaut appliqués à toutes les ressources
  default_labels = {
    project     = "price-intelligence"
    environment = var.environment
    managed_by  = "terraform"
    team        = "data-engineering"
  }
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}
