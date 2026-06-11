# modules/bigtable/variables.tf

variable "instance_name" {
  description = "Nom de l'instance Bigtable"
  type        = string
}

variable "zone" {
  description = "Zone GCP"
  type        = string
}

variable "num_nodes" {
  description = "Nombre de nœuds (prod uniquement)"
  type        = number
  default     = 1
}

variable "storage_type" {
  description = "Type de stockage (SSD ou HDD)"
  type        = string
  default     = "SSD"
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
}
