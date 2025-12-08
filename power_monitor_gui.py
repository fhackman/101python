import tkinter as tk
from tkinter import ttk
import psutil
import time
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import pandas as pd
from collections import deque
import threading

# Import FileHandler from batter_V2
try:
    from batter_V2 import FileHandler
except ImportError:
    # Fallback if batter_V2 is not found or has issues
    import csv
    from pathlib import Path
    class FileHandler:
        @staticmethod
        def write_csv(filename, header, data):
            file_path = Path(filename)
            mode = 'a' if file_path.exists() else 'w'
            with file_path.open(mode, newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if mode == 'w':
                    writer.writerow(header)
                writer.writerows(data)

class PowerMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Power Monitor Pro")
        self.root.geometry("900x700")
        self.root.configure(bg="#2E2E2E")
        
        # Data storage
        self.history_len = 60 # Keep last 60 points (approx 1 hour if 1 min interval, but we update faster for demo)
        self.times = deque(maxlen=self.history_len)
        self.levels = deque(maxlen=self.history_len)
        self.log_file = "realtime_battery_log.csv"
        
        # Initialize log file
        FileHandler.write_csv(self.log_file, ["timestamp", "percent", "plugged", "status"], [])
        
        self.setup_styles()
        self.setup_ui()
        self.update_loop()
        
    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Dark theme colors
        bg_color = "#2E2E2E"
        fg_color = "#FFFFFF"
        accent_color = "#00ADB5"
        
        self.style.configure("TFrame", background=bg_color)
        self.style.configure("TLabel", background=bg_color, foreground=fg_color, font=("Segoe UI", 12))
        self.style.configure("Header.TLabel", font=("Segoe UI", 24, "bold"), foreground=accent_color)
        self.style.configure("Big.TLabel", font=("Segoe UI", 48, "bold"), foreground="#EEEEEE")
        self.style.configure("Status.TLabel", font=("Segoe UI", 14), foreground="#AAAAAA")
        
    def setup_ui(self):
        # Main Container
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Header
        header_lbl = ttk.Label(main_frame, text="Realtime Power Monitor", style="Header.TLabel")
        header_lbl.pack(pady=(0, 20))
        
        # Top Section: Gauge and Stats
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill="x", pady=10)
        
        # Left: Visual Gauge (Canvas)
        self.canvas = tk.Canvas(top_frame, width=200, height=100, bg="#2E2E2E", highlightthickness=0)
        self.canvas.pack(side="left", padx=20)
        self.draw_battery_gauge(0) # Initial draw
        
        # Right: Stats
        stats_frame = ttk.Frame(top_frame)
        stats_frame.pack(side="left", fill="both", expand=True, padx=20)
        
        self.percent_lbl = ttk.Label(stats_frame, text="--%", style="Big.TLabel")
        self.percent_lbl.pack(anchor="w")
        
        self.status_lbl = ttk.Label(stats_frame, text="Status: --", style="Status.TLabel")
        self.status_lbl.pack(anchor="w")
        
        self.time_lbl = ttk.Label(stats_frame, text="Time Left: --", style="Status.TLabel")
        self.time_lbl.pack(anchor="w")
        
        self.action_lbl = ttk.Label(stats_frame, text="Smart Action: --", style="Status.TLabel", foreground="#FFD700")
        self.action_lbl.pack(anchor="w", pady=(10, 0))
        
        # Bottom Section: Chart
        chart_frame = ttk.Frame(main_frame)
        chart_frame.pack(fill="both", expand=True, pady=20)
        
        # Matplotlib Figure
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots(figsize=(8, 4), dpi=100)
        self.fig.patch.set_facecolor('#2E2E2E')
        self.ax.set_facecolor('#2E2E2E')
        
        self.canvas_chart = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas_chart.draw()
        self.canvas_chart.get_tk_widget().pack(fill="both", expand=True)
        
    def draw_battery_gauge(self, percent):
        self.canvas.delete("all")
        
        # Battery Outline
        w, h = 160, 80
        x, y = 20, 10
        tip_w = 10
        
        # Body
        self.canvas.create_rectangle(x, y, x+w, y+h, outline="#FFFFFF", width=3)
        # Tip
        self.canvas.create_rectangle(x+w, y+h//3, x+w+tip_w, y+2*h//3, fill="#FFFFFF")
        
        # Fill
        fill_width = (w - 6) * (percent / 100)
        color = "#00FF00" if percent > 50 else "#FFFF00" if percent > 20 else "#FF0000"
        
        if percent > 0:
            self.canvas.create_rectangle(x+3, y+3, x+3+fill_width, y+h-3, fill=color, outline="")
            
        # Text inside
        self.canvas.create_text(x+w//2, y+h//2, text=f"{percent}%", fill="#000000" if percent > 50 else "#FFFFFF", font=("Arial", 20, "bold"))

    def update_loop(self):
        try:
            battery = psutil.sensors_battery()
            
            if battery:
                percent = battery.percent
                plugged = battery.power_plugged
                secsleft = battery.secsleft
                
                # Update UI
                self.percent_lbl.config(text=f"{percent}%")
                
                status_text = "⚡ Charging" if plugged else "🔋 Discharging"
                if percent == 100 and plugged:
                    status_text = "✅ Fully Charged"
                self.status_lbl.config(text=status_text)
                
                if secsleft == psutil.POWER_TIME_UNLIMITED:
                    time_str = "Unlimited (Plugged In)"
                elif secsleft == psutil.POWER_TIME_UNKNOWN:
                    time_str = "Calculating..."
                else:
                    hours = secsleft // 3600
                    mins = (secsleft % 3600) // 60
                    time_str = f"{hours}h {mins}m remaining"
                self.time_lbl.config(text=time_str)
                
                # Smart Logic: Auto Recharge/Discharge
                smart_action = "Monitoring..."
                action_color = "#AAAAAA"
                
                if percent <= 60 and not plugged:
                    smart_action = "⚠️ AUTO RECHARGE TRIGGERED (Plug In)"
                    action_color = "#FF5555" # Red alert
                elif percent >= 100 and plugged:
                    smart_action = "⚠️ AUTO DISCHARGE TRIGGERED (Unplug)"
                    action_color = "#FF5555" # Red alert
                elif plugged:
                    smart_action = "Charging in progress..."
                    action_color = "#00FF00"
                else:
                    smart_action = "Discharging (Optimal Range)"
                    action_color = "#00ADB5"
                    
                self.action_lbl.config(text=smart_action, foreground=action_color)
                
                self.draw_battery_gauge(percent)
                
                # Update Data
                now = datetime.now()
                self.times.append(now)
                self.levels.append(percent)
                
                # Log to file
                FileHandler.write_csv(self.log_file, [], [[now.strftime("%Y-%m-%d %H:%M:%S"), percent, plugged, status_text]])
                
                # Update Chart
                self.update_chart()
                
        except Exception as e:
            print(f"Error: {e}")
            
        # Schedule next update (every 2 seconds)
        self.root.after(2000, self.update_loop)
        
    def update_chart(self):
        if not self.times:
            return
            
        self.ax.clear()
        self.ax.plot(self.times, self.levels, color='#00ADB5', linewidth=2, marker='o', markersize=4)
        
        self.ax.set_title("Battery Level History", color='white', fontsize=10)
        self.ax.set_ylim(0, 105)
        self.ax.grid(True, color='#444444', linestyle='--', alpha=0.5)
        
        # Format dates
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.fig.autofmt_xdate()
        
        # Style ticks
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        
        self.canvas_chart.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = PowerMonitorGUI(root)
    root.mainloop()
