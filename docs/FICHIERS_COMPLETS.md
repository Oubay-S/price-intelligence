# 📂 ARBORESCENCE COMPLÈTE — Tous les fichiers

Copie cette structure sur ta machine pour créer le projet.

```
price-intelligence/                  ← Dossier racine (clone sur GitHub)
│
├── 📌 FICHIERS À LIRE D'ABORD
│   ├── COMMENCER_ICI.md             ✅ À lire EN PREMIER (checklist)
│   ├── 00_GUIDE_COMPLET.md          ✅ Guide étape par étape GitHub
│   ├── 01_FICHIERS_A_TELECHARGER.md ✅ Explication des fichiers
│   ├── README.md                    ✅ Présentation du projet
│   ├── DEMARRAGE.md                 ✅ Guide pour l'équipe
│   └── ARCHITECTURE.md              ✅ Diagramme de la structure
│
├── 🐳 INFRASTRUCTURE DOCKER
│   ├── docker-compose.yml           ✅ Lance 6 services (NiFi, Airflow, etc.)
│   ├── .env.example                 ✅ Variables d'env (template)
│   ├── .gitignore                   ✅ Protège tes secrets
│   └── GIT_SETUP.sh                 ✅ Commandes Git à copier
│
├── ⚙️ AIRFLOW (Data Orchestration)
│   ├── dags/
│   │   └── example_hello_dag.py     ✅ DAG d'exemple (à enrichir)
│   ├── plugins/                     📁 Dossier (vide pour l'instant)
│   ├── logs/                        📁 Dossier (ignoré par Git)
│   └── requirements.txt             ✅ google-cloud-bigtable, dbt-core
│
├── 📊 DBT (Transformations SQL)
│   ├── dbt_project.yml              ✅ Configuration du projet dbt
│   ├── profiles.yml                 ✅ Connexions dev/ci/prod
│   ├── packages.yml                 ✅ Dépendances (dbt-utils)
│   │
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_prices.sql       ✅ Nettoyage données brutes
│   │   │   └── .gitkeep             📝 (garde le dossier)
│   │   │
│   │   ├── intermediate/
│   │   │   ├── int_price_daily.sql  ✅ Agrégations journalières
│   │   │   └── .gitkeep
│   │   │
│   │   └── mart/
│   │       ├── mart_price_trends.sql ✅ Table finale pour dashboard
│   │       └── .gitkeep
│   │
│   └── tests/
│       ├── assert_price_positive.sql ✅ Test custom (prix > 0)
│       └── .gitkeep
│
├── 🕷️ SCRAPERS (Web Scraping)
│   ├── spiders/
│   │   ├── myprotein_spider.py      ✅ Spider Scrapy (exemple)
│   │   └── __init__.py              ✅ (fichier Python vide)
│   │
│   ├── settings.py                  ✅ Config Scrapy (robots.txt, rate limit)
│   ├── requirements.txt             ✅ scrapy, beautifulsoup4, selenium
│   └── scrapy.cfg                   📁 (créé automatiquement par Scrapy)
│
├── 💻 STREAMLIT (Dashboard Frontend)
│   ├── app.py                       ✅ Application principale (3 pages)
│   ├── pages/                       📁 Dossier (pages additionnelles)
│   ├── components/                  📁 Dossier (composants réutilisables)
│   └── requirements.txt             ✅ streamlit, plotly, pandas
│
├── 📈 ANALYTICS (Python Stats)
│   ├── notebooks/                   📁 Dossier (Jupyter notebooks)
│   └── requirements.txt             ✅ pandas, scipy, statsmodels, jupyter
│
├── 🔧 INFRASTRUCTURE & SCRIPTS
│   ├── init_bigtable.py             ✅ Crée les tables Bigtable
│   └── terraform/                   📁 Dossier (pour la semaine 4)
│
├── 🔄 CI/CD & VERSION CONTROL
│   ├── .github/
│   │   └── workflows/
│   │       └── ci.yml               ✅ GitHub Actions (lint, tests, validation)
│   │
│   ├── nifi/
│   │   └── templates/               📁 Dossier (flows NiFi versionnés)
│   │
│   └── (git branches)
│       ├── main                     → Branche stable (démos, prod)
│       └── develop                  → Branche d'intégration de l'équipe
│
└── 📝 NOTES
    ├── .env                         ❌ À NE PAS COMMITER (secret)
    ├── airflow/logs/                ❌ À NE PAS COMMITER (trop gros)
    ├── dbt/target/                  ❌ À NE PAS COMMITER (généré)
    └── data/                        ❌ À NE PAS COMMITER (données brutes)
```

---

## ✅ CHECKLIST DE TÉLÉCHARGEMENT

**Total : 30+ fichiers | 8 dossiers**

### Fichiers racine (à télécharger)
- [ ] COMMENCER_ICI.md
- [ ] 00_GUIDE_COMPLET.md
- [ ] 01_FICHIERS_A_TELECHARGER.md
- [ ] README.md
- [ ] DEMARRAGE.md
- [ ] ARCHITECTURE.md
- [ ] docker-compose.yml
- [ ] .gitignore
- [ ] .env.example
- [ ] GIT_SETUP.sh

### `.github/workflows/` (1 fichier)
- [ ] ci.yml

### `airflow/` (3 fichiers)
- [ ] dags/example_hello_dag.py
- [ ] requirements.txt
- [ ] logs/.gitkeep (crée le dossier vide)

### `dbt/` (8 fichiers)
- [ ] dbt_project.yml
- [ ] profiles.yml
- [ ] packages.yml
- [ ] models/staging/stg_prices.sql
- [ ] models/intermediate/int_price_daily.sql
- [ ] models/mart/mart_price_trends.sql
- [ ] tests/assert_price_positive.sql
- [ ] Crée les dossiers vides (staging, intermediate, mart, tests)

### `scrapers/` (3 fichiers)
- [ ] spiders/myprotein_spider.py
- [ ] spiders/__init__.py
- [ ] settings.py
- [ ] requirements.txt

### `streamlit/` (2 fichiers)
- [ ] app.py
- [ ] requirements.txt
- [ ] Crée dossiers vides : pages/, components/

### `analytics/` (1 fichier)
- [ ] requirements.txt
- [ ] Crée dossier vide : notebooks/

### `nifi/` (1 dossier)
- [ ] Crée dossier vide : templates/

### `infra/` (1 fichier)
- [ ] init_bigtable.py

---

## 🎯 TAILLES APPROXIMATIVES

| Fichier | Taille |
|---------|--------|
| docker-compose.yml | 12 KB |
| .gitignore | 3 KB |
| dbt/*.sql (7 fichiers) | ~15 KB |
| Python files (5 fichiers) | ~8 KB |
| requirements.txt (4 fichiers) | ~2 KB |
| Markdown (7 fichiers) | ~25 KB |
| **Total** | **~70 KB** |

**Très léger !** Téléchargement en quelques secondes.

---

## 💡 CONSEIL

Utilise cette structure **exacte**. Les chemins dans `docker-compose.yml` et les `requirements.txt` dépendent de cette arborescence.

Si tu mets les fichiers à un autre endroit → des chemins seront cassés → Docker ne démarrera pas. ⚠️

Lis `COMMENCER_ICI.md` une fois tout téléchargé. C'est la clé ! 🔑
