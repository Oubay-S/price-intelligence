from walmart_scraper_utils import scrape_walmart_category
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import json
import sys

# Add parent directory to sys.path to import load_all_to_bigtable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from load_all_to_bigtable import get_bigtable_table, load_file_to_bigtable
    BIGTABLE_AVAILABLE = True
except ImportError:
    BIGTABLE_AVAILABLE = False

def run_all_walmart_scrapes():
    print("Launching Stealth Chrome Browser... Prepare to solve any CAPTCHAs!")
    options = Options()
    
    # --- Docker/Headless Configuration ---
    # Detect if we are running in Docker (Airflow sets AIRFLOW_HOME)
    if os.environ.get("AIRFLOW_HOME"):
        print("🐳 Docker environment detected. Running in HEADLESS mode.")
        options.add_argument("--headless=new")
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # Anti-detection flags
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

    # Try to use the system's chromedriver or let selenium find it
    try:
        driver = webdriver.Chrome(options=options)
    except Exception:
        # Fallback to webdriver_manager if system driver is not found
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # Further hide Selenium
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    driver.maximize_window()
    
    # --- Cookie Loading Logic ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cookie_path = os.path.join(script_dir, "walmart_cookies.json")
    
    if os.path.exists(cookie_path):
        print("🍪 Loading saved cookies...")
        try:
            # We must visit the domain once before adding cookies
            driver.get("https://www.walmart.com")
            time.sleep(2)
            
            with open(cookie_path, "r") as f:
                cookies = json.load(f)
                for cookie in cookies:
                    # Filter out problematic keys for Selenium
                    if 'expiry' in cookie:
                        del cookie['expiry']
                    try:
                        driver.add_cookie(cookie)
                    except Exception as e:
                        print(f"  Warning: Could not add a cookie: {e}")
            
            print("✅ Cookies injected. Refreshing page...")
            driver.refresh()
            time.sleep(2)
        except Exception as e:
            print(f"❌ Error loading cookies: {e}")
    else:
        print("⚠️ No walmart_cookies.json found. Proceeding without saved session.")
    # ----------------------------
    
    # Initialize Bigtable if available
    table = None
    if BIGTABLE_AVAILABLE:
        print("🔗 Connecting to Bigtable Emulator...")
        table = get_bigtable_table()
    else:
        print("⚠️ Bigtable loading utility not found. Scraping only.")

    scrapes = [
        # Basketball
        ("basketball", "walmart/basketball/walmart_basketball_data.json"),
        ("basketball shoes", "walmart/basketball/walmart_basketball_shoes_data.json"),
        ("compression sleeves", "walmart/basketball/walmart_compression_sleeves_data.json"),
        
        # Football (Soccer)
        ("soccer ball", "walmart/football/walmart_football_balls_data.json"),
        ("soccer cleats", "walmart/football/walmart_football_shoes_data.json"),
        ("goalkeeper gloves", "walmart/football/walmart_goalkeeper_gloves_data.json"),
        ("soccer shin guards", "walmart/football/walmart_shin_pads_data.json"),
        
        # Gym
        ("creatine", "walmart/gym/walmart_creatine_data.json"),
        ("supplements", "walmart/gym/walmart_supplements_data.json"),
        ("whey protein", "walmart/gym/walmart_whey_protein_data.json"),
        
        # Combat Sports
        ("boxing gloves", "walmart/combat-sports/walmart_combat_gloves_data.json"),
        ("groin guards", "walmart/combat-sports/walmart_groin_guards_data.json"),
        ("mma headgear", "walmart/combat-sports/walmart_headgear_data.json"),
        ("mouthguards", "walmart/combat-sports/walmart_mouthguards_data.json"),
        ("mma shin protectors", "walmart/combat-sports/walmart_shin_protectors_data.json"),
        
        # Racket Sports
        ("tennis balls", "walmart/Racket-Sports/walmart_tennis_balls_data.json"),
        
        # Volleyball
        ("volleyball", "walmart/Volleyball/walmart_volleyball_data.json"),
        ("volleyball net", "walmart/Volleyball/walmart_volleyball_nets_data.json"),
    ]
    
    for query, output_file in scrapes:
        scrape_walmart_category(query, output_file, driver)
        
        # Load to Bigtable if scraping was successful and table is available
        if table and os.path.exists(output_file):
            print(f"📥 Loading data from {output_file} to Bigtable...")
            rows_added = load_file_to_bigtable(table, output_file, "walmart")
            print(f"✅ Loaded {rows_added} records to Bigtable.")
            
        time.sleep(5)
        
    print("All scraping finished! Closing browser...")
    driver.quit()

if __name__ == "__main__":
    if not os.path.exists("walmart"):
        os.makedirs("walmart")
    
    run_all_walmart_scrapes()
