from walmart_scraper_utils import scrape_walmart_category
import os
import time
import json
import sys
import random
# pyrefly: ignore [missing-import]
import undetected_chromedriver as uc

# Add parent directory to sys.path to import load_all_to_bigtable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from load_all_to_bigtable import get_bigtable_table, load_file_to_bigtable
    BIGTABLE_AVAILABLE = True
except ImportError:
    BIGTABLE_AVAILABLE = False

def _build_chrome_options(profile_dir, use_profile=True):
    """Build a fresh ChromeOptions object (must NOT be reused across launch attempts)."""
    # Detect version to match UA
    chrome_version = _get_chrome_version() or 136
    ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36"

    options = uc.ChromeOptions()
    if use_profile:
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument("--profile-directory=Default")
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # removing: options.add_argument(f"user-agent={ua}")
    
    # Stealth options
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    
    # Force a very common, clean User-Agent
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    # Extra flags when running inside Airflow/Docker
    if os.environ.get("AIRFLOW_HOME") or os.path.exists("/.dockerenv"):
        options.add_argument("--headless=new")
        options.add_argument("--disable-extensions")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--blink-settings=imagesEnabled=true")

    return options


def _fix_permissions(path):
    """Recursively set 777 permissions on a directory to avoid UID mismatches in Docker."""
    if not os.path.exists(path):
        return
    try:
        print(f"🔓 Fixing permissions for: {path}")
        # Use subprocess.run for better security and reliability
        import subprocess
        subprocess.run(["chmod", "-R", "777", path], check=False, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"⚠️ Warning: Could not fix permissions for {path}: {e}")


def _get_chrome_version():
    """Detect the major version of the installed Chrome binary at runtime.
    This avoids the version_main mismatch that causes 'cannot connect to chrome'
    when google-chrome-stable auto-updates between Docker builds.
    """
    import subprocess as _sp
    for binary in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        try:
            out = _sp.check_output([binary, "--version"], stderr=_sp.DEVNULL, text=True)
            # e.g. "Google Chrome 136.0.7103.92" → 136
            major = int(out.strip().split()[-1].split(".")[0])
            print(f"🔍 Detected Chrome version: {major} (binary: '{binary}')")
            return major
        except Exception:
            continue
    print("⚠️  Could not detect Chrome version — letting undetected-chromedriver auto-detect")
    return None


