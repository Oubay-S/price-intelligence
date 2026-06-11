# modules/cloud-run/variables.tf

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "backend_image" {
  description = "Image Docker du backend (Artifact Registry)"
  type        = string
}

variable "cpu" {
  type    = string
  default = "1"
}

variable "memory" {
  type    = string
  default = "512Mi"
}

variable "min_instances" {
  type    = number
  default = 0
}

variable "max_instances" {
  type    = number
  default = 10
}

variable "vpc_connector_id" {
  description = "ID du connecteur VPC serverless"
  type        = string
}

variable "service_account_email" {
  type = string
}

variable "database_url" {
  type      = string
  sensitive = true
}

variable "redis_url" {
  type = string
}

variable "bigtable_instance_name" {
  type = string
}

variable "frontend_url" {
  type    = string
  default = ""
}

variable "jwt_secret" {
  type      = string
  sensitive = true
}

variable "environment" {
  type = string
}
