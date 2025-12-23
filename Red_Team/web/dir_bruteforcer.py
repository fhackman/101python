#!/usr/bin/env python3
"""
Red Team Tools - Directory Bruteforcer
For educational and authorized security testing only
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import *

# Handle brotli/urllib3 compatibility issues
try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    REQUESTS_AVAILABLE = True
except Exception as e:
    REQUESTS_AVAILABLE = False
    REQUESTS_ERROR = str(e)


class DirectoryBruteforcer:
    """Directory and file enumeration tool"""
    
    # Default wordlist
    DEFAULT_DIRS = [
        "admin", "administrator", "login", "wp-admin", "wp-login", "cpanel",
        "dashboard", "config", "api", "backup", "backups", "db", "database",
        "dev", "development", "test", "testing", "staging", "prod", "production",
        "upload", "uploads", "files", "data", "logs", "log", "debug",
        "private", "secret", "hidden", "old", "new", "temp", "tmp",
        "assets", "static", "js", "css", "images", "img", "media",
        "includes", "include", "lib", "libs", "vendor", "vendors",
        "cgi-bin", "scripts", "bin", "etc", "src", "source",
        "server", "status", "info", "phpinfo", "phpmyadmin",
        "manager", "console", "portal", "panel", "control",
        "robots.txt", "sitemap.xml", ".htaccess", ".git", ".env",
        "web.config", "config.php", "config.yml", "settings.py",
        ".svn", ".hg", ".gitignore", "readme", "README.md",
        "install", "setup", "update", "upgrade", "maintenance"
    ]
    
    # Common file extensions
    EXTENSIONS = [
        "", ".php", ".html", ".htm", ".asp", ".aspx", ".jsp",
        ".txt", ".xml", ".json", ".bak", ".old", ".orig",
        ".sql", ".db", ".log", ".conf", ".config", ".ini"
    ]
    
    def __init__(self, target_url: str, wordlist: list = None, 
                 extensions: list = None, threads: int = 10,
                 timeout: float = 5.0, follow_redirects: bool = False):
        self.target_url = target_url.rstrip('/')
        self.wordlist = wordlist or self.DEFAULT_DIRS
        self.extensions = extensions or [""]
        self.threads = threads
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.results = []
        self.lock = threading.Lock()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _check_path(self, path: str) -> dict:
        """Check if a path exists"""
        url = urljoin(self.target_url + '/', path)
        result = {"url": url, "status": 0, "size": 0, "redirect": ""}
        
        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=self.follow_redirects,
                verify=False
            )
            
            result["status"] = response.status_code
            result["size"] = len(response.content)
            
            if response.is_redirect or response.status_code in [301, 302, 303, 307, 308]:
                result["redirect"] = response.headers.get('Location', '')
            
        except requests.exceptions.Timeout:
            result["status"] = -1
        except requests.exceptions.ConnectionError:
            result["status"] = -2
        except Exception as e:
            result["status"] = -3
        
        return result
    
    def scan(self, show_progress: bool = True, 
            status_filter: list = None) -> list:
        """Scan for directories and files"""
        if status_filter is None:
            status_filter = [200, 201, 204, 301, 302, 307, 308, 401, 403]
        
        # Generate all paths to check
        paths = []
        for word in self.wordlist:
            for ext in self.extensions:
                paths.append(f"{word}{ext}")
        
        total = len(paths)
        checked = 0
        
        info(f"Target: {self.target_url}")
        info(f"Wordlist: {len(self.wordlist)} words")
        info(f"Extensions: {self.extensions}")
        info(f"Total requests: {total}")
        print()
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {executor.submit(self._check_path, path): path for path in paths}
            
            for future in as_completed(futures):
                result = future.result()
                checked += 1
                
                if result["status"] in status_filter:
                    with self.lock:
                        self.results.append(result)
                    
                    # Print found immediately
                    status = result["status"]
                    if status == 200:
                        color = G
                    elif status in [301, 302, 307, 308]:
                        color = B
                    elif status in [401, 403]:
                        color = Y
                    else:
                        color = W
                    
                    print(f"\r{' '*80}\r", end="")  # Clear line
                    print(f"{color}[{status}]{RESET} {result['url']} ({result['size']} bytes)")
                
                if show_progress and checked % 10 == 0:
                    progress_bar(checked, total, prefix="Scanning")
        
        elapsed = time.time() - start_time
        
        print()
        success(f"Scan complete in {elapsed:.2f}s")
        success(f"Found {len(self.results)} resources")
        
        return self.results
    
    def print_results(self):
        """Print scan results"""
        print(f"\n{C}{'═' * 70}{RESET}")
        print(f"{BRIGHT}DIRECTORY SCAN RESULTS{RESET}")
        print(f"{C}{'═' * 70}{RESET}")
        
        if not self.results:
            warning("No resources found")
            return
        
        # Group by status
        by_status = {}
        for r in self.results:
            status = r["status"]
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(r)
        
        for status in sorted(by_status.keys()):
            resources = by_status[status]
            
            if status == 200:
                print(f"\n{G}[200 OK] - {len(resources)} found:{RESET}")
            elif status in [301, 302, 307, 308]:
                print(f"\n{B}[{status} Redirect] - {len(resources)} found:{RESET}")
            elif status == 401:
                print(f"\n{Y}[401 Unauthorized] - {len(resources)} found:{RESET}")
            elif status == 403:
                print(f"\n{Y}[403 Forbidden] - {len(resources)} found:{RESET}")
            else:
                print(f"\n{W}[{status}] - {len(resources)} found:{RESET}")
            
            for r in resources[:20]:
                path = urlparse(r["url"]).path
                redirect = f" → {r['redirect']}" if r["redirect"] else ""
                print(f"  {path} ({r['size']}){redirect}")
            
            if len(resources) > 20:
                print(f"  ... and {len(resources) - 20} more")
    
    def save_results(self, filename: str):
        """Save results to file"""
        with open(filename, 'w') as f:
            for r in self.results:
                f.write(f"{r['status']},{r['url']},{r['size']}\n")
        success(f"Results saved to {filename}")


def load_wordlist(filepath: str) -> list:
    """Load wordlist from file"""
    if not os.path.exists(filepath):
        error(f"Wordlist not found: {filepath}")
        return []
    
    words = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            word = line.strip()
            if word and not word.startswith('#'):
                words.append(word)
    return words


def interactive_mode():
    """Interactive mode for directory bruteforcing"""
    print_banner("DIR BUSTER", color="red")
    warning("For authorized security testing only!")
    
    if not REQUESTS_AVAILABLE:
        error(f"Requests library failed to load: {REQUESTS_ERROR}")
        error("Fix: pip uninstall brotli brotlicffi && pip install brotli")
        return
    
    target = prompt("Enter target URL (e.g., http://example.com)")
    
    if not target.startswith(('http://', 'https://')):
        target = 'http://' + target
    
    options = [
        "Quick Scan (Default Wordlist)",
        "Quick Scan with Extensions",
        "Custom Wordlist",
        "Comprehensive Scan"
    ]
    
    choice = menu_selector(options, "Select Scan Type")
    
    if choice == 0:
        return
    
    if choice == 1:
        bruteforcer = DirectoryBruteforcer(target)
        bruteforcer.scan()
        bruteforcer.print_results()
    
    elif choice == 2:
        ext_input = prompt("Extensions (comma-separated, e.g., .php,.html)")
        extensions = [""] + [e.strip() for e in ext_input.split(',')]
        
        bruteforcer = DirectoryBruteforcer(target, extensions=extensions)
        bruteforcer.scan()
        bruteforcer.print_results()
    
    elif choice == 3:
        wordlist_path = prompt("Enter wordlist path")
        wordlist = load_wordlist(wordlist_path)
        
        if not wordlist:
            error("Empty or invalid wordlist")
            return
        
        info(f"Loaded {len(wordlist)} words")
        
        bruteforcer = DirectoryBruteforcer(target, wordlist=wordlist)
        bruteforcer.scan()
        bruteforcer.print_results()
    
    elif choice == 4:
        extensions = ["", ".php", ".html", ".asp", ".aspx", ".txt", ".bak", ".old"]
        
        bruteforcer = DirectoryBruteforcer(target, extensions=extensions, threads=20)
        bruteforcer.scan()
        bruteforcer.print_results()
    
    if confirm("Save results to file?"):
        filename = prompt("Filename") or "dirscan_results.txt"
        bruteforcer.save_results(filename)


if __name__ == "__main__":
    interactive_mode()
