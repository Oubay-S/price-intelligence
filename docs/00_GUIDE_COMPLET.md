# 📚 GUIDE COMPLET — Du zéro à GitHub en 30 minutes

> Suis ce guide **étape par étape**, dans l'ordre. Ne saute rien.

---

## PHASE 1️⃣ : PRÉPARATION SUR GITHUB (5 min)

### Étape 1.1 — Créer un compte GitHub (si pas encore fait)
1. Va sur **https://github.com/signup**
2. Crée un compte avec ton email universitaire
3. Confirme ton email
4. Ajoute une photo de profil (optionnel mais sympa 😊)

### Étape 1.2 — Créer un nouveau repository
1. Va sur **https://github.com/new**
2. Remplissage :
   - **Repository name** : `price-intelligence`
   - **Description** : "Platform de veille tarifaire e-commerce — Nutrition sportive"
   - **Visibility** : 🔒 **Private** (le projet reste privé)
   - **Initialize this repository with** : ⚠️ **Ne coche RIEN** (on le fera nous-mêmes)
3. Clique **"Create repository"**
4. GitHub t'affiche une page avec deux options. **Copie l'URL** qui ressemble à :
   ```
   https://github.com/TON-USERNAME/price-intelligence.git
   ```
   → **Tu en auras besoin dans 2 minutes** 📌

---

## PHASE 2️⃣ : INITIALISER LE PROJET LOCALEMENT (5 min)

### Étape 2.1 — Crée un dossier et rentre dedans
```bash
# Ouvre un terminal (Git Bash sur Windows, Terminal sur Mac/Linux)
cd ~/Bureau   # ou le dossier où tu veux travailler
mkdir price-intelligence
cd price-intelligence
```

### Étape 2.2 — Initialise Git
```bash
git init
```

### Étape 2.3 — Configure Git avec tes informations
```bash
git config user.name "Ton Nom Complet"
git config user.email "ton.email@etudiant.ma"
```

### Étape 2.4 — Copie tous les fichiers du projet
1. **Télécharge tous les fichiers** que j'ai créés (voir section ci-dessous)
2. **Copie-les dans le dossier `price-intelligence/`**
3. Vérifie que tu as cette structure :
```
price-intelligence/
├── .gitignore
├── .env.example
├── docker-compose.yml
├── README.md
├── DEMARRAGE.md
├── GIT_SETUP.sh
├── ARCHITECTURE.md
├── .github/
│   └── workflows/
│       └── ci.yml
├── airflow/
│   ├── dags/
│   │   └── example_hello_dag.py
│   ├── plugins/
│   ├── logs/
│   └── requirements.txt
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── packages.yml
│   ├── models/
│   │   ├── staging/
│   │   │   └── stg_prices.sql
│   │   ├── intermediate/
│   │   │   └── int_price_daily.sql
│   │   └── mart/
│   │       └── mart_price_trends.sql
│   └── tests/
│       └── assert_price_positive.sql
├── nifi/
│   └── templates/
├── scrapers/
│   ├── spiders/
│   │   └── myprotein_spider.py
│   ├── settings.py
│   └── requirements.txt
├── streamlit/
│   ├── app.py
│   └── requirements.txt
├── analytics/
│   ├── notebooks/
│   └── requirements.txt
└── infra/
    └── init_bigtable.py
```

---

## PHASE 3️⃣ : PREMIER COMMIT (5 min)

### Étape 3.1 — Vérifier ce qui sera commité
```bash
git status
```
**Résultat attendu :**
- ✅ En **vert** : tous les fichiers `.py`, `.yml`, `.md`, `.sql`, etc.
- ❌ **Pas de** : `.env` (secret), `gcp-credentials.json`, logs/
- Si tu vois du rouge = problème avec .gitignore, contacte-moi !

### Étape 3.2 — Ajouter tous les fichiers
```bash
git add .
```

### Étape 3.3 — Premier commit
```bash
git commit -m "feat: initialisation du projet price-intelligence

- Architecture hybride batch + streaming
- docker-compose.yml avec NiFi, Airflow, Bigtable emulator
- Modèles dbt (staging → intermediate → mart)
- Spider Scrapy et DAGs Airflow starters
- Dashboard Streamlit avec pages
- GitHub Actions CI/CD (lint, validation DAGs, tests dbt)
- Guide complet de démarrage (DEMARRAGE.md)"
```

---

## PHASE 4️⃣ : POUSSER SUR GITHUB (5 min)

### Étape 4.1 — Renommer la branche en `main`
```bash
git branch -M main
```

### Étape 4.2 — Connecter ton repo local au repo GitHub
Remplace `TON-USERNAME` et `TON-REPO` par **l'URL copiée à l'étape 1.2** :
```bash
git remote add origin https://github.com/TON-USERNAME/price-intelligence.git
```

### Étape 4.3 — Pousser ton code
```bash
git push -u origin main
```

