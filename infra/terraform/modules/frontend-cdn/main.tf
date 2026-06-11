# =============================================================
# modules/frontend-cdn/main.tf — Frontend Angular (GCS + CDN)
# =============================================================
# Équivalent GCP des services docker-compose :
#   - frontend (Angular SPA servie par nginx interne)
#   - nginx (reverse proxy → Load Balancer GCP)
#
# Architecture :
#   Cloud CDN → Cloud Load Balancer → GCS Bucket (Angular static files)
#   Le backend est routé via /api/* sur le même Load Balancer
# =============================================================

# ─────────────────────────────────────────────
# BUCKET GCS — Héberge les fichiers Angular buildés
# ─────────────────────────────────────────────

resource "google_storage_bucket" "frontend" {
  name          = "${var.bucket_name}-${var.project_id}"
  location      = var.region
  force_destroy = var.environment != "prod"
  project       = var.project_id

  # Configuration de site web statique
  website {
    main_page_suffix = "index.html"
    not_found_page   = "index.html" # SPA routing — toutes les routes → index.html
  }

  # CORS pour les appels API depuis le frontend
  cors {
    origin          = var.environment == "prod" ? [var.domain_name] : ["*"]
    method          = ["GET", "HEAD", "OPTIONS"]
    response_header = ["Content-Type", "Access-Control-Allow-Origin"]
    max_age_seconds = 3600
  }

  # Versioning pour rollback
  versioning {
    enabled = true
  }

  # Cycle de vie — supprimer les anciennes versions après 30 jours
  lifecycle_rule {
    condition {
      num_newer_versions = 5
      with_state         = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }

  uniform_bucket_level_access = true

  labels = {
    component   = "frontend"
    environment = var.environment
  }
}

# Rendre le bucket public en lecture
resource "google_storage_bucket_iam_member" "public_read" {
  bucket = google_storage_bucket.frontend.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

# ─────────────────────────────────────────────
# LOAD BALANCER + CDN
# Remplace nginx du docker-compose comme point d'entrée unique
# ─────────────────────────────────────────────

# Backend bucket (pour les fichiers statiques Angular)
resource "google_compute_backend_bucket" "frontend" {
  name        = "price-intel-frontend-bucket"
  bucket_name = google_storage_bucket.frontend.name
  enable_cdn  = true

  cdn_policy {
    cache_mode                   = "CACHE_ALL_STATIC"
    default_ttl                  = 3600
    max_ttl                      = 86400
    serve_while_stale            = 86400
    signed_url_cache_max_age_sec = 0
  }
}

# IP externe statique
resource "google_compute_global_address" "frontend" {
  name = "price-intel-frontend-ip"
}

# URL Map — Routage (équivalent de nginx.conf)
# /api/* → backend Cloud Run (via NEG)
# /*     → frontend GCS bucket
resource "google_compute_url_map" "main" {
  name            = "price-intel-url-map"
  default_service = google_compute_backend_bucket.frontend.id

  # Route /api/* vers le backend Cloud Run
  host_rule {
    hosts        = ["*"]
    path_matcher = "api-routes"
  }

  path_matcher {
    name            = "api-routes"
    default_service = google_compute_backend_bucket.frontend.id

    path_rule {
      paths   = ["/api/*"]
      service = var.backend_service_id
    }
  }
}

# HTTPS Proxy
resource "google_compute_target_https_proxy" "main" {
  count   = var.domain_name != "" ? 1 : 0
  name    = "price-intel-https-proxy"
  url_map = google_compute_url_map.main.id

  ssl_certificates = [google_compute_managed_ssl_certificate.main[0].id]
}

# HTTP Proxy (dev — sans SSL)
resource "google_compute_target_http_proxy" "main" {
  name    = "price-intel-http-proxy"
  url_map = google_compute_url_map.main.id
}

# Forwarding rule HTTP
resource "google_compute_global_forwarding_rule" "http" {
  name       = "price-intel-http-forwarding"
  target     = google_compute_target_http_proxy.main.id
  port_range = "80"
  ip_address = google_compute_global_address.frontend.address
}

# Forwarding rule HTTPS (uniquement si domaine configuré)
resource "google_compute_global_forwarding_rule" "https" {
  count      = var.domain_name != "" ? 1 : 0
  name       = "price-intel-https-forwarding"
  target     = google_compute_target_https_proxy.main[0].id
  port_range = "443"
  ip_address = google_compute_global_address.frontend.address
}

# Certificat SSL managé (gratuit, automatique)
resource "google_compute_managed_ssl_certificate" "main" {
  count = var.domain_name != "" ? 1 : 0
  name  = "price-intel-ssl-cert"

  managed {
    domains = [var.domain_name]
  }
}
