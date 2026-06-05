import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scrapers', 'jumia'))

from jumia_scraper_utils import is_excluded_jumia_product


@pytest.mark.unit
@pytest.mark.parametrize(
    'product',
    [
        {'name': 'VR BOX 3D Glasses for phones'},
        {'name': 'Casque VR Realite Virtuelle 3D'},
        {'name': 'Lunettes VR smartphone', 'current_price': '99'},
        {'product_url': 'https://www.jumia.ma/mlp-vr-box/vr-box-g02.html'},
        {'features': ['Virtual Reality headset', 'Phone support']},
        {'name': 'Dentifrice mousse blanchissant EELHOE a la menthe poivree'},
        {'name': 'Dents sensibles soin quotidien haleine fraiche'},
        {'name': 'OPI Top Coat Gel Color Stay Shiny Vernis de Protection GC003 15ml'},
        {'name': 'Kiwi Shine & Protect Nettoyant Chaussure/Cirage Marine 75 ml neutre'},
        {'name': 'Car Interior Shine & Protect Spray 118ml Vinyl Renovation Treatment'},
        {'name': 'Flamingo Shine & Protect Spray Nettoyant Auto pour Vinyle Caoutchouc'},
        {'name': 'Sac sport non souhaite'},
        {'name': 'Machine revelateur cahier stickers led notebook jeu'},
        {'name': 'Espadrilles pour femmes couleur beige'},
        {'name': 'T-shirt mug sandale piege aquatique brace montre casquette'},
        {'name': 'Produit medical dentaire'},
        {'name': "Bellota Scie de jardinage, Scie d'Elagage a Dents Japonaises"},
        {'name': 'Peigne metallique anti-poux pour cuir chevelu et pelage animal'},
        {'name': 'Brosse nettoyage'},
        {'name': 'Poisson decoratif aquarium'},
        {'name': 'Bracelet fantaisie femme'},
    ],
)
def test_excludes_jumia_non_sports_products(product):
    assert is_excluded_jumia_product(product) is True


@pytest.mark.unit
@pytest.mark.parametrize(
    'product',
    [
        {'name': 'Casque de boxe professionnel'},
        {'name': 'Gants de boxe entrainement'},
        {'name': 'Protege dents boxe adulte'},
        {'name': 'Ballon de football taille 5'},
    ],
)
def test_keeps_real_sports_products(product):
    assert is_excluded_jumia_product(product) is False
