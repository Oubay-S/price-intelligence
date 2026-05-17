# 🛒 Price Intelligence Platform

**Plateforme hybride Batch + Streaming de veille tarifaire e-commerce** spécialisée dans les produits de nutrition sportive (protéines, créatine, vitamines...).

Le système scrape automatiquement les prix depuis **Jumia**, **Sports Direct** et **eBay**, les stocke dans Google Cloud Bigtable, puis les transforme via dbt pour alimenter des analyses statistiques et un tableau de bord interactif.

> 🎓 Projet académique — Data Engineering & Analytics · Pr. ELAACHAK · 2025-2026

---

## 📖 Table des matières

- [Vue d'ensemble](#-vue-densemble)
- [Architecture technique](#-architecture-technique)
- [Équipe & responsabilités](#-équipe--responsabilités)
- [Démarrage rapide](#-démarrage-rapide)
- [Stack technique](#-stack-technique)
- [Comment ça marche ?](#-comment-ça-marche-)
- [Structure du projet](#-structure-du-projet)
- [Pipeline CI/CD](#-pipeline-cicd-github-actions)
- [Guide Git pour l'équipe](#-guide-git-pour-léquipe)
- [Dépannage](#-dépannage)
- [Sécurité](#-sécurité)
- [Roadmap](#-roadmap)

---

## 🎯 Vue d'ensemble

### Le problème
Les prix des produits de nutrition sportive varient fortement d'une plateforme à l'autre et d'un jour à l'autre. Impossible de suivre manuellement les tendances sur 3 marketplaces en même temps.

### Notre solution
Une plateforme **100% automatisée** qui :
1. 🕷️ **Scrape** les prix sur Jumia, Sports Direct et eBay chaque jour à 13h
2. 📡 **Ingère** les données en temps réel via Apache NiFi
3. 💾 **Stocke** dans Google Cloud Bigtable (émulé en local)
4. 🔄 **Transforme** les données brutes en modèles analytiques via dbt
5. 📊 **Analyse** les tendances avec Python (SciPy, statsmodels)
6. 🖥️ **Affiche** les résultats dans un frontend Angular avec une API FastAPI

### Flux de données simplifié
```
Jumia ──┐
Sports Direct ├──► Scrapers Python ──► NiFi (temps réel) ──► Bigtable ──► dbt ──► Analytics
eBay ───┘         │                                                           │
                  └──► Airflow (batch quotidien) ──────────────────────────────┘
                                                                              │
                                                                              ▼
                                                           FastAPI ──► Angular Dashboard
```

---

## 🏗️ Architecture technique

Le projet est organisé en **2 couches isolées** par des réseaux Docker séparés :

```
┌──────────────────────────────────────────────────────────────────┐
│                    COUCHE APPLICATIVE                            │
│                    Réseau : app-network                          │
│                                                                  │
│  ┌─────────┐    ┌──────────────────┐    ┌───────────────────┐   │
│  │ nginx   │───►│ Frontend Angular │    │ PostgreSQL App    │   │
│  │ :80     │    │ :4200            │    │ :5432             │   │
│  │         │    └──────────────────┘    │ users, watchlist  │   │
│  │         │───►┌──────────────────┐   │ alerts, sessions  │   │
│  │ /api/*  │    │ Backend FastAPI  │◄──┘───────────────────┘   │
│  │ /ws/*   │───►│ :8000            │                            │
│  └─────────┘    │                  │◄──┌───────────────────┐   │
│                 └──────────────────┘   │ Redis :6379       │   │
│                                        │ cache, pub/sub    │   │
│                                        │ sessions          │   │
│                                        └───────────────────┘   │
├──────────────────────────────────────────────────────────────────┤
│                      COUCHE DATA                                │
│                      Réseau : price-intel-network                │
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │ Airflow          │    │ Bigtable         │                   │
│  │ Webserver :8080  │    │ Emulator :8086   │                   │
│  │ Scheduler        │    │ (gRPC)           │                   │
│  └────────┬─────────┘    └────────▲─────────┘                   │
│           │                       │                              │
│           ▼                       │                              │
│  ┌──────────────────┐    ┌───────┴──────────┐                   │
│  │ PostgreSQL       │    │ Apache NiFi      │                   │
│  │ Airflow :5433    │    │ :8443 (HTTPS)    │                   │
│  │ metadata, logs   │    │ streaming        │                   │
│  └──────────────────┘    └──────────────────┘                   │
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │ bigtable-init    │    │ dbt              │                   │
│  │ charge les JSON  │    │ transformations  │                   │
│  │ au démarrage     │    │ SQL → BigQuery   │                   │
│  └──────────────────┘    └──────────────────┘                   │
└──────────────────────────────────────────────────────────────────┘

⟵── Le Backend FastAPI est connecté aux DEUX réseaux ──⟶
     (accès à Bigtable + accès à Redis/PostgreSQL App)
```

---

## 👥 Équipe & responsabilités

| Rôle | Qui | Responsabilité | Dossiers |
|------|-----|---------------|----------|
| 🔧 DataOps | — | Infra Docker, CI/CD, sécurité, déploiement | `docker-compose.yml`, `.github/`, `nginx/` |
| 🕷️ Data Engineer | — | Scrapers, DAGs Airflow, ingestion Bigtable | `scrapers/`, `airflow/` |
| 📊 Data Analyst | — | Modèles dbt, analyses statistiques Python | `dbt/`, `analytics/` |
| 💻 Dev Fullstack | — | API FastAPI, Frontend Angular, WebSocket | `backend/`, `frontend/` |

---

## 🚀 Démarrage rapide

### Prérequis
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et **lancé**
- [Git](https://git-scm.com/downloads) installé
- 8 Go de RAM minimum (les conteneurs Airflow + NiFi sont gourmands)

### Étape 1 — Cloner le projet
```bash
git clone https://github.com/Oubay-S/price-intelligence.git
cd price-intelligence
```

### Étape 2 — Préparer l'environnement (🔒 Sécurité)
```bash
# Créer le fichier d'environnement local
cp .env.example .env

# Créer le fichier des clés GCP (requis pour BigQuery/dbt en semaine 4)
cp gcp-credentials.json.example gcp-credentials.json
```

> ⚠️ **RÈGLES DE SÉCURITÉ — À respecter par TOUS**
> - **`.env`** et **`gcp-credentials.json`** sont **ignorés par Git** → ils ne seront jamais poussés
> - **Ne modifiez jamais** les fichiers `.example` avec de vraies clés
> - Pour que BigQuery fonctionne : remplacez le contenu de `gcp-credentials.json` par votre vraie clé GCP (Service Account JSON)

### Étape 3 — Lancer l'infrastructure
```bash
# Lancer TOUS les services (12 conteneurs)
docker-compose up -d --build
```

> ⏳ **Premier lancement :** Comptez ~10 minutes pour le build des images (Airflow, Backend, Frontend).
> Les lancements suivants sont quasi-instantanés grâce au cache Docker.

#### Lancement partiel (si besoin)
```bash
# Couche DATA uniquement (Data Engineer / Data Analyst)
docker-compose up -d --build bigtable-emulator postgres airflow-init airflow-webserver airflow-scheduler nifi bigtable-init

# Couche APPLICATIVE uniquement (Dev Fullstack)
docker-compose up -d --build postgres-app redis backend frontend nginx
```

### Étape 4 — Vérifier que tout tourne
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Résultat attendu : **10 conteneurs**, tous en `healthy` ou `Up` :
```
NAMES               STATUS
nginx               Up (healthy)
backend             Up (healthy)
frontend            Up (healthy)
airflow-webserver   Up (healthy)
airflow-scheduler   Up (healthy)
nifi                Up (healthy)
postgres-app        Up (healthy)
airflow-postgres    Up (healthy)
redis               Up (healthy)
bigtable-emulator   Up (healthy)
```

### Étape 5 — Accéder aux services

| Service | URL | Identifiants | Qui l'utilise ? |
|---------|-----|-------------|-----------------|
| 🌐 **Application** | http://localhost | — | Tout le monde |
| 🖥️ Frontend Angular | http://localhost:4200 | — | Dev Fullstack |
| ⚡ Backend FastAPI (Swagger) | http://localhost:8000/docs | — | Dev Fullstack |
| 🔧 Airflow | http://localhost:8080 | `admin` / `admin123` | Data Engineer |
| 📡 NiFi | https://localhost:8443/nifi | `admin` / `adminpassword123` | Data Engineer |
| 🗄️ PostgreSQL App | `localhost:5432` | `app_user` / `app_secret` | Dev Fullstack |
| 🗄️ PostgreSQL Airflow | `localhost:5433` | `airflow` / `airflow_secret` | DataOps |
| 📦 Redis | `localhost:6379` | — | Dev Fullstack |

> 💡 **Astuce NiFi :** Le navigateur affichera un avertissement SSL (certificat auto-signé). Cliquez "Avancé" → "Continuer" — c'est normal en local !

---

## 🛠️ Stack technique

| Couche | Outil | Version | Rôle |
|--------|-------|---------|------|
| 🕷️ Scraping | Scrapy + BeautifulSoup | — | Extraction des prix depuis Jumia, Sports Direct, eBay |
| 📡 Streaming | Apache NiFi | 1.23.2 | Ingestion en temps réel des données scrapées |
| ⏱️ Orchestration | Apache Airflow | 2.9.1 | Planification des scrapers (cron quotidien 13h) |
| 💾 NoSQL | Google Cloud Bigtable | Émulateur | Stockage des données de prix (format wide-column) |
| 🗄️ SQL | PostgreSQL | 15 Alpine | 2 instances : metadata Airflow + données application |
| 🚀 Cache / Pub-Sub | Redis | 7 Alpine | Cache API, sessions JWT, WebSocket pub/sub |
| 🔄 Transformation | dbt-core | 1.8.2 | Modèles SQL : staging → intermediate → mart |
| 📊 Analyse | Python (SciPy, statsmodels) | — | Analyse statistique des tendances de prix |
| ⚡ Backend API | FastAPI + Uvicorn | — | API REST + WebSocket pour le frontend |
| 🖥️ Frontend | Angular 21 + Tailwind CSS | 21.2 | SPA avec dashboard et alertes de prix |
| 🔀 Reverse Proxy | Nginx | 1.25 | Point d'entrée unique : routage API + WebSocket + SPA |
| 🐳 Infra | Docker Compose | — | 12 services, 2 réseaux, orchestration locale |
| 🔄 CI/CD | GitHub Actions | — | 9 jobs : lint, build, test, SAST, secrets, CVE, Docker |

---

## ⚙️ Comment ça marche ?

### 1. Le scraping (Data Engineer)
Les scrapers Python dans `scrapers/` utilisent Selenium + BeautifulSoup pour extraire les prix des produits de nutrition sportive depuis 3 marketplaces :
- `scrapers/jumia/` → Scrape Jumia.ma
- `scrapers/sport-direct/` → Scrape SportsDirect.com
- `scrapers/ebay/` → Scrape eBay.com

Les données sont sauvegardées en fichiers JSON locaux (dans les sous-dossiers).

### 2. L'orchestration (Data Engineer)
Le DAG Airflow `price_intelligence_pipeline` (`airflow/dags/price_intelligence_dag.py`) :
- Se déclenche **tous les jours à 13h** (`schedule_interval='0 13 * * *'`)
- Lance les 3 scrapers **en parallèle** (Jumia, Sports Direct, eBay)
- Puis charge les résultats dans Bigtable via `load_all_to_bigtable.py`

```
task_jumia  ──┐
task_sport_direct ──┼──► task_load_bigtable
task_ebay   ──┘
```

### 3. L'ingestion en temps réel (Data Engineer)
Apache NiFi surveille les fichiers JSON produits par les scrapers et les ingère dans Bigtable en temps réel, en complément du batch Airflow.

### 4. Le stockage (DataOps)
- **Bigtable Emulator** : Stocke les données de prix (clé = `{source}#{product_id}#{timestamp}`, famille = `info`)
- **PostgreSQL App** : Stocke les utilisateurs, watchlists, alertes, sessions
- **PostgreSQL Airflow** : Stocke les métadonnées d'Airflow (état des DAGs, logs)
- **Redis** : Cache les réponses API, gère les sessions JWT, et sert de broker WebSocket

### 5. La transformation (Data Analyst)
dbt transforme les données brutes en modèles analytiques :
```
sources.yml ──► stg_prices.sql (staging) ──► int_price_daily.sql (intermediate) ──► mart_price_trends.sql (mart)
```
- **staging** → Nettoyage, typage, dédoublonnage
- **intermediate** → Agrégation par jour, calcul des moyennes
- **mart** → Modèles finaux pour le dashboard (tendances, comparaisons)

### 6. L'API et le frontend (Dev Fullstack)
- **FastAPI** (`backend/main.py`) expose les endpoints REST (`/api/v1/...`) et les WebSocket (`/ws/...`)
- **Angular** (`frontend/sportsintelligence/`) consomme l'API et affiche le dashboard
- **Nginx** route tout : `/api/*` → backend, `/ws/*` → backend (WebSocket), `/*` → frontend

---

## 📁 Structure du projet

```
price-intelligence/
│
├── 📋 .github/workflows/
│   └── ci.yml                 # Pipeline CI/CD (9 jobs)
│
├── ⏱️ airflow/
│   ├── dags/
│   │   └── price_intelligence_dag.py   # DAG principal (3 scrapers → Bigtable)
│   └── requirements.txt               # Dépendances Python Airflow
│
├── 📊 analytics/
│   └── requirements.txt       # Dépendances pour l'analyse statistique
│
├── ⚡ backend/
│   ├── Dockerfile             # Image FastAPI (Python 3.10)
│   ├── main.py                # Point d'entrée FastAPI (healthcheck + status)
│   ├── sql/                   # Schéma SQL app (auto-exécuté au 1er boot de postgres-app)
│   └── requirements.txt       # Dépendances Python backend
│
├── 🔄 dbt/
│   ├── dbt_project.yml        # Config du projet dbt
│   ├── profiles.yml           # Connexion BigQuery
│   ├── models/
│   │   ├── staging/           # stg_prices.sql
│   │   ├── intermediate/      # Agrégations
│   │   └── mart/              # Modèles finaux
│   ├── tests/
│   │   └── assert_price_positive.sql   # Test dbt
│   └── sources.yml            # Définition des sources
│
├── 📖 docs/
│   ├── 00_GUIDE_COMPLET.md    # Guide GitHub pas à pas
│   ├── DEMARRAGE.md           # Guide de démarrage pour les nouveaux
│   └── SEMAINE_1_PLANNING.md  # Planning semaine 1
│
├── 🖥️ frontend/
│   ├── Dockerfile             # Multi-stage : Node 20 → nginx:alpine
│   ├── nginx.conf             # Config SPA (try_files → index.html)
│   └── sportsintelligence/    # Code source Angular 21
│       ├── src/               # Composants, services, routes
│       ├── package.json       # Dépendances Angular + Tailwind
│       └── angular.json       # Config Angular CLI
│
├── 📡 nifi/
│   └── templates/             # Flows NiFi versionnés (.xml)
│
├── 🔀 nginx/
│   └── nginx.conf             # Reverse proxy (/api, /ws, /)
│
├── 🕷️ scrapers/
│   ├── jumia/                 # Scraper Jumia
│   ├── sport-direct/          # Scraper Sports Direct
│   ├── ebay/                  # Scraper eBay
│   ├── load_all_to_bigtable.py    # Charge les JSON dans Bigtable
│   ├── nifi_to_bigtable.py        # Script NiFi → Bigtable
│   └── spiders/                   # Spiders Scrapy legacy
│
├── 🐳 docker-compose.yml     # 12 services, 2 réseaux
├── 🐳 Dockerfile             # Image Airflow custom (Chrome + dépendances)
├── ⚙️ .env.example            # Template des variables d'environnement
├── 🔑 gcp-credentials.json.example  # Template clé GCP (dummy)
└── 📖 README.md               # ← Vous êtes ici !
```

---

## 🔄 Pipeline CI/CD (GitHub Actions)

Chaque push (sur **n'importe quelle branche**) et chaque pull request déclenchent automatiquement une pipeline de **9 jobs** :

```
  🔍 Lint           🏗️ Build (3 images Docker)
       \                  |
        \                 |          🛡️ SAST (Bandit)
         \                |          🔐 Secrets Scan
          └──► 🧪 Tests   |          📦 Dependency Scan
               Integration|          🐳 Docker Security (Trivy)
                    |      |          🏗️ IaC Scan (Checkov + Hadolint)
                    └──────┼──────────────┘
                           ▼
                  ✅ Merge Gate
```

| Job | Outil | Ce qu'il fait | Bloquant ? |
|-----|-------|---------------|:----------:|
| 🔍 Lint | Flake8 | Vérifie la syntaxe Python + validité des DAGs | ✅ |
| 🏗️ Build | Docker Buildx | Build les 3 images (Airflow, Backend, Frontend) | ✅ |
| 🧪 Tests | Docker Compose | Lance les 12 services, vérifie la connectivité entre eux | ✅ |
| 🛡️ SAST | Bandit | Détecte injections SQL, exec/eval dangereux, failles crypto | ✅ |
| 🔐 Secrets | TruffleHog + Gitleaks | Vérifie qu'aucun secret n'est dans l'historique Git | ✅ |
| 📦 Dépendances | pip-audit | Détecte les CVE connues dans les packages Python | ⚠️ Info |
| 🐳 Docker | Trivy | Scan des vulnérabilités dans les images Docker | ⚠️ Info |
| 🏗️ IaC | Checkov + Hadolint | Lint des 3 Dockerfiles et du docker-compose | ⚠️ Info |
| ✅ Gate | — | Bloque le merge si un check critique (✅) échoue | 🚫 |

> 📂 Les rapports de sécurité (Bandit, Trivy, pip-audit) sont archivés dans les **Artifacts** de chaque run GitHub Actions (conservés 30 jours).

---

## 🌿 Guide Git pour l'équipe

### Conventions de branches
```bash
# Format : feature/<rôle>/<description>
feature/dataops/ci-cd-pipeline
feature/engineer/scraper-jumia
feature/analyst/dbt-staging-models
feature/fullstack/auth-module
```

### Workflow quotidien
```bash
# 1. Se mettre à jour
git checkout develop
git pull origin develop

# 2. Créer sa branche de travail
git checkout -b feature/MON-ROLE/ma-tache

# 3. Travailler, commit régulièrement
git add .
git commit -m "feat: description claire de ce qui a été fait"

# 4. Pousser sa branche
git push origin feature/MON-ROLE/ma-tache

# 5. Créer une Pull Request sur GitHub → develop
#    Attendre que la CI passe ✅
#    Un autre membre review et approuve
#    Squash & Merge
```

### Convention de commits
```bash
feat: nouvelle fonctionnalité
fix: correction de bug
docs: documentation
refactor: refactoring sans changement de comportement
ci: modifications CI/CD
chore: maintenance, nettoyage
```

---

## 🔧 Dépannage

### Docker ne démarre pas ?
```bash
# Vérifier que Docker Desktop est lancé
docker ps

# Si rien ne s'affiche → ouvrir Docker Desktop puis réessayer
docker-compose up -d --build
```

### Airflow-init crash ?
```bash
# Repartir de zéro (supprime les volumes)
docker-compose down -v
docker-compose up -d --build
```

### NiFi ne répond pas ?
```bash
# NiFi met ~60 secondes à démarrer (Java = lent)
docker logs nifi --tail 20

# Chercher "NiFi has started" dans les logs
```

### Backend "unhealthy" ?
```bash
# Vérifier les logs du backend
docker logs backend --tail 20

# Si "Could not import module main" → le fichier main.py manque dans backend/
```

### Port déjà utilisé ?
```bash
# Identifier quel processus utilise le port (ex: 5432)
netstat -ano | findstr :5432

# Arrêter le processus ou changer le port dans docker-compose.yml
```

---

## 🔒 Sécurité

### Fichiers protégés par `.gitignore`
| Fichier | Contenu | Risque si poussé |
|---------|---------|-----------------|
| `.env` | Mots de passe PostgreSQL, JWT secret, credentials NiFi | 🔴 Critique |
| `gcp-credentials.json` | Clé privée Google Cloud (Service Account) | 🔴 Critique |
| `logs/` | Logs d'exécution Airflow | 🟡 Moyen |
| `scrapers/*/data/` | Données scrapées (JSON) | 🟢 Faible |

### Bonnes pratiques
1. **Ne jamais** mettre de vrais secrets dans les fichiers `.example`
2. **Toujours** utiliser `cp .env.example .env` et modifier le `.env` local
3. Les **scans de secrets** (TruffleHog + Gitleaks) dans la CI/CD bloquent automatiquement le merge si un secret est détecté
4. Les mots de passe par défaut (`admin123`, `airflow_secret`, `app_secret`) sont **uniquement pour le dev local** — ils doivent être changés en production

---

## 📅 Roadmap

- [x] **Semaine 1** — Environnement local Docker (12 services), structure Git
- [x] **Semaine 1.5** — Pipeline CI/CD complète (9 jobs : lint, build, test, SAST, secrets, Docker scan)
- [ ] **Semaine 2** — Pipeline data complet : scrape → NiFi → Bigtable → dbt → BigQuery
- [ ] **Semaine 3** — Backend FastAPI (auth, CRUD, WebSocket) + Frontend Angular (dashboard, alertes)
- [ ] **Semaine 4** — Déploiement GCP + analyses statistiques + démo vidéo

---

## 📚 Documentation complémentaire

| Document | Contenu |
|----------|---------|
| [DEMARRAGE.md](./docs/DEMARRAGE.md) | Guide de démarrage détaillé |
| [00_GUIDE_COMPLET.md](./docs/00_GUIDE_COMPLET.md) | Guide Git pas à pas (5 phases) |
| [SEMAINE_1_PLANNING.md](./docs/SEMAINE_1_PLANNING.md) | Planning détaillé semaine 1 |

---

<p align="center">
  <b>🚀 Price Intelligence Platform</b><br>
  Fait avec ❤️ par l'équipe Data Engineering — LSI_1 2025-2026
</p>
