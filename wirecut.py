import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pywifi
from pywifi import const
import threading
import time
import csv

class WireCutApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WireCut - Wi-Fi Scanner")
        self.root.geometry("700x450")
        
        self.wifi = pywifi.PyWiFi()
        self.interfaces = self.wifi.interfaces()
        self.selected_interface = None
        self.scanned_networks = []

        self.setup_ui()

    def setup_ui(self):
        # --- Status Bar ---
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # --- Toolbar ---
        toolbar = tk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Interface Selection
        tk.Label(toolbar, text="Interface:").pack(side=tk.LEFT, padx=2)
        
        if self.interfaces:
            iface_names = [i.name() for i in self.interfaces]
            self.combo_iface = ttk.Combobox(toolbar, values=iface_names, state="readonly", width=30)
            self.combo_iface.pack(side=tk.LEFT, padx=5)
            self.combo_iface.current(0)
            self.combo_iface.bind("<<ComboboxSelected>>", self.on_iface_change)
            self.on_iface_change(None) # Set initial interface
        else:
            tk.Label(toolbar, text="No Interfaces Found", fg="red").pack(side=tk.LEFT, padx=5)
            self.combo_iface = None

        self.btn_scan = tk.Button(toolbar, text="Scan Networks", command=self.start_scan, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.btn_scan.pack(side=tk.LEFT, padx=15)

        self.btn_save = tk.Button(toolbar, text="Save to File", command=self.save_results, bg="#2196F3", fg="white", font=("Arial", 10, "bold"))
        self.btn_save.pack(side=tk.LEFT, padx=5)

        self.btn_exit = tk.Button(toolbar, text="Exit", command=self.root.quit, bg="#f44336", fg="white", font=("Arial", 10, "bold"))
        self.btn_exit.pack(side=tk.RIGHT, padx=5)

        # --- Network Table ---
        columns = ("ssid", "bssid", "signal", "security")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings")
        
        self.tree.heading("ssid", text="SSID")
        self.tree.heading("bssid", text="BSSID")
        self.tree.heading("signal", text="Signal")
        self.tree.heading("security", text="Security")
        
        self.tree.column("ssid", width=200)
        self.tree.column("bssid", width=150)
        self.tree.column("signal", width=80)
        self.tree.column("security", width=100)

        scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def on_iface_change(self, event):
        if self.combo_iface:
            idx = self.combo_iface.current()
            if idx >= 0:
                self.selected_interface = self.interfaces[idx]
                self.status_var.set(f"Selected Interface: {self.selected_interface.name()}")

    def start_scan(self):
        if not self.selected_interface:
            messagebox.showerror("Error", "No interface selected.")
            return

        self.btn_scan.config(state="disabled")
        self.status_var.set(f"Scanning on {self.selected_interface.name()}...")
        self.tree.delete(*self.tree.get_children())
        threading.Thread(target=self.scan_networks, daemon=True).start()

    def scan_networks(self):
        try:
            iface = self.selected_interface
            iface.scan()
            time.sleep(5)
            
            results = iface.scan_results()
            self.scanned_networks = []
            seen_bssids = set()

            for profile in results:
                if profile.bssid in seen_bssids:
                    continue
                seen_bssids.add(profile.bssid)
                
                security = "Open"
                if const.AKM_TYPE_WPA in profile.akm:
                    security = "WPA"
                elif const.AKM_TYPE_WPA2 in profile.akm:
                    security = "WPA2"
                elif const.AKM_TYPE_WPA2PSK in profile.akm:
                    security = "WPA2-PSK"
                
                network = {
                    "ssid": profile.ssid or "<Hidden>",
                    "bssid": profile.bssid,
                    "signal": profile.signal,
                    "security": security
                }
                self.scanned_networks.append(network)

            # Sort by signal
            self.scanned_networks.sort(key=lambda x: x["signal"], reverse=True)

            self.root.after(0, self.update_table)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Scan failed: {e}"))
            self.root.after(0, self.reset_ui)

    def update_table(self):
        for net in self.scanned_networks:
            self.tree.insert("", tk.END, values=(net["ssid"], net["bssid"], net["signal"], net["security"]))
        
        self.status_var.set(f"Scan complete. Found {len(self.scanned_networks)} networks.")
        self.btn_scan.config(state="normal")

    def reset_ui(self):
        self.status_var.set("Ready")
        self.btn_scan.config(state="normal")

    def save_results(self):
        if not self.scanned_networks:
            messagebox.showwarning("Warning", "No networks to save. Scan first.")
            return

        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=(("CSV Files", "*.csv"), ("All Files", "*.*")))
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["SSID", "BSSID", "Signal", "Security"])
                    for net in self.scanned_networks:
                        writer.writerow([net["ssid"], net["bssid"], net["signal"], net["security"]])
                messagebox.showinfo("Success", f"Saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = WireCutApp(root)
    root.mainloop()