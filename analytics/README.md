# Price Intelligence - Data Analysis

Espace professionnel pour la partie **Data Analyst** du projet Price Intelligence.

## Rôle

Le travail Data Analyst commence après la collecte et le stockage des données. Il couvre : compréhension des données, nettoyage analytique, statistiques descriptives, statistiques inférentielles, visualisations, recommandations business et rapport final.

## Ordre d'exécution

1. `notebooks/01_data_understanding.ipynb`
2. `notebooks/02_data_cleaning.ipynb`
3. `notebooks/03_exploratory_analysis.ipynb`
4. `notebooks/04_statistical_tests.ipynb`
5. `notebooks/05_final_insights.ipynb`

## Installation

```bash
conda activate price-analytics
cd C:\Users\Admin\Desktop\data-analysis
pip install -r requirements.txt
```

## Dashboard

```bash
streamlit run dashboard/app.py
```

## Couverture du PDF

- Statistiques descriptives : moyenne, médiane, écart-type, distributions, tendances par catégorie.
- Time-series plots : notebook 03.
- Tests inférentiels : ANOVA, Kruskal-Wallis, Mann-Whitney, corrélations.
- Régression : notebook 04 avec variables store, category, stars, discount et time si plusieurs dates existent.
- Intervalles de confiance : notebook 04.
- Power analysis : notebook 04.
- Effect size : notebook 04.
- Dashboard Streamlit : `dashboard/app.py`.


## Source officielle BigQuery

Après le dernier merge, la table officielle est :

```text
price-intelligence-495411.price_intelligence.products
```

Profil observé dans BigQuery :

```text
total_rows       = 20908
null_name        = 192
null_price       = 192
store values     = ebay, jumia, sport-direct, unknown
```

Les notebooks 01 et 02 chargent maintenant BigQuery en priorité. Si l'accès BigQuery n'est pas disponible dans Anaconda, placer un export CSV de la table ici :

```text
outputs/raw_data/bigquery_products_export.csv
```


## Regeneration obligatoire apres mise a jour BigQuery

Les notebooks utilisent BigQuery live comme source officielle: `price-intelligence-495411.price_intelligence.products`.
Les anciens fichiers generes ont ete archives dans `_backup_professional_bigquery_fix_20260520_154303/old_outputs_archived` pour eviter de melanger anciennes et nouvelles donnees.

Ordre professionnel d'execution:
1. `notebooks/01_data_understanding.ipynb`
2. `notebooks/02_data_cleaning.ipynb`
3. `notebooks/03_exploratory_analysis.ipynb`
4. `notebooks/04_statistical_tests.ipynb`
5. `notebooks/05_final_insights.ipynb`

Controle attendu dans le notebook 01: environ 20 908 lignes brutes, `sport-direct` dans les plateformes, et environ 192 prix nulls dans la table brute.
Si le notebook affiche `local_json_fallback`, `bigquery_export`, ou environ 2 251 lignes, il faut fermer/reouvrir le notebook et relancer le kernel.
