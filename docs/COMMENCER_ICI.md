# ⚡ ACTION IMMÉDIATE — À faire MAINTENANT

Tu as 4 fichiers à lire EN CET ORDRE. Fais-le maintenant.

---

## 📖 LECTURE (5 minutes)

Lis dans cet ordre **EXACT** :

1. **`01_FICHIERS_A_TELECHARGER.md`** ← Commence ICI
   - Comprends ce que tu télécharges et pourquoi
   
2. **`00_GUIDE_COMPLET.md`** ← C'est le guide étape par étape
   - Les 5 phases pour mettre le code sur GitHub
   - Suivre ligne par ligne
   
3. **`DEMARRAGE.md`** ← À envoyer à tes collègues
   - Comment lancer l'environnement Docker
   - Comment accéder aux interfaces web
   
4. **`README.md`** ← Présentation générale du projet
   - Aperçu architecture
   - Stack tech
   - Roadmap 4 semaines

---

## 💾 TÉLÉCHARGEMENT (2 minutes)

**Télécharge tous ces fichiers** dans un dossier appelé `price-intelligence/` :

**Fichiers racine :**
```
✅ docker-compose.yml
✅ .gitignore
✅ .env.example
✅ README.md
✅ DEMARRAGE.md
✅ ARCHITECTURE.md
✅ 00_GUIDE_COMPLET.md
✅ 01_FICHIERS_A_TELECHARGER.md
✅ GIT_SETUP.sh
```

**Dossier `.github/workflows/` :**
```
✅ ci.yml
```

**Dossier `airflow/` :**
```
✅ dags/example_hello_dag.py
✅ requirements.txt
```

**Dossier `dbt/` :**
```
✅ dbt_project.yml
✅ profiles.yml
✅ packages.yml
✅ models/staging/stg_prices.sql
✅ models/intermediate/int_price_daily.sql
✅ models/mart/mart_price_trends.sql
✅ tests/assert_price_positive.sql
```

**Dossier `scrapers/` :**
```
✅ settings.py
✅ requirements.txt
✅ spiders/myprotein_spider.py
```

**Dossier `streamlit/` :**
```
✅ app.py
✅ requirements.txt
```

**Dossier `analytics/` :**
```
✅ requirements.txt
```

**Dossier `infra/` :**
```
✅ init_bigtable.py
```

---

## 🚀 EXÉCUTION (20 minutes)

**Suis le `00_GUIDE_COMPLET.md` étape par étape** :

### Phase 1 : GitHub (5 min)
```
1. Crée un compte GitHub si pas encore
2. Crée un nouveau repo "price-intelligence"
3. Copie l'URL du repo
```

### Phase 2 : Dossier local (5 min)
```
4. Ouvre un terminal
5. Crée le dossier : mkdir price-intelligence && cd price-intelligence
6. Lance : git init
7. Configure : git config user.name "Ton Nom" + git config user.email "email"
8. Copie tous les fichiers téléchargés ici
9. Lance : git status (vérifie qu'il n'y a pas .env)
```

### Phase 3 : Commit (5 min)
```
10. git add .
11. git commit -m "feat: initialisation du projet price-intelligence..."
```

### Phase 4 : GitHub (3 min)
```
12. git branch -M main
13. git remote add origin <L'URL COPIÉE À L'ÉTAPE 3>
14. git push -u origin main
```

### Phase 5 : Équipe (2 min)
```
15. git checkout -b develop && git push origin develop && git checkout main
16. Va sur GitHub → Settings → Collaborators → Invite les 3 autres
```

---

## ✅ VÉRIFICATION

Après la Phase 5, vérifie sur GitHub :
```
✅ Tu vois tous les fichiers dans le repo
✅ 2 branches : main et develop
✅ Les 3 collègues sont invités
✅ Aucun .env, aucun credentials, aucun logs
```

---

## 📲 MESSAGE POUR LES COLLÈGUES

Envoie-leur ce message :

---

> **Salut ! 🚀**
>
> Le repo est prêt !
>
> **Clonez avec :**
> ```bash
> git clone https://github.com/USERNAME/price-intelligence.git
> cd price-intelligence
> cp .env.example .env
> docker-compose up -d --build
> ```
>
> **Puis lisez :** `DEMARRAGE.md`
>
> **Créez votre branche :**
> ```bash
> git checkout -b feature/VOTRE-ROLE/nom-de-la-tâche
> ```
>
> **Workflow :** feature → Pull Request → develop → main (fin du projet)
>
> Questions ? Ouvrez une issue GitHub.
>
> À bientôt au standup ! 💪

---

## 🎯 APRÈS ÇA (Semaine 1)

1. **Demain** : Les 3 collègues clonent et lancent `docker-compose up -d --build`
2. **J+1** : Vérifiez tous que Airflow + NiFi + Bigtable tournent
3. **J+2** : Initialisez Bigtable : `python infra/init_bigtable.py`
4. **Semaine 1 fin** : Chacun crée un exemple simple dans sa branche
   - Data Engineer : 1er spider qui scrape une page
   - Data Analyst : 1er modèle dbt qui compile
   - Dev Fullstack : Dashboard Streamlit affiche "Hello"
   - DataOps (toi) : Vérifie que le CI passe et les données fluent

---

## 🆘 SI PROBLÈME

**Problème lors du `git push` ?**
- Vérifie que tu as copié la **bonne URL du repo** (avec `.git` à la fin)
- Utilise un Personal Access Token au lieu du mot de passe
- Voir la section "Alternative authentification" du guide complet

**Problème avec .env dans le repo ?**
- Urgence ! Lance : `git rm --cached .env && git commit -m "remove .env"`
- Puis : `git push origin main`
- Puis change IMMÉDIATEMENT tous les mots de passe Airflow + NiFi + GitHub

**Docker ne démarre pas ?**
- Vérifie que Docker Desktop est bien **ouvert**
- Relance le terminal après avoir ouvert Docker
- Teste avec : `docker ps`

**Airflow-init s'arrête en erreur ?**
- Regarde les logs : `docker-compose logs airflow-init`
- 99% du temps = permissions. Redémarre tout : `docker-compose down -v && docker-compose up -d`

---

## 🎉 BRAVO !

Tu viens de :
✅ Créer une architecture data engineering moderne
✅ Mettre en place l'infrastructure Docker complète
✅ Versionner le code avec Git
✅ Configurer le CI/CD GitHub Actions
✅ Préparer l'équipe pour 4 semaines de développement

**Maintenant, fais connaître le guiiide complet à tes collègues et on démarre !** 🚀

---

*Relis ces 4 fichiers au besoin. Ils sont ta bible pour les 4 prochaines semaines.* 📚
