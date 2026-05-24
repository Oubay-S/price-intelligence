"""
Fixtures partagées pour les tests de la pipeline data.
Fournit des données JSON d'exemple, des chemins temporaires,
et des helpers pour simuler la structure scraper.
"""

import json
import os
import pytest
from pathlib import Path


# ─────────────────────────────────────────────
# SAMPLE DATA — Produits valides et invalides
# ─────────────────────────────────────────────

VALID_PRODUCT = {
    "name": "Nike Air Max 270",
    "current_price": "89.99 €",
    "price_before_discount": "129.99 €",
    "discount": "-30%",
    "stars": "4.5",
    "availability": "In Stock",
    "product_url": "https://www.jumia.ma/nike-air-max-270-123456.html",
    "image_url": "https://img.jumia.ma/nike-air-max-270.jpg",
    "features": "Comfortable, Lightweight",
    "sizes": "[\"40\", \"41\", \"42\", \"43\"]",
    "scraped_at": "2025-05-20T10:30:00Z",
    "source": "jumia",
    "store": "jumia",
    "category": "football",
}

VALID_PRODUCT_EBAY = {
    "name": "Adidas Predator Edge.1 FG",
    "current_price": "$149.99",
    "scraped_at": "2025-05-20T11:00:00+00:00",
    "product_url": "https://www.ebay.com/itm/adidas-predator-edge-12345",
    "image_url": "https://i.ebayimg.com/images/adidas-predator.jpg",
    "source": "ebay",
    "store": "ebay",
    "category": "football",
}

VALID_PRODUCT_SPORT_DIRECT = {
    "name": "Under Armour HOVR Phantom 3",
    "current_price": "£129.99",
    "price_before_discount": "£159.99",
    "discount": "-19%",
    "scraped_at": "2025-05-20T09:15:00Z",
    "product_url": "https://www.sportsdirect.com/under-armour-hovr-789",
    "source": "sport-direct",
    "store": "sport-direct",
    "category": "gym",
}

PRODUCT_MISSING_NAME = {
    "current_price": "89.99 €",
    "scraped_at": "2025-05-20T10:30:00Z",
    "source": "jumia",
}

PRODUCT_MISSING_PRICE = {
    "name": "Nike Air Max 270",
    "scraped_at": "2025-05-20T10:30:00Z",
    "source": "jumia",
}

PRODUCT_MISSING_SCRAPED_AT = {
    "name": "Nike Air Max 270",
    "current_price": "89.99 €",
    "source": "jumia",
}

PRODUCT_INVALID_PRICE = {
    "name": "Nike Air Max 270",
    "current_price": "prix inconnu",
    "scraped_at": "2025-05-20T10:30:00Z",
    "source": "jumia",
}

PRODUCT_INVALID_DATE = {
    "name": "Nike Air Max 270",
    "current_price": "89.99 €",
    "scraped_at": "not-a-date",
    "source": "jumia",
}

PRODUCT_EMPTY_FIELDS = {
    "name": "",
    "current_price": "",
    "scraped_at": "",
    "source": "jumia",
}


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture
def valid_product():
    """Un produit valide complet."""
    return VALID_PRODUCT.copy()


@pytest.fixture
def valid_products_list():
    """Liste de produits valides multi-source."""
    return [
        VALID_PRODUCT.copy(),
        VALID_PRODUCT_EBAY.copy(),
        VALID_PRODUCT_SPORT_DIRECT.copy(),
    ]


@pytest.fixture
def invalid_products_list():
    """Liste de produits invalides (champs manquants)."""
    return [
        PRODUCT_MISSING_NAME.copy(),
        PRODUCT_MISSING_PRICE.copy(),
        PRODUCT_MISSING_SCRAPED_AT.copy(),
    ]


@pytest.fixture
def mixed_products_list():
    """Mix de produits valides et invalides."""
    return [
        VALID_PRODUCT.copy(),
        PRODUCT_MISSING_NAME.copy(),
        VALID_PRODUCT_EBAY.copy(),
    ]


@pytest.fixture
def scraper_output_dir(tmp_path):
    """
    Crée une structure de répertoire scraper réaliste dans un dossier temporaire.

    Structure :
        tmp/jumia/football/products.json
        tmp/ebay/football/products.json
        tmp/sport-direct/gym/products.json
    """
    stores = {
        "jumia": {
            "football": [VALID_PRODUCT.copy()],
        },
        "ebay": {
            "football": [VALID_PRODUCT_EBAY.copy()],
        },
        "sport-direct": {
            "gym": [VALID_PRODUCT_SPORT_DIRECT.copy()],
        },
    }

    for store, categories in stores.items():
        for category, products in categories.items():
            category_dir = tmp_path / store / category
            category_dir.mkdir(parents=True, exist_ok=True)
            json_file = category_dir / "products.json"
            json_file.write_text(
                json.dumps(products, ensure_ascii=False),
                encoding="utf-8",
            )

    return tmp_path


@pytest.fixture
def empty_scraper_dir(tmp_path):
    """Répertoire scraper vide (aucun JSON)."""
    for store in ["jumia", "ebay", "sport-direct"]:
        (tmp_path / store).mkdir(parents=True)
    return tmp_path


@pytest.fixture
def scraper_dir_with_metadata(tmp_path):
    """Répertoire scraper avec des fichiers metadata qui doivent être ignorés."""
    # Vrai fichier produit
    football_dir = tmp_path / "jumia" / "football"
    football_dir.mkdir(parents=True)
    (football_dir / "products.json").write_text(
        json.dumps([VALID_PRODUCT.copy()], ensure_ascii=False),
        encoding="utf-8",
    )
    # Fichiers metadata à ignorer
    metadata_dir = tmp_path / "jumia" / "_metadata"
    metadata_dir.mkdir(parents=True)
    (metadata_dir / "browser_state.json").write_text("{}", encoding="utf-8")
    (tmp_path / "jumia" / "manifest.json").write_text("{}", encoding="utf-8")
    (tmp_path / "jumia" / "session_cookies.json").write_text("[]", encoding="utf-8")

    return tmp_path


@pytest.fixture
def sample_json_file(tmp_path):
    """Crée un fichier JSON temporaire avec des produits valides."""
    data = [VALID_PRODUCT.copy(), VALID_PRODUCT_EBAY.copy()]
    file_path = tmp_path / "products.json"
    file_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return file_path


@pytest.fixture
def invalid_json_file(tmp_path):
    """Crée un fichier JSON invalide (syntaxe cassée)."""
    file_path = tmp_path / "broken.json"
    file_path.write_text("{invalid json content", encoding="utf-8")
    return file_path


@pytest.fixture
def bigtable_env():
    """Configure les variables d'environnement pour le Bigtable Emulator."""
    env = {
        "BIGTABLE_EMULATOR_HOST": "localhost:8086",
        "GOOGLE_CLOUD_PROJECT": "price-intel-local",
        "BIGTABLE_INSTANCE_ID": "price-intel-instance",
    }
    original = {}
    for key, value in env.items():
        original[key] = os.environ.get(key)
        os.environ[key] = value

    yield env

    # Restore
    for key, orig_value in original.items():
        if orig_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = orig_value
