import os
import json
import platform
import shutil
import argparse
import time
import tempfile

# Cache file for Tor path (in temp dir for security)
CACHE_FILE = os.path.join(tempfile.gettempdir(), 'tor_prefs_cache.txt')

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            path = f.read().strip()
            if os.path.exists(path):
                return path
    return None

def save_cache(path):
    with open(CACHE_FILE, 'w') as f:
        f.write(path)

def edit_json_prefs(prefs_path, browser_name, custom_keys=None):
    """Generic function for JSON-based browsers (Chrome, Brave)"""
    if not os.path.exists(prefs_path):
        print(f"{browser_name} Preferences file not found.")
        return
    backup_path = prefs_path + '.bak'
    shutil.copy(prefs_path, backup_path)
    print(f"Backed up Preferences to {backup_path} for {browser_name}")
    try:
        with open(prefs_path, 'r', encoding='utf-8') as f:
            prefs = json.load(f)
        # Common settings
        if 'session' not in prefs:
            prefs['session'] = {}
        prefs['session']['restore_on_startup'] = 4
        profile_key = custom_keys.get('profile_key', 'profile') if custom_keys else 'profile'
        if profile_key not in prefs:
            prefs[profile_key] = {}
        prefs[profile_key]['exit_type'] = 'Normal'
        prefs[profile_key]['exited_cleanly'] = True
        with open(prefs_path, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, indent=2)
        print(f"Disabled session restore for {browser_name}.")
    except json.JSONDecodeError:
        print(f"Error parsing JSON for {browser_name}. File may be locked or corrupted.")

