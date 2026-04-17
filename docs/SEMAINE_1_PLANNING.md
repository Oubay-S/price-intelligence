# 📅 SEMAINE 1 — Planning jour par jour

> **Objectif** : Environnement local up, pipeline vide qui tourne, équipe synchronisée.

---

## 🗓️ JOUR 1 (Lundi) — Setup GitHub & Docker

### Matin (1h)
```
[ ] Lire COMMENCER_ICI.md
[ ] Lire 00_GUIDE_COMPLET.md
[ ] Télécharger TOUS les fichiers
[ ] Organiser dans dossier price-intelligence/
```

### Midi (1h)
```
[ ] Créer repo GitHub
[ ] git init + configurer user.name/email
[ ] git add . && git commit
[ ] git push vers GitHub
[ ] Créer branche develop
```

### Après-midi (1h)
```
[ ] Inviter 3 collègues comme collaborators sur GitHub
[ ] Écrire le message à envoyer aux collègues
[ ] Vérifier que le .gitignore bloque .env + logs
[ ] GitHub Actions CI s'exécute (2-3 min) ✅
```

### Fin de jour
✅ **Status check** :
- Repo GitHub créé et privé
- Tous les fichiers poussés
- 3 collègues invités
- Branche develop existe
- 0 erreur CI

---

## 🗓️ JOUR 2 (Mardi) — Équipe démarre

### Matin (1h)
```
[ ] Verifier que les 3 collègues ont clonez
[ ] git clone ... && cd price-intelligence
[ ] cp .env.example .env
[ ] docker-compose up -d (chez chacun)
```

### Midi (1h)
```
[ ] StandUp équipe : vérifier que Docker démarre partout
[ ] Data Engineer : docker-compose logs airflow-scheduler
[ ] Data Analyst : docker-compose logs nifi
[ ] Dev Fullstack : docker-compose ps
```

### Après-midi (2h)
```
[ ] Chacun crée sa branche feature
    - git checkout -b feature/MON-ROLE/setup
[ ] Test accès Airflow http://localhost:8080
[ ] Test accès NiFi https://localhost:8443/nifi
[ ] Tester les logins (voir .env)
```

### Fin de jour
✅ **Status check** :
- Docker tourne sur les 4 machines
- Airflow accessible + login OK
- NiFi accessible + login OK
- Bigtable emulator healthy
- 4 branches feature créées

---

## 🗓️ JOUR 3 (Mercredi) — Initialiser Bigtable

### Matin (30 min)
```
[ ] DataOps : lancer init_bigtable.py
    pip install google-cloud-bigtable
    export BIGTABLE_EMULATOR_HOST=localhost:8086
    python infra/init_bigtable.py
```

### Midi (1h)
```
[ ] StandUp : vérifier que Bigtable est initialisé
[ ] DataOps teste la connexion Bigtable
[ ] Créer un test simple Python pour vérifier
```

### Après-midi (2h)
```
[ ] Data Engineer : créer un 1er spider simple
    - clone le template myprotein_spider.py
    - scrape UNE PAGE de test (MyProtein ou autre)
    - exporte en CSV local pour tester
    
[ ] Data Analyst : DAG Airflow qui lance dbt compile
    - crée un DAG qui fait : airflow dbt compile
    - vérifie que ça marche (pas d'erreur de syntaxe)
    
[ ] Dev Fullstack : Streamlit affiche "Hello world"
    - streamlit run streamlit/app.py
    - page Accueil affiche un titre + info basique
    
[ ] DataOps : GitHub Actions passa tous les tests
    - chaque commit lance ci.yml
    - 0 erreurs de lint
```

### Fin de jour
✅ **Status check** :
- Bigtable table "prices" créée
- 1er spider scrape une page
- 1er DAG compile sans erreur
- Streamlit démarre + affiche quelque chose
- CI passe pour tout le monde

---

## 🗓️ JOUR 4 (Jeudi) — Connexions entre les briques

### Matin (2h)
```
[ ] Data Engineer : spider scrape → CSV local
[ ] Data Analyst : DAG Airflow charge le CSV → Bigtable (test)
[ ] DataOps : crée un petit hook Airflow → Bigtable
    (voir bigtable_hook.py en exemple)
```

### Midi (1h)
```
[ ] StandUp : tester la chaîne complète
    Spider → CSV → Airflow → Bigtable
```

### Après-midi (2h)
```
[ ] Data Analyst : dbt lit depuis Bigtable
    - dbt models peuvent accéder aux données testées
    - dbt compile sans erreur sur les modèles
    
[ ] Dev Fullstack : Streamlit lit depuis Bigtable
    - création d'une connexion test Bigtable
    - une page affiche "X produits trouvés"
    
[ ] Chacun : fait un 1er commit sur sa branche
    git add . && git commit -m "feat: init setup MONROLE"
    git push origin feature/ROLE/setup
```

### Fin de jour
✅ **Status check** :
- Spider scrape → Airflow → Bigtable ✅
- dbt accède aux données ✅
- Streamlit accède aux données ✅
- 4 branches avec code initial

---

## 🗓️ JOUR 5 (Vendredi) — Intégration & PR

### Matin (1h)
```
[ ] Chacun : fait une Pull Request vers develop
    1. Va sur GitHub
    2. Crée PR : feature/* → develop
    3. Décrit ce qu'il a fait
    4. Demand review à 1 autre membre
```

### Midi (1h)
```
[ ] Code Review croisée
    Data Engineer ← → Data Analyst
    Dev Fullstack ← → DataOps
    
[ ] Corrections si besoin
    (petits bugs, style Python, comments)
```

### Après-midi (2h)
```
[ ] Merge des 4 PRs vers develop
    - CI passe ? ✅ OK
    - Revue approuvée ? ✅ OK
    - "Squash and merge"
    - Supprime la branche feature
```

### Fin de jour
✅ **Status check (fin de semaine 1) :**
- Branche develop = code intégré de tous
- Pipeline vide mais tourne : Scraper → Airflow → Bigtable → dbt → Streamlit
- Docker-compose up -d → tout démarre sans erreur
- Équipe synchronisée et a collaboré
- 4 branches cleanées, develop à jour

---

## 📊 Checklist Semaine 1

- [ ] J1 : Repo GitHub up + équipe invitée
- [ ] J2 : Docker tourne chez tout le monde
- [ ] J3 : Bigtable initialisé, chacun a commencé
- [ ] J4 : Chaîne complète connectée
- [ ] J5 : Code intégré dans develop, 1er démo local

**Si tout est ✅ vendredi 17h → Semaine 1 réussie ! 🎉**

---

## ⚠️ Si tu es en retard

**Jeudi 18h et pas fini ?**
```
→ Mercredi dernier sprint : demande de l'aide sur Slack
→ Fais juste la partie qui bloque (ex: Docker)
→ Le reste peut attendre lundi
```

**Vendredi 14h et pas de PR ?**
```
→ Push quand même ta branche (ton code n'est pas perdu)
→ Crée la PR même incomplète (c'est pour la review)
→ Tes collègues peuvent t'aider lundi
```

---

## 🚀 Semaine 2 (aperçu)

Une fois que Semaine 1 est ✅ :

- Data Engineer : vraies données scrappées (2-3 marques)
- Data Analyst : modèles dbt enrichis (agrégations, anomalies)
- Dev Fullstack : dashboard avec graphiques + data
- DataOps : CI/CD amélioré, monitoring des logs

À lundi ! 💪
