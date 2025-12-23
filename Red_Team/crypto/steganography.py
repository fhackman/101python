#!/usr/bin/env python3
"""
Red Team Tools - Steganography
For educational and authorized security testing only
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import *

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class Steganography:
    """Basic image steganography tool"""
    
    def __init__(self):
        if not HAS_PIL:
            warning("Pillow library not installed. Install with: pip install Pillow")
    
    def encode_lsb(self, image_path: str, message: str, output_path: str = None) -> str:
        """Hide message in image using LSB steganography"""
        if not HAS_PIL:
            error("Pillow library required")
            return ""
        
        # Load image
        img = Image.open(image_path)
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        pixels = list(img.getdata())
        width, height = img.size
        
        # Prepare message
        message += "\x00"  # Null terminator
        binary_message = ''.join(format(ord(c), '08b') for c in message)
        
        if len(binary_message) > len(pixels) * 3:
            error("Message too long for this image")
            return ""
        
        # Encode message
        new_pixels = []
        msg_idx = 0
        
        for pixel in pixels:
            r, g, b = pixel
            
            if msg_idx < len(binary_message):
                r = (r & ~1) | int(binary_message[msg_idx])
                msg_idx += 1
            
            if msg_idx < len(binary_message):
                g = (g & ~1) | int(binary_message[msg_idx])
                msg_idx += 1
            
            if msg_idx < len(binary_message):
                b = (b & ~1) | int(binary_message[msg_idx])
                msg_idx += 1
            
            new_pixels.append((r, g, b))
        
        # Create new image
        new_img = Image.new('RGB', (width, height))
        new_img.putdata(new_pixels)
        
        if output_path is None:
            base, ext = os.path.splitext(image_path)
            output_path = f"{base}_encoded{ext}"
        
        new_img.save(output_path)
        return output_path
    
    def decode_lsb(self, image_path: str) -> str:
        """Extract hidden message from image using LSB"""
        if not HAS_PIL:
            error("Pillow library required")
            return ""
        
        img = Image.open(image_path)
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        pixels = list(img.getdata())
        
        # Extract bits
        binary_message = ""
        for pixel in pixels:
            r, g, b = pixel
            binary_message += str(r & 1)
            binary_message += str(g & 1)
            binary_message += str(b & 1)
        
        # Convert to characters
        message = ""
        for i in range(0, len(binary_message), 8):
            byte = binary_message[i:i+8]
            if len(byte) == 8:
                char = chr(int(byte, 2))
                if char == '\x00':  # Null terminator
                    break
                message += char
        
        return message
    
    def encode_metadata(self, image_path: str, data: str, output_path: str = None) -> str:
        """Hide data in image EXIF metadata"""
        if not HAS_PIL:
            error("Pillow library required")
            return ""
        
        img = Image.open(image_path)
        
        # Add data to image info
        img.info['secret'] = data
        
        if output_path is None:
            base, ext = os.path.splitext(image_path)
            output_path = f"{base}_meta{ext}"
        
        # Save with metadata
        img.save(output_path)
        
        return output_path
    
    def analyze_image(self, image_path: str) -> dict:
        """Analyze image for hidden data indicators"""
        if not HAS_PIL:
            error("Pillow library required")
            return {}
        
        img = Image.open(image_path)
        pixels = list(img.getdata())
        
        width, height = img.size
        
        # Analyze LSB distribution
        lsb_ones = 0
        total_bits = 0
        
        for pixel in pixels:
            if img.mode == 'RGB':
                r, g, b = pixel
                lsb_ones += (r & 1) + (g & 1) + (b & 1)
                total_bits += 3
            elif img.mode == 'RGBA':
                r, g, b, a = pixel
                lsb_ones += (r & 1) + (g & 1) + (b & 1)
                total_bits += 3
        
        lsb_ratio = lsb_ones / total_bits if total_bits > 0 else 0
        
        # Check for anomalies
        suspicious = False
        if abs(lsb_ratio - 0.5) < 0.01:  # Very close to 50%
            suspicious = True
        
        analysis = {
            "format": img.format,
            "mode": img.mode,
            "size": f"{width}x{height}",
            "pixels": len(pixels),
            "max_hidden_bytes": (len(pixels) * 3) // 8,
            "lsb_ratio": lsb_ratio,
            "possibly_contains_hidden_data": suspicious,
            "metadata": dict(img.info) if img.info else {}
        }
        
        return analysis
    
    def create_carrier_image(self, width: int = 800, height: int = 600, 
                            output_path: str = "carrier.png") -> str:
        """Create a carrier image for steganography"""
        if not HAS_PIL:
            error("Pillow library required")
            return ""
        
        import random
        
        # Create random noise image (harder to detect modifications)
        pixels = []
        for _ in range(width * height):
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            pixels.append((r, g, b))
        
        img = Image.new('RGB', (width, height))
        img.putdata(pixels)
        img.save(output_path)
        
        return output_path


def interactive_mode():
    """Interactive mode for steganography"""
    print_banner("STEGANOGRAPHY", color="red")
    warning("For educational and authorized security testing only!")
    
    if not HAS_PIL:
        error("Pillow library required. Install with: pip install Pillow")
        return
    
    stego = Steganography()
    
    options = [
        "Hide Message in Image (LSB)",
        "Extract Message from Image",
        "Analyze Image",
        "Create Carrier Image"
    ]
    
    choice = menu_selector(options, "Select Option")
    
    if choice == 0:
        return
    
    elif choice == 1:
        image_path = prompt("Enter image path")
        message = prompt("Enter message to hide")
        output = prompt("Output path (or leave empty)")
        
        if not os.path.exists(image_path):
            error("Image not found")
            return
        
        result = stego.encode_lsb(image_path, message, output or None)
        
        if result:
            success(f"Message hidden in: {result}")
            
            analysis = stego.analyze_image(result)
            info(f"Max capacity: {analysis['max_hidden_bytes']} bytes")
    
    elif choice == 2:
        image_path = prompt("Enter image path")
        
        if not os.path.exists(image_path):
            error("Image not found")
            return
        
        message = stego.decode_lsb(image_path)
        
        if message:
            print(f"\n{G}Extracted Message:{RESET}")
            print(message)
        else:
            warning("No hidden message found (or empty)")
    
    elif choice == 3:
        image_path = prompt("Enter image path to analyze")
        
        if not os.path.exists(image_path):
            error("Image not found")
            return
        
        analysis = stego.analyze_image(image_path)
        
        print(f"\n{C}Image Analysis:{RESET}")
        print(f"  Format: {analysis['format']}")
        print(f"  Mode: {analysis['mode']}")
        print(f"  Size: {analysis['size']}")
        print(f"  Max Hidden Bytes: {analysis['max_hidden_bytes']}")
        print(f"  LSB Ratio: {analysis['lsb_ratio']:.4f}")
        
        if analysis['possibly_contains_hidden_data']:
            warning("Image may contain hidden data (LSB distribution anomaly)")
        else:
            info("No obvious LSB anomalies detected")
        
        if analysis['metadata']:
            print(f"\n{Y}Metadata:{RESET}")
            for key, value in list(analysis['metadata'].items())[:5]:
                print(f"  {key}: {str(value)[:50]}")
    
    elif choice == 4:
        width = int(prompt("Width") or "800")
        height = int(prompt("Height") or "600")
        output = prompt("Output path") or "carrier.png"
        
        result = stego.create_carrier_image(width, height, output)
        
        if result:
            success(f"Carrier image created: {result}")


if __name__ == "__main__":
    interactive_mode()
