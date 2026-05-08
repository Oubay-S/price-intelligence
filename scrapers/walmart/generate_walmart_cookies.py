# pyrefly: ignore [missing-import]
import undetected_chromedriver as uc
import time
import json
import os
import random
import sys

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

def _fix_permissions(path):
    """Recursively set 777 permissions on a directory."""
    if not os.path.exists(path):
        return
    try:
        print(f"🔓 Setting permissions to 777 for: {path}")
        # Use subprocess.run for better security and reliability
        import subprocess
        subprocess.run(["chmod", "-R", "777", path], check=False, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"⚠️ Warning: Could not fix permissions: {e}")

def generate_cookies():
    print("🧹 Cleaning up old Chrome processes...")
    import subprocess
    subprocess.run(["pkill", "-9", "chrome"], check=False, stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "chromedriver"], check=False, stderr=subprocess.DEVNULL)
    
    print("🚀 Launching VISIBLE browser with Persistent Profile...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    profile_dir = os.path.join(script_dir, "walmart_profile")
    
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir, exist_ok=True)
    
    # Clean up all lock files/symlinks (SingletonLock, SingletonCookie, SingletonSocket)
    for lock_name in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
        lock_file = os.path.join(profile_dir, lock_name)
        if os.path.exists(lock_file) or os.path.islink(lock_file):
            try:
                print(f"🔓 Removing lock/link: {lock_file}")
                os.remove(lock_file)
            except Exception as e:
                print(f"⚠️ Could not remove {lock_name}: {e}")
    
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--profile-directory=Default")
    
    # Stealth arguments
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--window-size=1920,1080")
    
    # Let UC handle the User-Agent naturally to avoid version mismatches
    # removing: options.add_argument(f"user-agent={ua}")
    
    try:
        chrome_version = _get_chrome_version()
        driver = uc.Chrome(version_main=chrome_version, options=options, use_subprocess=True)
    except Exception as e:
        print(f"❌ Failed to launch browser: {e}")
        print("Retrying with fresh options...")
        options2 = uc.ChromeOptions()
        options2.add_argument(f"--user-data-dir={profile_dir}")
        options2.add_argument("--profile-directory=Default")
        options2.add_argument("--no-sandbox")
        options2.add_argument("--window-size=1920,1080")
        driver = uc.Chrome(options=options2, use_subprocess=True)
    
    # Advanced CDP Overrides to bypass PerimeterX
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
    
    print("Navigating to Walmart...")
    driver.get("https://www.walmart.com")
    
    print("\n" + "="*60)
    print("⚠️  ACTION REQUIRED ⚠️")
    print("1. If you see a CAPTCHA (Press & Hold), SOLVE IT NOW.")
    print("2. Search for a product and browse for a few seconds.")
    print("3. This profile data will be used by Airflow.")
    print("4. Ensure you are NOT in a 'Please try again' loop before pressing ENTER.")
    print("="*60 + "\n")
    
    input("👉 Press ENTER here once you are on a normal Walmart page (e.g. search results): ")
    
    print("Saving session data to profile...")
    # We also save a backup JSON just in case
    cookies = driver.get_cookies()
    cookie_path = os.path.join(script_dir, "walmart_cookies.json")
    with open(cookie_path, "w") as f:
        json.dump(cookies, f, indent=4)
        
    print(f"✅ Profile updated and backup saved to {cookie_path}!")
    
    # Ensure Airflow can read the new profile data
    _fix_permissions(profile_dir)
    
    print("Closing browser...")
    driver.quit()


if __name__ == "__main__":
    generate_cookies()
