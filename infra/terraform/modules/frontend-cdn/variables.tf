# modules/frontend-cdn/variables.tf

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "bucket_name" {
  type    = string
  default = "price-intel-frontend"
}

variable "domain_name" {
  description = "Nom de domaine (vide = pas de SSL)"
  type        = string
  default     = ""
}

variable "backend_service_id" {
  description = "ID du backend service Cloud Run (pour le routage /api/*)"
  type        = string
}

variable "environment" {
  type = string
}
