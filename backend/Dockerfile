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

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Port exposé par Uvicorn
EXPOSE 8000

# Healthcheck — liveness only.  /health/live answers 200 as soon as the
# FastAPI process is up; it does NOT touch Postgres/Redis/BigQuery.
# Readiness (/health/ready) is for an L7 load balancer to decide whether
# to route traffic; using it here would put the container in a restart
# loop in dev environments where BigQuery isn't reachable.
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,sys; r=urllib.request.urlopen('http://localhost:8000/health/live', timeout=8); sys.exit(0 if r.status==200 else 1)" || exit 1

# Commande de démarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
