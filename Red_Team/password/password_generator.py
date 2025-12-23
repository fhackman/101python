#!/usr/bin/env python3
"""
Red Team Tools - Password & Wordlist Generator
For educational and authorized security testing only
"""

import random
import string
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import *


class PasswordGenerator:
    """Advanced password and wordlist generator"""
    
    # Character sets
    LOWERCASE = string.ascii_lowercase
    UPPERCASE = string.ascii_uppercase
    DIGITS = string.digits
    SPECIAL = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    EXTENDED_SPECIAL = "!@#$%^&*()_+-=[]{}|;:,.<>?/\\`~'\""
    LEET_MAP = {
        'a': ['4', '@'], 'e': ['3'], 'i': ['1', '!'], 'o': ['0'],
        's': ['5', '$'], 't': ['7'], 'l': ['1'], 'b': ['8']
    }
    
    def __init__(self):
        self.wordlist = []
    
    def generate_random(self, length: int = 16, count: int = 1,
                       lowercase: bool = True, uppercase: bool = True,
                       digits: bool = True, special: bool = True) -> list:
        """Generate random passwords"""
        charset = ""
        if lowercase:
            charset += self.LOWERCASE
        if uppercase:
            charset += self.UPPERCASE
        if digits:
            charset += self.DIGITS
        if special:
            charset += self.SPECIAL
        
        if not charset:
            charset = self.LOWERCASE + self.DIGITS
        
        passwords = []
        for _ in range(count):
            pwd = ''.join(random.choice(charset) for _ in range(length))
            passwords.append(pwd)
        
        return passwords
    
    def generate_passphrase(self, words: int = 4, separator: str = "-",
                           capitalize: bool = True, add_number: bool = True) -> str:
        """Generate memorable passphrase"""
        # Common words for passphrases
        word_list = [
            "apple", "banana", "cherry", "dragon", "eagle", "falcon", "grape",
            "hammer", "igloo", "jungle", "kettle", "lemon", "mango", "night",
            "orange", "piano", "queen", "river", "storm", "tiger", "ultra",
            "violet", "winter", "xenon", "yellow", "zebra", "alpha", "bravo",
            "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india",
            "juliet", "kilo", "lima", "mike", "november", "oscar", "papa",
            "quebec", "romeo", "sierra", "tango", "uniform", "victor", "whiskey"
        ]
        
        selected = random.sample(word_list, min(words, len(word_list)))
        
        if capitalize:
            selected = [w.capitalize() for w in selected]
        
        passphrase = separator.join(selected)
        
        if add_number:
            passphrase += separator + str(random.randint(10, 99))
        
        return passphrase
    
    def generate_pattern(self, pattern: str, count: int = 1) -> list:
        """
        Generate passwords from pattern
        L = lowercase, U = uppercase, D = digit, S = special, ? = any
        """
        passwords = []
        
        for _ in range(count):
            pwd = ""
            for char in pattern:
                if char == 'L':
                    pwd += random.choice(self.LOWERCASE)
                elif char == 'U':
                    pwd += random.choice(self.UPPERCASE)
                elif char == 'D':
                    pwd += random.choice(self.DIGITS)
                elif char == 'S':
                    pwd += random.choice(self.SPECIAL)
                elif char == '?':
                    pwd += random.choice(self.LOWERCASE + self.UPPERCASE + self.DIGITS)
                else:
                    pwd += char
            passwords.append(pwd)
        
        return passwords
    
    def leet_transform(self, word: str, level: int = 1) -> list:
        """Transform word to leet speak variations"""
        variations = [word]
        
        for i, char in enumerate(word.lower()):
            if char in self.LEET_MAP:
                new_variations = []
                for var in variations:
                    for replacement in self.LEET_MAP[char][:level]:
                        new_var = var[:i] + replacement + var[i+1:]
                        new_variations.append(new_var)
                variations.extend(new_variations)
        
        return list(set(variations))
    
    def generate_wordlist(self, base_words: list, options: dict = None) -> list:
        """
        Generate wordlist from base words with mutations
        Options: append_numbers, prepend_numbers, leet, case_mutations, 
                 append_special, year_suffix
        """
        if options is None:
            options = {
                "append_numbers": True,
                "prepend_numbers": False,
                "leet": True,
                "case_mutations": True,
                "append_special": True,
                "year_suffix": True
            }
        
        wordlist = set(base_words)
        
        for word in base_words:
            # Case mutations
            if options.get("case_mutations"):
                wordlist.add(word.lower())
                wordlist.add(word.upper())
                wordlist.add(word.capitalize())
                wordlist.add(word.swapcase())
            
            # Leet speak
            if options.get("leet"):
                wordlist.update(self.leet_transform(word))
            
            # Append numbers
            if options.get("append_numbers"):
                for i in range(100):
                    wordlist.add(f"{word}{i}")
                    wordlist.add(f"{word}{i:02d}")
            
            # Prepend numbers
            if options.get("prepend_numbers"):
                for i in range(10):
                    wordlist.add(f"{i}{word}")
            
            # Append special
            if options.get("append_special"):
                for s in "!@#$%&*":
                    wordlist.add(f"{word}{s}")
            
            # Year suffix
            if options.get("year_suffix"):
                for year in range(2020, 2026):
                    wordlist.add(f"{word}{year}")
                    wordlist.add(f"{word}_{year}")
        
        self.wordlist = sorted(list(wordlist))
        return self.wordlist
    
    def generate_combination_wordlist(self, words1: list, words2: list,
                                      separators: list = None) -> list:
        """Generate combinations of two word lists"""
        if separators is None:
            separators = ["", "_", "-", ".", "@"]
        
        wordlist = []
        for w1, w2 in itertools.product(words1, words2):
            for sep in separators:
                wordlist.append(f"{w1}{sep}{w2}")
                wordlist.append(f"{w2}{sep}{w1}")
        
        return wordlist
    
    def save_wordlist(self, filename: str, words: list = None):
        """Save wordlist to file"""
        if words is None:
            words = self.wordlist
        
        with open(filename, 'w', encoding='utf-8') as f:
            for word in words:
                f.write(f"{word}\n")
        
        success(f"Saved {len(words)} words to {filename}")
    
    def calculate_strength(self, password: str) -> dict:
        """Calculate password strength"""
        score = 0
        feedback = []
        
        # Length check
        length = len(password)
        if length >= 8:
            score += 1
        if length >= 12:
            score += 1
        if length >= 16:
            score += 1
        if length < 8:
            feedback.append("Too short (min 8 characters)")
        
        # Character variety
        has_lower = any(c in self.LOWERCASE for c in password)
        has_upper = any(c in self.UPPERCASE for c in password)
        has_digit = any(c in self.DIGITS for c in password)
        has_special = any(c in self.EXTENDED_SPECIAL for c in password)
        
        variety = sum([has_lower, has_upper, has_digit, has_special])
        score += variety
        
        if not has_lower:
            feedback.append("Add lowercase letters")
        if not has_upper:
            feedback.append("Add uppercase letters")
        if not has_digit:
            feedback.append("Add numbers")
        if not has_special:
            feedback.append("Add special characters")
        
        # Pattern checks
        if password.lower() in ['password', '123456', 'qwerty', 'admin']:
            score = 0
            feedback.append("Common password detected!")
        
        # Calculate entropy
        charset_size = 0
        if has_lower:
            charset_size += 26
        if has_upper:
            charset_size += 26
        if has_digit:
            charset_size += 10
        if has_special:
            charset_size += 32
        
        import math
        entropy = length * math.log2(charset_size) if charset_size > 0 else 0
        
        # Strength rating
        if score <= 2:
            strength = "Weak"
            color = "red"
        elif score <= 4:
            strength = "Fair"
            color = "yellow"
        elif score <= 6:
            strength = "Good"
            color = "green"
        else:
            strength = "Strong"
            color = "cyan"
        
        return {
            "score": score,
            "max_score": 7,
            "strength": strength,
            "color": color,
            "entropy": round(entropy, 2),
            "feedback": feedback
        }


