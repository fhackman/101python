#!/usr/bin/env python3
"""
Red Team Tools - Shared Utilities
For educational and authorized security testing only
"""

import os
import sys
import time
import datetime
import logging
from typing import Optional

try:
    from colorama import Fore, Back, Style, init
    init(autoreset=True)
except ImportError:
    # Fallback if colorama not installed
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
        LIGHTRED_EX = LIGHTGREEN_EX = LIGHTYELLOW_EX = LIGHTBLUE_EX = ""
        LIGHTMAGENTA_EX = LIGHTCYAN_EX = LIGHTWHITE_EX = ""
    class Back:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ""

try:
    import pyfiglet
    HAS_PYFIGLET = True
except ImportError:
    HAS_PYFIGLET = False


# Explicitly define what gets exported to prevent conflicts
__all__ = [
    'R', 'G', 'Y', 'B', 'M', 'C', 'W', 'RESET', 'BRIGHT',
    'clear_screen', 'banner', 'print_banner',
    'success', 'error', 'warning', 'info', 'debug',
    'prompt', 'confirm', 'print_table',
    'progress_bar', 'spinner_animation', 'get_timestamp',
    'setup_logging', 'validate_ip', 'validate_port', 'validate_url',
    'bytes_to_human', 'menu_selector', 'hacker_intro'
]

# Color shortcuts
R = Fore.RED
G = Fore.GREEN
Y = Fore.YELLOW
B = Fore.BLUE
M = Fore.MAGENTA
C = Fore.CYAN
W = Fore.WHITE
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT


def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def banner(text: str, font: str = "slant", color: str = None) -> str:
    """Generate ASCII art banner"""
    if HAS_PYFIGLET:
        art = pyfiglet.figlet_format(text, font=font)
    else:
        art = f"\n{'='*50}\n  {text}\n{'='*50}\n"
    
    if color:
        color_map = {
            'red': R, 'green': G, 'yellow': Y, 
            'blue': B, 'magenta': M, 'cyan': C, 'white': W
        }
        return color_map.get(color.lower(), C) + art + RESET
    return C + art + RESET


def print_banner(text: str, font: str = "slant", color: str = "cyan"):
    """Print ASCII art banner"""
    print(banner(text, font, color))


def success(msg: str):
    """Print success message"""
    print(f"{G}[+]{RESET} {msg}")


def error(msg: str):
    """Print error message"""
    print(f"{R}[-]{RESET} {msg}")


def warning(msg: str):
    """Print warning message"""
    print(f"{Y}[!]{RESET} {msg}")


def info(msg: str):
    """Print info message"""
    print(f"{B}[*]{RESET} {msg}")


def debug(msg: str):
    """Print debug message"""
    print(f"{M}[D]{RESET} {msg}")


def prompt(msg: str) -> str:
    """Get user input with styled prompt"""
    return input(f"{C}[?]{RESET} {msg}: ")


def confirm(msg: str) -> bool:
    """Get yes/no confirmation"""
    response = input(f"{Y}[?]{RESET} {msg} (y/n): ").strip().lower()
    return response in ('y', 'yes')


def print_table(headers: list, rows: list, color: str = "cyan"):
    """Print formatted table"""
    color_map = {'red': R, 'green': G, 'yellow': Y, 'blue': B, 'magenta': M, 'cyan': C, 'white': W}
    c = color_map.get(color.lower(), C)
    
    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))
    
    # Print header
    header_row = " | ".join(f"{h:<{widths[i]}}" for i, h in enumerate(headers))
    separator = "-+-".join("-" * w for w in widths)
    
    print(f"{c}{header_row}{RESET}")
    print(f"{c}{separator}{RESET}")
    
    # Print rows
    for row in rows:
        row_str = " | ".join(f"{str(cell):<{widths[i]}}" for i, cell in enumerate(row))
        print(row_str)


def progress_bar(current: int, total: int, prefix: str = "", suffix: str = "", length: int = 50):
    """Print progress bar"""
    percent = current / total if total > 0 else 0
    filled = int(length * percent)
    bar = f"{G}{'█' * filled}{RESET}{'░' * (length - filled)}"
    print(f"\r{prefix} |{bar}| {percent*100:.1f}% {suffix}", end="", flush=True)
    if current >= total:
        print()


def spinner_animation(duration: float = 2.0, message: str = "Loading"):
    """Show spinner animation"""
    chars = "⣾⣽⣻⢿⡿⣟⣯⣷"
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        print(f"\r{C}{chars[i % len(chars)]}{RESET} {message}...", end="", flush=True)
        time.sleep(0.1)
        i += 1
    print(f"\r{G}✓{RESET} {message}... Done!")


def get_timestamp() -> str:
    """Get formatted timestamp"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def setup_logging(name: str, filename: Optional[str] = None, level: int = logging.INFO):
    """Setup logging with file and console handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    # File handler (optional)
    if filename:
        file_handler = logging.FileHandler(filename)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def validate_ip(ip: str) -> bool:
    """Validate IPv4 address"""
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    for part in parts:
        try:
            num = int(part)
            if num < 0 or num > 255:
                return False
        except ValueError:
            return False
    return True


def validate_port(port: int) -> bool:
    """Validate port number"""
    return 1 <= port <= 65535


def validate_url(url: str) -> bool:
    """Basic URL validation"""
    return url.startswith(('http://', 'https://'))


def bytes_to_human(size: int) -> str:
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def menu_selector(options: list, title: str = "Select Option") -> int:
    """Display menu and get selection"""
    print(f"\n{C}{BRIGHT}=== {title} ==={RESET}")
    for i, opt in enumerate(options, 1):
        print(f"  {Y}[{i}]{RESET} {opt}")
    print(f"  {R}[0]{RESET} Exit/Back")
    print()
    
    while True:
        try:
            choice = int(prompt("Enter choice"))
            if 0 <= choice <= len(options):
                return choice
            error("Invalid choice")
        except ValueError:
            error("Please enter a number")


def hacker_intro():
    """Display hacker-themed intro"""
    clear_screen()
    print_banner("RED TEAM", font="slant", color="red")
    print(f"{R}{'═' * 60}{RESET}")
    print(f"{Y}  ⚠  AUTHORIZED SECURITY TESTING ONLY  ⚠{RESET}")
    print(f"{R}{'═' * 60}{RESET}")
    print()


if __name__ == "__main__":
    # Demo
    hacker_intro()
    success("This is a success message")
    error("This is an error message")
    warning("This is a warning message")
    info("This is an info message")
    
    print("\nTable Demo:")
    print_table(
        ["Tool", "Status", "Version"],
        [
            ["Port Scanner", "Ready", "1.0"],
            ["Hash Cracker", "Ready", "1.0"],
            ["XSS Scanner", "Ready", "1.0"],
        ]
    )
