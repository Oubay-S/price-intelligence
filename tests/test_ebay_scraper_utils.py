import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scrapers', 'ebay'))

from ebay_scraper_utils import is_excluded_ebay_product, is_relevant_ebay_product


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
def test_excludes_ebay_dental_sleep_mouthguards(product):
    assert is_excluded_ebay_product(product) is True
    assert is_relevant_ebay_product('mouthguards', product) is False


@pytest.mark.unit
@pytest.mark.parametrize(
    'product',
    [
        {'name': 'Mouth Guard Boxing MMA Gum Shield Boil & Bite Teeth Protection Adult Kids'},
        {'name': 'BLUE DOUBLE MOUTH GUARD w/ CASE - Meister MMA Gum Shield Boxing CUSTOM MOLDABLE'},
        {'name': 'RDX Boxing Mouth Guard with Case MMA Gum Shield Teeth Grinding, Mouth Protector'},
    ],
)
def test_keeps_ebay_combat_mouthguards(product):
    assert is_excluded_ebay_product(product) is False
    assert is_relevant_ebay_product('boxing mma mouthguard gum shield', product) is True


@pytest.mark.unit
def test_rejects_non_combat_mouthguards_for_combat_query():
    product = {'name': 'Vettex Double Mouthguard Lip Guard Protection Football Mouth Piece ADULT'}

    assert is_excluded_ebay_product(product) is False
    assert is_relevant_ebay_product('boxing mma mouthguard gum shield', product) is False
