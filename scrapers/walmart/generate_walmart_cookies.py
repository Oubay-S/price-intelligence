import undetected_chromedriver as uc
import time
import json
import os

def generate_cookies():
    print("🚀 Launching visible browser to grab Walmart cookies...")
    options = uc.ChromeOptions()
    driver = uc.Chrome(version_main=147, options=options)
    
    print("Navigating to Walmart...")
    driver.get("https://www.walmart.com")
    
    print("\n" + "="*60)
    print("⚠️ PLEASE LOOK AT THE BROWSER ⚠️")
    print("If you see a CAPTCHA (Press & Hold), solve it now.")
    print("Search for a random product and browse for 5-10 seconds.")
    print("This builds a 'trust score' with Walmart.")
    print("Once the page looks completely normal, come back here.")
    print("="*60 + "\n")
    
    input("👉 Press ENTER here in the terminal ONLY AFTER you are verified and the site is fully loaded: ")
    
    print("Saving cookies...")
    cookies = driver.get_cookies()
    
    # Save to file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cookie_path = os.path.join(script_dir, "walmart_cookies.json")
    
    with open(cookie_path, "w") as f:
        json.dump(cookies, f, indent=4)
        
    print(f"✅ Successfully saved {len(cookies)} cookies to {cookie_path}!")
    print("You can now run your Airflow scraper in the background. If it fails again next week, just run this script again.")
    driver.quit()

if __name__ == "__main__":
    generate_cookies()
