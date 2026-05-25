"""
Tests pour load_all_to_bigtable.py
Teste : _row_key, _parse_scraped_at, _load_json_file, load_file_to_bigtable
"""

import json
import os
import sys
import datetime
import pytest

# Ajouter scrapers/ au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scrapers'))

from load_all_to_bigtable import (
    _row_key,
    _parse_scraped_at,
    _load_json_file,
    REQUIRED_FIELDS,
)


# ═══════════════════════════════════════════
# TESTS — _parse_scraped_at
# ═══════════════════════════════════════════

class TestParseScrapedAt:
    """Tests pour le parsing des dates dans load_all_to_bigtable."""

    @pytest.mark.unit
    def test_iso_with_z(self):
        result = _parse_scraped_at("2025-05-20T10:30:00Z")
        assert result.year == 2025
        assert result.month == 5
        assert result.tzinfo is not None

    @pytest.mark.unit
    def test_iso_with_offset(self):
        result = _parse_scraped_at("2025-05-20T10:30:00+01:00")
        assert result.tzinfo is not None

    @pytest.mark.unit
    def test_naive_iso(self):
        """Un datetime naive doit être converti en UTC."""
        result = _parse_scraped_at("2025-05-20T10:30:00")
        assert result.tzinfo is not None
        assert result.tzinfo == datetime.timezone.utc

    @pytest.mark.unit
    def test_none_returns_now(self):
        """None doit retourner l'heure actuelle."""
        result = _parse_scraped_at(None)
        assert result is not None
        assert (datetime.datetime.now(datetime.timezone.utc) - result).total_seconds() < 5

    @pytest.mark.unit
    def test_empty_returns_now(self):
        result = _parse_scraped_at("")
        assert result is not None

    @pytest.mark.unit
    def test_invalid_returns_now(self):
        """Une date invalide doit retourner l'heure actuelle (fallback)."""
        result = _parse_scraped_at("invalid-date-format")
        assert result is not None
        assert (datetime.datetime.now(datetime.timezone.utc) - result).total_seconds() < 5


# ═══════════════════════════════════════════
# TESTS — _row_key
# ═══════════════════════════════════════════

class TestRowKey:
    """Tests pour la génération de clés Bigtable."""

    @pytest.mark.unit
    def test_row_key_format(self, valid_product):
        """La clé doit suivre le format store#category#slug#hash#timestamp."""
        key = _row_key("jumia", "football", valid_product)
        assert isinstance(key, bytes)
        parts = key.decode("utf-8").split("#")
        assert parts[0] == "jumia"
        assert parts[1] == "football"
        assert len(parts) >= 4

    @pytest.mark.unit
    def test_row_key_deterministic(self, valid_product):
        """La même entrée doit toujours produire la même clé."""
        key1 = _row_key("jumia", "football", valid_product)
        key2 = _row_key("jumia", "football", valid_product)
        assert key1 == key2

    @pytest.mark.unit
    def test_row_key_different_stores(self, valid_product):
        """Des stores différents doivent produire des clés différentes."""
        key1 = _row_key("jumia", "football", valid_product)
        key2 = _row_key("ebay", "football", valid_product)
        assert key1 != key2

    @pytest.mark.unit
    def test_row_key_different_categories(self, valid_product):
        """Des catégories différentes doivent produire des clés différentes."""
        key1 = _row_key("jumia", "football", valid_product)
        key2 = _row_key("jumia", "gym", valid_product)
        assert key1 != key2

    @pytest.mark.unit
    def test_row_key_slug_sanitized(self):
        """Les caractères spéciaux dans le nom doivent être nettoyés."""
        product = {
            "name": "Nike Air Max 270!!! @#$ Special",
            "current_price": "89.99",
            "scraped_at": "2025-05-20T10:30:00Z",
            "product_url": "https://example.com/test",
        }
        key = _row_key("jumia", "football", product)
        decoded = key.decode("utf-8")
        # Le slug ne doit pas contenir de caractères spéciaux
        slug = decoded.split("#")[2]
        assert "!" not in slug
        assert "@" not in slug
        assert "$" not in slug

    @pytest.mark.unit
    def test_row_key_missing_name(self):
        """Un produit sans nom doit utiliser 'unknown' comme slug."""
        product = {
            "current_price": "89.99",
            "scraped_at": "2025-05-20T10:30:00Z",
        }
        key = _row_key("jumia", "football", product)
        decoded = key.decode("utf-8")
        assert "unknown" in decoded


# ═══════════════════════════════════════════
# TESTS — _load_json_file
# ═══════════════════════════════════════════

class TestLoadJsonFile:
    """Tests pour le chargement des fichiers JSON."""

    @pytest.mark.unit
    def test_valid_json_file(self, sample_json_file):
        data = _load_json_file(str(sample_json_file))
        assert isinstance(data, list)
        assert len(data) == 2

    @pytest.mark.unit
    def test_invalid_json_raises(self, invalid_json_file):
        with pytest.raises(Exception):
            _load_json_file(str(invalid_json_file))

    @pytest.mark.unit
    def test_not_a_list_raises(self, tmp_path):
        """Un fichier avec un objet (pas un array) doit lever ValueError."""
        file = tmp_path / "object.json"
        file.write_text('{"key": "value"}', encoding="utf-8")
        with pytest.raises(ValueError, match="expected a JSON array"):
            _load_json_file(str(file))


# ═══════════════════════════════════════════
# TESTS — REQUIRED_FIELDS constant
# ═══════════════════════════════════════════

class TestRequiredFields:
    """Tests pour la constante REQUIRED_FIELDS."""

    @pytest.mark.unit
    def test_required_fields(self):
        assert "name" in REQUIRED_FIELDS
        assert "current_price" in REQUIRED_FIELDS
        assert "scraped_at" in REQUIRED_FIELDS

    @pytest.mark.unit
    def test_required_fields_count(self):
        assert len(REQUIRED_FIELDS) == 3
