from walmart.walmart_scraper_utils import scrape_walmart_category
import os
import undetected_chromedriver as uc
import time
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
    options = uc.ChromeOptions()
    # We will launch the browser so the user can interact if a CAPTCHA appears
    driver = uc.Chrome(version_main=147, options=options)
    driver.maximize_window()
    
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
