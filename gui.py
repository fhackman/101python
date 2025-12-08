# wifi_tool/gui.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
from typing import List
from core import WifiConnectionManager, AuditLogger


class WifiToolGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🔐 Professional Wi-Fi Audit Tool v2.0")
        self.root.geometry("650x500")
        self.root.resizable(False, False)
        self.manager = WifiConnectionManager()
        AuditLogger.tool_start("GUI")
        self.setup_ui()
        self.show_legal_notice()

    def show_legal_notice(self):
        msg = (
            "⚠️ LEGAL & ETHICAL NOTICE\n\n"
            "This tool must be used ONLY on networks you own\n"
            "or have explicit written authorization to test.\n\n"
            "Unauthorized access violates:\n"
            "• Thailand Computer Crime Act B.E. 2550\n"
            "• GDPR / PDPA (if personal data processed)\n"
            "• ISO/IEC 27001:2022 A.12.4 (Audit)\n\n"
            "Audit logs are immutable and may be used as evidence.\n"
            "By proceeding, you accept full legal responsibility."
        )
        messagebox.showwarning("Legal Notice", msg)

    def setup_ui(self):
        # Vault Frame
        vault_frame = ttk.LabelFrame(self.root, text="🔐 Password Vault", padding=10)
        vault_frame.pack(fill="x", padx=20, pady=(10, 5))
        
        self.vault_status = tk.StringVar(value="🔒 Vault Locked")
        ttk.Label(vault_frame, textvariable=self.vault_status).pack(side="left", padx=(0, 10))
        self.unlock_btn = ttk.Button(vault_frame, text="🔑 Unlock Vault", command=self.unlock_vault)
        self.unlock_btn.pack(side="right")

        # Interface Frame
        iface_frame = ttk.LabelFrame(self.root, text="📡 Wi-Fi Interface", padding=10)
        iface_frame.pack(fill="x", padx=20, pady=5)
        
        self.iface_var = tk.StringVar()
        self.iface_combo = ttk.Combobox(iface_frame, textvariable=self.iface_var, state="readonly", width=55)
        self.iface_combo.pack(pady=5)
        self.iface_combo.bind("<<ComboboxSelected>>", self.on_iface_select)

        # SSID Frame
        ssid_frame = ttk.LabelFrame(self.root, text="📶 Networks", padding=10)
        ssid_frame.pack(fill="x", padx=20, pady=5)
        
        self.scan_btn = ttk.Button(ssid_frame, text="🔍 Scan", command=self.scan_networks)
        self.scan_btn.pack(pady=5)
        
        self.ssid_var = tk.StringVar()
        self.ssid_combo = ttk.Combobox(ssid_frame, textvariable=self.ssid_var, state="disabled", width=55)
        self.ssid_combo.pack(pady=5)
        self.ssid_combo.bind("<<ComboboxSelected>>", self.on_ssid_select)

        # Audit Button
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="📋 View Audit Log", command=self.view_audit).pack()

        # Status Bar
        self.status_var = tk.StringVar(value="Ready. Select interface and unlock vault to begin.")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
        status_bar.pack(side="bottom", fill="x")

        # Populate interfaces
        interfaces = self.manager.get_interface_names()
        if not interfaces:
            messagebox.showerror("Error", "❌ No Wi-Fi interfaces found.")
            self.root.destroy()
            return
        self.iface_combo["values"] = interfaces
        self.iface_combo.set("– Select Interface –")

    def unlock_vault(self):
        passphrase = simpledialog.askstring("Vault Unlock", "Enter vault passphrase:", show="•")
        if not passphrase:
            return
        if self.manager.unlock_vault(passphrase):
            self.vault_status.set("🔓 Vault Unlocked")
            self.unlock_btn.config(state="disabled")
            self.status_var.set("✅ Vault unlocked. Ready to use passwords.")
        else:
            messagebox.showerror("Error", "❌ Incorrect passphrase or vault not initialized.")
            self.status_var.set("🔒 Vault remains locked.")

    def on_iface_select(self, event=None):
        self.ssid_combo.set("")
        self.ssid_combo.config(state="disabled")
        self.status_var.set("✅ Interface selected. Click 'Scan' to find networks.")

    def scan_networks(self):
        idx = self.iface_combo.current()
        if idx < 0:
            self.status_var.set("⚠️ Please select an interface first.")
            return
        self.status_var.set("🔄 Scanning... (up to 5 sec)")
        self.scan_btn.config(state="disabled")
        threading.Thread(target=self._scan_thread, args=(idx,), daemon=True).start()

    def _scan_thread(self, idx: int):
        ssids = self.manager.scan_blocking(idx)
        self.root.after(0, lambda: self._scan_done(ssids))

    def _scan_done(self, ssids: List[str]):
        self.scan_btn.config(state="normal")
        if ssids:
            self.ssid_combo["values"] = ssids
            self.ssid_combo.set("– Select Network –")
            self.ssid_combo.config(state="readonly")
            self.status_var.set(f"✅ Found {len(ssids)} networks.")
        else:
            self.ssid_combo.config(state="disabled")
            self.status_var.set("⚠️ No networks found. Try again.")

    def on_ssid_select(self, event=None):
        ssid = self.ssid_var.get().strip()
        if not ssid or ssid == "– Select Network –":
            return
        idx = self.iface_combo.current()
        if idx < 0:
            messagebox.showwarning("Warning", "Please select an interface.")
            return

        AuditLogger.connection_attempt(
            ssid=ssid,
            interface=self.iface_combo.get(),
            method="BRUTEFORCE" if self.manager.is_vault_unlocked() else "OPEN_ONLY"
        )

        self.status_var.set(f"🔗 Connecting to '{ssid}'...")
        self.scan_btn.config(state="disabled")
        self.iface_combo.config(state="disabled")
        self.ssid_combo.config(state="disabled")
        threading.Thread(target=self._connect_thread, args=(idx, ssid), daemon=True).start()

    def _connect_thread(self, idx: int, ssid: str):
        success, password = self.manager.connect(idx, ssid)
        pwd_len = len(password) if password else 0
        AuditLogger.connection_result(ssid, success, pwd_len)
        self.root.after(0, lambda: self._connect_done(ssid, success, pwd_len))

    def _connect_done(self, ssid: str, success: bool, pwd_len: int):
        self.scan_btn.config(state="normal")
        self.iface_combo.config(state="readonly")
        self.ssid_combo.config(state="readonly")
        if success:
            msg = f"✅ Connected to '{ssid}'"
            if pwd_len > 0:
                msg += f"\n🔑 Password length: {pwd_len} chars (redacted)"
            messagebox.showinfo("Success", msg)
            self.status_var.set(f"🟢 Connected to '{ssid}'")
        else:
            msg = f"❌ Failed to connect to '{ssid}'."
            if not self.manager.is_vault_unlocked():
                msg += "\n💡 Vault is locked — passwords not used."
            messagebox.showerror("Failed", msg)
            self.status_var.set("🔴 Connection failed.")

    def view_audit(self):
        try:
            if not AUDIT_LOG_PATH.exists():
                messagebox.showinfo("Audit Log", "No audit log found.")
                return
            lines = AUDIT_LOG_PATH.read_text(encoding="utf-8").strip().split("\n")
            if not lines or lines == [""]:
                messagebox.showinfo("Audit Log", "Audit log is empty.")
                return
            # Show last 20 entries in new window
            top = tk.Toplevel(self.root)
            top.title("📋 Audit Log (Last 20 Entries)")
            top.geometry("800x500")
            text = tk.Text(top, wrap="none", font=("Consolas", 10))
            scroll_y = ttk.Scrollbar(top, orient="vertical", command=text.yview)
            scroll_x = ttk.Scrollbar(top, orient="horizontal", command=text.xview)
            text.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
            text.pack(side="left", fill="both", expand=True)
            scroll_y.pack(side="right", fill="y")
            scroll_x.pack(side="bottom", fill="x")
            for line in lines[-20:]:
                text.insert("end", line + "\n")
            text.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read audit log:\n{e}")