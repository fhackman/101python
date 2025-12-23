#!/usr/bin/env python3
"""
Red Team Tools - Service Enumerator
For educational and authorized security testing only
"""

import socket
import ssl
import re
import time
from concurrent.futures import ThreadPoolExecutor
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import *


class ServiceEnumerator:
    """Service fingerprinting and version detection"""
    
    # Service probes for fingerprinting
    PROBES = {
        "http": b"GET / HTTP/1.1\r\nHost: {host}\r\n\r\n",
        "https": b"",  # SSL handshake
        "ftp": b"",
        "ssh": b"",
        "smtp": b"EHLO test\r\n",
        "pop3": b"",
        "imap": b"",
        "mysql": b"",
        "redis": b"INFO\r\n",
        "mongodb": b"",
    }
    
    # Common response patterns
    PATTERNS = {
        "apache": r"Apache/(\d+\.[\d.]+)",
        "nginx": r"nginx/(\d+\.[\d.]+)",
        "iis": r"Microsoft-IIS/(\d+\.[\d.]+)",
        "openssh": r"OpenSSH[_-](\d+\.[\d.p]+)",
        "dropbear": r"dropbear[_-](\d+\.[\d.]+)",
        "vsftpd": r"vsftpd (\d+\.[\d.]+)",
        "proftpd": r"ProFTPD (\d+\.[\d.]+)",
        "mysql": r"(\d+\.[\d.]+)-MariaDB|mysql_native_password",
        "postgresql": r"PostgreSQL (\d+\.[\d.]+)",
        "redis": r"redis_version:(\d+\.[\d.]+)",
        "mongodb": r"mongodb (\d+\.[\d.]+)",
        "smtp": r"(Postfix|Sendmail|Exim|Microsoft SMTP)",
    }
    
    def __init__(self, target: str, ports: list = None, timeout: float = 3.0):
        self.target = target
        self.ports = ports or [21, 22, 25, 80, 110, 143, 443, 3306, 3389, 5432, 6379]
        self.timeout = timeout
        self.results = {}
    
    def _grab_banner(self, port: int, probe: bytes = b"") -> str:
        """Grab service banner"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.target, port))
            
            # Wait for banner or send probe
            if probe:
                probe = probe.replace(b"{host}", self.target.encode())
                sock.send(probe)
            
            banner = sock.recv(2048).decode('utf-8', errors='ignore')
            sock.close()
            return banner.strip()
        except:
            return ""
    
    def _grab_ssl_info(self, port: int) -> dict:
        """Get SSL certificate information"""
        info = {"ssl": False, "cert": {}}
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((self.target, port), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=self.target) as ssock:
                    cert = ssock.getpeercert(binary_form=True)
                    cert_info = ssock.getpeercert()
                    
                    info["ssl"] = True
                    info["version"] = ssock.version()
                    info["cipher"] = ssock.cipher()
                    
                    if cert_info:
                        info["cert"]["subject"] = dict(x[0] for x in cert_info.get("subject", []))
                        info["cert"]["issuer"] = dict(x[0] for x in cert_info.get("issuer", []))
                        info["cert"]["expires"] = cert_info.get("notAfter", "")
        except:
            pass
        
        return info
    
    def _identify_service(self, banner: str) -> dict:
        """Identify service and version from banner"""
        result = {"service": "unknown", "version": "", "product": ""}
        
        if not banner:
            return result
        
        banner_lower = banner.lower()
        
        # Check patterns
        for product, pattern in self.PATTERNS.items():
            match = re.search(pattern, banner, re.IGNORECASE)
            if match:
                result["product"] = product
                result["version"] = match.group(1) if match.groups() else ""
                
                # Determine service type
                if product in ["apache", "nginx", "iis"]:
                    result["service"] = "http"
                elif product in ["openssh", "dropbear"]:
                    result["service"] = "ssh"
                elif product in ["vsftpd", "proftpd"]:
                    result["service"] = "ftp"
                elif product in ["postfix", "sendmail", "exim"]:
                    result["service"] = "smtp"
                else:
                    result["service"] = product
                
                return result
        
        # Generic detection
        if "ssh" in banner_lower:
            result["service"] = "ssh"
        elif "http" in banner_lower:
            result["service"] = "http"
        elif "ftp" in banner_lower:
            result["service"] = "ftp"
        elif "smtp" in banner_lower or "mail" in banner_lower:
            result["service"] = "smtp"
        elif "pop" in banner_lower:
            result["service"] = "pop3"
        elif "imap" in banner_lower:
            result["service"] = "imap"
        elif "mysql" in banner_lower or "mariadb" in banner_lower:
            result["service"] = "mysql"
        elif "postgresql" in banner_lower:
            result["service"] = "postgresql"
        elif "redis" in banner_lower:
            result["service"] = "redis"
        elif "rdp" in banner_lower or "terminal" in banner_lower:
            result["service"] = "rdp"
        
        return result
    
    def enumerate_port(self, port: int) -> dict:
        """Enumerate service on a single port"""
        result = {
            "port": port,
            "state": "closed",
            "service": "",
            "version": "",
            "product": "",
            "banner": "",
            "ssl": False
        }
        
        # Check if port is open
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            if sock.connect_ex((self.target, port)) != 0:
                sock.close()
                return result
            sock.close()
            result["state"] = "open"
        except:
            return result
        
        # Try SSL first for common SSL ports
        if port in [443, 8443, 993, 995, 465]:
            ssl_info = self._grab_ssl_info(port)
            if ssl_info["ssl"]:
                result["ssl"] = True
                result["ssl_info"] = ssl_info
        
        # Grab banner
        probe = self.PROBES.get(result.get("service", ""), b"")
        banner = self._grab_banner(port, probe)
        result["banner"] = banner[:200] if banner else ""
        
        # Identify service
        service_info = self._identify_service(banner)
        result.update(service_info)
        
        return result
    
    def enumerate_all(self) -> dict:
        """Enumerate all specified ports"""
        info(f"Enumerating services on {self.target}")
        info(f"Ports: {len(self.ports)}")
        print()
        
        results = {}
        total = len(self.ports)
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.enumerate_port, port): port for port in self.ports}
            
            for i, future in enumerate(futures):
                result = future.result()
                results[result["port"]] = result
                progress_bar(i + 1, total, prefix="Enumerating")
        
        self.results = results
        return results
    
    def print_results(self):
        """Print enumeration results"""
        print(f"\n{C}{'═' * 70}{RESET}")
        print(f"{BRIGHT}SERVICE ENUMERATION RESULTS{RESET}")
        print(f"{C}{'═' * 70}{RESET}")
        print(f"{Y}Target:{RESET} {self.target}")
        print()
        
        rows = []
        for port, data in sorted(self.results.items()):
            if data["state"] == "open":
                ssl_mark = "🔒" if data.get("ssl") else ""
                rows.append([
                    str(port),
                    data.get("service", "unknown"),
                    data.get("product", "-"),
                    data.get("version", "-"),
                    ssl_mark,
                    data.get("banner", "")[:30]
                ])
        
        if rows:
            print_table(["PORT", "SERVICE", "PRODUCT", "VERSION", "SSL", "BANNER"], rows, color="green")
        else:
            warning("No open ports found")
        
        print(f"\n{C}{'═' * 70}{RESET}")


def interactive_mode():
    """Interactive mode for service enumeration"""
    print_banner("SERVICE ENUM", color="red")
    warning("For authorized security testing only!")
    
    target = prompt("Enter target IP/hostname")
    
    options = [
        "Quick Enum (Common Ports)",
        "Web Services (80, 443, 8080, 8443)",
        "Database Services (MySQL, PostgreSQL, Redis, MongoDB)",
        "Custom Ports"
    ]
    
    choice = menu_selector(options, "Select Scan Type")
    
    if choice == 0:
        return
    elif choice == 1:
        ports = [21, 22, 25, 80, 110, 143, 443, 445, 3306, 3389, 5432, 6379, 8080]
    elif choice == 2:
        ports = [80, 443, 8080, 8443, 8000, 8888]
    elif choice == 3:
        ports = [3306, 5432, 6379, 27017, 1433, 1521, 5984]
    elif choice == 4:
        ports_str = prompt("Enter ports (comma-separated)")
        ports = [int(p.strip()) for p in ports_str.split(',')]
    
    enum = ServiceEnumerator(target, ports)
    enum.enumerate_all()
    enum.print_results()


if __name__ == "__main__":
    interactive_mode()
