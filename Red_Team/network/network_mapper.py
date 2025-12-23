#!/usr/bin/env python3
"""
Red Team Tools - Network Mapper
For educational and authorized security testing only
"""

import socket
import struct
import threading
import time
import subprocess
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import *


class NetworkMapper:
    """Network discovery and host enumeration tool"""
    
    def __init__(self, network: str = None, threads: int = 50, timeout: float = 1.0):
        self.network = network or self._get_local_network()
        self.threads = threads
        self.timeout = timeout
        self.hosts = []
        self.lock = threading.Lock()
    
    def _get_local_network(self) -> str:
        """Detect local network automatically"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            # Assume /24 subnet
            parts = ip.split('.')
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        except:
            return "192.168.1.0/24"
    
    def _cidr_to_hosts(self, cidr: str) -> list:
        """Convert CIDR notation to list of hosts"""
        if '/' not in cidr:
            return [cidr]
        
        network, mask = cidr.split('/')
        mask = int(mask)
        
        parts = [int(x) for x in network.split('.')]
        ip_int = (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]
        
        num_hosts = 2 ** (32 - mask) - 2  # Exclude network and broadcast
        start_ip = (ip_int & (0xFFFFFFFF << (32 - mask))) + 1
        
        hosts = []
        for i in range(num_hosts):
            ip = start_ip + i
            host = f"{(ip >> 24) & 0xFF}.{(ip >> 16) & 0xFF}.{(ip >> 8) & 0xFF}.{ip & 0xFF}"
            hosts.append(host)
        
        return hosts
    
    def _ping_host(self, host: str) -> dict:
        """Ping a single host"""
        result = {"ip": host, "alive": False, "hostname": "", "response_time": 0}
        
        try:
            start = time.time()
            
            # Use system ping
            param = "-n" if platform.system().lower() == "windows" else "-c"
            timeout_param = "-w" if platform.system().lower() == "windows" else "-W"
            timeout_val = str(int(self.timeout * 1000)) if platform.system().lower() == "windows" else str(int(self.timeout))
            
            cmd = ["ping", param, "1", timeout_param, timeout_val, host]
            
            process = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=self.timeout + 1
            )
            
            if process.returncode == 0:
                result["alive"] = True
                result["response_time"] = round((time.time() - start) * 1000, 2)
                
                # Try reverse DNS
                try:
                    hostname = socket.gethostbyaddr(host)[0]
                    result["hostname"] = hostname
                except:
                    pass
        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            pass
        
        return result
    
    def _tcp_ping(self, host: str, port: int = 80) -> bool:
        """TCP ping fallback"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((host, port)) == 0
            sock.close()
            return result
        except:
            return False
    
    def _arp_scan(self, host: str) -> dict:
        """ARP-based host discovery (Windows/Linux)"""
        result = {"ip": host, "alive": False, "mac": "", "hostname": ""}
        
        try:
            # Send ICMP first
            param = "-n" if platform.system().lower() == "windows" else "-c"
            subprocess.run(
                ["ping", param, "1", host],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1
            )
            
            # Check ARP table
            if platform.system().lower() == "windows":
                output = subprocess.check_output(["arp", "-a", host], stderr=subprocess.DEVNULL).decode()
            else:
                output = subprocess.check_output(["arp", "-n", host], stderr=subprocess.DEVNULL).decode()
            
            if host in output and "incomplete" not in output.lower():
                result["alive"] = True
                # Extract MAC address
                for line in output.split('\n'):
                    if host in line:
                        parts = line.split()
                        for part in parts:
                            if ':' in part or '-' in part:
                                result["mac"] = part.upper().replace('-', ':')
                                break
        except:
            pass
        
        return result
    
    def discover_hosts(self, method: str = "ping") -> list:
        """Discover alive hosts on network"""
        hosts_to_scan = self._cidr_to_hosts(self.network)
        total = len(hosts_to_scan)
        scanned = 0
        alive_hosts = []
        
        info(f"Scanning network: {self.network}")
        info(f"Total hosts to scan: {total}")
        print()
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            if method == "arp":
                futures = {executor.submit(self._arp_scan, host): host for host in hosts_to_scan}
            else:
                futures = {executor.submit(self._ping_host, host): host for host in hosts_to_scan}
            
            for future in as_completed(futures):
                result = future.result()
                scanned += 1
                
                if result["alive"]:
                    alive_hosts.append(result)
                    with self.lock:
                        self.hosts.append(result)
                
                progress_bar(scanned, total, prefix="Discovering", suffix=f"{len(alive_hosts)} hosts found")
        
        elapsed = time.time() - start_time
        print()
        success(f"Discovery complete in {elapsed:.2f}s")
        
        return alive_hosts
    
    def get_host_info(self, ip: str) -> dict:
        """Get detailed information about a host"""
        info_dict = {
            "ip": ip,
            "hostname": "",
            "mac": "",
            "open_ports": [],
            "os_guess": ""
        }
        
        # Get hostname
        try:
            info_dict["hostname"] = socket.gethostbyaddr(ip)[0]
        except:
            pass
        
        # Quick port scan for common ports
        common_ports = [21, 22, 80, 443, 445, 3389, 8080]
        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                if sock.connect_ex((ip, port)) == 0:
                    info_dict["open_ports"].append(port)
                sock.close()
            except:
                pass
        
        # Basic OS fingerprinting based on ports
        if 3389 in info_dict["open_ports"]:
            info_dict["os_guess"] = "Windows (RDP open)"
        elif 22 in info_dict["open_ports"] and 3389 not in info_dict["open_ports"]:
            info_dict["os_guess"] = "Linux/Unix (SSH open)"
        
        return info_dict
    
    def print_results(self, hosts: list):
        """Print discovered hosts"""
        print(f"\n{C}{'═' * 60}{RESET}")
        print(f"{BRIGHT}DISCOVERED HOSTS{RESET}")
        print(f"{C}{'═' * 60}{RESET}")
        
        if not hosts:
            warning("No hosts discovered")
            return
        
        rows = []
        for h in hosts:
            rows.append([
                h.get("ip", ""),
                h.get("hostname", "-")[:20],
                h.get("mac", "-"),
                f"{h.get('response_time', 0)}ms"
            ])
        
        print_table(["IP ADDRESS", "HOSTNAME", "MAC", "RESPONSE"], rows, color="green")
        print(f"\n{Y}Total hosts found: {len(hosts)}{RESET}")


