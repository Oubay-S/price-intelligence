from ebay_scraper_utils import scrape_ebay_category
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

def run_all_ebay_scrapes():
    print("Launching Stealth Chrome Browser for eBay... Prepare to solve any CAPTCHAs!")
    options = uc.ChromeOptions()
    # Launch visible browser so user can interact if needed
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
        ("basketball ball",     "ebay/basketball/ebay_basketball_data.json"),
        ("basketball shoes",    "ebay/basketball/ebay_basketball_shoes_data.json"),
        ("compression sleeves", "ebay/basketball/ebay_compression_sleeves_data.json"),

        # Football (Soccer)
        ("soccer ball",         "ebay/football/ebay_football_balls_data.json"),
        ("soccer shoes",       "ebay/football/ebay_football_shoes_data.json"),
        ("goalkeeper gloves",   "ebay/football/ebay_goalkeeper_gloves_data.json"),
        ("soccer shin guards",  "ebay/football/ebay_shin_pads_data.json"),

        # Gym
        ("creatine",            "ebay/gym/ebay_creatine_data.json"),
        ("supplements",   "ebay/gym/ebay_supplements_data.json"),
        ("whey protein",        "ebay/gym/ebay_whey_protein_data.json"),

        # Combat Sports
        ("boxing gloves",       "ebay/combat-sports/ebay_combat_gloves_data.json"),
        ("groin guards",        "ebay/combat-sports/ebay_groin_guards_data.json"),
        ("mma headgear",        "ebay/combat-sports/ebay_headgear_data.json"),
        ("mouthguards",   "ebay/combat-sports/ebay_mouthguards_data.json"),
        ("mma shin protectors", "ebay/combat-sports/ebay_shin_protectors_data.json"),

        # Racket Sports
        ("tennis balls",        "ebay/Racket-Sports/ebay_tennis_balls_data.json"),
        ("tennis rackets",      "ebay/Racket-Sports/ebay_tennis_rackets_data.json"),

        # Volleyball
        ("volleyball",          "ebay/Volleyball/ebay_volleyball_data.json"),
        ("volleyball net",      "ebay/Volleyball/ebay_volleyball_nets_data.json"),
    ]

    for query, output_file in scrapes:
        count = scrape_ebay_category(query, output_file, driver)
        
        # Load to Bigtable if scraping was successful
        if count > 0 and table:
            print(f"📥 Loading {count} items from {output_file} to Bigtable...")
            rows_added = load_file_to_bigtable(table, output_file, "ebay")
            print(f"✅ Loaded {rows_added} records to Bigtable.")
            
        time.sleep(5)

    print("All eBay scraping finished! Closing browser...")
    driver.quit()

if __name__ == "__main__":
    if not os.path.exists("ebay"):
        os.makedirs("ebay")

    run_all_ebay_scrapes()
