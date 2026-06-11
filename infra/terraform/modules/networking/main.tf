# =============================================================
# modules/networking/main.tf — VPC, Sous-réseaux, Firewall, NAT
# =============================================================
# Reproduit l'isolation réseau du docker-compose :
#   - price-intel-network → sous-réseau "data"
#   - app-network         → sous-réseau "app"
# =============================================================

# ─────────────────────────────────────────────
# VPC PRINCIPAL
# ─────────────────────────────────────────────

resource "google_compute_network" "main" {
  name                    = var.vpc_name
  auto_create_subnetworks = false
  description             = "VPC principal de la plateforme Price Intelligence"
}

# ─────────────────────────────────────────────
# SOUS-RÉSEAU DATA (Bigtable, Composer, Cloud SQL Airflow)
# Équivalent : price-intel-network dans docker-compose
# ─────────────────────────────────────────────

resource "google_compute_subnetwork" "data" {
  name          = "${var.vpc_name}-data"
  ip_cidr_range = "10.10.0.0/20"
  region        = var.region
  network       = google_compute_network.main.id
  description   = "Sous-réseau pour la couche data (Bigtable, Composer, Cloud SQL)"

  secondary_ip_range {
    range_name    = "composer-pods"
    ip_cidr_range = "10.20.0.0/16"
  }

  secondary_ip_range {
    range_name    = "composer-services"
    ip_cidr_range = "10.30.0.0/20"
  }

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
  }
}

# ─────────────────────────────────────────────
# SOUS-RÉSEAU APP (Backend, Frontend, Redis)
# Équivalent : app-network dans docker-compose
# ─────────────────────────────────────────────

resource "google_compute_subnetwork" "app" {
  name          = "${var.vpc_name}-app"
  ip_cidr_range = "10.11.0.0/20"
  region        = var.region
  network       = google_compute_network.main.id
  description   = "Sous-réseau pour la couche applicative (Cloud Run, Redis)"

  private_ip_google_access = true
}

# ─────────────────────────────────────────────
# CONNECTEUR VPC SERVERLESS (pour Cloud Run → VPC)
# Permet au backend Cloud Run d'accéder à Redis
# et Cloud SQL via IP privées
# ─────────────────────────────────────────────

resource "google_vpc_access_connector" "serverless" {
  name          = "price-intel-connector"
  region        = var.region
  ip_cidr_range = "10.12.0.0/28"
  network       = google_compute_network.main.name

  min_instances = 2
  max_instances = 3

  machine_type = "f1-micro"
}

# ─────────────────────────────────────────────
# CLOUD NAT (accès Internet sortant pour les sous-réseaux privés)
# ─────────────────────────────────────────────

resource "google_compute_router" "nat_router" {
  name    = "${var.vpc_name}-router"
  region  = var.region
  network = google_compute_network.main.id
}

resource "google_compute_router_nat" "nat" {
  name                               = "${var.vpc_name}-nat"
  router                             = google_compute_router.nat_router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# ─────────────────────────────────────────────
# FIREWALL — Règles de sécurité
# ─────────────────────────────────────────────

# Autoriser le trafic interne entre les sous-réseaux
resource "google_compute_firewall" "internal" {
  name    = "${var.vpc_name}-allow-internal"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [
    "10.10.0.0/20", # data subnet
    "10.11.0.0/20", # app subnet
  ]

  description = "Autoriser le trafic interne entre sous-réseaux"
}

# Autoriser les health checks Google (pour Load Balancer + Cloud Run)
resource "google_compute_firewall" "health_checks" {
  name    = "${var.vpc_name}-allow-health-checks"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["80", "443", "8000", "8080"]
  }

  source_ranges = [
    "130.211.0.0/22",  # Google health check IPs
    "35.191.0.0/16",   # Google health check IPs
  ]

  target_tags = ["allow-health-checks"]
  description = "Autoriser les health checks Google Cloud"
}

# Bloquer tout le trafic SSH sauf depuis IAP (sécurité)
resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "${var.vpc_name}-allow-iap-ssh"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["35.235.240.0/20"] # IAP TCP forwarding
  description   = "SSH uniquement via IAP (Identity-Aware Proxy)"
}

# ─────────────────────────────────────────────
# ALLOCATION IP PRIVÉE (pour Cloud SQL Private Service Connect)
# ─────────────────────────────────────────────

resource "google_compute_global_address" "private_ip_range" {
  name          = "price-intel-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 20
  network       = google_compute_network.main.id
}

resource "google_service_networking_connection" "private_vpc" {
  network                 = google_compute_network.main.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
}
