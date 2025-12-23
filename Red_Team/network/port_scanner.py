#!/usr/bin/env python3
"""
Red Team Tools - Multi-threaded Port Scanner
For educational and authorized security testing only
"""

import socket
import threading
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import sys
import os

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import *


class PortScanner:
    """Advanced multi-threaded port scanner with service detection"""
    
    # Common service ports
    COMMON_PORTS = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
        80: "HTTP", 110: "POP3", 111: "RPCBind", 135: "MSRPC", 139: "NetBIOS",
        143: "IMAP", 443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S",
        1433: "MSSQL", 1521: "Oracle", 3306: "MySQL", 3389: "RDP",
        5432: "PostgreSQL", 5900: "VNC", 6379: "Redis", 8080: "HTTP-Proxy",
        8443: "HTTPS-Alt", 27017: "MongoDB"
    }
    
    def __init__(self, target: str, ports: str = "1-1024", threads: int = 100, timeout: float = 1.0):
        self.target = target
        self.ports = self._parse_ports(ports)
        self.threads = threads
        self.timeout = timeout
        self.open_ports = []
        self.scan_results = {}
        self.lock = threading.Lock()
        self.scanned = 0
        self.total_ports = len(self.ports)
    
    def _parse_ports(self, ports_str: str) -> list:
        """Parse port string to list of ports"""
        ports = []
        for part in ports_str.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-')
                ports.extend(range(int(start), int(end) + 1))
            else:
                ports.append(int(part))
        return sorted(set(ports))
    
    def _resolve_target(self) -> str:
        """Resolve hostname to IP"""
        try:
            return socket.gethostbyname(self.target)
        except socket.gaierror:
            error(f"Cannot resolve hostname: {self.target}")
            return None
    
    def _grab_banner(self, sock: socket.socket) -> str:
        """Attempt to grab service banner"""
        try:
            sock.send(b"HEAD / HTTP/1.0\r\n\r\n")
            banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
            return banner[:100] if banner else ""
        except:
            return ""
    
    def _scan_port(self, port: int) -> dict:
        """Scan a single port"""
        result = {"port": port, "state": "closed", "service": "", "banner": ""}
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            
            connection = sock.connect_ex((self.target, port))
            
            if connection == 0:
                result["state"] = "open"
                result["service"] = self.COMMON_PORTS.get(port, "unknown")
                
                # Try banner grab
                try:
                    result["banner"] = self._grab_banner(sock)
                except:
                    pass
            
            sock.close()
        except socket.timeout:
            result["state"] = "filtered"
        except Exception as e:
            result["state"] = "error"
        
        with self.lock:
            self.scanned += 1
            if result["state"] == "open":
                self.open_ports.append(port)
        
        return result
    
    def scan(self, show_progress: bool = True) -> dict:
        """Execute port scan"""
        ip = self._resolve_target()
        if not ip:
            return {}
        
        info(f"Scanning target: {self.target} ({ip})")
        info(f"Ports: {len(self.ports)} | Threads: {self.threads} | Timeout: {self.timeout}s")
        print()
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {executor.submit(self._scan_port, port): port for port in self.ports}
            
            for future in as_completed(futures):
                result = future.result()
                self.scan_results[result["port"]] = result
                
                if show_progress:
                    progress_bar(self.scanned, self.total_ports, prefix="Scanning", suffix=f"Port {result['port']}")
        
        elapsed = time.time() - start_time
        
        return {
            "target": self.target,
            "ip": ip,
            "open_ports": sorted(self.open_ports),
            "total_scanned": self.total_ports,
            "elapsed_time": elapsed,
            "results": self.scan_results
        }
    
    def print_results(self, results: dict):
        """Print scan results in formatted table"""
        print(f"\n{C}{'═' * 60}{RESET}")
        print(f"{BRIGHT}SCAN RESULTS{RESET}")
        print(f"{C}{'═' * 60}{RESET}")
        
        print(f"\n{Y}Target:{RESET} {results['target']} ({results['ip']})")
        print(f"{Y}Ports Scanned:{RESET} {results['total_scanned']}")
        print(f"{Y}Open Ports:{RESET} {len(results['open_ports'])}")
        print(f"{Y}Scan Time:{RESET} {results['elapsed_time']:.2f} seconds")
        
        if results['open_ports']:
            print(f"\n{G}OPEN PORTS:{RESET}")
            rows = []
            for port in results['open_ports']:
                r = results['results'][port]
                rows.append([
                    str(port),
                    r['service'],
                    r['banner'][:40] if r['banner'] else "-"
                ])
            print_table(["PORT", "SERVICE", "BANNER"], rows, color="green")
        else:
            warning("No open ports found")
        
        print(f"\n{C}{'═' * 60}{RESET}")


def scan_top_ports(target: str, num_ports: int = 100) -> dict:
    """Quick scan of top N common ports"""
    top_ports = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 
                 993, 995, 1433, 1521, 3306, 3389, 5432, 5900, 6379, 8080, 8443]
    scanner = PortScanner(target, ','.join(map(str, top_ports[:num_ports])))
    return scanner.scan()


def quick_scan(target: str) -> list:
    """Ultra-quick scan of most common ports"""
    common = [22, 80, 443, 21, 25, 3306, 3389, 8080]
    open_ports = []
    
    for port in common:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            if sock.connect_ex((target, port)) == 0:
                open_ports.append(port)
            sock.close()
        except:
            pass
    
    return open_ports


def main():
    parser = argparse.ArgumentParser(description="Red Team Port Scanner")
    parser.add_argument("target", help="Target IP or hostname")
    parser.add_argument("-p", "--ports", default="1-1024", help="Ports to scan (e.g., 1-1024,8080)")
    parser.add_argument("-t", "--threads", type=int, default=100, help="Number of threads")
    parser.add_argument("--timeout", type=float, default=1.0, help="Connection timeout")
    parser.add_argument("-q", "--quick", action="store_true", help="Quick scan (common ports only)")
    
    args = parser.parse_args()
    
    print_banner("PORT SCANNER", color="red")
    warning("For authorized security testing only!")
    print()
    
    if args.quick:
        info("Running quick scan...")
        open_ports = quick_scan(args.target)
        if open_ports:
            success(f"Open ports: {', '.join(map(str, open_ports))}")
        else:
            warning("No common ports found open")
    else:
        scanner = PortScanner(
            args.target,
            ports=args.ports,
            threads=args.threads,
            timeout=args.timeout
        )
        results = scanner.scan()
        scanner.print_results(results)


def interactive_mode():
    """Interactive mode for port scanning"""
    print_banner("PORT SCANNER", color="red")
    warning("For authorized security testing only!")
    
    target = prompt("Enter target IP/hostname")
    
    options = ["Quick Scan (Common Ports)", "Top 100 Ports", "Full Scan (1-1024)", "Custom Ports"]
    choice = menu_selector(options, "Scan Type")
    
    if choice == 0:
        return
    elif choice == 1:
        open_ports = quick_scan(target)
        if open_ports:
            success(f"Open ports: {', '.join(map(str, open_ports))}")
        else:
            warning("No common ports found open")
    elif choice == 2:
        results = scan_top_ports(target, 100)
        PortScanner(target).print_results(results)
    elif choice == 3:
        scanner = PortScanner(target, "1-1024")
        results = scanner.scan()
        scanner.print_results(results)
    elif choice == 4:
        ports = prompt("Enter ports (e.g., 22,80,443 or 1-1000)")
        scanner = PortScanner(target, ports)
        results = scanner.scan()
        scanner.print_results(results)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        interactive_mode()