def get_local_ip() -> str:
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def get_gateway() -> str:
    """Get default gateway"""
    try:
        if platform.system().lower() == "windows":
            output = subprocess.check_output(["ipconfig"], shell=True).decode()
            for line in output.split('\n'):
                if "Default Gateway" in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        gw = parts[1].strip()
                        if gw:
                            return gw
        else:
            output = subprocess.check_output(["ip", "route"]).decode()
            for line in output.split('\n'):
                if "default" in line:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p == "via":
                            return parts[i + 1]
    except:
        pass
    return ""


def interactive_mode():
    """Interactive mode for network mapping"""
    print_banner("NETWORK MAPPER", color="red")
    warning("For authorized security testing only!")
    
    print(f"\n{Y}Local IP:{RESET} {get_local_ip()}")
    print(f"{Y}Gateway:{RESET} {get_gateway()}")
    
    options = [
        "Scan Local Network (Auto-detect)",
        "Scan Custom Network (CIDR)",
        "Scan IP Range",
        "Get Host Info"
    ]
    
    choice = menu_selector(options, "Select Option")
    
    if choice == 0:
        return
    elif choice == 1:
        mapper = NetworkMapper()
        hosts = mapper.discover_hosts()
        mapper.print_results(hosts)
    elif choice == 2:
        network = prompt("Enter network CIDR (e.g., 192.168.1.0/24)")
        mapper = NetworkMapper(network)
        hosts = mapper.discover_hosts()
        mapper.print_results(hosts)
    elif choice == 3:
        start_ip = prompt("Enter start IP")
        end_ip = prompt("Enter end IP")
        # Convert range to list
        start_parts = [int(x) for x in start_ip.split('.')]
        end_parts = [int(x) for x in end_ip.split('.')]
        
        hosts_to_scan = []
        for i in range(start_parts[3], end_parts[3] + 1):
            hosts_to_scan.append(f"{start_parts[0]}.{start_parts[1]}.{start_parts[2]}.{i}")
        
        mapper = NetworkMapper()
        mapper.network = start_ip.rsplit('.', 1)[0] + ".0/24"
        results = []
        for host in hosts_to_scan:
            result = mapper._ping_host(host)
            if result["alive"]:
                results.append(result)
                success(f"Host alive: {host}")
        mapper.print_results(results)
    elif choice == 4:
        ip = prompt("Enter IP address")
        mapper = NetworkMapper()
        info_dict = mapper.get_host_info(ip)
        print(f"\n{C}Host Information:{RESET}")
        print(f"  IP: {info_dict['ip']}")
        print(f"  Hostname: {info_dict['hostname'] or 'N/A'}")
        print(f"  Open Ports: {', '.join(map(str, info_dict['open_ports'])) or 'None detected'}")
        print(f"  OS Guess: {info_dict['os_guess'] or 'Unknown'}")


if __name__ == "__main__":
    interactive_mode()
