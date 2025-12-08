# wifi_tool/core.py
import sys
import json
import socket
import getpass
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import pywifi
from pywifi import const
from crypto import SecureVault


AUDIT_LOG_PATH = Path("audit.log")


class AuditLogger:
    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _get_user() -> str:
        try:
            return getpass.getuser()
        except:
            return "unknown"

    @staticmethod
    def _get_host() -> str:
        try:
            return socket.gethostname()
        except:
            return "unknown"

    @classmethod
    def _write_entry(cls, entry: Dict[str, Any]) -> None:
        try:
            with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[AUDIT FAILURE] {e}", file=sys.stderr)

    @classmethod
    def log(cls, event_type: str, details: Dict[str, Any]) -> None:
        entry = {
            "timestamp": cls._timestamp(),
            "event_type": event_type.upper(),
            "user": cls._get_user(),
            "host": cls._get_host(),
            "details": details
        }
        cls._write_entry(entry)

    @classmethod
    def tool_start(cls, mode: str):
        cls.log("TOOL_START", {"mode": mode})

    @classmethod
    def connection_attempt(cls, ssid: str, interface: str, method: str):
        cls.log("CONNECTION_ATTEMPT", {
            "ssid": ssid,
            "interface": interface,
            "method": method
        })

    @classmethod
    def connection_result(cls, ssid: str, success: bool, password_length: int = 0):
        cls.log("CONNECTION_RESULT", {
            "ssid": ssid,
            "success": success,
            "password_length": password_length
        })

    @classmethod
    def vault_unlock_attempt(cls, success: bool):
        cls.log("VAULT_UNLOCK", {"success": success})

    @classmethod
    def warning(cls, message: str):
        cls.log("WARNING", {"message": message})


class WifiConnectionManager:
    def __init__(self):
        self.wifi = pywifi.PyWiFi()
        self.interfaces = self.wifi.interfaces()
        self.vault = SecureVault()
        self._unlocked = False

    def get_interface_names(self) -> List[str]:
        return [iface.name() for iface in self.interfaces]

    def scan_blocking(self, interface_index: int) -> List[str]:
        if not self.interfaces or interface_index < 0 or interface_index >= len(self.interfaces):
            return []
        iface = self.interfaces[interface_index]
        iface.scan()
        for _ in range(10):
            time.sleep(0.5)
            results = iface.scan_results()
            if results:
                break
        else:
            results = iface.scan_results()
        seen = set()
        ssids = []
        for res in results:
            ssid = res.ssid.strip()
            if ssid and ssid not in seen:
                seen.add(ssid)
                ssids.append(ssid)
        return ssids

    def unlock_vault(self, passphrase: str) -> bool:
        success = self.vault.unlock(passphrase)
        self._unlocked = success
        AuditLogger.vault_unlock_attempt(success)
        return success

    def is_vault_unlocked(self) -> bool:
        return self._unlocked

    def get_passwords(self) -> List[str]:
        if not self._unlocked:
            return []
        return self.vault.get_passwords()

    def connect_to_open(self, iface, ssid: str) -> bool:
        try:
            profile = pywifi.Profile()
            profile.ssid = ssid
            profile.auth = const.AUTH_ALG_OPEN
            profile.akm.append(const.AKM_TYPE_NONE)
            iface.remove_all_network_profiles()
            tmp_profile = iface.add_network_profile(profile)
            iface.connect(tmp_profile)
            for _ in range(8):
                time.sleep(0.5)
                if iface.status() == const.IFACE_CONNECTED:
                    return True
            return False
        except Exception:
            return False

    def connect_with_passwords(self, iface, ssid: str, passwords: List[str]) -> Optional[str]:
        for pwd in passwords:
            if not pwd:
                continue
            try:
                profile = pywifi.Profile()
                profile.ssid = ssid
                profile.auth = const.AUTH_ALG_OPEN
                profile.akm.append(const.AKM_TYPE_WPA2PSK)
                profile.cipher = const.CIPHER_TYPE_CCMP
                profile.key = pwd
                iface.remove_all_network_profiles()
                tmp_profile = iface.add_network_profile(profile)
                iface.connect(tmp_profile)
                for _ in range(8):
                    time.sleep(0.5)
                    if iface.status() == const.IFACE_CONNECTED:
                        return pwd
            except Exception:
                continue
        return None

    def connect(self, interface_index: int, ssid: str) -> Tuple[bool, str]:
        if not self.interfaces or interface_index < 0 or interface_index >= len(self.interfaces):
            return False, ""
        iface = self.interfaces[interface_index]
        ssid = ssid.strip()
        if not ssid:
            return False, ""

        # Try open
        if self.connect_to_open(iface, ssid):
            return True, ""

        # Try vault (if unlocked)
        if self._unlocked:
            passwords = self.get_passwords()
            pwd = self.connect_with_passwords(iface, ssid, passwords)
            return (pwd is not None), (pwd or "")
        else:
            return False, ""