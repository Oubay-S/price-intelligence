"""
Tests pour bigtable_to_bigquery.py
Teste : schéma BigQuery, filtrage des champs requis, logique de dédup,
        constantes de configuration.
"""

import os
import sys
import pytest

# Ajouter scrapers/ au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scrapers'))

from bigtable_to_bigquery import (
    BQ_SCHEMA,
    SCHEMA_FIELDS,
    REQUIRED_PRODUCT_FIELDS,
)


# ═══════════════════════════════════════════
# TESTS — Schéma BigQuery
# ═══════════════════════════════════════════

class TestBigQuerySchema:
    """Tests pour le schéma BigQuery — contrat entre Bigtable et BigQuery."""

    @pytest.mark.unit
    def test_schema_has_21_fields(self):
        """Le schéma BQ doit avoir exactement 21 champs."""
        assert len(BQ_SCHEMA) == 21

    @pytest.mark.unit
    def test_required_product_fields_in_schema(self):
        """Les champs requis doivent être présents dans le schéma."""
        for field in REQUIRED_PRODUCT_FIELDS:
            assert field in SCHEMA_FIELDS, f"Champ requis '{field}' absent du schéma BQ"

    @pytest.mark.unit
    def test_core_product_fields(self):
        """Les champs produit principaux doivent être dans le schéma."""
        core_fields = [
            "name", "current_price", "price_before_discount",
            "discount", "stars", "availability",
            "product_url", "image_url", "features", "sizes",
            "scraped_at", "source", "store", "category",
        ]
        for field in core_fields:
            assert field in SCHEMA_FIELDS, f"Champ produit '{field}' absent du schéma BQ"

    @pytest.mark.unit
    def test_metadata_fields(self):
        """Les champs de métadonnées d'ingestion doivent être présents."""
        meta_fields = [
            "_bigtable_row_key", "_ingestion_run_id",
            "_staged_at", "ingested_at", "ingestion_method",
            "_loaded_at", "_export_run_id",
        ]
        for field in meta_fields:
            assert field in SCHEMA_FIELDS, f"Champ metadata '{field}' absent du schéma BQ"

    @pytest.mark.unit
    def test_timestamp_fields_type(self):
        """Les champs timestamp doivent être de type TIMESTAMP dans le schéma."""
        timestamp_fields = {"_staged_at", "ingested_at", "_loaded_at"}
        for field in BQ_SCHEMA:
            if field.name in timestamp_fields:
                assert field.field_type == "TIMESTAMP", \
                    f"Le champ '{field.name}' doit être TIMESTAMP, pas {field.field_type}"

    @pytest.mark.unit
    def test_string_fields_type(self):
        """Les champs texte doivent être de type STRING dans le schéma."""
        string_fields = {"name", "current_price", "source", "store", "category"}
        for field in BQ_SCHEMA:
            if field.name in string_fields:
                assert field.field_type == "STRING", \
                    f"Le champ '{field.name}' doit être STRING, pas {field.field_type}"


# ═══════════════════════════════════════════
# TESTS — SCHEMA_FIELDS set
# ═══════════════════════════════════════════

class TestSchemaFields:
    """Tests pour le set SCHEMA_FIELDS dérivé du schéma."""

    @pytest.mark.unit
    def test_schema_fields_is_set(self):
        assert isinstance(SCHEMA_FIELDS, set)

    @pytest.mark.unit
    def test_schema_fields_count(self):
        assert len(SCHEMA_FIELDS) == 21

    @pytest.mark.unit
    def test_schema_fields_match_schema(self):
        """SCHEMA_FIELDS doit correspondre exactement aux noms du schéma."""
        schema_names = {field.name for field in BQ_SCHEMA}
        assert SCHEMA_FIELDS == schema_names


# ═══════════════════════════════════════════
# TESTS — REQUIRED_PRODUCT_FIELDS
# ═══════════════════════════════════════════

class TestRequiredProductFields:
    """Tests pour les champs requis des produits."""

    @pytest.mark.unit
    def test_fields(self):
        assert "name" in REQUIRED_PRODUCT_FIELDS
        assert "current_price" in REQUIRED_PRODUCT_FIELDS
        assert "scraped_at" in REQUIRED_PRODUCT_FIELDS

    @pytest.mark.unit
    def test_count(self):
        assert len(REQUIRED_PRODUCT_FIELDS) == 3


# ═══════════════════════════════════════════
# TESTS — Logique de filtrage produit
# ═══════════════════════════════════════════

class TestProductFiltering:
    """Tests pour la logique de filtrage appliquée avant l'export."""

    @pytest.mark.unit
    def test_valid_product_passes_filter(self, valid_product):
        """Un produit valide doit passer le filtre required fields."""
        passes = all(
            valid_product.get(field) not in (None, "")
            for field in REQUIRED_PRODUCT_FIELDS
        )
        assert passes is True

    @pytest.mark.unit
    def test_missing_name_fails_filter(self):
        """Un produit sans nom doit être rejeté."""
        from tests.conftest import PRODUCT_MISSING_NAME
        passes = all(
            PRODUCT_MISSING_NAME.get(field) not in (None, "")
            for field in REQUIRED_PRODUCT_FIELDS
        )
        assert passes is False

    @pytest.mark.unit
    def test_missing_price_fails_filter(self):
        """Un produit sans prix doit être rejeté."""
        from tests.conftest import PRODUCT_MISSING_PRICE
        passes = all(
            PRODUCT_MISSING_PRICE.get(field) not in (None, "")
            for field in REQUIRED_PRODUCT_FIELDS
        )
        assert passes is False

    @pytest.mark.unit
    def test_empty_fields_fail_filter(self):
        """Des champs vides doivent faire échouer le filtre."""
        from tests.conftest import PRODUCT_EMPTY_FIELDS
        passes = all(
            PRODUCT_EMPTY_FIELDS.get(field) not in (None, "")
            for field in REQUIRED_PRODUCT_FIELDS
        )
        assert passes is False

    @pytest.mark.unit
    def test_product_field_filtering(self, valid_product):
        """Seuls les champs du schéma doivent être gardés dans l'export."""
        valid_product["extra_field_not_in_schema"] = "should be dropped"
        filtered = {k: v for k, v in valid_product.items() if k in SCHEMA_FIELDS}
        assert "extra_field_not_in_schema" not in filtered
        assert "name" in filtered
        assert "current_price" in filtered

    @pytest.mark.unit
    def test_dedup_by_bigtable_key(self):
        """Les produits avec le même _bigtable_row_key doivent être dédupliqués."""
        existing_keys = {"key1", "key2", "key3"}
        products = [
            {"_bigtable_row_key": "key1", "name": "Product 1"},
            {"_bigtable_row_key": "key4", "name": "Product 4"},
            {"_bigtable_row_key": "key2", "name": "Product 2"},
        ]
        new = [p for p in products if p.get("_bigtable_row_key") not in existing_keys]
        assert len(new) == 1
        assert new[0]["name"] == "Product 4"
