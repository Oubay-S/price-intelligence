# 🚀 Guide de Démarrage — Price Intelligence Platform
## Lis ce fichier en PREMIER avant de toucher quoi que ce soit

---

## ✅ Prérequis (à installer UNE SEULE FOIS)

| Outil | Version min | Vérification |
|-------|-------------|--------------|
| **Git** | 2.x | `git --version` |
| **Docker Desktop** | 4.x | Ouvrir l'appli, voir l'icône whale 🐳 |
| **Python** | 3.10+ | `python --version` |

> ⚠️ **Windows** : Utilise **Git Bash** ou **WSL2** pour toutes les commandes.
> ⚠️ **Docker Desktop** doit être **ouvert** avant de lancer les commandes Docker.

---

## 📦 Étape 1 — Cloner le projet

```bash
git clone https://github.com/VOTRE-ORG/price-intelligence.git
cd price-intelligence
```

---

## ⚙️ Étape 2 — Configurer (une seule fois)

```bash
cp .env.example .env
```

Le `.env` contient des mots de passe locaux. Pas besoin de les changer pour le dev.

---

## 🐳 Étape 3 — Lancer l'infrastructure complète

```bash
docker-compose up -d --build
```

**Première fois : ~10 minutes** (téléchargement des images Docker).
**Fois suivantes : ~2 minutes**.

---

## 🔍 Étape 4 — Vérifier que tout tourne

```bash
docker-compose ps
```

Résultat attendu :
```
NAME                    STATUS
bigtable-emulator       running (healthy)
airflow-postgres        running (healthy)
airflow-init            exited (0)       ← Normal ! Il a fini son boulot.
airflow-webserver       running (healthy)
airflow-scheduler       running (healthy)
nifi                    running (healthy)
```

> NiFi peut prendre jusqu'à **90 secondes** pour passer en `healthy`.

---

## 🌐 Interfaces Web

| Service | URL | Login | Mot de passe |
|---------|-----|-------|-------------|
| **Apache Airflow** | http://localhost:8081 | `admin` | `admin123` |
| **Apache NiFi** | https://localhost:8443/nifi | `admin` | `adminpassword123` |

**⚠️ Avertissement SSL NiFi** : Clique sur "Avancé" → "Continuer" — c'est normal en local.

---

## 🔧 Étape 5 — Initialiser Bigtable (une seule fois)

```bash
# Installer la librairie Python Bigtable
pip install google-cloud-bigtable

# Créer les tables dans l'émulateur
export BIGTABLE_EMULATOR_HOST=localhost:8086
export GOOGLE_CLOUD_PROJECT=price-intel-local
python infra/init_bigtable.py
```

---

## 🛑 Arrêter l'environnement

```bash
docker-compose down            # Arrête (données conservées)
docker-compose down -v         # Arrête ET efface tout (repartir de zéro)
```

---

## 🔄 Mise à jour depuis Git

```bash
git pull
docker-compose up -d --build
```

---

## 🌿 Workflow Git de l'équipe

```
main          ← Branche stable (démo, prod)
  └── develop ← Intégration des features
        ├── feature/dataops/docker-setup    (DataOps)
        ├── feature/engineer/dag-scraping   (Data Engineer)
        ├── feature/analyst/dbt-models      (Data Analyst)
        └── feature/dev/streamlit-dashboard (Dev Fullstack)
```

**Chaque membre travaille dans sa branche et fait une Pull Request vers `develop`.**

```bash
# Créer et basculer sur ta branche
git checkout -b feature/ton-role/nom-de-la-feature

# Sauvegarder ton travail
git add .
git commit -m "feat: description claire de ce que tu as fait"
git push origin feature/ton-role/nom-de-la-feature
```

---

## 🐛 Dépannage

```bash
# Voir les logs d'un service
docker-compose logs -f airflow-scheduler
docker-compose logs -f nifi
docker-compose logs -f bigtable-emulator

# Redémarrer un service
docker-compose restart nifi

# Si une page affiche "Server is up and running" sur le port 8081:
# Cela veut dire qu'un service local Windows (ex: Postgres/EnterpriseDB)
# bloque le port de Docker. Pensez à couper vos serveurs locaux.

# Entrer dans un conteneur pour déboguer
docker-compose exec airflow-webserver bash
```
