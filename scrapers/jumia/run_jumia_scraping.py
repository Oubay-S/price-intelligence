from jumia_scraper_utils import scrape_jumia_category
import os
import time
import sys

# Add parent directory to sys.path to import load_all_to_bigtable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from load_all_to_bigtable import get_bigtable_table, load_file_to_bigtable
    BIGTABLE_AVAILABLE = True
except ImportError:
    BIGTABLE_AVAILABLE = False

def run_all_jumia_scrapes():
    # Initialize Bigtable if available
    table = None
    if BIGTABLE_AVAILABLE:
        print("🔗 Connecting to Bigtable Emulator...")
        table = get_bigtable_table()
    else:
        print("⚠️ Bigtable loading utility not found. Scraping only.")

    scrapes = [
        # Basketball
        ("ballon basketball",        "jumia/basketball/basketballs_data.json"),
        ("basketball shoes",         "jumia/basketball/basketball_shoes_data.json"),
        ("Compression Sleeves",      "jumia/basketball/compression_sleeves_data.json"),

        # Football (Soccer)
        ("ballon de football",       "jumia/football/balls_data.json"),
        ("football shoes",           "jumia/football/football-shoes.json"),
        ("shin guards",              "jumia/football/shin_pads_data.json"),
        ("Goalkeeper Gloves",        "jumia/football/goalkeeper_gloves_data.json"),

        # Gym
        ("Creatine",                 "jumia/gym/creatine_data.json"),
        ("supplements",              "jumia/gym/supplements_data.json"),
        ("Whey Protein",             "jumia/gym/whey_protein_data.json"),

        # Combat Sports
        ("gants de boxe",            "jumia/combat-sports/combat_gloves_data.json"),
        ("coquille boxe",            "jumia/combat-sports/groin_guards_data.json"),
        ("casque boxe",              "jumia/combat-sports/headgear_data.json"),
        ("protege dents",            "jumia/combat-sports/mouthguards_data.json"),
        ("protege tibia",            "jumia/combat-sports/shin_protectors_data.json"),

        # Racket Sports
        ("balle de tennis",          "jumia/Racket-Sports/tennis_balls_data.json"),

        # Volleyball
        ("volleyball",               "jumia/Volleyball/volleyball_data.json"),
        ("filet volleyball",         "jumia/Volleyball/volleyball_nets_data.json"),
    ]

    for query, output_file in scrapes:
        count = scrape_jumia_category(query, output_file)
        
        # Load to Bigtable if scraping was successful
        if count > 0 and table:
            # Adjust path for loading (relative to project root)
            full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), output_file)
            print(f"📥 Loading {count} items from {output_file} to Bigtable...")
            rows_added = load_file_to_bigtable(table, full_path, "jumia")
            print(f"✅ Loaded {rows_added} records to Bigtable.")
            
        time.sleep(3)

    print("\nAll Jumia scraping finished!")

if __name__ == "__main__":
    if not os.path.exists("jumia"):
        os.makedirs("jumia")

    run_all_jumia_scrapes()
