import datetime
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

SCRAPERS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRAPERS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRAPERS_ROOT))

from product_quality import is_relevant_product

GBP_TO_MAD = 12.50
BASE_URL = "https://www.sportsdirect.com"

CATEGORY_PATHS = {
    "basketball": "/basketball/all-basketball",
    "basketball ball": "/basketball/basketballs",
    "basketballs": "/basketball/basketballs",
    "basketball shoes": "/basketball/basketball-shoes",
    "football": "/football/football-equipment/footballs",
    "football boots": "/football/football-boots",
    "football shoes": "/football/football-boots",
    "goalkeeper gloves": "/football/goalkeeper-gloves",
    "shin pads": "/football/shin-pads",
    "tennis balls": "/tennis/tennis-balls",
    "tennis rackets": "/tennis/tennis-rackets",
    "volleyball": "/volleyball",
    "footballs": "/football/football-equipment/footballs",
}

REQUIRED_NAME_PATTERNS = {
    "basketball": (r"\bbasketball\b",),
    "basketball shoes": (r"\bbasketball\b", r"\b(shoe|shoes|trainer|trainers)\b"),
    "compression sleeves": (r"\b(compression|sleeve|sleeves)\b",),
    "football": (r"\b(football|ball|balls)\b",),
    "footballs": (r"\b(football|ball|balls)\b",),
    "football boots": (r"\b(football|boot|boots|astro|turf|firm ground|fg|mg|ag)\b",),
    "football shoes": (r"\b(football|boot|boots|astro|turf|firm ground|fg|mg|ag)\b",),
    "goalkeeper gloves": (r"\b(goalkeeper|glove|gloves)\b",),
    "shin pads": (r"\b(shin|guard|guards|pad|pads)\b",),
    "creatine": (r"\bcreatine\b",),
    "supplements": (r"\b(supplement|supplements|vitamin|multivitamin|omega|probiotic|protein|creatine|cbd|caps|capsule|capsules|tablet|tablets|softgel|softgels|oil)\b",),
    "whey protein": (r"\b(whey|protein)\b",),
    "boxing gloves": (r"\b(boxing|glove|gloves)\b",),
    "groin guards": (r"\b(groin|abdo|protector)\b",),
    "head guard": (r"\b(headguard|headguards|head guard|head guards|headgear)\b",),
    "mouthguards": (r"\b(mouthguard|mouthguards|mouth guard|mouth guards|mgrd)\b",),
    "shin guards": (r"\b(shin|guard|guards|pad|pads)\b",),
    "tennis balls": (r"\btennis\b", r"\b(ball|balls)\b"),
    "tennis rackets": (r"\btennis\b", r"\b(racket|rackets|racquet|racquets)\b"),
    "volleyball": (r"\bvolleyball\b",),
}


def _parse_number(value):
    if value in (None, "", "N/A"):
        return None
    match = re.search(r"(\d+(?:[.,]\d+)?)", str(value).replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _format_mad(gbp_value):
    if gbp_value is None:
        return None
    return f"{gbp_value * GBP_TO_MAD:.2f}"


def convert_to_mad(price_str):
    gbp_value = _parse_number(price_str)
    if gbp_value is None:
        return "N/A" if price_str in (None, "", "N/A") else str(price_str)
    return _format_mad(gbp_value)


def _clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def _clean_discount(value):
    discount = _clean_text(value)
    match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*off", discount, flags=re.I)
    return match.group(1) if match else (discount or None)


def _discount_percent(value):
    match = re.search(r"(\d+(?:\.\d+)?)", value or "")
    return float(match.group(1)) if match else None


def _calculate_price_before_discount(current_price_gbp, discount):
    percent = _discount_percent(discount)
    if current_price_gbp is None or percent is None or percent >= 100:
        return None
    return current_price_gbp / (1 - (percent / 100))


def _candidate_urls(query):
    normalized = query.lower().strip()
    urls = []
    if normalized in CATEGORY_PATHS:
        urls.append(urljoin(BASE_URL, CATEGORY_PATHS[normalized]))
    urls.append(f"{BASE_URL}/searchresults?descriptionfilter={quote_plus(query)}")
    return urls


def _extract_sizes(card):
    text = _clean_text(card.get_text(" "))
    match = re.search(r"Sizes?:\s*(.*?)(?:£|RRP|$)", text, flags=re.I)
    if not match:
        return "N/A"
    sizes = match.group(1).strip(" ,")
    return re.sub(r"\s+From$", "", sizes, flags=re.I)


def _is_relevant_product(query, name):
    product = {"name": name}
    if not is_relevant_product(product, store="sport-direct", query=query):
        return False

    patterns = REQUIRED_NAME_PATTERNS.get(query.lower().strip())
    if not patterns:
        return True
    return all(re.search(pattern, name, flags=re.I) for pattern in patterns)


def _parse_product_cards(soup, query):
    cards = soup.select("li[li-productid][li-name]")
    products = []

    for card in cards:
        name = _clean_text(card.get("li-name"))
        if not name or not _is_relevant_product(query, name):
            continue

        raw_price = card.get("li-price") or "N/A"
        current_price_gbp = _parse_number(raw_price)
        old_price_el = card.select_one(".wasprice, .rrp, [class*='WasPrice'], [class*='TicketPrice']")
        discount_match = re.search(r"\(([^)]*off[^)]*)\)", card.get_text(" "), flags=re.I)
        discount = _clean_discount(discount_match.group(1)) if discount_match else None
        old_price_gbp = _parse_number(old_price_el.get_text(" ")) if old_price_el else None
        if old_price_gbp is None and discount:
            old_price_gbp = _calculate_price_before_discount(current_price_gbp, discount)

        products.append({
            "name": name,
            "current_price": _format_mad(current_price_gbp) or "N/A",
            "price_before_discount": _format_mad(old_price_gbp),
            "discount": discount,
            "sizes": _extract_sizes(card),
            "features": card.get("li-brand") or "N/A",
            "product_url": urljoin(BASE_URL, card.get("li-url") or ""),
            "image_url": card.get("li-imageurl") or "N/A",
            "stars": "0",
            "availability": "In Stock",
            "scraped_at": datetime.datetime.now().isoformat(),
        })

    return products


def scrape_sport_direct_category(query, output_file):
    print(f"Scraping Sports Direct for: {query}")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-GB,en;q=0.9",
    }

    last_html = ""
    last_url = ""

    try:
        for url in _candidate_urls(query):
            response = requests.get(url, headers=headers, timeout=25)
            last_html = response.text
            last_url = response.url
            if response.status_code != 200:
                print(f"Failed to load Sports Direct page {response.url}: {response.status_code}")
                continue

            products = _parse_product_cards(BeautifulSoup(response.text, "html.parser"), query)
            if products:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(products, f, indent=4, ensure_ascii=False)
                print(f"Success: {len(products)} products saved to {output_file}")
                return len(products)

            print(f"No product cards found at {response.url}; trying next candidate if available.")

        debug_path = os.path.join(os.path.dirname(output_file), "sport_direct_debug.html")
        os.makedirs(os.path.dirname(debug_path), exist_ok=True)
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(last_html)
        print(f"No products found for query '{query}'. Last URL was {last_url}. Saved debug HTML to {debug_path}")
        return 0

    except Exception as exc:
        print(f"Error scraping Sports Direct: {exc}")
        return 0
