# modules/redis/outputs.tf

output "host" {
  description = "Adresse IP de l'instance Redis"
  value       = google_redis_instance.main.host
}

output "port" {
  description = "Port de l'instance Redis"
  value       = google_redis_instance.main.port
}

output "redis_url" {
  description = "URL de connexion Redis (format identique au docker-compose)"
  value       = "redis://${google_redis_instance.main.host}:${google_redis_instance.main.port}/0"
}
