# 🏗️ Infrastructure as Code — Terraform (GCP)

## Vue d'ensemble

Ce dossier contient la **configuration Terraform complète** pour déployer
la plateforme Price Intelligence sur Google Cloud Platform (GCP).

L'infrastructure reproduit fidèlement l'architecture locale (Docker Compose)
en utilisant des services GCP managés :

| Service Local (Docker)       | Service GCP (Terraform)               |
|------------------------------|---------------------------------------|
| `bigtable-emulator`         | **Cloud Bigtable** (instance + table) |
| `postgres` (Airflow)        | **Cloud SQL for PostgreSQL**          |
| `postgres-app`              | **Cloud SQL for PostgreSQL** (2e)     |
| `airflow-*`                 | **Cloud Composer v2**                 |
| `redis`                     | **Memorystore for Redis**             |
| `backend` (FastAPI)         | **Cloud Run**                         |
| `frontend` (Angular)        | **Cloud Storage** + **Cloud CDN**     |
| `nginx`                     | **Cloud Load Balancer**               |
| BigQuery (analytics)        | **BigQuery** (dataset + tables)       |
| Artifact storage            | **Artifact Registry**                 |

## Structure des fichiers

```
terraform/
├── main.tf              # Module root — assemble tous les composants
├── provider.tf          # Configuration du provider GCP
├── variables.tf         # Variables d'entrée (projet, région, etc.)
├── outputs.tf           # Valeurs de sortie après déploiement
├── versions.tf          # Contraintes de versions Terraform + providers
├── backend.tf           # Configuration du state backend (GCS)
│
├── modules/
│   ├── networking/      # VPC, sous-réseaux, firewall, Cloud NAT
│   ├── bigtable/        # Instance et table Bigtable
│   ├── bigquery/        # Dataset et tables BigQuery
│   ├── cloud-sql/       # Instances PostgreSQL (Airflow + App)
│   ├── redis/           # Memorystore for Redis
│   ├── composer/        # Cloud Composer v2 (Airflow managé)
│   ├── cloud-run/       # Backend FastAPI sur Cloud Run
│   ├── frontend-cdn/    # Frontend Angular sur GCS + CDN
│   └── iam/             # Service accounts et rôles IAM
│
└── environments/
    ├── dev.tfvars       # Variables pour l'environnement de développement
    └── prod.tfvars      # Variables pour l'environnement de production
```

## 🆓 Validation SANS déploiement (0€)

Ce projet est académique. Vous pouvez valider que le code Terraform est
**syntaxiquement et structurellement correct** sans créer aucune ressource
GCP et donc sans dépenser un seul centime :

```bash
# 1. Installer Terraform (https://developer.hashicorp.com/terraform/install)
#    Windows : winget install HashiCorp.Terraform
#    macOS   : brew install terraform
#    Linux   : sudo apt install terraform

# 2. Naviguer dans le dossier
cd infra/terraform

# 3. Initialiser (télécharge les providers — gratuit)
terraform init

# 4. Valider la syntaxe et la cohérence (gratuit, rien n'est créé)
terraform validate

# 5. Générer un plan d'exécution (gratuit, rien n'est créé)
#    Montre CE QUI SERAIT créé si on déployait réellement
terraform plan -var-file=environments/dev.tfvars
```

> **⚠️ Important :** `terraform plan` nécessite des credentials GCP valides
> pour résoudre les APIs. Si vous n'en avez pas, `terraform validate` suffit
> pour prouver que le code est correct.

## Déploiement réel (si budget disponible)

```bash
# Appliquer l'infrastructure (COÛTE DE L'ARGENT — ne pas exécuter sans budget)
terraform apply -var-file=environments/prod.tfvars

# Détruire toute l'infrastructure (nettoyage)
terraform destroy -var-file=environments/prod.tfvars
```
