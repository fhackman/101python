#!/usr/bin/env python3
"""
Red Team Tools - Main Menu
For educational and authorized security testing only

██████╗ ███████╗██████╗     ████████╗███████╗ █████╗ ███╗   ███╗
██╔══██╗██╔════╝██╔══██╗    ╚══██╔══╝██╔════╝██╔══██╗████╗ ████║
██████╔╝█████╗  ██║  ██║       ██║   █████╗  ███████║██╔████╔██║
██╔══██╗██╔══╝  ██║  ██║       ██║   ██╔══╝  ██╔══██║██║╚██╔╝██║
██║  ██║███████╗██████╔╝       ██║   ███████╗██║  ██║██║ ╚═╝ ██║
╚═╝  ╚═╝╚══════╝╚═════╝        ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝
"""

import os
import sys
import importlib

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import *


class RedTeamMenu:
    """Main menu for Red Team Tools"""
    
    TOOLS = {
        "Network Reconnaissance": [
            ("Port Scanner", "network.port_scanner"),
            ("Network Mapper", "network.network_mapper"),
            ("Service Enumerator", "network.service_enum"),
            ("Packet Sniffer", "network.packet_sniffer"),
        ],
        "Password & Credentials": [
            ("Password Generator", "password.password_generator"),
            ("Hash Cracker", "password.hash_cracker"),
            ("Hash Identifier", "password.hash_identifier"),
        ],
        "Web Security": [
            ("Directory Bruteforcer", "web.dir_bruteforcer"),
            ("XSS Scanner", "web.xss_scanner"),
            ("SQL Injection Tester", "web.sqli_tester"),
            ("Subdomain Enumerator", "web.subdomain_enum"),
        ],
        "System Tools": [
            ("Process Monitor", "system.process_monitor"),
            ("Privilege Escalation Checker", "system.priv_escalation_checker"),
            ("Persistence Checker", "system.persistence_checker"),
        ],
        "Phishing & Social Engineering": [
            ("Email Spoofer", "phishing.email_spoofer"),
            ("Phishing Page Generator", "phishing.phishing_generator"),
        ],
        "Exploit Development": [
            ("Shellcode Generator", "exploit.shellcode_gen"),
            ("Buffer Overflow Helper", "exploit.buffer_overflow_helper"),
            ("Payload Encoder", "exploit.payload_encoder"),
        ],
        "Cryptography": [
            ("Crypto Tools", "crypto.crypto_tools"),
            ("Steganography", "crypto.steganography"),
        ],
    }
    
    def __init__(self):
        self.running = True
    
    def display_banner(self):
        """Display main banner"""
        clear_screen()
        
        banner_text = """
██████╗ ███████╗██████╗     ████████╗███████╗ █████╗ ███╗   ███╗
██╔══██╗██╔════╝██╔══██╗    ╚══██╔══╝██╔════╝██╔══██╗████╗ ████║
██████╔╝█████╗  ██║  ██║       ██║   █████╗  ███████║██╔████╔██║
██╔══██╗██╔══╝  ██║  ██║       ██║   ██╔══╝  ██╔══██║██║╚██╔╝██║
██║  ██║███████╗██████╔╝       ██║   ███████╗██║  ██║██║ ╚═╝ ██║
╚═╝  ╚═╝╚══════╝╚═════╝        ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝
        """
        
        print(f"{R}{banner_text}{RESET}")
        print(f"{R}{'═' * 70}{RESET}")
        print(f"{Y}  ⚠  FOR AUTHORIZED SECURITY TESTING ONLY  ⚠{RESET}")
        print(f"{R}{'═' * 70}{RESET}")
        print()
    
    def display_categories(self):
        """Display tool categories"""
        print(f"\n{C}{BRIGHT}TOOL CATEGORIES{RESET}")
        print(f"{C}{'─' * 40}{RESET}")
        
        categories = list(self.TOOLS.keys())
        for i, cat in enumerate(categories, 1):
            tool_count = len(self.TOOLS[cat])
            print(f"  {Y}[{i}]{RESET} {cat} ({tool_count} tools)")
        
        print(f"\n  {R}[0]{RESET} Exit")
        print()
        
        return categories
    
    def display_tools(self, category: str):
        """Display tools in a category"""
        tools = self.TOOLS.get(category, [])
        
        clear_screen()
        print(f"\n{C}{BRIGHT}{category.upper()}{RESET}")
        print(f"{C}{'─' * 40}{RESET}")
        
        for i, (name, module) in enumerate(tools, 1):
            print(f"  {Y}[{i}]{RESET} {name}")
        
        print(f"\n  {R}[0]{RESET} Back to Main Menu")
        print()
        
        return tools
    
    def run_tool(self, module_path: str):
        """Run a specific tool"""
        try:
            # Import and run the tool
            module = importlib.import_module(module_path)
            
            if hasattr(module, 'interactive_mode'):
                module.interactive_mode()
            else:
                error("Tool does not have interactive mode")
        except ImportError as e:
            error(f"Failed to load tool: {e}")
        except Exception as e:
            error(f"Error running tool: {e}")
        
        print()
        input(f"{C}Press Enter to continue...{RESET}")
    
    def main_loop(self):
        """Main menu loop"""
        while self.running:
            self.display_banner()
            categories = self.display_categories()
            
            try:
                choice = int(prompt("Select category"))
                
                if choice == 0:
                    self.running = False
                    clear_screen()
                    print(f"\n{G}Thanks for using Red Team Tools!{RESET}")
                    print(f"{Y}Stay ethical. Stay legal.{RESET}\n")
                    break
                
                if 1 <= choice <= len(categories):
                    category = categories[choice - 1]
                    
                    while True:
                        tools = self.display_tools(category)
                        
                        tool_choice = int(prompt("Select tool"))
                        
                        if tool_choice == 0:
                            break
                        
                        if 1 <= tool_choice <= len(tools):
                            name, module_path = tools[tool_choice - 1]
                            clear_screen()
                            self.run_tool(module_path)
                        else:
                            error("Invalid selection")
                else:
                    error("Invalid selection")
            
            except ValueError:
                error("Please enter a number")
            except KeyboardInterrupt:
                print()
                if confirm("Exit Red Team Tools?"):
                    self.running = False
                    break


