from ebay_scraper_utils import scrape_ebay_category
import os
import time
import random
import sys
# pyrefly: ignore [missing-import]
import undetected_chromedriver as uc

def _get_chrome_version():
    """Detect the major version of the installed Chrome binary."""
    import subprocess as _sp
    for binary in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        try:
            out = _sp.check_output([binary, "--version"], stderr=_sp.DEVNULL, text=True)
            major = int(out.strip().split()[-1].split(".")[0])
            return major
        except Exception:
            continue
    return None

def run_all_ebay_scrapes():
    print("Launching Stealth Chrome Browser for eBay...")
    
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # Check if running in Docker/Airflow
    if os.environ.get("AIRFLOW_HOME") or os.path.exists("/.dockerenv"):
        options.add_argument("--headless=new")
        options.add_argument("--disable-extensions")

    chrome_version = _get_chrome_version()
    driver = uc.Chrome(options=options, version_main=chrome_version, use_subprocess=True)
    
    # Execute CDP commands to further hide automation
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """
    })

    print("🌐 Warming up session (Visiting eBay homepage)...")
    try:
        driver.get("https://www.ebay.com")
        time.sleep(random.uniform(3, 6))
    except Exception as e:
        print(f"⚠️ Warm-up failed: {e}. Attempting to continue...")

    # Determine base directory for outputs (scrapers/ebay)
    base_dir = os.path.dirname(os.path.abspath(__file__))

    scrapes = [
        # Basketball
        ("basketball ball",     os.path.join(base_dir, "basketball/ebay_basketball_data.json")),
        ("basketball shoes",    os.path.join(base_dir, "basketball/ebay_basketball_shoes_data.json")),
        ("compression sleeves", os.path.join(base_dir, "basketball/ebay_compression_sleeves_data.json")),

        # Football (Soccer)
        ("soccer ball",         os.path.join(base_dir, "football/ebay_football_balls_data.json")),
        ("soccer shoes",       os.path.join(base_dir, "football/ebay_football_shoes_data.json")),
        ("goalkeeper gloves",   os.path.join(base_dir, "football/ebay_goalkeeper_gloves_data.json")),
        ("soccer shin pads",    os.path.join(base_dir, "football/ebay_shin_pads_data.json")),

        # Gym
        ("creatine",            os.path.join(base_dir, "gym/ebay_creatine_data.json")),
        ("supplements",   os.path.join(base_dir, "gym/ebay_supplements_data.json")),
        ("whey protein",        os.path.join(base_dir, "gym/ebay_whey_protein_data.json")),

        # Combat Sports
        ("boxing gloves",       os.path.join(base_dir, "combat-sports/ebay_combat_gloves_data.json")),
        ("groin guards",        os.path.join(base_dir, "combat-sports/ebay_groin_guards_data.json")),
        ("mma headgear",        os.path.join(base_dir, "combat-sports/ebay_headgear_data.json")),
        ("mouthguards",   os.path.join(base_dir, "combat-sports/ebay_mouthguards_data.json")),
        ("mma shin protectors", os.path.join(base_dir, "combat-sports/ebay_shin_protectors_data.json")),

        # Racket Sports
        ("tennis balls",        os.path.join(base_dir, "Racket-Sports/ebay_tennis_balls_data.json")),
        ("tennis rackets",      os.path.join(base_dir, "Racket-Sports/ebay_tennis_rackets_data.json")),

        # Volleyball
        ("volleyball",          os.path.join(base_dir, "Volleyball/ebay_volleyball_data.json")),
        ("volleyball net",      os.path.join(base_dir, "Volleyball/ebay_volleyball_nets_data.json")),
    ]

    total_success = 0
    total_products = 0

    for query, output_file in scrapes:
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Remove old file to avoid stale data
        if os.path.exists(output_file):
            os.remove(output_file)

        count = scrape_ebay_category(query, output_file, driver)
        
        if count > 0:
            total_success += 1
            total_products += count
        else:
            print(f"⚠️ Failed to scrape any products for: {query}")
            
        time.sleep(random.uniform(4, 7)) # Added more delay between categories

    print(f"\nScraping Summary (eBay):")
    print(f"Categories Attempted: {len(scrapes)}")
    print(f"Categories Successful: {total_success}")
    print(f"Total Products Scraped: {total_products}")

    driver.quit()

    if total_products == 0:
        print("❌ CRITICAL: No products were scraped for eBay. Failing script.")
        sys.exit(1)

if __name__ == "__main__":
    run_all_ebay_scrapes()
