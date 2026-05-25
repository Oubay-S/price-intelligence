from jumia_scraper_utils import scrape_jumia_category
import os
import time
import sys

def run_all_jumia_scrapes():
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
        time.sleep(3)

    print("\nAll Jumia scraping finished!")

if __name__ == "__main__":
    if not os.path.exists("jumia"):
        os.makedirs("jumia")

    run_all_jumia_scrapes()
