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


@pytest.mark.unit
@pytest.mark.parametrize(
    'product',
    [
        {'name': 'OPI Top Coat Gel Color Stay Shiny Vernis de Protection GC003 15ml'},
        {'name': 'Kiwi Shine & Protect Nettoyant Chaussure/Cirage Marine 75 ml neutre transparent'},
        {'name': 'Car Interior Shine & Protect Spray 118ml Leather Plastic and Vinyl Renovation Treatment with Application Sponge'},
        {'name': 'Flamingo Shine & Protect Spray Nettoyant Auto pour Vinyle Caoutchouc et Plastique'},
        {'name': "Bellota Scie de jardinage, Scie d'Elagage a Dents Japonaises"},
        {'name': 'Peigne metallique de haute qualite anti-poux pour cheveux et pelage animal'},
        {'name': 'Espadrilles pour femmes couleur beige'},
        {'name': 'Cahier stickers LED notebook jeu mug sandale'},
        {'name': 'Brosse medicale dentaire avec revelateur'},
        {'name': 'Poisson decoratif aquarium'},
        {'name': 'Bracelet fantaisie femme'},
    ],
)
def test_rejects_jumia_false_positive_products(product):
    assert is_excluded_product(product, store='jumia') is True
    assert is_relevant_product(product, store='jumia', category='football') is False


@pytest.mark.unit
def test_jumia_keyword_exclusions_are_store_scoped():
    product = {'name': 'Sac de frappe boxe lourd entrainement'}

    assert is_relevant_product(product, store='jumia', category='combat-sports') is False
    assert is_relevant_product(product, store='ebay', category='combat-sports') is True


@pytest.mark.unit
@pytest.mark.parametrize(
    'product',
    [
        {'name': 'Laptop Sleeve 15 Inch Protective Case'},
        {'name': 'Women Running Trainers'},
        {'name': "Women's Football Boots"},
        {'name': 'Womens Gym Top'},
    ],
)
def test_rejects_sport_direct_false_positive_products(product):
    assert is_excluded_product(product, store='sport-direct') is True
    assert is_relevant_product(product, store='sport-direct', category='football') is False


@pytest.mark.unit
def test_sport_direct_women_exclusion_is_store_scoped():
    product = {'name': "Women's Boxing Gloves"}

    assert is_relevant_product(product, store='sport-direct', category='combat-sports') is False
    assert is_relevant_product(product, store='ebay', category='combat-sports') is True
