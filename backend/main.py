"""
Price Intelligence — Backend FastAPI (Bootstrap)
================================================
Ce fichier est un point d'entrée minimal pour que le conteneur
Docker démarre correctement. Le dev fullstack doit le remplacer
par le vrai code de l'API.

Endpoints disponibles :
  GET /health  → Healthcheck (utilisé par Docker)
  GET /api/v1/status → Status de l'API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import redis as redis_lib

app = FastAPI(
    title="Price Intelligence API",
    description="API backend pour la plateforme de veille tarifaire",
    version="0.1.0",
)

# CORS — Autorise le frontend Angular à appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, restreindre aux domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Healthcheck endpoint — utilisé par Docker pour vérifier que le backend est vivant."""
    return {"status": "healthy"}


@app.get("/api/v1/status")
def status():
    """Retourne le status de l'API et la connectivité aux services."""
    checks = {
        "api": "ok",
        "database": _check_db(),
        "redis": _check_redis(),
    }
    return {
        "service": "price-intelligence-api",
        "version": "0.1.0",
        "checks": checks,
    }


def _check_db():
    """Vérifie la connexion à PostgreSQL App."""
    try:
        import psycopg2
        db_url = os.environ.get("DATABASE_URL", "")
        # Extraire les paramètres de connexion depuis l'URL
        conn = psycopg2.connect(db_url.replace("postgresql+psycopg2://", "postgresql://"))
        conn.close()
        return "ok"
    except Exception as e:
        return f"error: {str(e)}"


def _check_redis():
    """Vérifie la connexion à Redis."""
    try:
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        r = redis_lib.from_url(redis_url)
        r.ping()
        return "ok"
    except Exception as e:
        return f"error: {str(e)}"
