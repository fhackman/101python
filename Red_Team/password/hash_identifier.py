#!/usr/bin/env python3
"""
Red Team Tools - Hash Identifier
For educational and authorized security testing only
"""

import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import *


class HashIdentifier:
    """Automatic hash type identification"""
    
    # Hash patterns with regex and descriptions
    HASH_PATTERNS = [
        # MD5 and variants
        {
            "name": "MD5",
            "regex": r"^[a-f0-9]{32}$",
            "description": "Message-Digest Algorithm 5",
            "john": "raw-md5",
            "hashcat": "0"
        },
        {
            "name": "MD5(Unix)",
            "regex": r"^\$1\$.{8}\$.{22}$",
            "description": "MD5 Unix crypt",
            "john": "md5crypt",
            "hashcat": "500"
        },
        {
            "name": "MD5(APR)",
            "regex": r"^\$apr1\$.{8}\$.{22}$",
            "description": "Apache MD5",
            "john": "md5crypt-apache",
            "hashcat": "1600"
        },
        
        # SHA family
        {
            "name": "SHA-1",
            "regex": r"^[a-f0-9]{40}$",
            "description": "Secure Hash Algorithm 1",
            "john": "raw-sha1",
            "hashcat": "100"
        },
        {
            "name": "SHA-224",
            "regex": r"^[a-f0-9]{56}$",
            "description": "Secure Hash Algorithm 224",
            "john": "raw-sha224",
            "hashcat": "1300"
        },
        {
            "name": "SHA-256",
            "regex": r"^[a-f0-9]{64}$",
            "description": "Secure Hash Algorithm 256",
            "john": "raw-sha256",
            "hashcat": "1400"
        },
        {
            "name": "SHA-384",
            "regex": r"^[a-f0-9]{96}$",
            "description": "Secure Hash Algorithm 384",
            "john": "raw-sha384",
            "hashcat": "10800"
        },
        {
            "name": "SHA-512",
            "regex": r"^[a-f0-9]{128}$",
            "description": "Secure Hash Algorithm 512",
            "john": "raw-sha512",
            "hashcat": "1700"
        },
        {
            "name": "SHA-512(Unix)",
            "regex": r"^\$6\$.{8,16}\$.{86}$",
            "description": "SHA-512 Unix crypt",
            "john": "sha512crypt",
            "hashcat": "1800"
        },
        
        # bcrypt
        {
            "name": "bcrypt",
            "regex": r"^\$2[aby]?\$\d{2}\$[./A-Za-z0-9]{53}$",
            "description": "Blowfish crypt",
            "john": "bcrypt",
            "hashcat": "3200"
        },
        
        # NTLM/LM
        {
            "name": "NTLM",
            "regex": r"^[a-f0-9]{32}$",
            "description": "NT LAN Manager (Windows)",
            "john": "nt",
            "hashcat": "1000"
        },
        {
            "name": "LM",
            "regex": r"^[a-f0-9]{32}$",
            "description": "LAN Manager (Windows legacy)",
            "john": "lm",
            "hashcat": "3000"
        },
        
        # MySQL
        {
            "name": "MySQL 4.1+",
            "regex": r"^\*[A-F0-9]{40}$",
            "description": "MySQL 4.1 and above",
            "john": "mysql-sha1",
            "hashcat": "300"
        },
        {
            "name": "MySQL 3.x",
            "regex": r"^[a-f0-9]{16}$",
            "description": "MySQL 3.x",
            "john": "mysql",
            "hashcat": "200"
        },
        
        # Oracle
        {
            "name": "Oracle 10g",
            "regex": r"^[a-f0-9]{16}$",
            "description": "Oracle Database 10g",
            "john": "oracle",
            "hashcat": "3100"
        },
        
        # PostgreSQL
        {
            "name": "PostgreSQL MD5",
            "regex": r"^md5[a-f0-9]{32}$",
            "description": "PostgreSQL MD5",
            "john": "postgres",
            "hashcat": "12"
        },
        
        # Cisco
        {
            "name": "Cisco Type 5",
            "regex": r"^\$1\$[a-zA-Z0-9./]{8}\$[a-zA-Z0-9./]{22}$",
            "description": "Cisco IOS Type 5",
            "john": "md5crypt",
            "hashcat": "500"
        },
        {
            "name": "Cisco Type 7",
            "regex": r"^[0-9]{2}[a-f0-9]+$",
            "description": "Cisco IOS Type 7 (weak)",
            "john": "cisco",
            "hashcat": "-"
        },
        
        # WordPress
        {
            "name": "WordPress",
            "regex": r"^\$P\$.{31}$",
            "description": "WordPress PHPass",
            "john": "phpass",
            "hashcat": "400"
        },
        
        # Joomla
        {
            "name": "Joomla",
            "regex": r"^[a-f0-9]{32}:[a-zA-Z0-9]{32}$",
            "description": "Joomla MD5 + Salt",
            "john": "joomla",
            "hashcat": "11"
        },
        
        # Django
        {
            "name": "Django PBKDF2-SHA256",
            "regex": r"^pbkdf2_sha256\$\d+\$[a-zA-Z0-9+/=]+\$[a-zA-Z0-9+/=]+$",
            "description": "Django PBKDF2 SHA-256",
            "john": "django",
            "hashcat": "10000"
        },
        
        # Drupal
        {
            "name": "Drupal 7",
            "regex": r"^\$S\$.{52}$",
            "description": "Drupal 7",
            "john": "drupal7",
            "hashcat": "7900"
        },
        
        # SHA3
        {
            "name": "SHA3-256",
            "regex": r"^[a-f0-9]{64}$",
            "description": "SHA-3 256 bit",
            "john": "raw-sha3",
            "hashcat": "17400"
        },
        {
            "name": "SHA3-512",
            "regex": r"^[a-f0-9]{128}$",
            "description": "SHA-3 512 bit",
            "john": "raw-sha3-512",
            "hashcat": "17600"
        },
        
        # Keccak
        {
            "name": "Keccak-256",
            "regex": r"^0x[a-f0-9]{64}$",
            "description": "Keccak 256 (Ethereum)",
            "john": "raw-keccak-256",
            "hashcat": "17800"
        },
        
        # Argon2
        {
            "name": "Argon2",
            "regex": r"^\$argon2[id]+\$v=\d+\$m=\d+,t=\d+,p=\d+\$[a-zA-Z0-9+/]+\$[a-zA-Z0-9+/]+$",
            "description": "Argon2 Password Hashing",
            "john": "argon2",
            "hashcat": "-"
        },
        
        # scrypt
        {
            "name": "scrypt",
            "regex": r"^\$scrypt\$",
            "description": "scrypt Password Hashing",
            "john": "scrypt",
            "hashcat": "8900"
        },
        
        # Base64 encoded hashes
        {
            "name": "Base64 (possibly encoded hash)",
            "regex": r"^[A-Za-z0-9+/]{20,}={0,2}$",
            "description": "Base64 encoded data",
            "john": "-",
            "hashcat": "-"
        },
    ]
    
    def __init__(self):
        pass
    
    def identify(self, hash_string: str) -> list:
        """Identify possible hash types"""
        hash_string = hash_string.strip()
        matches = []
        
        # Check against patterns
        for pattern in self.HASH_PATTERNS:
            if re.match(pattern["regex"], hash_string, re.IGNORECASE):
                matches.append({
                    "name": pattern["name"],
                    "description": pattern["description"],
                    "john": pattern.get("john", "-"),
                    "hashcat": pattern.get("hashcat", "-")
                })
        
        # If no matches, provide length-based guess
        if not matches:
            length = len(hash_string)
            if re.match(r'^[a-f0-9]+$', hash_string, re.IGNORECASE):
                matches.append({
                    "name": f"Unknown (hex, {length} chars)",
                    "description": f"Hexadecimal string of length {length}",
                    "john": "-",
                    "hashcat": "-"
                })
        
        return matches
    
    def identify_file(self, filepath: str) -> dict:
        """Identify hashes from a file"""
        results = {}
        
        if not os.path.exists(filepath):
            error(f"File not found: {filepath}")
            return results
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                hash_string = line.strip()
                if hash_string:
                    # Handle hash:password format
                    if ':' in hash_string:
                        hash_string = hash_string.split(':')[0]
                    
                    matches = self.identify(hash_string)
                    if matches:
                        results[hash_string] = {
                            "line": line_num,
                            "types": matches
                        }
        
        return results
    
    def print_results(self, hash_string: str, matches: list):
        """Print identification results"""
        print(f"\n{C}{'═' * 60}{RESET}")
        print(f"{BRIGHT}HASH IDENTIFICATION{RESET}")
        print(f"{C}{'═' * 60}{RESET}")
        
        print(f"\n{Y}Hash:{RESET} {hash_string}")
        print(f"{Y}Length:{RESET} {len(hash_string)} characters")
        
        if not matches:
            warning("No matching hash types found")
            return
        
        print(f"\n{G}Possible Types:{RESET}")
        
        rows = []
        for m in matches:
            rows.append([
                m["name"],
                m["description"][:30],
                m.get("hashcat", "-"),
                m.get("john", "-")
            ])
        
        print_table(["TYPE", "DESCRIPTION", "HASHCAT", "JOHN"], rows, color="green")


