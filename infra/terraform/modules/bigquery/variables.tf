# modules/bigquery/variables.tf

variable "project_id" {
  description = "ID du projet GCP"
  type        = string
}

variable "dataset_id" {
  description = "ID du dataset BigQuery"
  type        = string
}

variable "location" {
  description = "Localisation du dataset"
  type        = string
  default     = "US"
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
}

variable "dbt_service_account_email" {
  description = "Email du service account utilisé par dbt"
  type        = string
}