def interactive_mode():
    """Interactive mode for password generation"""
    print_banner("PASSWORD GEN", color="red")
    
    gen = PasswordGenerator()
    
    options = [
        "Generate Random Passwords",
        "Generate Passphrase",
        "Generate from Pattern",
        "Generate Wordlist from Base Words",
        "Check Password Strength",
        "Leet Transform"
    ]
    
    choice = menu_selector(options, "Select Option")
    
    if choice == 0:
        return
    elif choice == 1:
        length = int(prompt("Password length") or "16")
        count = int(prompt("Number of passwords") or "5")
        passwords = gen.generate_random(length, count)
        
        print(f"\n{G}Generated Passwords:{RESET}")
        for pwd in passwords:
            strength = gen.calculate_strength(pwd)
            print(f"  {pwd}  [{strength['strength']}]")
    
    elif choice == 2:
        words = int(prompt("Number of words") or "4")
        passphrase = gen.generate_passphrase(words)
        strength = gen.calculate_strength(passphrase)
        print(f"\n{G}Passphrase:{RESET} {passphrase}")
        print(f"{Y}Strength:{RESET} {strength['strength']} (Entropy: {strength['entropy']} bits)")
    
    elif choice == 3:
        print(f"\n{Y}Pattern Guide:{RESET}")
        print("  L = lowercase, U = uppercase, D = digit, S = special, ? = any")
        print("  Example: ULLLDDDS = Abc12!@#")
        pattern = prompt("Enter pattern")
        count = int(prompt("Number to generate") or "5")
        passwords = gen.generate_pattern(pattern, count)
        
        print(f"\n{G}Generated:{RESET}")
        for pwd in passwords:
            print(f"  {pwd}")
    
    elif choice == 4:
        words_input = prompt("Enter base words (comma-separated)")
        base_words = [w.strip() for w in words_input.split(',')]
        
        wordlist = gen.generate_wordlist(base_words)
        print(f"\n{G}Generated {len(wordlist)} variations{RESET}")
        
        if confirm("Save to file?"):
            filename = prompt("Filename") or "wordlist.txt"
            gen.save_wordlist(filename, wordlist)
    
    elif choice == 5:
        password = prompt("Enter password to check")
        result = gen.calculate_strength(password)
        
        color_map = {"red": R, "yellow": Y, "green": G, "cyan": C}
        c = color_map.get(result["color"], W)
        
        print(f"\n{c}Strength: {result['strength']}{RESET}")
        print(f"Score: {result['score']}/{result['max_score']}")
        print(f"Entropy: {result['entropy']} bits")
        
        if result["feedback"]:
            print(f"\n{Y}Suggestions:{RESET}")
            for fb in result["feedback"]:
                print(f"  • {fb}")
    
    elif choice == 6:
        word = prompt("Enter word to transform")
        variations = gen.leet_transform(word, level=2)
        print(f"\n{G}Leet Variations ({len(variations)}):{RESET}")
        for v in variations[:20]:
            print(f"  {v}")
        if len(variations) > 20:
            print(f"  ... and {len(variations) - 20} more")


if __name__ == "__main__":
    interactive_mode()
