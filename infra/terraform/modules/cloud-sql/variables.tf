# modules/cloud-sql/variables.tf

variable "region" {
  description = "Région GCP"
  type        = string
}

variable "network_id" {
  description = "ID du réseau VPC"
  type        = string
}

variable "private_vpc_connection" {
  description = "Connexion VPC privée (dépendance)"
  type        = any
}

variable "tier" {
  description = "Tier de la machine Cloud SQL"
  type        = string
  default     = "db-f1-micro"
}

variable "disk_size" {
  description = "Taille du disque en Go"
  type        = number
  default     = 10
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
}

# Airflow DB
variable "airflow_db_name" {
  type    = string
  default = "airflow"
}

variable "airflow_db_user" {
  type    = string
  default = "airflow"
}

variable "airflow_db_password" {
  type      = string
  sensitive = true
}

# App DB
variable "app_db_name" {
  type    = string
  default = "price_intelligence"
}

variable "app_db_user" {
  type    = string
  default = "app_user"
}

variable "app_db_password" {
  type      = string
  sensitive = true
}
