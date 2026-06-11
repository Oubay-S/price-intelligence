# modules/composer/variables.tf

variable "project_id" {
  description = "ID du projet GCP"
  type        = string
}

variable "region" {
  description = "Région GCP"
  type        = string
}

variable "network_id" {
  description = "ID du réseau VPC"
  type        = string
}

variable "data_subnet_id" {
  description = "ID du sous-réseau data"
  type        = string
}

variable "service_account_email" {
  description = "Email du service account Composer"
  type        = string
}

variable "bigtable_instance_name" {
  description = "Nom de l'instance Bigtable"
  type        = string
}

variable "image_version" {
  description = "Version de l'image Composer"
  type        = string
  default     = "composer-2.9.7-airflow-2.9.3"
}

variable "environment_size" {
  description = "Taille de l'environnement (SMALL, MEDIUM, LARGE)"
  type        = string
  default     = "ENVIRONMENT_SIZE_SMALL"
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
}
