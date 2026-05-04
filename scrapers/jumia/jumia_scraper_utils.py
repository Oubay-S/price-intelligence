import requests
import json
import datetime
import re
import os
from bs4 import BeautifulSoup

def scrape_jumia_category(query, output_file):
    print(f"Scraping Jumia for: {query}")
    
    base_url = "https://www.jumia.ma"
    search_url = f"{base_url}/catalog/?q={query.replace(' ', '+')}" 
    
    h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        response = requests.get(search_url, headers=h)
        if response.status_code != 200:
            print(f"Failed to load search page: {response.status_code}")
            return 0
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        # Find all product articles
        product_links = soup.select('article.prd a.core')
        
        if not product_links:
            print(f"No products found for query: {query}")
            return 0
            
        print(f"Found {len(product_links)} products. Scraping details...")
        
        for a in product_links:
            try:
                url = base_url + a['href'] if not a['href'].startswith('http') else a['href']
                
                # Small delay to be polite
                # time.sleep(0.5) 
                
                s_resp = requests.get(url, headers=h)
                if s_resp.status_code != 200:
                    continue
                    
                s = BeautifulSoup(s_resp.text, 'html.parser')
                
                get_text = lambda sel: s.select_one(sel).text.strip() if s.select_one(sel) else None
                
                # Extract numeric part from price strings
                def clean_price(p_str):
                    if not p_str: return ""
                    return p_str.replace('Dhs', '').replace(',', '').strip()

                results.append({
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
                })
            except Exception as e:
                # print(f"Error scraping product {url}: {e}")
                continue
                
        if results:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"Success: {len(results)} products saved to {output_file}")
            return len(results)
        else:
            print(f"No products successfully scraped for query: {query}")
            return 0
            
    except Exception as e:
        print(f"Error scraping Jumia: {e}")
        return 0
