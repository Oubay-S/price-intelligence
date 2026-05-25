# 🔒 Branch Protection Rules — Price Intelligence

## Guide de configuration (GitHub UI)

### Prérequis
- Accès admin au repo `Oubay-S/price-intelligence`
- Pipeline CI fonctionnelle (`.github/workflows/ci.yml`)

---

## Étapes pour protéger la branche `develop`

### 1. Accéder aux paramètres
```
GitHub → Settings → Branches → Add branch protection rule
```

### 2. Configuration

| Paramètre | Valeur |
|-----------|--------|
| **Branch name pattern** | `develop` |
| **Require a pull request before merging** | ✅ Activé |
| **Required approvals** | `1` |
| **Require status checks to pass before merging** | ✅ Activé |
| **Require branches to be up to date before merging** | ✅ Activé |

### 3. Status checks requis (à ajouter)

Cocher ces checks comme **requis** :

| Check Name | Bloquant ? |
|------------|:---------:|
| `🔍 Lint & Qualité de Code` | ✅ Oui |
| `🏗️ Build Docker (Airflow + Backend + Frontend)` | ✅ Oui |
| `🧪 Tests d'Intégration` | ✅ Oui |
| `🧪 Tests Pipeline Data` | ✅ Oui |
| `🛡️ SAST — Analyse de Sécurité Statique` | ✅ Oui |
| `🔐 Détection de Secrets` | ✅ Oui |
| `🔧 dbt — Validation SQL` | ✅ Oui |
| `✅ Merge Gate — Prêt pour Review` | ✅ Oui |

> **Note** : Les checks `docker-security`, `iac-scan`, `dependency-scan` et `frontend-quality` sont en mode `soft_fail` / `continue-on-error` — ils sont informatifs mais ne bloquent pas le merge.

### 4. Paramètres supplémentaires

| Paramètre | Valeur |
|-----------|--------|
| **Do not allow bypassing the above settings** | ✅ Activé |
| **Restrict who can push to matching branches** | Optionnel |
| **Allow force pushes** | ❌ Désactivé |
| **Allow deletions** | ❌ Désactivé |

### 5. Sauvegarder
Cliquer **Create** ou **Save changes**

---

## Pour la branche `main` (fin de projet)

Même configuration que `develop` avec en plus :
- **Required approvals** : `2` (au lieu de 1)
- **Require conversation resolution before merging** : ✅
- **Require linear history** : ✅ (optionnel mais recommandé)

---

## Configuration des secrets SMTP pour les notifications

### 1. Accéder aux secrets
```
GitHub → Settings → Secrets and variables → Actions → New repository secret
```

### 2. Secrets à créer

| Secret Name | Valeur | Description |
|-------------|--------|-------------|
| `SMTP_SERVER` | `smtp.gmail.com` | Serveur SMTP |
| `SMTP_PORT` | `587` | Port TLS |
| `SMTP_USERNAME` | `serghinioubay62@gmail.com` | Adresse email |
| `SMTP_PASSWORD` | *(App Password)* | Mot de passe d'application |
| `NOTIFICATION_EMAIL` | `serghinioubay62@gmail.com` | Destinataire |

### 3. Créer un App Password Gmail

1. Aller sur https://myaccount.google.com/security
2. Activer **l'authentification à deux facteurs** (si pas déjà fait)
3. Aller dans **Mots de passe des applications**
4. Créer un nouveau mot de passe pour "Autre (nom personnalisé)" → `GitHub Actions CI`
5. Copier le mot de passe généré (16 caractères)
6. Le coller comme valeur du secret `SMTP_PASSWORD` dans GitHub

> ⚠️ **Ne jamais committer le mot de passe dans le code !**
