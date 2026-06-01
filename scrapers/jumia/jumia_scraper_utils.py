import requests
import json
import datetime
import re
import os
import unicodedata
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

EXCLUDED_PRODUCT_PATTERNS = [
    re.compile(r"\bvr[\s_-]*box\b"),
    re.compile(r"\bvrbox\b"),
    re.compile(r"\bvirtual[\s_-]*reality\b"),
    re.compile(r"\brealite[\s_-]*virtuelle\b"),
    re.compile(r"\bcasque[\s_-]+vr\b"),
    re.compile(r"\blunettes?[\s_-]+vr\b"),
    re.compile(r"\b3d[\s_-]+vr\b"),
    re.compile(r"\bdentifrice\b"),
    re.compile(r"\bmousse[\s_-]+blanchissante?\b"),
    re.compile(r"\beelhoe\b"),
    re.compile(r"\bmenthe[\s_-]+poivree\b"),
    re.compile(r"\bdents?[\s_-]+sensibles?\b"),
    re.compile(r"\bhaleine\b"),
]
EXCLUDED_PRODUCT_FIELDS = ("name", "product_url", "features")


def _searchable_text(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        value = " ".join(str(item) for item in value)
    normalized = unicodedata.normalize("NFKD", str(value).lower())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def is_excluded_jumia_product(product):
    haystack = " ".join(
        _searchable_text(product.get(field))
        for field in EXCLUDED_PRODUCT_FIELDS
    )
    return any(pattern.search(haystack) for pattern in EXCLUDED_PRODUCT_PATTERNS)


def scrape_product_details(url, session, headers, base_url):
    """Helper function to scrape a single product page."""
    try:
        # Extract numeric part from price strings
        def clean_price(p_str):
            if not p_str: return ""
            return p_str.replace('Dhs', '').replace(',', '').strip()

        resp = session.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
            
        s = BeautifulSoup(resp.text, 'html.parser')
        get_text = lambda sel: s.select_one(sel).text.strip() if s.select_one(sel) else None
        
        return {
            'name': get_text('h1.-fs20'),
            'current_price': clean_price(get_text('[data-price="true"]') or get_text('span.-b.-fs24')),
            'price_before_discount': clean_price(get_text('[data-price-old="true"]')),
            'discount': s.select_one('[data-disc]')['data-disc'] if s.select_one('[data-disc]') else None,
            'sizes': [lbl.text.strip() for lbl in s.select('.var-w .vl')],
            'features': [li.text.strip() for li in s.select('.markup.-mhm li, .card-b ul li')][:5],
            'product_url': url,
            'image_url': s.select_one('meta[property="og:image"]')['content'] if s.select_one('meta[property="og:image"]') else None,
            'stars': re.search(r'(\d+\.?\d*)', get_text('.stars') or '0').group(1) if re.search(r'(\d+\.?\d*)', get_text('.stars') or '0') else '0',
            'availability': "In Stock" if get_text('.stockInfo, p.-df.-i-ctr.-fs12.-pbs.-rd5') and "out of stock" not in get_text('.stockInfo, p.-df.-i-ctr.-fs12.-pbs.-rd5').lower() else ("Out of Stock" if get_text('.stockInfo, p.-df.-i-ctr.-fs12.-pbs.-rd5') and "out of stock" in get_text('.stockInfo, p.-df.-i-ctr.-fs12.-pbs.-rd5').lower() else "-"),
            'scraped_at': datetime.datetime.now().isoformat(),
        }
    except Exception as e:
        # print(f"Error scraping product {url}: {e}")
        return None

def scrape_jumia_category(query, output_file):
    print(f"Scraping Jumia for: {query}")
    
    base_url = "https://www.jumia.ma"
    search_url = f"{base_url}/catalog/?q={query.replace(' ', '+')}" 
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    session = requests.Session()
    
    try:
        response = session.get(search_url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to load search page: {response.status_code}")
            return 0
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all product articles
        product_links = soup.select('article.prd a.core')
        
        if not product_links:
            print(f"No products found for query: {query}")
            return 0
            
        print(f"Found {len(product_links)} products. Scraping details in parallel...")
        
        urls = [base_url + a['href'] if not a['href'].startswith('http') else a['href'] for a in product_links]
        
        # Use ThreadPoolExecutor to scrape product details in parallel
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            # map maintains order, but here we just want the results
            details = list(executor.map(lambda url: scrape_product_details(url, session, headers, base_url), urls))
            scraped_results = [d for d in details if d is not None]
            priced_results = [d for d in scraped_results if d.get('current_price')]
            results = [d for d in priced_results if not is_excluded_jumia_product(d)]

        skipped_without_price = len(scraped_results) - len(priced_results)
        if skipped_without_price:
            print(f"Skipped {skipped_without_price} products without current_price for query: {query}")
        skipped_excluded = len(priced_results) - len(results)
        if skipped_excluded:
            print(f"Skipped {skipped_excluded} excluded non-sports products for query: {query}")
                
        if results:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"Success: {len(results)} products saved to {output_file}")
            return len(results)
        else:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2, ensure_ascii=False)
            print(f"No products successfully scraped with prices for query: {query}; cleared {output_file}")
            return 0
            
    except Exception as e:
        print(f"Error scraping Jumia: {e}")
        return 0
            
    except Exception as e:
        print(f"Error scraping Jumia: {e}")
        return 0
