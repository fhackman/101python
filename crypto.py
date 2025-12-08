# wifi_tool/crypto.py
import os
import sys
from pathlib import Path
from typing import Optional, List
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64


class SecureVault:
    """AES-256-GCM encrypted password vault — zero plaintext at rest"""

    def __init__(self, vault_path: Path = Path("output.txt.enc"), key_path: Path = Path("vault.key")):
        self.vault_path = vault_path
        self.key_path = key_path
        self._key: Optional[bytes] = None

    def derive_key(self, passphrase: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600_000,
            backend=default_backend()
        )
        return kdf.derive(passphrase.encode())

    def initialize_vault(self, passphrase: str) -> bool:
        """Create new vault + key file (first-time setup)"""
        if self.vault_path.exists() or self.key_path.exists():
            return False  # already exists

        salt = os.urandom(16)
        key = self.derive_key(passphrase, salt)
        # Save salt + key (key encrypted by itself? no — key file = salt + encrypted key)
        # Simpler: key file = salt only; key derived at runtime
        self.key_path.write_bytes(salt)
        self.vault_path.write_bytes(b"")  # empty vault
        return True

    def unlock(self, passphrase: str) -> bool:
        """Unlock vault — derive key from passphrase + salt"""
        if not self.key_path.exists():
            return False
        salt = self.key_path.read_bytes()
        self._key = self.derive_key(passphrase, salt)
        return True

    def is_unlocked(self) -> bool:
        return self._key is not None

    def add_passwords(self, passwords: List[str]) -> None:
        """Append passwords to encrypted vault (no overwrite)"""
        if not self._key:
            raise ValueError("Vault not unlocked")

        # Read existing (decrypt)
        existing = self._load_decrypted() if self.vault_path.exists() else []

        # Deduplicate & merge
        new_set = set(existing) | set(p.strip() for p in passwords if p.strip())
        new_list = sorted(new_set)

        # Re-encrypt & write
        self._save_encrypted(new_list)

    def get_passwords(self) -> List[str]:
        """Return decrypted password list"""
        if not self._key:
            raise ValueError("Vault not unlocked")
        return self._load_decrypted()

    def _load_decrypted(self) -> List[str]:
        if not self.vault_path.exists() or self.vault_path.stat().st_size == 0:
            return []

        data = self.vault_path.read_bytes()
        if len(data) < 12 + 16:  # nonce (12) + tag (16) + ciphertext
            return []

        nonce = data[:12]
        tag = data[12:28]
        ciphertext = data[28:]

        decryptor = Cipher(
            algorithms.AES(self._key),
            modes.GCM(nonce, tag),
            backend=default_backend()
        ).decryptor()

        try:
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            return plaintext.decode("utf-8").strip().splitlines()
        except Exception:
            # Corrupt/invalid vault
            return []

    def _save_encrypted(self, passwords: List[str]) -> None:
        if not self._key:
            raise ValueError("Vault not unlocked")

        plaintext = "\n".join(passwords).encode("utf-8")

        nonce = os.urandom(12)
        encryptor = Cipher(
            algorithms.AES(self._key),
            modes.GCM(nonce),
            backend=default_backend()
        ).encryptor()

        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        tag = encryptor.tag

        self.vault_path.write_bytes(nonce + tag + ciphertext)