def quick_run(tool_name: str):
    """Quick run a specific tool by name"""
    tool_map = {
        "portscan": "network.port_scanner",
        "netmap": "network.network_mapper",
        "service": "network.service_enum",
        "sniffer": "network.packet_sniffer",
        "passgen": "password.password_generator",
        "hashcrack": "password.hash_cracker",
        "hashid": "password.hash_identifier",
        "dirbust": "web.dir_bruteforcer",
        "xss": "web.xss_scanner",
        "sqli": "web.sqli_tester",
        "subdomain": "web.subdomain_enum",
        "procmon": "system.process_monitor",
        "privesc": "system.priv_escalation_checker",
        "persist": "system.persistence_checker",
        "email": "phishing.email_spoofer",
        "phish": "phishing.phishing_generator",
        "shellcode": "exploit.shellcode_gen",
        "bof": "exploit.buffer_overflow_helper",
        "encode": "exploit.payload_encoder",
        "crypto": "crypto.crypto_tools",
        "stego": "crypto.steganography",
    }
    
    if tool_name in tool_map:
        module = importlib.import_module(tool_map[tool_name])
        if hasattr(module, 'interactive_mode'):
            module.interactive_mode()
    else:
        print(f"Available tools: {', '.join(tool_map.keys())}")


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        # Quick run mode
        tool_name = sys.argv[1].lower()
        quick_run(tool_name)
    else:
        # Interactive menu mode
        menu = RedTeamMenu()
        menu.main_loop()


if __name__ == "__main__":
    main()
