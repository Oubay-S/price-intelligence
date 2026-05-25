"""
Tests pour la fonction stage_scraped_json_for_nifi du DAG.
Teste : staging, enrichissement, filtrage des fichiers metadata.
"""

import json
import os
import sys
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch

# Charger le module DAG (réutilise le même loader que test_dag_validation)
import importlib.util
import types


def _load_dag_module():
    """Charge le module DAG sans dépendance Airflow en mockant les imports."""
    airflow_mock = types.ModuleType('airflow')
    DAGMock = type('DAG', (), {
        '__init__': lambda self, *a, **kw: None,
        '__enter__': lambda self: self,
        '__exit__': lambda self, *a: None,
    })
    airflow_mock.DAG = DAGMock
    sys.modules.setdefault('airflow', airflow_mock)

    operators_mock = types.ModuleType('airflow.operators')
    sys.modules.setdefault('airflow.operators', operators_mock)

    python_mock = types.ModuleType('airflow.operators.python')
    
    class PythonOperatorMock:
        def __init__(self, *a, **kw):
            pass
        def __rshift__(self, other):
            return other
        def __rrshift__(self, other):
            return self

    python_mock.PythonOperator = PythonOperatorMock
    sys.modules.setdefault('airflow.operators.python', python_mock)

    trigger_mock = types.ModuleType('airflow.utils')
    sys.modules.setdefault('airflow.utils', trigger_mock)

    trigger_rule_mock = types.ModuleType('airflow.utils.trigger_rule')
    trigger_rule_mock.TriggerRule = type('TriggerRule', (), {'ALL_DONE': 'all_done'})
    sys.modules.setdefault('airflow.utils.trigger_rule', trigger_rule_mock)

    spec = importlib.util.spec_from_file_location(
        "price_intelligence_dag_stage",
        os.path.join(os.path.dirname(__file__), '..', 'airflow', 'dags', 'price_intelligence_dag.py')
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dag_module = _load_dag_module()
stage_scraped_json_for_nifi = dag_module.stage_scraped_json_for_nifi
validate_scraper_json_file = dag_module.validate_scraper_json_file


# ═══════════════════════════════════════════
# TESTS — stage_scraped_json_for_nifi
# ═══════════════════════════════════════════

class TestStageScrapedJsonForNifi:
    """Tests pour le staging des fichiers JSON vers NiFi."""

    @pytest.mark.unit
    def test_stages_valid_files(self, scraper_output_dir):
        """Les fichiers valides doivent être copiés dans l'inbox NiFi."""
        inbox = scraper_output_dir / "nifi_inbox"
        with patch.dict(os.environ, {
            "SCRAPER_OUTPUT_ROOT": str(scraper_output_dir),
            "NIFI_INBOX": str(inbox),
        }):
            result = stage_scraped_json_for_nifi()

        assert inbox.exists()
        assert result["expected_records"] >= 3  # 3 produits (1 par store)

        # Vérifier que les fichiers sont là
        staged_files = list(inbox.rglob("*.json"))
        assert len(staged_files) >= 3

    @pytest.mark.unit
    def test_enriches_with_ingestion_metadata(self, scraper_output_dir):
        """Chaque record doit être enrichi avec _ingestion_run_id et _staged_at."""
        inbox = scraper_output_dir / "nifi_inbox"
        with patch.dict(os.environ, {
            "SCRAPER_OUTPUT_ROOT": str(scraper_output_dir),
            "NIFI_INBOX": str(inbox),
        }):
            result = stage_scraped_json_for_nifi()

        # Lire un fichier stagé
        staged_file = next(inbox.rglob("*.json"))
        data = json.loads(staged_file.read_text(encoding="utf-8"))
        assert len(data) > 0
        record = data[0]
        assert "_ingestion_run_id" in record
        assert "_staged_at" in record
        assert record["_ingestion_run_id"].startswith("airflow-")

    @pytest.mark.unit
    def test_enriches_source_and_store(self, scraper_output_dir):
        """Chaque record doit avoir source et store remplis."""
        inbox = scraper_output_dir / "nifi_inbox"
        with patch.dict(os.environ, {
            "SCRAPER_OUTPUT_ROOT": str(scraper_output_dir),
            "NIFI_INBOX": str(inbox),
        }):
            stage_scraped_json_for_nifi()

        for staged_file in inbox.rglob("*.json"):
            data = json.loads(staged_file.read_text(encoding="utf-8"))
            for record in data:
                assert record.get("source"), f"source manquant dans {staged_file}"
                assert record.get("store"), f"store manquant dans {staged_file}"

    @pytest.mark.unit
    def test_skips_metadata_files(self, scraper_dir_with_metadata):
        """Les fichiers metadata (_metadata, manifest.json, *_cookies.json) doivent être ignorés."""
        inbox = scraper_dir_with_metadata / "nifi_inbox"
        with patch.dict(os.environ, {
            "SCRAPER_OUTPUT_ROOT": str(scraper_dir_with_metadata),
            "NIFI_INBOX": str(inbox),
        }):
            result = stage_scraped_json_for_nifi()

        # Seul le fichier products.json doit être stagé, pas les metadata
        staged_files = list(inbox.rglob("*.json"))
        staged_names = [f.name for f in staged_files]
        assert "browser_state.json" not in staged_names
        assert "manifest.json" not in staged_names
        assert "session_cookies.json" not in staged_names
        assert "products.json" in staged_names

    @pytest.mark.unit
    def test_empty_scraper_dir_raises(self, empty_scraper_dir):
        """Un répertoire sans aucun JSON doit lever une exception."""
        inbox = empty_scraper_dir / "nifi_inbox"
        with patch.dict(os.environ, {
            "SCRAPER_OUTPUT_ROOT": str(empty_scraper_dir),
            "NIFI_INBOX": str(inbox),
        }):
            with pytest.raises(Exception, match="No scraper JSON files"):
                stage_scraped_json_for_nifi()

    @pytest.mark.unit
    def test_cleans_old_inbox(self, scraper_output_dir):
        """L'ancien inbox doit être nettoyé avant le staging."""
        inbox = scraper_output_dir / "nifi_inbox"
        inbox.mkdir(parents=True)
        old_file = inbox / "old_data.json"
        old_file.write_text("[]", encoding="utf-8")

        with patch.dict(os.environ, {
            "SCRAPER_OUTPUT_ROOT": str(scraper_output_dir),
            "NIFI_INBOX": str(inbox),
        }):
            stage_scraped_json_for_nifi()

        # L'ancien fichier doit avoir disparu
        assert not old_file.exists()

    @pytest.mark.unit
    def test_returns_ingestion_run_id(self, scraper_output_dir):
        """Le résultat doit contenir un ingestion_run_id traçable."""
        inbox = scraper_output_dir / "nifi_inbox"
        with patch.dict(os.environ, {
            "SCRAPER_OUTPUT_ROOT": str(scraper_output_dir),
            "NIFI_INBOX": str(inbox),
        }):
            result = stage_scraped_json_for_nifi()

        assert "ingestion_run_id" in result
        assert "expected_records" in result
        assert isinstance(result["expected_records"], int)
        assert result["expected_records"] > 0

    @pytest.mark.unit
    def test_custom_ingestion_run_id(self, scraper_output_dir):
        """Si INGESTION_RUN_ID est défini, il doit être utilisé."""
        inbox = scraper_output_dir / "nifi_inbox"
        with patch.dict(os.environ, {
            "SCRAPER_OUTPUT_ROOT": str(scraper_output_dir),
            "NIFI_INBOX": str(inbox),
            "INGESTION_RUN_ID": "test-run-12345",
        }):
            result = stage_scraped_json_for_nifi()

        assert result["ingestion_run_id"] == "test-run-12345"

        # Vérifier que les records ont le bon run_id
        staged_file = next(inbox.rglob("*.json"))
        data = json.loads(staged_file.read_text(encoding="utf-8"))
        assert data[0]["_ingestion_run_id"] == "test-run-12345"