def run_all_walmart_scrapes():
    print("🧹 Cleaning up old Chrome processes and locks...")
    import subprocess
    subprocess.run(["pkill", "-9", "chrome"], check=False, stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "chromedriver"], check=False, stderr=subprocess.DEVNULL)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    profile_dir = os.path.join(script_dir, "walmart_profile")
    
    # Clean up all lock files/symlinks (SingletonLock, SingletonCookie, SingletonSocket)
    for lock_name in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
        lock_file = os.path.join(profile_dir, lock_name)
        if os.path.exists(lock_file) or os.path.islink(lock_file):
            try:
                print(f"🔓 Removing lock/link: {lock_file}")
                os.remove(lock_file)
            except Exception as e:
                print(f"⚠️ Could not remove {lock_name}: {e}")

    # Fix permissions to ensure Airflow user (UID 50000) can read/write the profile
    _fix_permissions(profile_dir)

    print("Launching Undetected Browser...")

    if os.environ.get("AIRFLOW_HOME"):
        print("🐳 Docker environment detected. Running in HEADLESS mode.")

    chrome_version = _get_chrome_version()
    
    is_airflow = os.environ.get("AIRFLOW_HOME") is not None
    
    # Attempt 1 — standard launch with profile
    try:
        print("🚀 Attempt 1: Launching with profile...")
        driver = uc.Chrome(
            options=_build_chrome_options(profile_dir, use_profile=True), 
            version_main=chrome_version,
            headless=False, # We use --headless=new in options instead
            use_subprocess=is_airflow
        )
    except Exception as e:
        print(f"❌ Failed to launch (attempt 1): {e}. Retrying with subprocess=True...")
        
        # Attempt 2 — subprocess mode (if not already used)
        try:
            print("🚀 Attempt 2: Launching with profile + forced subprocess...")
            driver = uc.Chrome(
                options=_build_chrome_options(profile_dir, use_profile=True), 
                version_main=chrome_version, 
                use_subprocess=True,
                headless=False
            )
        except Exception as e2:
            print(f"❌ Failed to launch (attempt 2): {e2}. Attempting SAFE MODE (no profile)...")
            
            # Attempt 3 — Safe Mode (NO PROFILE)
            try:
                print("🚀 Attempt 3: SAFE MODE (No Profile)...")
                driver = uc.Chrome(
                    options=_build_chrome_options(profile_dir, use_profile=False), 
                    version_main=chrome_version, 
                    use_subprocess=True,
                    headless=False
                )
            except Exception as e3:
                print(f"❌ Failed to launch (attempt 3): {e3}. Chrome is completely unreachable.")
                raise RuntimeError(f"Could not start Chrome in any mode: {e3}") from e3
    
    driver.maximize_window()
    
    # Execute CDP commands to further hide automation
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            # Hide WebDriver
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            
            # Hide Chrome Test Flags
            window.chrome = { runtime: {} };
            
            # Mock Plugins (Bots often have 0)
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            
            # Mock Languages
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            
            # Fix Permissions API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
        """
    })
    
    # --- Profile is now used, so we don't need manual cookie injection anymore ---
    print("👤 Using persistent profile. Session should be active.")
    
    # Randomize window size slightly for stealth
    width = random.randint(1280, 1920)
    height = random.randint(720, 1080)
    driver.set_window_size(width, height)
    
    print(f"🌐 Navigating to Walmart Homepage (Warm-up)...")
    driver.get("https://www.walmart.com")
    time.sleep(random.uniform(5, 8))
    
    # Check if we have a backup cookie file and inject it if we are still blocked
    cookie_file = os.path.join(script_dir, "walmart_cookies.json")
    if ("Robot" in driver.title or "blocked" in driver.current_url.lower()) and os.path.exists(cookie_file):
        print("🍪 Still blocked. Injecting backup cookies...")
        try:
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            print("✅ Cookies injected. Refreshing...")
            driver.refresh()
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ Could not inject cookies: {e}")

    # Final check
    if "blocked" in driver.current_url.lower() or "verification" in driver.title.lower():
        print("⚠️  Warning: Still blocked. Solving manually if visible...")
        time.sleep(10) # Give user a chance to solve it
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
        ("basketball", os.path.join(script_dir, "basketball", "walmart_basketball_data.json")),
        ("basketball shoes", os.path.join(script_dir, "basketball", "walmart_basketball_shoes_data.json")),
        ("compression sleeves", os.path.join(script_dir, "basketball", "walmart_compression_sleeves_data.json")),

        # Football (Soccer)
        ("soccer ball", os.path.join(script_dir, "football", "walmart_football_balls_data.json")),
        ("soccer cleats", os.path.join(script_dir, "football", "walmart_football_shoes_data.json")),
        ("goalkeeper gloves", os.path.join(script_dir, "football", "walmart_goalkeeper_gloves_data.json")),
        ("soccer shin guards", os.path.join(script_dir, "football", "walmart_shin_pads_data.json")),

        # Gym
        ("creatine", os.path.join(script_dir, "gym", "walmart_creatine_data.json")),
        ("supplements", os.path.join(script_dir, "gym", "walmart_supplements_data.json")),
        ("whey protein", os.path.join(script_dir, "gym", "walmart_whey_protein_data.json")),

        # Combat Sports
        ("boxing gloves", os.path.join(script_dir, "combat-sports", "walmart_combat_gloves_data.json")),
        ("groin guards", os.path.join(script_dir, "combat-sports", "walmart_groin_guards_data.json")),
        ("mma headgear", os.path.join(script_dir, "combat-sports", "walmart_headgear_data.json")),
        ("mouthguards", os.path.join(script_dir, "combat-sports", "walmart_mouthguards_data.json")),
        ("mma shin protectors", os.path.join(script_dir, "combat-sports", "walmart_shin_protectors_data.json")),

        # Racket Sports
        ("tennis balls", os.path.join(script_dir, "Racket-Sports", "walmart_tennis_balls_data.json")),

        # Volleyball
        ("volleyball", os.path.join(script_dir, "Volleyball", "walmart_volleyball_data.json")),
        ("volleyball net", os.path.join(script_dir, "Volleyball", "walmart_volleyball_nets_data.json")),
    ]
    
    total_success = 0
    total_products = 0
    
    for query, output_file in scrapes:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Remove old file to ensure we don't have stale data if this scrape fails
        if os.path.exists(output_file):
            os.remove(output_file)
            print(f"🗑️ Removed old data file: {output_file}")

        num_products = scrape_walmart_category(query, output_file, driver)
        
        if num_products > 0:
            total_success += 1
            total_products += num_products
            # Load to Bigtable if scraping was successful and table is available
            if table and os.path.exists(output_file):
                print(f"📥 Loading data from {output_file} to Bigtable...")
                rows_added = load_file_to_bigtable(table, output_file, "walmart")
                print(f"✅ Loaded {rows_added} records to Bigtable.")
        else:
            print(f"⚠️ Failed to scrape any products for: {query}")
            
        # Increased delay between categories for stealth
        wait_time = random.uniform(15, 30) if os.environ.get("AIRFLOW_HOME") else random.uniform(5, 10)
        print(f"😴 Waiting {wait_time:.1f}s before next category...")
        time.sleep(wait_time)
        
    print(f"\nScraping Summary:")
    print(f"Categories Attempted: {len(scrapes)}")
    print(f"Categories Successful: {total_success}")
    print(f"Total Products Scraped: {total_products}")
    
    driver.quit()
    
    if total_products == 0:
        print("❌ CRITICAL: No products were scraped for any category. Failing script.")
        sys.exit(1)
    
    if total_success < len(scrapes) / 2:
        print("⚠️ Warning: More than half of the categories failed to scrape.")
        # We might still want to succeed if some data was got, but let's be strict if needed.
        # For now, as long as some data was got, we exit 0, but total 0 is a failure.

if __name__ == "__main__":
    # Ensure we run from the project root if possible, or handle paths correctly
    # The DAG runs it with cwd='/app', and files are in /app/scrapers/walmart/...
    # But the script uses relative paths like 'walmart/basketball/...'
    # If it's run from /app/scrapers/walmart, it will create a 'walmart' dir inside there.
    # The DAG calls it as 'walmart/run_walmart_scraping.py' with cwd='/app'
    # So it should be fine.
    
    run_all_walmart_scrapes()
