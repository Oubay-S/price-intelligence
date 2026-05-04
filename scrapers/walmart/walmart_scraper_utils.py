import os
import json
import time
import random
import re
import datetime
from bs4 import BeautifulSoup

# Conversion Rate: 1 USD = 9.25 MAD (Approx)
USD_TO_MAD = 9.25

def convert_to_mad(price_str):
    if not price_str or price_str == "N/A":
        return price_str
    # Extract numeric value (e.g. $9.99 -> 9.99)
    match = re.search(r"(\d+(?:,\d+)?(?:\.\d+)?)", price_str.replace(',', ''))
    if match:
        try:
            usd_val = float(match.group(1))
            mad_val = usd_val * USD_TO_MAD
            return f"{mad_val:.2f}"
        except:
            return price_str
    return price_str

def scrape_walmart_category(query, output_file, driver):
    print(f"Scraping Walmart for: {query}")
    
    url = f"https://www.walmart.com/search?q={query.replace(' ', '+')}"
    
    try:
        driver.get(url)
        time.sleep(random.uniform(2, 4))
        
        # Loop until CAPTCHA is solved
        while "Robot or human" in driver.title or "Verify you are a human" in driver.page_source or "px-captcha" in driver.page_source:
            print("CAPTCHA detected! Please solve it in the browser. Waiting 5 seconds...")
            time.sleep(5)
            
        print("Page loaded successfully! Scrolling to load images...")
        
        # Scroll down to trigger lazy loading of images
        for i in range(1, 4):
            driver.execute_script(f"window.scrollTo(0, {i * 1000});")
            time.sleep(1)
            
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Selectors for item containers
        items = soup.select('[data-testid="item-stack"] > div')
        if not items:
            items = soup.select('.mb0.ph0-xl.pv2-xl') or soup.select('[data-testid="list-view"] > div')
            
        if not items:
            with open("walmart_debug.html", "w", encoding='utf-8') as f:
                f.write(driver.page_source)
            print("No items found. Saved HTML to walmart_debug.html")
            
        products = []
        for item in items:
            try:
                name_el = item.select_one('[data-automation-id="product-title"]')
                if not name_el: continue
                name = name_el.text.strip()
                
                url_el = item.select_one('a[data-testid="product-title-link"]') or item.select_one('a')
                url_prod = "https://www.walmart.com" + url_el['href'] if url_el and url_el['href'].startswith('/') else (url_el['href'] if url_el else "N/A")
                
                price_container = item.select_one('[data-automation-id="product-price"]') or \
                                  item.select_one('[data-automation-id="price"]') or \
                                  item.select_one('span[itemprop="price"]')
                curr_p = "N/A"
                if price_container:
                    # Walmart has hidden spans for screen readers. 
                    # We want the main price, not the "price per unit" ($0.86/oz)
                    full_text = price_container.get_text(separator=" ").strip()
                    # Find all price-like patterns
                    prices = re.findall(r"\$\d+(?:,\d+)?(?:\.\d+)?", full_text)
                    
                    if prices:
                        # Logic: The first price is usually the main one. 
                        # But we must check if the text immediately following it contains a slash (unit price)
                        # or if there are multiple prices and the first is the "current" one.
                        main_price = None
                        for p in prices:
                            # Check if this specific price in the full_text is followed by a slash
                            # e.g. "$0.86 /oz"
                            price_index = full_text.find(p)
                            after_price = full_text[price_index + len(p) : price_index + len(p) + 5]
                            if '/' not in after_price:
                                main_price = p
                                break
                        
                        curr_p = main_price if main_price else prices[0]
                    else:
                        curr_p = full_text.split(" ")[0]
                
                old_p_el = item.select_one('[data-automation-id="product-price-was"]')
                old_p = None
                if old_p_el:
                    old_p_text = old_p_el.text.strip()
                    old_p_match = re.search(r"\$\d+(?:,\d+)?(?:\.\d+)?", old_p_text)
                    old_p = old_p_match.group(0) if old_p_match else old_p_text
                
                disc_el = item.select_one('.w_Vp')
                disc = disc_el.text.strip() if disc_el else None
                
                stars_el = item.select_one('[data-testid="product-ratings"]')
                stars = "0"
                if stars_el:
                    stars_text = stars_el.text.strip()
                    stars_match = re.search(r"(\d+\.?\d*)", stars_text)
                    stars = stars_match.group(1) if stars_match else "0"
                
                # Standardized availability logic
                avail = "In Stock"
                avail_el = item.select_one('.green, .red, .orange')
                if avail_el:
                    txt = avail_el.text.lower()
                    if 'out of' in txt: 
                        avail = "Out of Stock"
                    elif any(word in txt for word in ['in stock', 'left', 'only', 'available']):
                        avail = "In Stock"
                    else:
                        avail = "-"
                else:
                    # If nothing found, we assume In Stock based on search results usually showing live items
                    avail = "In Stock"
                
                img_el = item.select_one('img[data-testid="productTileImage"]') or item.select_one('img')
                img_url = "N/A"
                if img_el:
                    if img_el.get('srcset'):
                        img_url = img_el.get('srcset').split(',')[0].split(' ')[0]
                    else:
                        img_url = img_el.get('src') or img_el.get('data-src') or "N/A"
                
                features_el = item.select_one('[data-testid="product-variant-information"]')
                features = features_el.text.strip() if features_el else "N/A"
                if features != "N/A":
                    # Split by comma, take first 5, and join back
                    f_list = [f.strip() for f in features.split(',') if f.strip()]
                    features = ", ".join(f_list[:5])
                
                sizes = "N/A"
                
                products.append({
                    "name": name,
                    "current_price": convert_to_mad(curr_p),
                    "price_before_discount": convert_to_mad(old_p),
                    "discount": disc,
                    "sizes": sizes,
                    "features": features,
                    "product_url": url_prod,
                    "image_url": img_url,
                    "stars": stars,
                    "availability": avail,
                    "scraped_at": datetime.datetime.now().isoformat()
                })
                
                # Removed max_items break
            except:
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
        print(f"Error scraping Walmart: {e}")
        return 0
