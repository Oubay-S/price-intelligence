# =============================================================
# backend.tf — State backend (Google Cloud Storage)
# =============================================================
# Le state Terraform est stocké dans un bucket GCS pour permettre
# le travail en équipe et éviter les conflits de state local.
#
# IMPORTANT : Ce bucket doit être créé MANUELLEMENT avant le
# premier `terraform init` :
#
#   gsutil mb -p price-intelligence-495411 \
#     -l europe-west1 \
#     -b on \
#     gs://price-intel-terraform-state/
#
#   gsutil versioning set on gs://price-intel-terraform-state/
# =============================================================

terraform {
  backend "gcs" {
    bucket = "price-intel-terraform-state"
    prefix = "terraform/state"
  }
}
