import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scrapers'))

from product_quality import is_excluded_product, is_relevant_product


@pytest.mark.unit
@pytest.mark.parametrize(
    'product',
    [
        {'name': 'Silicone Dental Mouth Guard Bruxism Sleep Aid Night Teeth Tooth Grinding'},
        {'name': 'Stop Snoring Mouthpiece Sleep Apnea Guard Bruxism Anti Snore Pure Grind Aid Tray'},
        {'name': 'SOVA Aero Night Guard Mouthguard'},
        {'name': 'Dentek Professional Fit Dental Guard - Custom Fit'},
        {'name': 'ProForce Mouthguard Case Boxing Martial Arts Protective Gear'},
    ],
)
def test_excludes_dental_sleep_mouthguards(product):
    assert is_excluded_product(product) is True
    assert is_relevant_product(product, store='ebay', category='combat-sports') is False


@pytest.mark.unit
@pytest.mark.parametrize(
    'product',
    [
        {'name': 'Mouth Guard Boxing MMA Gum Shield Boil & Bite Teeth Protection Adult Kids'},
        {'name': 'BLUE DOUBLE MOUTH GUARD w/ CASE - Meister MMA Gum Shield Boxing CUSTOM MOLDABLE'},
        {'name': 'RDX Boxing Mouth Guard with Case MMA Gum Shield Teeth Grinding, Mouth Protector'},
    ],
)
def test_keeps_combat_mouthguards(product):
    assert is_excluded_product(product) is False
    assert is_relevant_product(product, store='ebay', category='combat-sports') is True


@pytest.mark.unit
def test_rejects_non_combat_mouthguard_in_combat_category():
    product = {'name': 'Vettex Double Mouthguard Lip Guard Protection Football Mouth Piece ADULT'}

    assert is_excluded_product(product) is False
    assert is_relevant_product(product, store='ebay', category='combat-sports') is False


@pytest.mark.unit
def test_keeps_other_combat_products_without_mouthguard_terms():
    product = {'name': 'Everlast Pro Style Boxing Gloves'}

    assert is_relevant_product(product, store='ebay', category='combat-sports') is True
