# Rapport Final - Data Analysis

Date de g?n?ration : 2026-05-24 15:58

## R?sum? Ex?cutif

| summary_point                                                                                   |
|:------------------------------------------------------------------------------------------------|
| L'analyse finale porte sur 6,306 produits nettoyés, répartis sur 3 plateformes et 7 catégories. |
| Le prix médian global est de 317.74, tandis que le prix moyen est de 427.51.                    |
| La plateforme la moins chère selon le prix médian est jumia (179.00).                           |
| La plateforme la plus chère selon le prix médian est ebay (342.16).                             |
| La catégorie la plus chère selon le prix médian est football (381.47).                          |
| La plateforme avec la remise médiane la plus élevée est sport-direct (45.00%).                  |

## Recommandations

| priorite   | recommandation                                                                                                                        | justification                                             |
|:-----------|:--------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------|
| Haute      | Utiliser jumia comme référence pour les prix compétitifs, car cette plateforme présente le prix médian le plus bas.                   | Comparaison des prix médians par plateforme.              |
| Moyenne    | Surveiller ebay séparément, car ses prix médians sont plus élevés et peuvent refléter des produits premium ou des annonces atypiques. | Prix médian le plus élevé par plateforme.                 |
| Haute      | Prioriser le monitoring de la catégorie football, car elle présente le prix médian le plus élevé.                                     | Catégorie avec le plus fort potentiel d'impact tarifaire. |
| Moyenne    | Analyser les promotions de sport-direct pour identifier les stratégies de discount les plus agressives.                               | Remise médiane la plus élevée par plateforme.             |
| Haute      | Conserver un indicateur d'outlier dans les pipelines analytiques pour éviter que les prix extrêmes biaisent les KPIs.                 | Les outliers influencent fortement la moyenne des prix.   |

## Limites de l'Analyse

| limitation                                                                                                                                                     |
|:---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Les données analysées proviennent d'un scraping ponctuel ou d'une période limitée ; elles ne représentent pas nécessairement une tendance long terme.          |
| Les prix peuvent être exprimés dans des contextes différents selon les plateformes, ce qui peut créer des écarts non liés uniquement à la stratégie tarifaire. |
| Certaines colonnes comme les remises ou les notes clients peuvent contenir des valeurs manquantes.                                                             |
| La comparaison entre plateformes peut être influencée par des produits non strictement équivalents.                                                            |
| Les outliers ont été traités avec une méthode statistique IQR ; certains peuvent être de vrais produits premium et non des erreurs.                            |

## Prochaines ?tapes

| next_step                                                                                              |
|:-------------------------------------------------------------------------------------------------------|
| Connecter l'analyse directement à BigQuery lorsque les tables finales sont stabilisées.                |
| Ajouter une dimension temporelle avec plusieurs jours de scraping pour analyser les tendances de prix. |
| Créer une table de matching produit pour comparer des produits équivalents entre plateformes.          |
| Ajouter des alertes sur fortes variations de prix.                                                     |
| Intégrer les KPIs finaux dans un dashboard Streamlit ou Looker Studio.                                 |
