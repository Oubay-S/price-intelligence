# ──────────────────────────────────────────────
# Dockerfile — FastAPI Backend (Price Intelligence)
# ──────────────────────────────────────────────
# Build : docker build -t price-intel-backend ./backend
# Run   : Géré par docker-compose
# ──────────────────────────────────────────────

FROM python:3.10-slim

# Empêche Python de créer des fichiers .pyc et force le flush des logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Installer les dépendances système nécessaires (psycopg2, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Port exposé par Uvicorn
EXPOSE 8000

# Healthcheck — vérifie que le backend répond
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Commande de démarrage
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
