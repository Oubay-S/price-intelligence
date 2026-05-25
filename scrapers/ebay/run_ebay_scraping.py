from ebay_scraper_utils import EbayDriverLostError, scrape_ebay_category
import os
from pathlib import Path
import time
import random
import sys


def _configure_writable_runtime_dirs():
    runtime_root = Path(os.environ.get("EBAY_CHROME_RUNTIME_DIR", "/tmp/ebay_chrome"))
    runtime_root.mkdir(parents=True, exist_ok=True)
    home_dir = runtime_root / "home"
    home_dir.mkdir(parents=True, exist_ok=True)
    (runtime_root / "undetected_chromedriver").mkdir(parents=True, exist_ok=True)
    for env_name, child in (
        ("XDG_CACHE_HOME", "cache"),
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_DATA_HOME", "data"),
    ):
        path = runtime_root / child
        path.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault(env_name, str(path))

    current_home = Path(os.environ.get("HOME", str(home_dir)))
    if not os.access(current_home, os.W_OK):
        os.environ["HOME"] = str(home_dir)
    return runtime_root


EBAY_CHROME_RUNTIME_ROOT = _configure_writable_runtime_dirs()

# pyrefly: ignore [missing-import]
import undetected_chromedriver as uc

MAX_DRIVER_RESTARTS = 2


def _get_chrome_version():
    """Detect the major version of the installed Chrome binary."""
    import subprocess as _sp
    for binary in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        try:
            out = _sp.check_output([binary, "--version"], stderr=_sp.DEVNULL, text=True)
            major = int(out.strip().split()[-1].split(".")[0])
            print(f"Detected Chrome version: {major} (binary: {binary})")
            return major
        except Exception:
            continue
    print("Could not detect Chrome version; letting undetected-chromedriver auto-detect")
    return None


def _build_chrome_options():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")

    if os.environ.get("AIRFLOW_HOME") or os.path.exists("/.dockerenv"):
        profile_dir = EBAY_CHROME_RUNTIME_ROOT / f"profile-{os.getpid()}"
        profile_dir.mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument("--disable-extensions")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        if os.environ.get("EBAY_HEADLESS", "false").lower() == "true":
            options.add_argument("--headless=new")

    return options


def _install_stealth_script(driver):
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """
    })


def _quit_driver(driver):
    if not driver:
        return
    try:
        driver.quit()
    except Exception as exc:
        print(f"Warning: could not quit eBay Chrome cleanly: {exc}")


def _launch_driver():
    print("Launching Stealth Chrome Browser for eBay...")
    chrome_version = _get_chrome_version()
    last_error = None

    for attempt in range(1, 4):
        try:
            print(f"Chrome launch attempt {attempt}/3")
            driver = uc.Chrome(
                options=_build_chrome_options(),
                version_main=chrome_version,
                driver_executable_path=str(EBAY_CHROME_RUNTIME_ROOT / "undetected_chromedriver" / "chromedriver"),
                use_subprocess=True,
                headless=False,
            )
            _install_stealth_script(driver)
            print("Warming up eBay session...")
            driver.get("https://www.ebay.com")
            time.sleep(random.uniform(3, 6))
            return driver
        except Exception as exc:
            last_error = exc
            print(f"Chrome launch attempt {attempt}/3 failed: {exc}")
            _quit_driver(locals().get("driver"))
            time.sleep(3)

    raise RuntimeError(f"Could not start a stable eBay Chrome session: {last_error}")


def run_all_ebay_scrapes():
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
        ("supplements",         os.path.join(base_dir, "gym/ebay_supplements_data.json")),
        ("whey protein",        os.path.join(base_dir, "gym/ebay_whey_protein_data.json")),

        # Combat Sports
        ("boxing gloves",       os.path.join(base_dir, "combat-sports/ebay_combat_gloves_data.json")),
        ("groin guards",        os.path.join(base_dir, "combat-sports/ebay_groin_guards_data.json")),
        ("mma headgear",        os.path.join(base_dir, "combat-sports/ebay_headgear_data.json")),
        ("mouthguards",         os.path.join(base_dir, "combat-sports/ebay_mouthguards_data.json")),
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
    driver = _launch_driver()

    try:
        for query, output_file in scrapes:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            if os.path.exists(output_file):
                os.remove(output_file)

            count = 0
            for restart_count in range(MAX_DRIVER_RESTARTS + 1):
                try:
                    count = scrape_ebay_category(query, output_file, driver)
                    break
                except EbayDriverLostError as exc:
                    if restart_count >= MAX_DRIVER_RESTARTS:
                        print(f"eBay Chrome died while scraping '{query}' and restart limit was reached: {exc}")
                        break

                    print(f"eBay Chrome died while scraping '{query}': {exc}")
                    print("Restarting eBay Chrome and retrying this category...")
                    _quit_driver(driver)
                    driver = _launch_driver()

            if count > 0:
                total_success += 1
                total_products += count
            else:
                print(f"Failed to scrape any products for: {query}")

            time.sleep(random.uniform(4, 7))
    finally:
        _quit_driver(driver)

    print(f"\nScraping Summary (eBay):")
    print(f"Categories Attempted: {len(scrapes)}")
    print(f"Categories Successful: {total_success}")
    print(f"Total Products Scraped: {total_products}")

    if total_products == 0:
        print("CRITICAL: No products were scraped for eBay. Failing script.")
        sys.exit(1)


if __name__ == "__main__":
    run_all_ebay_scrapes()
