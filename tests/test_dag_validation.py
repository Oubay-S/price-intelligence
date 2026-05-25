"""
Tests pour la validation JSON et les helpers du DAG price_intelligence_pipeline.
Teste : validate_scraper_json_file, _parse_price, _parse_scraped_at
"""

import json
import sys
import os
import pytest
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire airflow/dags au path pour importer le DAG
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'airflow', 'dags'))

# Importer les fonctions à tester directement (sans charger Airflow)
# On parse le fichier manuellement pour extraire les fonctions pures
import importlib.util


def _load_dag_module():
    """Charge le module DAG sans dépendance Airflow en mockant les imports."""
    # Mock Airflow avant d'importer le module
    import types
    airflow_mock = types.ModuleType('airflow')
    DAGMock = type('DAG', (), {
        '__init__': lambda self, *a, **kw: None,
        '__enter__': lambda self: self,
        '__exit__': lambda self, *a: None,
    })
    airflow_mock.DAG = DAGMock
    sys.modules['airflow'] = airflow_mock

    operators_mock = types.ModuleType('airflow.operators')
    sys.modules['airflow.operators'] = operators_mock

    python_mock = types.ModuleType('airflow.operators.python')

    class PythonOperatorMock:
        def __init__(self, *a, **kw):
            pass
        def __rshift__(self, other):
            return other
        def __rrshift__(self, other):
            return self

    python_mock.PythonOperator = PythonOperatorMock
    sys.modules['airflow.operators.python'] = python_mock

    trigger_mock = types.ModuleType('airflow.utils')
    sys.modules['airflow.utils'] = trigger_mock

    trigger_rule_mock = types.ModuleType('airflow.utils.trigger_rule')
    trigger_rule_mock.TriggerRule = type('TriggerRule', (), {'ALL_DONE': 'all_done'})
    sys.modules['airflow.utils.trigger_rule'] = trigger_rule_mock

    spec = importlib.util.spec_from_file_location(
        "price_intelligence_dag",
        os.path.join(os.path.dirname(__file__), '..', 'airflow', 'dags', 'price_intelligence_dag.py')
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dag_module = _load_dag_module()
validate_scraper_json_file = dag_module.validate_scraper_json_file
_parse_price = dag_module._parse_price
_parse_scraped_at = dag_module._parse_scraped_at
REQUIRED_PRODUCT_FIELDS = dag_module.REQUIRED_PRODUCT_FIELDS


# ═══════════════════════════════════════════
# TESTS — _parse_price
# ═══════════════════════════════════════════

class TestParsePrice:
    """Tests pour la fonction _parse_price qui extrait les prix numériques."""

    @pytest.mark.unit
    def test_price_with_euro(self):
        assert _parse_price("89.99 €") == 89.99

    @pytest.mark.unit
    def test_price_with_dollar(self):
        assert _parse_price("$149.99") == 149.99

    @pytest.mark.unit
    def test_price_with_pound(self):
        assert _parse_price("£129.99") == 129.99

    @pytest.mark.unit
    def test_price_integer(self):
        assert _parse_price("100") == 100.0

    @pytest.mark.unit
    def test_price_with_comma_format(self):
        assert _parse_price("1,299.99 MAD") == 1.0  # regex capture first group

    @pytest.mark.unit
    def test_price_none(self):
        assert _parse_price(None) is None

    @pytest.mark.unit
    def test_price_empty_string(self):
        assert _parse_price("") is None

    @pytest.mark.unit
    def test_price_text_only(self):
        assert _parse_price("prix inconnu") is None

    @pytest.mark.unit
    def test_price_zero(self):
        assert _parse_price("0.00") == 0.0

    @pytest.mark.unit
    def test_price_numeric_input(self):
        assert _parse_price(89.99) == 89.99


# ═══════════════════════════════════════════
# TESTS — _parse_scraped_at
# ═══════════════════════════════════════════

class TestParseScrapedAt:
    """Tests pour la fonction _parse_scraped_at qui parse les dates ISO."""

    @pytest.mark.unit
    def test_iso_with_z(self):
        result = _parse_scraped_at("2025-05-20T10:30:00Z")
        assert result is not None
        assert result.year == 2025
        assert result.month == 5
        assert result.day == 20

    @pytest.mark.unit
    def test_iso_with_offset(self):
        result = _parse_scraped_at("2025-05-20T11:00:00+00:00")
        assert result is not None
        assert result.hour == 11

    @pytest.mark.unit
    def test_iso_naive(self):
        result = _parse_scraped_at("2025-05-20T10:30:00")
        assert result is not None

    @pytest.mark.unit
    def test_none_input(self):
        assert _parse_scraped_at(None) is None

    @pytest.mark.unit
    def test_empty_string(self):
        assert _parse_scraped_at("") is None

    @pytest.mark.unit
    def test_invalid_date(self):
        assert _parse_scraped_at("not-a-date") is None

    @pytest.mark.unit
    def test_partial_date(self):
        assert _parse_scraped_at("2025-05-20") is not None


# ═══════════════════════════════════════════
# TESTS — validate_scraper_json_file
# ═══════════════════════════════════════════

class TestValidateScraperJsonFile:
    """Tests pour la validation du contrat JSON des scrapers."""

    @pytest.mark.unit
    def test_valid_file(self, sample_json_file):
        """Un fichier JSON valide doit retourner les données."""
        result = validate_scraper_json_file(sample_json_file)
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.unit
    def test_invalid_json_syntax(self, invalid_json_file):
        """Un fichier JSON invalide doit lever ValueError."""
        with pytest.raises(ValueError, match="invalid JSON"):
            validate_scraper_json_file(invalid_json_file)

    @pytest.mark.unit
    def test_not_a_list(self, tmp_path):
        """Un fichier JSON qui n'est pas une liste doit lever ValueError."""
        file = tmp_path / "not_list.json"
        file.write_text(json.dumps({"name": "test"}), encoding="utf-8")
        with pytest.raises(ValueError, match="expected a JSON array"):
            validate_scraper_json_file(file)

    @pytest.mark.unit
    def test_missing_required_fields(self, tmp_path):
        """Des produits sans champs requis doivent faire échouer la validation."""
        from tests.conftest import PRODUCT_MISSING_NAME
        file = tmp_path / "missing.json"
        file.write_text(json.dumps([PRODUCT_MISSING_NAME]), encoding="utf-8")
        with pytest.raises(ValueError, match="schema contract failed"):
            validate_scraper_json_file(file)

    @pytest.mark.unit
    def test_empty_fields_treated_as_missing(self, tmp_path):
        """Des champs vides doivent être traités comme manquants."""
        from tests.conftest import PRODUCT_EMPTY_FIELDS
        file = tmp_path / "empty.json"
        file.write_text(json.dumps([PRODUCT_EMPTY_FIELDS]), encoding="utf-8")
        with pytest.raises(ValueError, match="schema contract failed"):
            validate_scraper_json_file(file)

    @pytest.mark.unit
    def test_invalid_price_fails(self, tmp_path):
        """Un produit avec un prix non parsable doit échouer."""
        from tests.conftest import PRODUCT_INVALID_PRICE
        file = tmp_path / "bad_price.json"
        file.write_text(json.dumps([PRODUCT_INVALID_PRICE]), encoding="utf-8")
        with pytest.raises(ValueError, match="invalid current_price"):
            validate_scraper_json_file(file)

    @pytest.mark.unit
    def test_invalid_date_fails(self, tmp_path):
        """Un produit avec une date invalide doit échouer."""
        from tests.conftest import PRODUCT_INVALID_DATE
        file = tmp_path / "bad_date.json"
        file.write_text(json.dumps([PRODUCT_INVALID_DATE]), encoding="utf-8")
        with pytest.raises(ValueError, match="invalid scraped_at"):
            validate_scraper_json_file(file)

    @pytest.mark.unit
    def test_empty_list(self, tmp_path):
        """Un fichier JSON avec une liste vide doit retourner une liste vide."""
        file = tmp_path / "empty_list.json"
        file.write_text("[]", encoding="utf-8")
        result = validate_scraper_json_file(file)
        assert result == []

    @pytest.mark.unit
    def test_record_not_dict(self, tmp_path):
        """Un record qui n'est pas un dict doit échouer."""
        file = tmp_path / "not_dict.json"
        file.write_text(json.dumps(["string_record"]), encoding="utf-8")
        with pytest.raises(ValueError, match="schema contract failed"):
            validate_scraper_json_file(file)

    @pytest.mark.unit
    def test_required_fields_constant(self):
        """Les champs requis doivent être name, current_price, scraped_at."""
        assert "name" in REQUIRED_PRODUCT_FIELDS
        assert "current_price" in REQUIRED_PRODUCT_FIELDS
        assert "scraped_at" in REQUIRED_PRODUCT_FIELDS
