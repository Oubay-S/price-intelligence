# =============================================================
# sensitive.tf — Variables sensibles (jamais dans les .tfvars)
# =============================================================
# Ces variables doivent être passées via :
#   - Variables d'environnement : TF_VAR_airflow_db_password="..."
#   - Fichier .auto.tfvars (gitignored)
#   - Flag CLI : -var="airflow_db_password=..."
# =============================================================

variable "airflow_db_password" {
  description = "Mot de passe de la base Airflow"
  type        = string
  sensitive   = true
}

variable "app_db_password" {
  description = "Mot de passe de la base applicative"
  type        = string
  sensitive   = true
}

variable "jwt_secret" {
  description = "Clé secrète JWT pour le backend"
  type        = string
  sensitive   = true
}