def analyze_hash(hash_string: str) -> dict:
    """Quick analysis of a hash"""
    analysis = {
        "hash": hash_string,
        "length": len(hash_string),
        "is_hex": bool(re.match(r'^[a-f0-9]+$', hash_string, re.IGNORECASE)),
        "is_base64": bool(re.match(r'^[A-Za-z0-9+/]+={0,2}$', hash_string)),
        "has_salt_separator": ':' in hash_string or '$' in hash_string,
        "possible_types": []
    }
    
    identifier = HashIdentifier()
    matches = identifier.identify(hash_string)
    analysis["possible_types"] = [m["name"] for m in matches]
    
    return analysis


def interactive_mode():
    """Interactive mode for hash identification"""
    print_banner("HASH ID", color="red")
    
    options = [
        "Identify Single Hash",
        "Identify Hashes from File",
        "Analyze Hash"
    ]
    
    choice = menu_selector(options, "Select Option")
    
    if choice == 0:
        return
    
    identifier = HashIdentifier()
    
    if choice == 1:
        hash_input = prompt("Enter hash to identify")
        matches = identifier.identify(hash_input)
        identifier.print_results(hash_input, matches)
    
    elif choice == 2:
        filepath = prompt("Enter file path")
        results = identifier.identify_file(filepath)
        
        if results:
            print(f"\n{G}Found {len(results)} hashes:{RESET}")
            for hash_str, data in list(results.items())[:10]:
                types = ", ".join([t["name"] for t in data["types"][:3]])
                print(f"  Line {data['line']}: {hash_str[:32]}... → {types}")
            
            if len(results) > 10:
                print(f"  ... and {len(results) - 10} more")
        else:
            warning("No hashes found in file")
    
    elif choice == 3:
        hash_input = prompt("Enter hash to analyze")
        analysis = analyze_hash(hash_input)
        
        print(f"\n{C}Hash Analysis:{RESET}")
        print(f"  Length: {analysis['length']}")
        print(f"  Is Hex: {analysis['is_hex']}")
        print(f"  Is Base64: {analysis['is_base64']}")
        print(f"  Has Salt: {analysis['has_salt_separator']}")
        print(f"  Possible Types: {', '.join(analysis['possible_types'][:5])}")


if __name__ == "__main__":
    interactive_mode()
