#!/usr/bin/env python3
"""
Red Team Tools - Hash Cracker
For educational and authorized security testing only
"""

import hashlib
import itertools
import string
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import *


class HashCracker:
    """Multi-algorithm hash cracking tool"""
    
    ALGORITHMS = {
        "md5": hashlib.md5,
        "sha1": hashlib.sha1,
        "sha224": hashlib.sha224,
        "sha256": hashlib.sha256,
        "sha384": hashlib.sha384,
        "sha512": hashlib.sha512,
        "sha3_256": hashlib.sha3_256,
        "sha3_512": hashlib.sha3_512,
        "blake2b": hashlib.blake2b,
        "blake2s": hashlib.blake2s,
    }
    
    def __init__(self, target_hash: str, algorithm: str = "auto", threads: int = 4):
        self.target_hash = target_hash.lower().strip()
        self.algorithm = algorithm.lower()
        self.threads = threads
        self.found = False
        self.result = None
        self.attempts = 0
        self.lock = threading.Lock()
    
    def _detect_algorithm(self) -> str:
        """Auto-detect hash algorithm by length"""
        length = len(self.target_hash)
        
        detections = {
            32: "md5",
            40: "sha1",
            56: "sha224",
            64: "sha256",
            96: "sha384",
            128: "sha512"
        }
        
        return detections.get(length, "md5")
    
    def _hash_string(self, text: str, algo: str = None) -> str:
        """Hash a string with specified algorithm"""
        if algo is None:
            algo = self.algorithm
        
        if algo == "auto":
            algo = self._detect_algorithm()
        
        hash_func = self.ALGORITHMS.get(algo, hashlib.md5)
        return hash_func(text.encode()).hexdigest()
    
    def _check_word(self, word: str) -> bool:
        """Check if word matches target hash"""
        if self.found:
            return False
        
        hashed = self._hash_string(word)
        
        with self.lock:
            self.attempts += 1
        
        if hashed == self.target_hash:
            with self.lock:
                self.found = True
                self.result = word
            return True
        
        return False
    
    def dictionary_attack(self, wordlist_path: str, show_progress: bool = True) -> str:
        """Crack hash using wordlist"""
        if not os.path.exists(wordlist_path):
            error(f"Wordlist not found: {wordlist_path}")
            return None
        
        # Count lines
        with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
            total_words = sum(1 for _ in f)
        
        info(f"Loading wordlist: {wordlist_path}")
        info(f"Total words: {total_words:,}")
        
        start_time = time.time()
        
        with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
            batch = []
            batch_size = 10000
            
            for i, line in enumerate(f):
                if self.found:
                    break
                
                word = line.strip()
                batch.append(word)
                
                if len(batch) >= batch_size:
                    with ThreadPoolExecutor(max_workers=self.threads) as executor:
                        for w in batch:
                            if self.found:
                                break
                            executor.submit(self._check_word, w)
                    batch = []
                    
                    if show_progress:
                        progress_bar(i + 1, total_words, 
                                   prefix="Cracking", 
                                   suffix=f"{self.attempts:,} attempts")
            
            # Process remaining
            if batch and not self.found:
                with ThreadPoolExecutor(max_workers=self.threads) as executor:
                    for w in batch:
                        if self.found:
                            break
                        executor.submit(self._check_word, w)
        
        elapsed = time.time() - start_time
        
        print()
        if self.found:
            success(f"Hash cracked in {elapsed:.2f}s after {self.attempts:,} attempts")
            success(f"Password: {self.result}")
            return self.result
        else:
            warning(f"Password not found after {self.attempts:,} attempts ({elapsed:.2f}s)")
            return None
    
    def brute_force(self, charset: str = None, min_length: int = 1, 
                   max_length: int = 4, show_progress: bool = True) -> str:
        """Brute force attack"""
        if charset is None:
            charset = string.ascii_lowercase + string.digits
        
        info(f"Starting brute force attack")
        info(f"Charset: {charset[:30]}{'...' if len(charset) > 30 else ''}")
        info(f"Length: {min_length} to {max_length}")
        
        # Calculate total combinations
        total = sum(len(charset) ** i for i in range(min_length, max_length + 1))
        info(f"Total combinations: {total:,}")
        warning("This may take a very long time!")
        
        start_time = time.time()
        checked = 0
        
        for length in range(min_length, max_length + 1):
            if self.found:
                break
            
            for combo in itertools.product(charset, repeat=length):
                if self.found:
                    break
                
                word = ''.join(combo)
                checked += 1
                
                if self._check_word(word):
                    break
                
                if show_progress and checked % 10000 == 0:
                    rate = checked / (time.time() - start_time)
                    progress_bar(checked, total, 
                               prefix="Brute Force", 
                               suffix=f"{rate:.0f}/s")
        
        elapsed = time.time() - start_time
        
        print()
        if self.found:
            success(f"Hash cracked in {elapsed:.2f}s")
            success(f"Password: {self.result}")
            return self.result
        else:
            warning(f"Password not found ({elapsed:.2f}s)")
            return None
    
    def rule_based_attack(self, base_words: list) -> str:
        """Attack with common mutations"""
        info("Running rule-based attack...")
        
        mutations = []
        
        for word in base_words:
            # Original
            mutations.append(word)
            
            # Case variations
            mutations.append(word.lower())
            mutations.append(word.upper())
            mutations.append(word.capitalize())
            mutations.append(word.swapcase())
            
            # Number suffixes
            for i in range(100):
                mutations.append(f"{word}{i}")
                mutations.append(f"{word}{i:02d}")
            
            # Year suffixes
            for year in range(2015, 2026):
                mutations.append(f"{word}{year}")
                mutations.append(f"{word}_{year}")
            
            # Special char suffixes
            for s in "!@#$%&*":
                mutations.append(f"{word}{s}")
            
            # Leet speak
            leet = word
            leet = leet.replace('a', '4').replace('e', '3')
            leet = leet.replace('i', '1').replace('o', '0')
            leet = leet.replace('s', '5').replace('t', '7')
            mutations.append(leet)
        
        info(f"Testing {len(mutations):,} mutations...")
        
        start_time = time.time()
        
        for i, word in enumerate(mutations):
            if self.found:
                break
            
            self._check_word(word)
            
            if (i + 1) % 1000 == 0:
                progress_bar(i + 1, len(mutations), prefix="Testing")
        
        elapsed = time.time() - start_time
        
        print()
        if self.found:
            success(f"Hash cracked in {elapsed:.2f}s")
            success(f"Password: {self.result}")
            return self.result
        else:
            warning(f"Password not found ({elapsed:.2f}s)")
            return None
    
    def rainbow_table_attack(self, rainbow_file: str) -> str:
        """Attack using rainbow table (hash:password format)"""
        info(f"Loading rainbow table: {rainbow_file}")
        
        if not os.path.exists(rainbow_file):
            error("Rainbow table file not found")
            return None
        
        with open(rainbow_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parts = line.strip().split(':')
                if len(parts) >= 2:
                    stored_hash = parts[0].lower()
                    password = ':'.join(parts[1:])
                    
                    if stored_hash == self.target_hash:
                        success(f"Hash found in rainbow table!")
                        success(f"Password: {password}")
                        self.result = password
                        self.found = True
                        return password
        
        warning("Hash not found in rainbow table")
        return None


def generate_hash(text: str, algorithm: str = "md5") -> str:
    """Generate hash for a string"""
    cracker = HashCracker("", algorithm)
    return cracker._hash_string(text, algorithm)


def interactive_mode():
    """Interactive mode for hash cracking"""
    print_banner("HASH CRACKER", color="red")
    warning("For authorized security testing only!")
    
    options = [
        "Crack Hash (Dictionary Attack)",
        "Crack Hash (Brute Force)",
        "Crack Hash (Rule-Based)",
        "Generate Hash",
        "Identify Hash Type"
    ]
    
    choice = menu_selector(options, "Select Option")
    
    if choice == 0:
        return
    
    elif choice == 1:
        target_hash = prompt("Enter hash to crack")
        wordlist = prompt("Wordlist path (or 'default')")
        
        if wordlist.lower() == 'default':
            # Create a simple default wordlist
            wordlist = os.path.join(os.path.dirname(__file__), "default_wordlist.txt")
            if not os.path.exists(wordlist):
                info("Creating default wordlist...")
                common = ["password", "123456", "admin", "letmein", "welcome",
                         "monkey", "dragon", "master", "qwerty", "login",
                         "password123", "admin123", "root", "toor", "pass"]
                with open(wordlist, 'w') as f:
                    for w in common:
                        f.write(f"{w}\n")
        
        algo = prompt("Algorithm (md5/sha1/sha256/auto)") or "auto"
        
        cracker = HashCracker(target_hash, algo)
        cracker.dictionary_attack(wordlist)
    
    elif choice == 2:
        target_hash = prompt("Enter hash to crack")
        algo = prompt("Algorithm (md5/sha1/sha256/auto)") or "auto"
        max_len = int(prompt("Max password length") or "4")
        
        charset_choice = prompt("Charset (1=lowercase, 2=lowercase+digits, 3=all)") or "2"
        
        if charset_choice == "1":
            charset = string.ascii_lowercase
        elif charset_choice == "2":
            charset = string.ascii_lowercase + string.digits
        else:
            charset = string.ascii_lowercase + string.ascii_uppercase + string.digits
        
        cracker = HashCracker(target_hash, algo)
        cracker.brute_force(charset, max_length=max_len)
    
    elif choice == 3:
        target_hash = prompt("Enter hash to crack")
        base_words = prompt("Enter base words (comma-separated)")
        words = [w.strip() for w in base_words.split(',')]
        
        algo = prompt("Algorithm (md5/sha1/sha256/auto)") or "auto"
        
        cracker = HashCracker(target_hash, algo)
        cracker.rule_based_attack(words)
    
    elif choice == 4:
        text = prompt("Enter text to hash")
        algo = prompt("Algorithm (md5/sha1/sha256/sha512)") or "md5"
        
        result = generate_hash(text, algo)
        print(f"\n{G}Hash ({algo}):{RESET} {result}")
    
    elif choice == 5:
        hash_input = prompt("Enter hash to identify")
        length = len(hash_input)
        
        print(f"\n{Y}Hash Length:{RESET} {length} characters")
        
        if length == 32:
            info("Possible: MD5, NTLM, MD4")
        elif length == 40:
            info("Possible: SHA-1, MySQL5")
        elif length == 56:
            info("Possible: SHA-224")
        elif length == 64:
            info("Possible: SHA-256, SHA3-256")
        elif length == 96:
            info("Possible: SHA-384")
        elif length == 128:
            info("Possible: SHA-512, SHA3-512")
        else:
            warning("Unknown hash type")


if __name__ == "__main__":
    interactive_mode()
