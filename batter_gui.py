import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import logging
import threading
import queue
from datetime import datetime
import time

# Import core logic
from batter_V2 import SmartBattery, FileHandler, fetch_public_api_data

class TextHandler(logging.Handler):
    """Custom logging handler that sends messages to a Tkinter Text widget via a queue."""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        msg = self.format(record)
        self.log_queue.put(msg)

class BatteryGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🔋 Smart Battery Control Panel")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        # Initialize Battery
        self.battery = SmartBattery(initial_level=50)
        
        # Logging Setup
        self.log_queue = queue.Queue()
        self.setup_logging()
        
        self.setup_ui()
        self.update_log_loop()
        
    def setup_logging(self):
        # Add handler to the batter_V2 logger
        logger = logging.getLogger('batter_V2')
        handler = TextHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
    def setup_ui(self):
        # Styles
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 10))
        style.configure("TLabel", font=("Helvetica", 11))
        
        # --- Status Frame ---
        status_frame = ttk.LabelFrame(self.root, text="Battery Status", padding=15)
        status_frame.pack(fill="x", padx=15, pady=10)
        
        self.level_var = tk.StringVar(value=f"{self.battery.get_status()}%")
        
        # Progress Bar
        self.progress = ttk.Progressbar(status_frame, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=5)
        self.progress["value"] = self.battery.get_status()
        
        # Percentage Label
        self.lbl_percent = ttk.Label(status_frame, textvariable=self.level_var, font=("Helvetica", 16, "bold"))
        self.lbl_percent.pack(pady=5)
        
        # --- Controls Frame ---
        ctrl_frame = ttk.LabelFrame(self.root, text="Controls", padding=15)
        ctrl_frame.pack(fill="x", padx=15, pady=5)
        
        btn_grid = ttk.Frame(ctrl_frame)
        btn_grid.pack()
        
        ttk.Button(btn_grid, text="⚡ Charge", command=self.charge).grid(row=0, column=0, padx=10, pady=5)
        ttk.Button(btn_grid, text="⬇️ Discharge", command=self.discharge).grid(row=0, column=1, padx=10, pady=5)
        ttk.Button(btn_grid, text="📡 Fetch Data", command=self.fetch_data).grid(row=0, column=2, padx=10, pady=5)
        ttk.Button(btn_grid, text="💾 Save Log", command=self.save_log).grid(row=0, column=3, padx=10, pady=5)
        
        # --- Log Frame ---
        log_frame = ttk.LabelFrame(self.root, text="Activity Log", padding=10)
        log_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=10, state="disabled", font=("Consolas", 9))
        self.log_area.pack(fill="both", expand=True)
        
    def update_ui(self):
        level = self.battery.get_status()
        self.level_var.set(f"{level}%")
        self.progress["value"] = level
        
        # Color change based on level (simulated by style if needed, but basic bar is fine)
        
    def charge(self):
        msg = self.battery.attempt_charge()
        self.update_ui()
        
    def discharge(self):
        msg = self.battery.attempt_discharge()
        self.update_ui()
        
    def fetch_data(self):
        def _fetch():
            url = "https://jsonplaceholder.typicode.com/posts/1"
            data = fetch_public_api_data(url)
            if data:
                self.log_queue.put(f"Title: {data.get('title')}")
        
        threading.Thread(target=_fetch, daemon=True).start()
        
    def save_log(self):
        # Save a dummy log for demonstration
        filename = "gui_battery_log.csv"
        header = ["timestamp", "level", "note"]
        data = [
            [datetime.now().strftime("%H:%M:%S"), self.battery.get_status(), "GUI Snapshot"]
        ]
        FileHandler.write_csv(filename, header, data)
        
    def update_log_loop(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_area.config(state="normal")
                self.log_area.insert("end", msg + "\n")
                self.log_area.see("end")
                self.log_area.config(state="disabled")
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.update_log_loop)

if __name__ == "__main__":
    root = tk.Tk()
    app = BatteryGUI(root)
    root.mainloop()
