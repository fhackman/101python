# wifi_tool/crypto.py
from typing import List

class SecureVault:
    def __init__(self):
        self._is_unlocked = False
        # Mock data for demonstration
        self._mock_passwords = ["12345678", "password", "admin123"]

    def unlock(self, passphrase: str) -> bool:
        """
        Unlock the vault with a passphrase.
        For this basic implementation, any non-empty passphrase unlocks it.
        """
        if passphrase:
            self._is_unlocked = True
            return True
        return False

    def get_passwords(self) -> List[str]:
        """
        Retrieve passwords if the vault is unlocked.
        """
        if self._is_unlocked:
            return self._mock_passwords
        return []