def edit_prefs_js(prefs_path, browser_name):
    """Generic function for prefs.js-based browsers (Firefox, Tor)"""
    if not os.path.exists(prefs_path):
        print(f"{browser_name} prefs.js file not found.")
        return
    backup_path = prefs_path + '.bak'
    shutil.copy(prefs_path, backup_path)
    print(f"Backed up prefs.js to {backup_path} for {browser_name}")
    settings = [
        'user_pref("browser.sessionstore.resume_from_crash", false);',
        'user_pref("browser.sessionstore.resume_session_once", false);',
        'user_pref("browser.sessionstore.max_resumed_crashes", 0);'
    ]
    try:
        with open(prefs_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # Remove existing
        keys = [s.split('("')[1].split('",')[0] for s in settings]
        lines = [line for line in lines if not any(key in line for key in keys)]
        # Append new
        lines.extend([s + '\n' for s in settings])  # Add newline for safety
        with open(prefs_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"Disabled session restore for {browser_name}.")
    except IOError:
        print(f"Error writing to prefs.js for {browser_name}. File may be locked (browser running?).")

def get_chrome_prefs_path():
    system = platform.system()
    if system == 'Windows':
        return os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data', 'Default', 'Preferences')
    elif system == 'Linux':
        return os.path.expanduser('~/.config/google-chrome/Default/Preferences')
    elif system == 'Darwin':
        return os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Preferences')
    raise ValueError("Unsupported OS")

def get_brave_prefs_path():
    system = platform.system()
    if system == 'Windows':
        return os.path.join(os.environ.get('LOCALAPPDATA', ''), 'BraveSoftware', 'Brave-Browser', 'User Data', 'Default', 'Preferences')
    elif system == 'Linux':
        return os.path.expanduser('~/.config/BraveSoftware/Brave-Browser/Default/Preferences')
    elif system == 'Darwin':
        return os.path.expanduser('~/Library/Application Support/BraveSoftware/Brave-Browser/Default/Preferences')
    raise ValueError("Unsupported OS")

def get_firefox_prefs_path():
    system = platform.system()
    if system == 'Windows':
        base = os.path.join(os.environ.get('APPDATA', ''), 'Mozilla', 'Firefox', 'Profiles')
    elif system == 'Linux':
        base = os.path.expanduser('~/.mozilla/firefox')
    elif system == 'Darwin':
        base = os.path.expanduser('~/Library/Application Support/Firefox/Profiles')
    else:
        raise ValueError("Unsupported OS")
    profiles = [d for d in os.listdir(base) if d.endswith('.default') or d.endswith('.default-release')]
    if not profiles:
        raise FileNotFoundError("No Firefox default profile found.")
    return os.path.join(base, profiles[0], 'prefs.js')

def find_tor_prefs_path():
    """Optimized auto-detect: Check cache first, then targeted search with limited recursion"""
    cached = load_cache()
    if cached:
        print("Using cached Tor path.")
        return cached
    
    system = platform.system()
    base_dirs = []
    if system == 'Windows':
        user = os.environ.get('USERPROFILE', '')
        base_dirs = [
            os.path.join(user, 'Desktop', 'Tor Browser'),
            os.path.join(user, 'Downloads', 'Tor Browser'),
            os.path.join(user, 'Desktop'),
            os.path.join(user, 'Downloads'),
            user
        ]
    elif system == 'Linux':
        user = os.path.expanduser('~')
        base_dirs = [
            os.path.join(user, 'tor-browser'),
            os.path.join(user, 'Downloads', 'tor-browser'),
            user,
            '/opt'
        ]
    elif system == 'Darwin':
        base_dirs = [
            '/Applications/Tor Browser.app',
            os.path.expanduser('~/Applications/Tor Browser.app'),
            os.path.expanduser('~/Downloads')
        ]
    else:
        return None

    def recursive_search(dir_path, depth=0):
        if depth > 4:  # Stricter limit
            return None
        try:
            for item in os.listdir(dir_path):
                full_path = os.path.join(dir_path, item)
                if os.path.isdir(full_path):
                    if 'TorBrowser' in item or 'Tor Browser' in item:
                        candidate = os.path.join(full_path, 'Browser', 'TorBrowser', 'Data', 'Browser', 'profile.default', 'prefs.js')
                        if os.path.exists(candidate):
                            return candidate
                    # Recurse only if likely
                    if item in ['Browser', 'TorBrowser', 'Data', 'profile.default']:
                        result = recursive_search(full_path, depth + 1)
                        if result:
                            return result
        except PermissionError:
            pass
        return None

    for base in base_dirs:
        if os.path.exists(base):
            result = recursive_search(base)
            if result:
                save_cache(result)
                return result
    
    # Mac special
    if system == 'Darwin':
        for app in base_dirs:
            if app.endswith('.app') and os.path.exists(app):
                prefs = os.path.join(app, 'Contents', 'Resources', 'Browser', 'TorBrowser', 'Data', 'Browser', 'profile.default', 'prefs.js')
                if os.path.exists(prefs):
                    save_cache(prefs)
                    return prefs
    return None

def get_tor_prefs_path(tor_dir):
    if tor_dir:
        return os.path.join(tor_dir, 'Browser', 'TorBrowser', 'Data', 'Browser', 'profile.default', 'prefs.js')
    else:
        return find_tor_prefs_path()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Disable browser session restore - Optimized version")
    parser.add_argument('--browser', type=str, default='all', choices=['all', 'chrome', 'brave', 'firefox', 'tor'], help="Browser to disable (default: all)")
    parser.add_argument('--tor-dir', type=str, default=None, help="Path to Tor Browser directory (optional, auto-detect if not provided)")
    parser.add_argument('--no-cache', action='store_true', help="Disable cache for Tor path")
    args = parser.parse_args()

    if args.no_cache:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)

    start_time = time.time()
    print("Running optimized browser session restore disabler...")

    if args.browser in ['all', 'chrome']:
        try:
            chrome_path = get_chrome_prefs_path()
            edit_json_prefs(chrome_path, "Chrome")
        except Exception as e:
            print(f"Error with Chrome: {e}")

    if args.browser in ['all', 'brave']:
        try:
            brave_path = get_brave_prefs_path()
            edit_json_prefs(brave_path, "Brave", custom_keys={'profile_key': 'browser'})
        except Exception as e:
            print(f"Error with Brave: {e}")

    if args.browser in ['all', 'firefox']:
        try:
            firefox_path = get_firefox_prefs_path()
            edit_prefs_js(firefox_path, "Firefox")
        except Exception as e:
            print(f"Error with Firefox: {e}")

    if args.browser in ['all', 'tor']:
        try:
            tor_path = get_tor_prefs_path(args.tor_dir)
            edit_prefs_js(tor_path, "Tor")
        except Exception as e:
            print(f"Error with Tor: {e}")

    end_time = time.time()
    print(f"Done! Execution time: {end_time - start_time:.2f} seconds. Close and reopen browsers to see changes. Restore from .bak if issues. If Tor auto-detect fails, use --tor-dir.")