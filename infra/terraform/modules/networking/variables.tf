# modules/networking/variables.tf

variable "vpc_name" {
  description = "Nom du VPC"
  type        = string
}

variable "region" {
  description = "Région GCP"
  type        = string
}
