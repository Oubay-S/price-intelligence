# 📋 CHECKLIST — Tous les fichiers à télécharger

> ✅ Télécharge TOUS ces fichiers. Ils forment l'architecture complète du projet.

---

## 🟢 FICHIERS CRITIQUES (obligatoires)

```
✅ docker-compose.yml          → Lance NiFi, Airflow, Bigtable local, PostgreSQL
✅ .gitignore                  → Protège tes secrets (jamais commiter .env!)
✅ .env.example                → Template à copier en .env (sans secrets)
✅ README.md                   → Page d'accueil du projet
✅ DEMARRAGE.md                → Guide de démarrage pour toute l'équipe
✅ ARCHITECTURE.md             → Diagramme de la structure des dossiers
✅ 00_GUIDE_COMPLET.md         → Ce que tu lis en ce moment
```

---

## 🟡 FICHIERS AIRFLOW (Orchestration batch)

```
✅ airflow/dags/example_hello_dag.py
   → DAG d'exemple (point de départ pour le Data Engineer)

✅ airflow/requirements.txt
   → Packages Python pour Airflow (google-cloud-bigtable, dbt, etc.)
```

---

## 🔵 FICHIERS DBT (Transformations SQL)

```
✅ dbt/dbt_project.yml
   → Configuration du projet dbt (nom, chemins, matérialisation)

✅ dbt/profiles.yml
   → Connexions BigQuery/Bigtable pour dev/ci/prod

✅ dbt/packages.yml
   → Dépendances dbt (dbt-utils, etc.)

✅ dbt/models/staging/stg_prices.sql
   → Nettoyage des données brutes depuis Bigtable

✅ dbt/models/intermediate/int_price_daily.sql
   → Agrégations journalières (moyenne, médiane, std)

✅ dbt/models/mart/mart_price_trends.sql
   → Table finale avec signaux d'alerte pour le dashboard

✅ dbt/tests/assert_price_positive.sql
   → Test custom dbt (vérifie que les prix > 0)
```

---

## 🟣 FICHIERS SCRAPERS (Web scraping)

```
✅ scrapers/spiders/myprotein_spider.py
   → Spider Scrapy pour MyProtein (à adapter par le Data Engineer)

✅ scrapers/settings.py
   → Configuration Scrapy (respecte robots.txt, rate limit)

✅ scrapers/requirements.txt
   → Packages Python (scrapy, beautifulsoup4, selenium, google-cloud-bigtable)
```

---

## 🟠 FICHIERS STREAMLIT (Dashboard)

```
✅ streamlit/app.py
   → Application principale (pages, accueil, prix en direct, stats)

✅ streamlit/requirements.txt
   → Packages Python (streamlit, plotly, pandas, google-cloud-bigtable)
```

---

## 🟤 FICHIERS ANALYTICS (Jupyter + Stats Python)

```
✅ analytics/requirements.txt
   → Packages Python (pandas, scipy, statsmodels, plotly, jupyter)
```

---

## ⚫ FICHIERS CI/CD & INFRASTRUCTURE

```
✅ .github/workflows/ci.yml
   → Pipeline GitHub Actions (vérifie la qualité du code à chaque PR)

✅ infra/init_bigtable.py
   → Script pour créer les tables dans l'émulateur Bigtable
```

---

## 📊 RÉSUMÉ PAR RÔLE

### DataOps (toi) 👈 **C'est toi**
Télécharge :
- ✅ docker-compose.yml
- ✅ .gitignore
- ✅ .env.example
- ✅ DEMARRAGE.md
- ✅ .github/workflows/ci.yml
- ✅ infra/init_bigtable.py

**Action immédiate :**
1. Copie les fichiers dans un dossier `price-intelligence/`
2. Suis le guide `00_GUIDE_COMPLET.md`
3. Crée le repo GitHub
4. Pousse tout
5. Invite les 3 autres

### Data Engineer 👨‍💼
Télécharge :
- ✅ airflow/dags/example_hello_dag.py
- ✅ airflow/requirements.txt
- ✅ scrapers/spiders/myprotein_spider.py
- ✅ scrapers/settings.py
- ✅ scrapers/requirements.txt

### Data Analyst 📊
Télécharge :
- ✅ dbt/ (dossier complet)
- ✅ analytics/requirements.txt

### Dev Fullstack 💻
Télécharge :
- ✅ streamlit/app.py
- ✅ streamlit/requirements.txt

---

## 🎯 ÉTAPES D'APRÈS TÉLÉCHARGEMENT

1. **Tous** : Clonez depuis GitHub
   ```bash
   git clone https://github.com/USERNAME/price-intelligence.git
   cd price-intelligence
   cp .env.example .env
   ```

2. **DataOps** : Démarre l'infra
   ```bash
   docker-compose up -d
   ```

3. **Tous** : Vérifiez que c'est up
   ```bash
   docker-compose ps
   ```

4. **Chacun** : Crée sa branche
   ```bash
   git checkout -b feature/MON-ROLE/ma-tâche
   ```

5. **Semaine 1** : Les contours généraux de chaque composant
6. **Semaine 2** : Intégration complète du pipeline
7. **Semaine 3** : Finesse (tests, dashboard, analyses)
8. **Semaine 4** : Déploiement GCP + démo vidéo

---

## 🚨 IMPORTANT — CE QU'ON NE TÉLÉCHARGE PAS

```
❌ .env             (jamais ! Secret avec tes mots de passe)
❌ *.log            (logs Airflow — trop gros)
❌ __pycache__/     (cache Python — ignoré par .gitignore)
❌ dbt/target/      (artefacts compilés — ignorés par .gitignore)
❌ data/*.csv       (données brutes — ignorées par .gitignore)
❌ gcp-credentials.json (clés GCP — jamais !)
```

Le `.gitignore` bloque automatiquement ces fichiers. ✅

---

✨ **Prêt ?** Suis le `00_GUIDE_COMPLET.md` et on y va !