**Si GitHub demande une authentification :**
1. Clique sur le lien qu'il affiche
2. Tu vas sur GitHub, il te demande un accès
3. Clique "Authorize"
4. Reviens dans le terminal
5. Le push doit s'être fait automatiquement

**Alternative (si problème avec l'authentification OAuth) :**
1. Va sur **https://github.com/settings/tokens**
2. Clique "Generate new token"
3. Sélectionne `repo` comme permission
4. Clique "Generate token"
5. **Copie le token** (il ne s'affichera qu'une fois !)
6. Dans le terminal, quand GitHub demande le mot de passe :
   - Username : `TON-USERNAME`
   - Password : **Colle le token** (pas ton mot de passe GitHub !)

---

## PHASE 5️⃣ : CRÉER LES BRANCHES DE L'ÉQUIPE (5 min)

### Étape 5.1 — Créer la branche `develop`
```bash
git checkout -b develop
git push origin develop
```

### Étape 5.2 — Retour sur `main`
```bash
git checkout main
```

### Étape 5.3 — Inviter les 3 autres membres
1. Va sur ton repo GitHub : **https://github.com/TON-USERNAME/price-intelligence**
2. Clique sur **"Settings"** (en haut à droite)
3. Va dans **"Collaborators"** (menu de gauche)
4. Clique **"Add people"**
5. Tape le username GitHub de chacun de tes 3 collègues
6. Sélectionne la permission **"Write"** (ils pourront pusher)
7. Envoie l'invitation

Tes collègues recevront un email et pourront cloner le repo avec :
```bash
git clone https://github.com/TON-USERNAME/price-intelligence.git
```

---

## 👥 WORKFLOW DE L'ÉQUIPE (Semaines 1-4)

### Chacun travaille dans sa branche

**DataOps (toi) :**
```bash
git checkout -b feature/dataops/docker-setup
# ... tu fais des modifications ...
git add .
git commit -m "fix: ajustement des variables d'environnement Airflow"
git push origin feature/dataops/docker-setup
```

**Data Engineer :**
```bash
git checkout -b feature/engineer/scraper-setup
# ... crée les spiders Scrapy ...
git push origin feature/engineer/scraper-setup
```

**Data Analyst :**
```bash
git checkout -b feature/analyst/dbt-models
# ... enrichit les modèles dbt ...
git push origin feature/analyst/dbt-models
```

**Dev Fullstack :**
```bash
git checkout -b feature/dev/streamlit-dashboard
# ... crée les pages Streamlit ...
git push origin feature/dev/streamlit-dashboard
```

### Intégrer dans `develop` (Pull Request)

Quand ton travail est prêt :
1. Va sur GitHub
2. Tu verras un bouton **"Compare & pull request"** 🟢
3. Clique dessus
4. Titre : `feature: description claire`
5. Description : explique ce que tu as fait
6. Clique **"Create pull request"**
7. Attends que le CI passe ✅ (voir `.github/workflows/ci.yml`)
8. Un autre membre review et approuve
9. Clique **"Squash and merge"**
10. Supprime la branche

### Avant de déployer en prod (fin du projet)

```bash
# Sur `main`
git checkout main
git pull origin main

# Merge develop dans main
git merge develop

# Pousse
git push origin main
```

---

## 🚀 COMMANDES GIT ESSENTIELLES (cheat sheet)

```bash
# Voir l'état
git status

# Ajouter du code
git add .

# Sauvegarder
git commit -m "feat: description"

# Envoyer
git push origin nom-de-ta-branche

# Récupérer le dernier code
git pull origin develop

# Changer de branche
git checkout nom-branche

# Créer + changer de branche
git checkout -b nom-branche

# Voir les branches
git branch -a

# Supprimer une branche locale (après merge)
git branch -d nom-branche

# Supprimer une branche distante
git push origin --delete nom-branche
```

---

## ✅ CHECKLIST FINALE

- [ ] Repo GitHub créé et privé ✅
- [ ] Tous les fichiers copiés localement ✅
- [ ] `.gitignore` correctement ignorant les secrets ✅
- [ ] `.env.example` commité (pas `.env` !) ✅
- [ ] Docker-compose.yml présent ✅
- [ ] `DEMARRAGE.md` pour les collègues ✅
- [ ] 3 collègues invités comme collaborators ✅
- [ ] Branches `main` + `develop` créées ✅
- [ ] GitHub Actions CI configuré ✅

---

## 🎉 C'est fait !

Envoie cette liste à tes 3 collègues :

> **Salut les gars !** 👋
> 
> Le repo est prêt. Vous pouvez cloner avec :
> ```bash
> git clone https://github.com/MON-USERNAME/price-intelligence.git
> cd price-intelligence
> cp .env.example .env
> docker-compose up -d
> ```
> 
> Voir `DEMARRAGE.md` pour les détails.
> 
> Chacun crée sa branche `feature/role/nom-feature` et on merge dans `develop` par Pull Request.

---

*Questions ? Ouvre une issue sur GitHub ou écris sur Slack de l'équipe.* 💪
