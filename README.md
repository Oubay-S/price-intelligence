# 🛒 Price Intelligence Platform
### Plateforme hybride Batch + Streaming de veille tarifaire e-commerce (nutrition sportive)

> Projet académique — Data Engineering & Analytics · Pr. ELAACHAK · 2025-2026

---

## 🏗️ Architecture

```
Scrapy (Web Scraping)
        │
        ├──[Temps réel]──▶ Apache NiFi ──▶ Google Cloud Bigtable
        │                                         │
        └──[Batch quotidien]──▶ Airflow DAGs ─────┘
                                    │
                                    ▼
                              dbt (Transformations SQL)
                                    │
                                    ▼
                    Python Analytics (SciPy / statsmodels)
                                    │
                                    ▼
                         Streamlit Dashboard
```

## 👥 Équipe

| Rôle | Responsabilité | Dossier |
|------|---------------|---------|
| Data Engineer | Scrapers + DAGs Airflow | `scrapers/`, `airflow/` |
| Data Analyst | dbt models + Stats Python | `dbt/`, `analytics/` |
| Dev Fullstack | Dashboard Streamlit | `streamlit/` |
| DataOps | Infra Docker + CI/CD | `docker-compose.yml`, `.github/`, `infra/` |

## 🚀 Démarrage rapide

```bash
git clone https://github.com/VOTRE-ORG/price-intelligence.git
cd price-intelligence
cp .env.example .env
docker-compose up -d
```

Accès :
- **Airflow** → http://localhost:8080 (admin / admin123)
- **NiFi** → https://localhost:8443/nifi (admin / adminpassword123)

📖 Voir [DEMARRAGE.md](./docs/DEMARRAGE.md) pour le guide complet.

## 🛠️ Stack technique

| Couche | Outil |
|--------|-------|
| Scraping | Scrapy, BeautifulSoup |
| Streaming | Apache NiFi 1.23 |
| Orchestration | Apache Airflow 2.9 |
| Stockage | Google Cloud Bigtable (émulateur local) |
| Transformation | dbt-core |
| Analyse | Python, SciPy, statsmodels |
| Dashboard | Streamlit |
| Infra | Docker, GitHub Actions |

## 📁 Structure du projet

```
price-intelligence/
├── .github/workflows/      # CI/CD GitHub Actions
├── airflow/
│   ├── dags/               # DAGs Airflow (Python)
│   └── plugins/            # Hooks custom
├── analytics/              # Notebooks Python
├── dbt/
│   ├── models/             # Transformations SQL
│   └── tests/              # Tests dbt
├── docs/                   # Guides et documentations du projet
├── infra/                  # Scripts infrastructure
├── nifi/templates/         # Flows NiFi versionnés
├── scrapers/               # Spiders Scrapy
├── streamlit/              # Dashboard web
├── docker-compose.yml      # Environnement local complet
└── .env.example            # Template de configuration
```

## 📅 Roadmap

- [x] **Semaine 1** — Environnement local Docker, structure Git
- [ ] **Semaine 2** — Pipeline complet : scrape → NiFi → Bigtable → dbt
- [ ] **Semaine 3** — Dashboard Streamlit + analyses statistiques
- [ ] **Semaine 4** — Déploiement GCP + démo vidéo
