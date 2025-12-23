#!/usr/bin/env python3
"""
Red Team Tools - Packet Sniffer
For educational and authorized security testing only
"""

import socket
import struct
import sys
import os
import time
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import *


class PacketSniffer:
    """Network packet capture and analysis tool"""
    
    # Protocol numbers
    PROTOCOLS = {
        1: "ICMP",
        6: "TCP",
        17: "UDP",
        41: "IPv6",
        47: "GRE",
        50: "ESP",
        51: "AH",
        89: "OSPF"
    }
    
    # TCP Flags
    TCP_FLAGS = {
        0x01: "FIN",
        0x02: "SYN",
        0x04: "RST",
        0x08: "PSH",
        0x10: "ACK",
        0x20: "URG",
        0x40: "ECE",
        0x80: "CWR"
    }
    
    def __init__(self, interface: str = None, filter_protocol: str = None, 
                 filter_port: int = None, capture_count: int = 0):
        self.interface = interface
        self.filter_protocol = filter_protocol
        self.filter_port = filter_port
        self.capture_count = capture_count
        self.packets_captured = 0
        self.stats = defaultdict(int)
        self.running = False
    
    def _parse_ethernet_header(self, data: bytes) -> dict:
        """Parse Ethernet header"""
        eth_header = struct.unpack("!6s6sH", data[:14])
        return {
            "dest_mac": self._format_mac(eth_header[0]),
            "src_mac": self._format_mac(eth_header[1]),
            "eth_type": eth_header[2]
        }
    
    def _format_mac(self, mac_bytes: bytes) -> str:
        """Format MAC address"""
        return ":".join(f"{b:02x}" for b in mac_bytes)
    
    def _parse_ip_header(self, data: bytes) -> dict:
        """Parse IP header"""
        # Extract first 20 bytes of IP header
        ip_header = struct.unpack("!BBHHHBBH4s4s", data[:20])
        
        version = ip_header[0] >> 4
        ihl = (ip_header[0] & 0xF) * 4
        
        return {
            "version": version,
            "ihl": ihl,
            "tos": ip_header[1],
            "total_length": ip_header[2],
            "identification": ip_header[3],
            "flags": ip_header[4] >> 13,
            "fragment_offset": ip_header[4] & 0x1FFF,
            "ttl": ip_header[5],
            "protocol": ip_header[6],
            "protocol_name": self.PROTOCOLS.get(ip_header[6], "UNKNOWN"),
            "checksum": ip_header[7],
            "src_ip": socket.inet_ntoa(ip_header[8]),
            "dest_ip": socket.inet_ntoa(ip_header[9])
        }
    
    def _parse_tcp_header(self, data: bytes) -> dict:
        """Parse TCP header"""
        tcp_header = struct.unpack("!HHLLBBHHH", data[:20])
        
        flags = tcp_header[5]
        flag_list = [name for mask, name in self.TCP_FLAGS.items() if flags & mask]
        
        return {
            "src_port": tcp_header[0],
            "dest_port": tcp_header[1],
            "sequence": tcp_header[2],
            "acknowledgment": tcp_header[3],
            "data_offset": (tcp_header[4] >> 4) * 4,
            "flags": flags,
            "flag_names": flag_list,
            "window": tcp_header[6],
            "checksum": tcp_header[7],
            "urgent_pointer": tcp_header[8]
        }
    
    def _parse_udp_header(self, data: bytes) -> dict:
        """Parse UDP header"""
        udp_header = struct.unpack("!HHHH", data[:8])
        return {
            "src_port": udp_header[0],
            "dest_port": udp_header[1],
            "length": udp_header[2],
            "checksum": udp_header[3]
        }
    
    def _parse_icmp_header(self, data: bytes) -> dict:
        """Parse ICMP header"""
        icmp_header = struct.unpack("!BBHHH", data[:8])
        
        icmp_types = {
            0: "Echo Reply",
            3: "Destination Unreachable",
            5: "Redirect",
            8: "Echo Request",
            11: "Time Exceeded"
        }
        
        return {
            "type": icmp_header[0],
            "type_name": icmp_types.get(icmp_header[0], "Unknown"),
            "code": icmp_header[1],
            "checksum": icmp_header[2],
            "identifier": icmp_header[3],
            "sequence": icmp_header[4]
        }
    
    def _print_packet(self, packet_info: dict):
        """Print packet information"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        ip = packet_info.get("ip", {})
        protocol = ip.get("protocol_name", "?")
        
        # Color based on protocol
        if protocol == "TCP":
            proto_color = G
        elif protocol == "UDP":
            proto_color = B
        elif protocol == "ICMP":
            proto_color = Y
        else:
            proto_color = W
        
        # Build output
        output = f"{C}{timestamp}{RESET} "
        output += f"{proto_color}{protocol:<5}{RESET} "
        output += f"{ip.get('src_ip', '?'):>15} → {ip.get('dest_ip', '?'):<15}"
        
        # Add port info for TCP/UDP
        if protocol == "TCP" and "tcp" in packet_info:
            tcp = packet_info["tcp"]
            flags = ",".join(tcp.get("flag_names", []))
            output += f" :{tcp['src_port']} → :{tcp['dest_port']} [{flags}]"
        elif protocol == "UDP" and "udp" in packet_info:
            udp = packet_info["udp"]
            output += f" :{udp['src_port']} → :{udp['dest_port']}"
        elif protocol == "ICMP" and "icmp" in packet_info:
            icmp = packet_info["icmp"]
            output += f" {icmp.get('type_name', 'Unknown')}"
        
        print(output)
    
    def start_capture(self, verbose: bool = True):
        """Start packet capture"""
        info("Starting packet capture...")
        
        # Check for admin/root privileges
        if os.name == 'nt':
            try:
                import ctypes
                if not ctypes.windll.shell32.IsUserAnAdmin():
                    error("Administrator privileges required for packet capture on Windows")
                    warning("Please run as Administrator")
                    return
            except:
                pass
        
        try:
            # Create raw socket
            if os.name == 'nt':
                # Windows
                sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
                sock.bind((socket.gethostbyname(socket.gethostname()), 0))
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
                sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
            else:
                # Linux
                sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
        except PermissionError:
            error("Permission denied. Run with elevated privileges.")
            return
        except Exception as e:
            error(f"Failed to create socket: {e}")
            return
        
        self.running = True
        success("Capture started. Press Ctrl+C to stop.")
        print(f"\n{C}{'TIME':<12} {'PROTO':<5} {'SOURCE':<15} {'DESTINATION':<15} DETAILS{RESET}")
        print(f"{C}{'─' * 70}{RESET}")
        
        try:
            while self.running:
                if self.capture_count > 0 and self.packets_captured >= self.capture_count:
                    break
                
                data, addr = sock.recvfrom(65535)
                
                packet_info = {}
                
                # Parse IP header
                if os.name == 'nt':
                    ip_info = self._parse_ip_header(data)
                else:
                    # Skip Ethernet header on Linux
                    ip_info = self._parse_ip_header(data[14:])
                    packet_info["ethernet"] = self._parse_ethernet_header(data)
                
                packet_info["ip"] = ip_info
                
                # Apply filters
                if self.filter_protocol:
                    if ip_info["protocol_name"].lower() != self.filter_protocol.lower():
                        continue
                
                # Parse transport layer
                ip_header_len = ip_info["ihl"]
                if os.name == 'nt':
                    transport_data = data[ip_header_len:]
                else:
                    transport_data = data[14 + ip_header_len:]
                
                if ip_info["protocol"] == 6:  # TCP
                    packet_info["tcp"] = self._parse_tcp_header(transport_data)
                    if self.filter_port:
                        tcp = packet_info["tcp"]
                        if tcp["src_port"] != self.filter_port and tcp["dest_port"] != self.filter_port:
                            continue
                elif ip_info["protocol"] == 17:  # UDP
                    packet_info["udp"] = self._parse_udp_header(transport_data)
                    if self.filter_port:
                        udp = packet_info["udp"]
                        if udp["src_port"] != self.filter_port and udp["dest_port"] != self.filter_port:
                            continue
                elif ip_info["protocol"] == 1:  # ICMP
                    packet_info["icmp"] = self._parse_icmp_header(transport_data)
                
                self.packets_captured += 1
                self.stats[ip_info["protocol_name"]] += 1
                
                if verbose:
                    self._print_packet(packet_info)
        
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            if os.name == 'nt':
                sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
            sock.close()
            
            self._print_stats()
    
    def _print_stats(self):
        """Print capture statistics"""
        print(f"\n{C}{'═' * 40}{RESET}")
        print(f"{BRIGHT}CAPTURE STATISTICS{RESET}")
        print(f"{C}{'═' * 40}{RESET}")
        print(f"{Y}Total packets captured:{RESET} {self.packets_captured}")
        
        if self.stats:
            print(f"\n{Y}By Protocol:{RESET}")
            for proto, count in sorted(self.stats.items(), key=lambda x: -x[1]):
                bar_len = min(int(count / max(self.stats.values()) * 20), 20)
                bar = "█" * bar_len
                print(f"  {proto:<8} {G}{bar}{RESET} {count}")


def interactive_mode():
    """Interactive mode for packet sniffing"""
    print_banner("PACKET SNIFFER", color="red")
    warning("For authorized security testing only!")
    warning("Requires Administrator/root privileges!")
    
    options = [
        "Capture All Traffic",
        "Capture TCP Only",
        "Capture UDP Only",
        "Capture ICMP Only",
        "Capture Specific Port"
    ]
    
    choice = menu_selector(options, "Select Capture Mode")
    
    if choice == 0:
        return
    
    filter_protocol = None
    filter_port = None
    
    if choice == 2:
        filter_protocol = "TCP"
    elif choice == 3:
        filter_protocol = "UDP"
    elif choice == 4:
        filter_protocol = "ICMP"
    elif choice == 5:
        filter_port = int(prompt("Enter port number"))
    
    count_str = prompt("Number of packets to capture (0 for unlimited)")
    capture_count = int(count_str) if count_str else 0
    
    sniffer = PacketSniffer(
        filter_protocol=filter_protocol,
        filter_port=filter_port,
        capture_count=capture_count
    )
    sniffer.start_capture()


if __name__ == "__main__":
    interactive_mode()
