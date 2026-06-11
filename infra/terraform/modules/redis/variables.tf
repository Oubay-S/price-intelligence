# modules/redis/variables.tf

variable "region" {
  description = "Région GCP"
  type        = string
}

variable "network_id" {
  description = "ID du réseau VPC"
  type        = string
}

variable "memory_size_gb" {
  description = "Taille mémoire en Go"
  type        = number
  default     = 1
}

variable "redis_version" {
  description = "Version de Redis"
  type        = string
  default     = "REDIS_7_0"
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
}
