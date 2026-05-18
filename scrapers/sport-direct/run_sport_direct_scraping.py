from sport_direct_scraper_utils import scrape_sport_direct_category
import os
import time
import sys


def run_all_sport_direct_scrapes():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    scrapes = [
        # Basketball
        ("basketball", os.path.join(base_dir, "basketball/sport_direct_basketball_data.json")),
        ("basketball shoes", os.path.join(base_dir, "basketball/sport_direct_basketball_shoes_data.json")),
        ("compression sleeves", os.path.join(base_dir, "basketball/sport_direct_compression_sleeves_data.json")),

        # Football (Soccer)
        ("football", os.path.join(base_dir, "football/sport_direct_football_balls_data.json")),
        ("football boots", os.path.join(base_dir, "football/sport_direct_football_shoes_data.json")),
        ("goalkeeper gloves", os.path.join(base_dir, "football/sport_direct_goalkeeper_gloves_data.json")),
        ("shin pads", os.path.join(base_dir, "football/sport_direct_shin_pads_data.json")),

        # Gym
        ("creatine", os.path.join(base_dir, "gym/sport_direct_creatine_data.json")),
        ("supplements", os.path.join(base_dir, "gym/sport_direct_supplements_data.json")),
        ("whey protein", os.path.join(base_dir, "gym/sport_direct_whey_protein_data.json")),

        # Combat Sports
        ("boxing gloves", os.path.join(base_dir, "combat-sports/sport_direct_combat_gloves_data.json")),
        ("groin guards", os.path.join(base_dir, "combat-sports/sport_direct_groin_guards_data.json")),
        ("head guard", os.path.join(base_dir, "combat-sports/sport_direct_headgear_data.json")),
        ("mouthguards", os.path.join(base_dir, "combat-sports/sport_direct_mouthguards_data.json")),
        ("shin guards", os.path.join(base_dir, "combat-sports/sport_direct_shin_protectors_data.json")),

        # Racket Sports
        ("tennis balls", os.path.join(base_dir, "Racket-Sports/sport_direct_tennis_balls_data.json")),
        ("tennis rackets", os.path.join(base_dir, "Racket-Sports/sport_direct_tennis_rackets_data.json")),

        # Volleyball
        ("volleyball", os.path.join(base_dir, "Volleyball/sport_direct_volleyball_data.json")),
    ]

    total_success = 0
    total_products = 0

    for query, output_file in scrapes:
        count = scrape_sport_direct_category(query, output_file)
        if count > 0:
            total_success += 1
            total_products += count
        else:
            print(f"Failed to scrape any products for: {query}")
        time.sleep(3)

    print("\nScraping Summary (Sports Direct):")
    print(f"Categories Attempted: {len(scrapes)}")
    print(f"Categories Successful: {total_success}")
    print(f"Total Products Scraped: {total_products}")

    if total_products == 0:
        print("CRITICAL: No products were scraped for Sports Direct. Failing script.")
        sys.exit(1)


if __name__ == "__main__":
    run_all_sport_direct_scrapes()
