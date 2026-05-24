"""
Tests pour nifi_to_bigtable.py
Teste : _detect_source, _detect_category, _clean_metadata, _row_key, _cell_value
"""

import json
import os
import sys
import datetime
import pytest

# Ajouter scrapers/ au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scrapers'))

from nifi_to_bigtable import (
    _detect_source,
    _detect_category,
    _clean_metadata,
    _row_key,
    _cell_value,
    _parse_timestamp,
    _timestamp_key,
)


# ═══════════════════════════════════════════
# TESTS — _clean_metadata
# ═══════════════════════════════════════════

class TestCleanMetadata:
    """Tests pour le nettoyage des métadonnées NiFi."""

    @pytest.mark.unit
    def test_normal_value(self):
        assert _clean_metadata("football") == "football"

    @pytest.mark.unit
    def test_none(self):
        assert _clean_metadata(None) is None

    @pytest.mark.unit
    def test_empty_string(self):
        assert _clean_metadata("") is None

    @pytest.mark.unit
    def test_whitespace_only(self):
        assert _clean_metadata("   ") is None

    @pytest.mark.unit
    def test_unknown(self):
        """La valeur 'unknown' doit être traitée comme absente."""
        assert _clean_metadata("unknown") is None
        assert _clean_metadata("Unknown") is None
        assert _clean_metadata("UNKNOWN") is None

    @pytest.mark.unit
    def test_nifi_expression(self):
        """Les expressions NiFi ${...} doivent être traitées comme absentes."""
        assert _clean_metadata("${source}") is None
        assert _clean_metadata("${category.name}") is None

    @pytest.mark.unit
    def test_strips_whitespace(self):
        assert _clean_metadata("  football  ") == "football"


# ═══════════════════════════════════════════
# TESTS — _detect_source
# ═══════════════════════════════════════════

class TestDetectSource:
    """Tests pour la détection automatique de la source."""

    @pytest.mark.unit
    def test_from_arg(self):
        """La source fournie en argument doit avoir la priorité."""
        assert _detect_source({}, "jumia") == "jumia"

    @pytest.mark.unit
    def test_from_record_source_field(self):
        """Le champ 'source' du record doit être utilisé si pas d'argument."""
        assert _detect_source({"source": "ebay"}, None) == "ebay"

    @pytest.mark.unit
    def test_from_record_store_field(self):
        """Le champ 'store' doit être utilisé en fallback."""
        assert _detect_source({"store": "sport-direct"}, None) == "sport-direct"

    @pytest.mark.unit
    def test_from_url_ebay(self):
        """L'URL eBay doit être détectée automatiquement."""
        row = {"product_url": "https://www.ebay.com/itm/12345"}
        assert _detect_source(row, None) == "ebay"

    @pytest.mark.unit
    def test_from_url_sport_direct(self):
        """L'URL SportsDirect doit être détectée automatiquement."""
        row = {"product_url": "https://www.sportsdirect.com/product/789"}
        assert _detect_source(row, None) == "sport-direct"

    @pytest.mark.unit
    def test_from_url_jumia(self):
        """L'URL Jumia doit être détectée automatiquement."""
        row = {"product_url": "https://www.jumia.ma/nike-123.html"}
        assert _detect_source(row, None) == "jumia"

    @pytest.mark.unit
    def test_fallback_unknown(self):
        """Sans aucune info, la source doit être 'unknown'."""
        assert _detect_source({}, None) == "unknown"

    @pytest.mark.unit
    def test_arg_overrides_record(self):
        """L'argument doit prendre la priorité sur le champ du record."""
        row = {"source": "ebay", "product_url": "https://www.jumia.ma/test"}
        assert _detect_source(row, "sport-direct") == "sport-direct"

    @pytest.mark.unit
    def test_nifi_expression_ignored(self):
        """Les expressions NiFi dans le champ source doivent être ignorées."""
        row = {"source": "${source}"}
        assert _detect_source(row, None) == "unknown"


# ═══════════════════════════════════════════
# TESTS — _detect_category
# ═══════════════════════════════════════════

class TestDetectCategory:
    """Tests pour la détection de catégorie."""

    @pytest.mark.unit
    def test_from_arg(self):
        assert _detect_category({}, "football") == "football"

    @pytest.mark.unit
    def test_from_record(self):
        assert _detect_category({"category": "gym"}, None) == "gym"

    @pytest.mark.unit
    def test_fallback_unknown(self):
        assert _detect_category({}, None) == "unknown"

    @pytest.mark.unit
    def test_arg_overrides_record(self):
        assert _detect_category({"category": "gym"}, "football") == "football"

    @pytest.mark.unit
    def test_nifi_expression_ignored(self):
        assert _detect_category({"category": "${category}"}, None) == "unknown"


# ═══════════════════════════════════════════
# TESTS — _row_key
# ═══════════════════════════════════════════

class TestNifiRowKey:
    """Tests pour la clé de row Bigtable côté NiFi."""

    @pytest.mark.unit
    def test_key_is_bytes(self, valid_product):
        key = _row_key("jumia", "football", valid_product)
        assert isinstance(key, bytes)

    @pytest.mark.unit
    def test_key_contains_source(self, valid_product):
        key = _row_key("jumia", "football", valid_product)
        assert b"jumia" in key

    @pytest.mark.unit
    def test_key_contains_category(self, valid_product):
        key = _row_key("jumia", "football", valid_product)
        assert b"football" in key

    @pytest.mark.unit
    def test_key_deterministic(self, valid_product):
        key1 = _row_key("jumia", "football", valid_product)
        key2 = _row_key("jumia", "football", valid_product)
        assert key1 == key2

    @pytest.mark.unit
    def test_key_contains_hash(self, valid_product):
        key = _row_key("jumia", "football", valid_product)
        parts = key.decode("utf-8").split("#")
        # Le hash doit être au moins 12 caractères
        assert len(parts) >= 3
        assert len(parts[2]) >= 12


# ═══════════════════════════════════════════
# TESTS — _cell_value
# ═══════════════════════════════════════════

class TestCellValue:
    """Tests pour la sérialisation des valeurs de cellules."""

    @pytest.mark.unit
    def test_string(self):
        assert _cell_value("hello") == "hello"

    @pytest.mark.unit
    def test_number(self):
        assert _cell_value(42) == "42"

    @pytest.mark.unit
    def test_list(self):
        result = _cell_value(["a", "b"])
        assert result == json.dumps(["a", "b"], ensure_ascii=False)

    @pytest.mark.unit
    def test_dict(self):
        result = _cell_value({"key": "value"})
        assert result == json.dumps({"key": "value"}, ensure_ascii=False)

    @pytest.mark.unit
    def test_float(self):
        assert _cell_value(89.99) == "89.99"


# ═══════════════════════════════════════════
# TESTS — _parse_timestamp / _timestamp_key
# ═══════════════════════════════════════════

class TestTimestamp:
    """Tests pour le parsing et formatage des timestamps."""

    @pytest.mark.unit
    def test_parse_iso_z(self):
        result = _parse_timestamp("2025-05-20T10:30:00Z")
        assert result.year == 2025

    @pytest.mark.unit
    def test_parse_none_returns_now(self):
        result = _parse_timestamp(None)
        assert (datetime.datetime.now(datetime.timezone.utc) - result).total_seconds() < 5

    @pytest.mark.unit
    def test_timestamp_key_format(self):
        key = _timestamp_key("2025-05-20T10:30:00Z")
        assert "Z" in key
        assert "+" not in key
