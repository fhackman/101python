#!/usr/bin/env python3
"""
Red Team Tools - Cryptography Tools
For educational and authorized security testing only
"""

import os
import sys
import base64
import hashlib
import secrets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import *

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding, hashes
    from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class CryptoTools:
    """Encryption/decryption utilities"""
    
    def __init__(self):
        if not HAS_CRYPTO:
            warning("cryptography library not installed. Some features unavailable.")
    
    # AES Encryption
    def aes_encrypt(self, data: bytes, key: bytes = None, iv: bytes = None) -> dict:
        """AES-256-CBC encryption"""
        if not HAS_CRYPTO:
            error("cryptography library required")
            return {}
        
        # Generate key and IV if not provided
        if key is None:
            key = secrets.token_bytes(32)  # 256-bit key
        if iv is None:
            iv = secrets.token_bytes(16)   # 128-bit IV
        
        # Pad data
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()
        
        # Encrypt
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        return {
            "ciphertext": ciphertext,
            "key": key,
            "iv": iv,
            "ciphertext_b64": base64.b64encode(ciphertext).decode(),
            "key_b64": base64.b64encode(key).decode(),
            "iv_b64": base64.b64encode(iv).decode()
        }
    
    def aes_decrypt(self, ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
        """AES-256-CBC decryption"""
        if not HAS_CRYPTO:
            error("cryptography library required")
            return b""
        
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Unpad
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        
        return data
    
    # RSA Encryption
    def generate_rsa_keypair(self, key_size: int = 2048) -> dict:
        """Generate RSA key pair"""
        if not HAS_CRYPTO:
            error("cryptography library required")
            return {}
        
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return {
            "private_key": private_key,
            "public_key": public_key,
            "private_pem": private_pem.decode(),
            "public_pem": public_pem.decode()
        }
    
    def rsa_encrypt(self, data: bytes, public_key) -> bytes:
        """RSA encryption with public key"""
        if not HAS_CRYPTO:
            error("cryptography library required")
            return b""
        
        ciphertext = public_key.encrypt(
            data,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return ciphertext
    
    def rsa_decrypt(self, ciphertext: bytes, private_key) -> bytes:
        """RSA decryption with private key"""
        if not HAS_CRYPTO:
            error("cryptography library required")
            return b""
        
        plaintext = private_key.decrypt(
            ciphertext,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return plaintext
    
    # Hashing
    def hash_data(self, data: bytes, algorithm: str = "sha256") -> str:
        """Hash data with specified algorithm"""
        algos = {
            "md5": hashlib.md5,
            "sha1": hashlib.sha1,
            "sha256": hashlib.sha256,
            "sha512": hashlib.sha512,
            "sha3_256": hashlib.sha3_256,
            "sha3_512": hashlib.sha3_512,
        }
        
        if algorithm not in algos:
            algorithm = "sha256"
        
        return algos[algorithm](data).hexdigest()
    
    def generate_key(self, length: int = 32) -> bytes:
        """Generate cryptographically secure random key"""
        return secrets.token_bytes(length)
    
    def generate_password(self, length: int = 16) -> str:
        """Generate secure random password"""
        import string
        alphabet = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    # Simple XOR cipher (for quick operations)
    def xor_cipher(self, data: bytes, key: bytes) -> bytes:
        """Simple XOR cipher"""
        return bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])
    
    # File encryption
    def encrypt_file(self, filepath: str, key: bytes = None) -> dict:
        """Encrypt a file with AES-256"""
        if not os.path.exists(filepath):
            error(f"File not found: {filepath}")
            return {}
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        result = self.aes_encrypt(data, key)
        
        if result:
            enc_filepath = filepath + ".enc"
            with open(enc_filepath, 'wb') as f:
                # Write IV + ciphertext
                f.write(result["iv"] + result["ciphertext"])
            
            result["encrypted_file"] = enc_filepath
        
        return result
    
    def decrypt_file(self, filepath: str, key: bytes) -> str:
        """Decrypt a file encrypted with encrypt_file"""
        if not os.path.exists(filepath):
            error(f"File not found: {filepath}")
            return ""
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # Extract IV and ciphertext
        iv = data[:16]
        ciphertext = data[16:]
        
        plaintext = self.aes_decrypt(ciphertext, key, iv)
        
        # Write decrypted file
        dec_filepath = filepath.replace(".enc", ".dec")
        with open(dec_filepath, 'wb') as f:
            f.write(plaintext)
        
        return dec_filepath


def interactive_mode():
    """Interactive mode for crypto tools"""
    print_banner("CRYPTO TOOLS", color="red")
    
    crypto = CryptoTools()
    
    options = [
        "AES Encrypt",
        "AES Decrypt",
        "Generate RSA Key Pair",
        "Hash Data",
        "Generate Secure Key/Password",
        "Encrypt File",
        "Decrypt File"
    ]
    
    choice = menu_selector(options, "Select Option")
    
    if choice == 0:
        return
    
    elif choice == 1:
        data = prompt("Enter data to encrypt")
        
        result = crypto.aes_encrypt(data.encode())
        
        if result:
            print(f"\n{G}AES-256-CBC Encrypted:{RESET}")
            print(f"  Key (hex): {result['key'].hex()}")
            print(f"  IV (hex): {result['iv'].hex()}")
            print(f"  Ciphertext (base64): {result['ciphertext_b64']}")
            
            # Save key for later
            if confirm("Save key to file?"):
                with open("aes_key.txt", "w") as f:
                    f.write(f"Key: {result['key'].hex()}\n")
                    f.write(f"IV: {result['iv'].hex()}\n")
                success("Key saved to aes_key.txt")
    
    elif choice == 2:
        ciphertext_b64 = prompt("Enter ciphertext (base64)")
        key_hex = prompt("Enter key (hex)")
        iv_hex = prompt("Enter IV (hex)")
        
        try:
            ciphertext = base64.b64decode(ciphertext_b64)
            key = bytes.fromhex(key_hex)
            iv = bytes.fromhex(iv_hex)
            
            plaintext = crypto.aes_decrypt(ciphertext, key, iv)
            
            print(f"\n{G}Decrypted:{RESET}")
            print(plaintext.decode())
        except Exception as e:
            error(f"Decryption failed: {e}")
    
    elif choice == 3:
        key_size = int(prompt("Key size (2048/4096)") or "2048")
        
        info("Generating RSA key pair...")
        result = crypto.generate_rsa_keypair(key_size)
        
        if result:
            print(f"\n{G}RSA Key Pair Generated:{RESET}")
            print(f"\n{Y}Private Key:{RESET}")
            print(result["private_pem"][:200] + "...")
            print(f"\n{Y}Public Key:{RESET}")
            print(result["public_pem"])
            
            if confirm("Save keys to files?"):
                with open("private_key.pem", "w") as f:
                    f.write(result["private_pem"])
                with open("public_key.pem", "w") as f:
                    f.write(result["public_pem"])
                success("Keys saved to private_key.pem and public_key.pem")
    
    elif choice == 4:
        data = prompt("Enter data to hash")
        algorithm = prompt("Algorithm (md5/sha1/sha256/sha512)") or "sha256"
        
        result = crypto.hash_data(data.encode(), algorithm)
        
        print(f"\n{G}{algorithm.upper()} Hash:{RESET}")
        print(result)
    
    elif choice == 5:
        key_type = prompt("Generate key or password? (k/p)") or "p"
        length = int(prompt("Length") or "32")
        
        if key_type.lower() == "k":
            key = crypto.generate_key(length)
            print(f"\n{G}Random Key ({length} bytes):{RESET}")
            print(f"  Hex: {key.hex()}")
            print(f"  Base64: {base64.b64encode(key).decode()}")
        else:
            password = crypto.generate_password(length)
            print(f"\n{G}Random Password:{RESET}")
            print(f"  {password}")
    
    elif choice == 6:
        filepath = prompt("Enter file path to encrypt")
        
        result = crypto.encrypt_file(filepath)
        
        if result:
            print(f"\n{G}File Encrypted:{RESET}")
            print(f"  Output: {result.get('encrypted_file', 'N/A')}")
            print(f"  Key (hex): {result['key'].hex()}")
            warning("SAVE THIS KEY! You need it to decrypt the file.")
    
    elif choice == 7:
        filepath = prompt("Enter encrypted file path")
        key_hex = prompt("Enter key (hex)")
        
        try:
            key = bytes.fromhex(key_hex)
            dec_file = crypto.decrypt_file(filepath, key)
            
            if dec_file:
                success(f"File decrypted to: {dec_file}")
        except Exception as e:
            error(f"Decryption failed: {e}")


if __name__ == "__main__":
    interactive_mode()
