# =============================================================
# modules/redis/main.tf — Memorystore for Redis
# =============================================================
# Équivalent GCP du service docker-compose : redis (redis:7-alpine)
# Utilisé pour : cache, sessions JWT, pub/sub WebSocket
# =============================================================

resource "google_redis_instance" "main" {
  name               = "price-intel-redis"
  tier               = var.environment == "prod" ? "STANDARD_HA" : "BASIC"
  memory_size_gb     = var.memory_size_gb
  region             = var.region
  redis_version      = var.redis_version
  display_name       = "Price Intelligence — Cache & Sessions"
  authorized_network = var.network_id

  # Configuration Redis (équivalent du command docker-compose)
  redis_configs = {
    maxmemory-policy = "allkeys-lru" # Même politique que docker-compose
    notify-keyspace-events = ""
  }

  # Maintenance planifiée
  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 3
        minutes = 0
      }
    }
  }

  labels = {
    component   = "app-layer"
    service     = "redis"
    environment = var.environment
  }
}
