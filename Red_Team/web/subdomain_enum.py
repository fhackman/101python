#!/usr/bin/env python3
"""
Red Team Tools - Subdomain Enumerator
For educational and authorized security testing only
"""

import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import *

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    REQUESTS_AVAILABLE = True
except Exception as e:
    REQUESTS_AVAILABLE = False
    REQUESTS_ERROR = str(e)

try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False


class SubdomainEnumerator:
    """Subdomain enumeration and discovery tool"""
    
    # Common subdomains
    DEFAULT_SUBDOMAINS = [
        "www", "mail", "ftp", "localhost", "webmail", "smtp", "pop", "ns1", "ns2",
        "dns", "dns1", "dns2", "mx", "mx1", "mx2", "blog", "dev", "stage", "staging",
        "test", "testing", "admin", "administrator", "api", "app", "apps", "beta",
        "cdn", "cloud", "cms", "cpanel", "dashboard", "db", "demo", "docs", "email",
        "git", "gitlab", "imap", "jenkins", "jira", "legacy", "login", "m", "mobile",
        "monitor", "mysql", "new", "news", "old", "panel", "portal", "prod", "proxy",
        "secure", "server", "shop", "sql", "ssh", "ssl", "static", "store", "support",
        "svn", "sync", "syslog", "vpn", "web", "webdisk", "wiki", "ww", "www1", "www2",
        "www3", "xml", "autodiscover", "autoconfig", "backup", "billing", "bbs",
        "calendar", "chat", "client", "crm", "direct", "download", "exchange", "files",
        "forum", "gateway", "gw", "help", "helpdesk", "home", "host", "hosting", "hr",
        "img", "images", "internal", "intranet", "lab", "logs", "mdm", "media", "meeting",
        "members", "my", "ntp", "office", "ops", "order", "origin", "owa", "payment",
        "pda", "photo", "photos", "piwik", "private", "projects", "remote", "reports",
        "s", "s1", "s2", "s3", "sandbox", "search", "security", "service", "services",
        "share", "sharepoint", "sip", "sites", "smtp1", "smtp2", "social", "sp",
        "status", "streaming", "survey", "terminal", "tickets", "tools", "track",
        "tracker", "training", "update", "upload", "v", "v1", "v2", "video", "vod",
        "voip", "webconf", "webhost", "weblog", "webserver", "work", "ws"
    ]
    
    def __init__(self, domain: str, wordlist: list = None, 
                 threads: int = 20, timeout: float = 3.0):
        self.domain = domain.lower().strip()
        self.wordlist = wordlist or self.DEFAULT_SUBDOMAINS
        self.threads = threads
        self.timeout = timeout
        self.found_subdomains = []
        self.lock = threading.Lock()
        
        # Setup DNS resolver
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = timeout
        self.resolver.lifetime = timeout
    
    def _resolve_subdomain(self, subdomain: str) -> dict:
        """Resolve a subdomain"""
        full_domain = f"{subdomain}.{self.domain}"
        result = {
            "subdomain": subdomain,
            "domain": full_domain,
            "ips": [],
            "cnames": [],
            "alive": False
        }
        
        try:
            # Try A record
            answers = self.resolver.resolve(full_domain, 'A')
            for rdata in answers:
                result["ips"].append(str(rdata))
            result["alive"] = True
        except dns.resolver.NXDOMAIN:
            return result
        except dns.resolver.NoAnswer:
            pass
        except dns.resolver.NoNameservers:
            pass
        except Exception:
            pass
        
        # Try CNAME record
        try:
            answers = self.resolver.resolve(full_domain, 'CNAME')
            for rdata in answers:
                result["cnames"].append(str(rdata.target))
            result["alive"] = True
        except:
            pass
        
        return result
    
    def _check_http(self, domain: str) -> dict:
        """Check HTTP/HTTPS response"""
        result = {"http": False, "https": False, "http_status": 0, "https_status": 0}
        
        # Try HTTP
        try:
            response = requests.get(f"http://{domain}", timeout=self.timeout, verify=False, allow_redirects=True)
            result["http"] = True
            result["http_status"] = response.status_code
        except:
            pass
        
        # Try HTTPS
        try:
            response = requests.get(f"https://{domain}", timeout=self.timeout, verify=False, allow_redirects=True)
            result["https"] = True
            result["https_status"] = response.status_code
        except:
            pass
        
        return result
    
    def bruteforce(self, check_http: bool = False) -> list:
        """Bruteforce subdomains"""
        info(f"Enumerating subdomains for: {self.domain}")
        info(f"Wordlist: {len(self.wordlist)} entries")
        info(f"Threads: {self.threads}")
        print()
        
        total = len(self.wordlist)
        checked = 0
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {executor.submit(self._resolve_subdomain, sub): sub for sub in self.wordlist}
            
            for future in as_completed(futures):
                result = future.result()
                checked += 1
                
                if result["alive"]:
                    # Check HTTP if requested
                    if check_http:
                        http_result = self._check_http(result["domain"])
                        result.update(http_result)
                    
                    with self.lock:
                        self.found_subdomains.append(result)
                    
                    # Print immediately
                    ips = ", ".join(result["ips"][:3])
                    print(f"\r{' '*80}\r", end="")
                    print(f"{G}[+]{RESET} {result['domain']} → {ips}")
                
                if checked % 10 == 0:
                    progress_bar(checked, total, prefix="Scanning")
        
        elapsed = time.time() - start_time
        
        print()
        success(f"Enumeration complete in {elapsed:.2f}s")
        success(f"Found {len(self.found_subdomains)} subdomains")
        
        return self.found_subdomains
    
    def crt_sh_lookup(self) -> list:
        """Query crt.sh for subdomains from certificate transparency logs"""
        info("Querying crt.sh for certificate transparency data...")
        
        try:
            response = requests.get(
                f"https://crt.sh/?q=%.{self.domain}&output=json",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                subdomains = set()
                for entry in data:
                    name = entry.get('name_value', '')
                    for sub in name.split('\n'):
                        if sub.endswith(self.domain):
                            # Extract subdomain part
                            subdomain = sub.replace(f".{self.domain}", '').strip('*.')
                            if subdomain and subdomain != self.domain:
                                subdomains.add(subdomain)
                
                info(f"Found {len(subdomains)} subdomains from crt.sh")
                return list(subdomains)
        except Exception as e:
            warning(f"crt.sh lookup failed: {e}")
        
        return []
    
    def print_results(self):
        """Print enumeration results"""
        print(f"\n{C}{'═' * 70}{RESET}")
        print(f"{BRIGHT}SUBDOMAIN ENUMERATION RESULTS{RESET}")
        print(f"{C}{'═' * 70}{RESET}")
        print(f"{Y}Domain:{RESET} {self.domain}")
        print(f"{Y}Subdomains Found:{RESET} {len(self.found_subdomains)}")
        print()
        
        if not self.found_subdomains:
            warning("No subdomains found")
            return
        
        rows = []
        for sub in sorted(self.found_subdomains, key=lambda x: x['subdomain']):
            ips = ", ".join(sub["ips"][:2])
            cnames = ", ".join(sub["cnames"][:1]) if sub["cnames"] else "-"
            
            http_status = ""
            if sub.get("http"):
                http_status += f"HTTP:{sub['http_status']}"
            if sub.get("https"):
                http_status += f" HTTPS:{sub['https_status']}"
            
            rows.append([
                sub["domain"],
                ips or "-",
                cnames[:20],
                http_status or "-"
            ])
        
        print_table(["SUBDOMAIN", "IPs", "CNAME", "HTTP"], rows, color="green")
    
    def save_results(self, filename: str):
        """Save results to file"""
        with open(filename, 'w') as f:
            for sub in self.found_subdomains:
                f.write(f"{sub['domain']}\n")
        success(f"Results saved to {filename}")


def load_wordlist(filepath: str) -> list:
    """Load wordlist from file"""
    if not os.path.exists(filepath):
        error(f"Wordlist not found: {filepath}")
        return []
    
    words = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            word = line.strip().lower()
            if word and not word.startswith('#'):
                words.append(word)
    return words


def interactive_mode():
    """Interactive mode for subdomain enumeration"""
    print_banner("SUBDOMAIN ENUM", color="red")
    warning("For authorized security testing only!")
    
    domain = prompt("Enter domain (e.g., example.com)")
    
    # Remove protocol if present
    if domain.startswith(('http://', 'https://')):
        from urllib.parse import urlparse
        domain = urlparse(domain).netloc
    
    options = [
        "Quick Scan (Common Subdomains)",
        "Certificate Transparency + Quick Scan",
        "Custom Wordlist",
        "Comprehensive Scan"
    ]
    
    choice = menu_selector(options, "Select Scan Type")
    
    if choice == 0:
        return
    
    check_http = confirm("Check HTTP/HTTPS status?")
    
    enumerator = SubdomainEnumerator(domain)
    
    if choice == 1:
        enumerator.bruteforce(check_http=check_http)
    
    elif choice == 2:
        # Get subdomains from crt.sh
        crt_subs = enumerator.crt_sh_lookup()
        
        # Combine with default list
        combined = list(set(enumerator.wordlist + crt_subs))
        enumerator.wordlist = combined
        info(f"Combined wordlist: {len(combined)} entries")
        
        enumerator.bruteforce(check_http=check_http)
    
    elif choice == 3:
        wordlist_path = prompt("Enter wordlist path")
        wordlist = load_wordlist(wordlist_path)
        
        if not wordlist:
            error("Empty or invalid wordlist")
            return
        
        enumerator.wordlist = wordlist
        enumerator.bruteforce(check_http=check_http)
    
    elif choice == 4:
        # Comprehensive: crt.sh + large wordlist
        crt_subs = enumerator.crt_sh_lookup()
        
        # Add more subdomains
        extended = [
            f"dev{i}" for i in range(1, 11)
        ] + [
            f"test{i}" for i in range(1, 11)
        ] + [
            f"api{i}" for i in range(1, 6)
        ] + [
            f"server{i}" for i in range(1, 11)
        ]
        
        combined = list(set(enumerator.wordlist + crt_subs + extended))
        enumerator.wordlist = combined
        enumerator.threads = 50
        
        enumerator.bruteforce(check_http=check_http)
    
    enumerator.print_results()
    
    if confirm("Save results to file?"):
        filename = prompt("Filename") or f"{domain}_subdomains.txt"
        enumerator.save_results(filename)


if __name__ == "__main__":
    interactive_mode()
