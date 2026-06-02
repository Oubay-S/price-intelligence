import os
import json
import time
import random
import re
import datetime
import sys
from pathlib import Path

SCRAPERS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRAPERS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRAPERS_ROOT))

from product_quality import is_excluded_product, is_relevant_product

# Conversion Rate: 1 USD = 9.25 MAD (Approx) — same as other USD sources
USD_TO_MAD = 9.25

class EbayDriverLostError(RuntimeError):
    """Raised when Selenium's connection to Chrome is no longer usable."""


def _is_driver_lost_error(exc):
    message = str(exc).lower()
    return any(marker in message for marker in (
        "connection refused",
        "remote end closed connection",
        "max retries exceeded",
        "invalid session id",
        "disconnected",
        "chrome not reachable",
    ))


def is_excluded_ebay_product(product):
    return is_excluded_product(product)


def is_relevant_ebay_product(query, product):
    return is_relevant_product(product, store="ebay", query=query)


def convert_to_mad(price_str):
    if not price_str or price_str == "N/A":
        return price_str
    # Extract numeric value (e.g. "$9.99" or "9.99" -> 9.99)
    match = re.search(r"(\d+(?:[.,]\d+)?)", price_str.replace(',', ''))
    if match:
        try:
            usd_val = float(match.group(1))
            mad_val = usd_val * USD_TO_MAD
            return f"{mad_val:.2f}"
        except:
            return price_str
    return price_str

def scrape_ebay_category(query, output_file, driver):
    from bs4 import BeautifulSoup
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    print(f"Scraping eBay for: {query}")

    url = f"https://www.ebay.com/sch/i.html?_nkw={query.replace(' ', '+')}&_sacat=0"

    try:
        driver.get(url)
        time.sleep(random.uniform(2, 4))

        # Loop until CAPTCHA/Security Challenge is solved OR products appear
        while ("Security Measure" in driver.title or "unusual activity" in driver.page_source or "Please verify you're a human" in driver.page_source):
            # Check if products are actually visible (this is the most reliable way)
            if driver.find_elements(By.CSS_SELECTOR, ".s-item__title") or driver.find_elements(By.ID, "srp-river-results"):
                break
            
            print(f"Waiting for manual verification... (Title: {driver.title})")
            time.sleep(5)

        # Wait for the result items or the spinner to disappear
        print("Waiting for items to load...")
        try:
            # Wait up to 10 seconds for at least one product item to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".s-item"))
            )
        except:
            print("Items didn't appear in time, scrolling anyway...")

        print("Page loaded. Scrolling to trigger lazy loading...")

        for i in range(1, 5):
            driver.execute_script(f"window.scrollTo(0, {i * 1000});")
            time.sleep(1.5)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Universal Selectors - Try all known formats (List view, Grid/Card view, etc.)
        items = soup.select('ul.srp-results .s-item') or \
                soup.select('.s-item') or \
                soup.select('.s-card') or \
                soup.select('.su-card-container')

        if not items:
            source = driver.page_source
            if source and len(source) > 100:
                with open("ebay_debug.html", "w", encoding='utf-8') as f:
                    f.write(source)
                print(f"No items found. Saved {len(source)} bytes of HTML to ebay_debug.html")
            else:
                print("No items found, and page source was empty or too small. Likely a connection block.")

        products = []
        for item in items:
            try:
                # --- Name ---
                # Try multiple possible title selectors
                name_el = item.select_one('.s-item__title') or \
                          item.select_one('.s-card__title') or \
                          item.select_one('.su-card-container__title')
                
                if not name_el:
                    continue
                
                name = name_el.get_text(separator=' ').strip()
                if name.lower() in ["shop on ebay", ""]:
                    continue

                # --- URL ---
                url_el = item.select_one('a.s-item__link') or \
                         item.select_one('a[href*="/itm/"]')
                url_prod = url_el['href'] if url_el else "N/A"

                # --- Current Price ---
                price_el = item.select_one('.s-item__price') or \
                           item.select_one('.s-card__price') or \
                           item.select_one('.su-card-container__price')
                curr_p = price_el.text.strip() if price_el else "N/A"

                # --- Old Price (before discount) ---
                old_p_el = item.select_one('.s-item__trending-price') or \
                           item.select_one('.s-item__original-price') or \
                           item.select_one('.s-card__trending-price')
                old_p = old_p_el.text.strip() if old_p_el else None

                # --- Discount ---
                disc_el = item.select_one('.s-item__discount') or \
                          item.select_one('.s-card__discount')
                disc = disc_el.text.strip() if disc_el else None

                # --- Stars / Rating ---
                stars_el = item.select_one('.x-star-rating') or \
                           item.select_one('.s-card__reviews')
                stars = "0"
                if stars_el:
                    stars_match = re.search(r"(\d+\.?\d*)", stars_el.text)
                    stars = stars_match.group(1) if stars_match else "0"

                # --- Availability ---
                avail = "In Stock"

                # --- Image ---
                img_el = item.select_one('img') # Fallback to first img in container
                img_url = "N/A"
                if img_el:
                    img_url = img_el.get('src') or img_el.get('data-src') or img_el.get('data-lazy-src') or "N/A"

                # --- Features / Condition ---
                cond_el = item.select_one('.SECONDARY_INFO') or \
                          item.select_one('.s-item__subtitle') or \
                          item.select_one('.s-card__subtitle')
                features = cond_el.text.strip() if cond_el else "N/A"

                product = {
                    "name": name,
                    "current_price": convert_to_mad(curr_p),
                    "price_before_discount": convert_to_mad(old_p),
                    "discount": disc,
                    "sizes": "N/A",
                    "features": features,
                    "product_url": url_prod,
                    "image_url": img_url,
                    "stars": stars,
                    "availability": avail,
                    "scraped_at": datetime.datetime.now().isoformat()
                }

                if not is_relevant_ebay_product(query, product):
                    continue

                products.append(product)

            except Exception as e:
                # print(f"Error parsing item: {e}")
                continue

        if products:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=4, ensure_ascii=False)
            print(f"Success: {len(products)} products saved to {output_file}")
            return len(products)
        else:
            print(f"No products found for query: {query}")
            return 0

    except Exception as e:
        if _is_driver_lost_error(e):
            raise EbayDriverLostError(f"eBay Chrome/WebDriver session was lost: {e}") from e
        print(f"Error scraping eBay: {e}")
        return 0
