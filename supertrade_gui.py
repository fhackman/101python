import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import time
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import pandas as pd
import ast
import MetaTrader5 as mt5

# Import the bot
from supertrade import SuperpointTradingBot, CONFIG

class TradingBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Superpoint Trading Bot")
        self.root.geometry("1000x850")
        
        self.bot = None
        self.bot_thread = None
        self.log_queue = queue.Queue()
        self.last_chart_update_time = None
        self.last_data_shape = None
        
        # Timeframe mapping
        self.timeframe_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
            "W1": mt5.TIMEFRAME_W1,
            "MN": mt5.TIMEFRAME_MN1
        }
        
        self.setup_ui()
        self.update_log_from_queue()
        self.update_chart_loop()
        
    def setup_ui(self):
        # Top Control Panel
        control_frame = ttk.LabelFrame(self.root, text="Controls", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side="left", fill="y")
        
        self.start_btn = ttk.Button(btn_frame, text="Start Bot", command=self.start_bot)
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="Stop Bot", command=self.stop_bot, state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        # Settings
        settings_frame = ttk.Frame(control_frame)
        settings_frame.pack(side="left", padx=20, fill="y")
        
        # Symbol Selection
        ttk.Label(settings_frame, text="Symbol:").pack(side="left", padx=2)
        self.symbol_var = tk.StringVar(value=CONFIG['SYMBOL'])
        self.symbol_combo = ttk.Combobox(settings_frame, textvariable=self.symbol_var, width=10, state="readonly")
        self.symbol_combo['values'] = ['XAUUSD.m', 'EURUSD.m', 'NVIDIA.m', 'AMD.m', 'TESLA.m']
        self.symbol_combo.pack(side="left", padx=5)
        
        # Timeframe Selection
        ttk.Label(settings_frame, text="TF:").pack(side="left", padx=2)
        self.tf_var = tk.StringVar(value="H4") # Default
        self.tf_combo = ttk.Combobox(settings_frame, textvariable=self.tf_var, width=5, state="readonly")
        self.tf_combo['values'] = list(self.timeframe_map.keys())
        self.tf_combo.pack(side="left", padx=5)
        
        # Bot Interval
        ttk.Label(settings_frame, text="Interval (s):").pack(side="left", padx=2)
        self.bot_interval_var = tk.IntVar(value=CONFIG['POLL_INTERVAL'])
        self.bot_interval_spin = ttk.Spinbox(settings_frame, from_=1, to=3600, width=5, 
                                           textvariable=self.bot_interval_var, command=self.update_bot_config)
        self.bot_interval_spin.pack(side="left", padx=5)
        self.bot_interval_spin.bind('<Return>', lambda e: self.update_bot_config())
        self.bot_interval_spin.bind('<FocusOut>', lambda e: self.update_bot_config())
        
        # Chart Refresh
        ttk.Label(settings_frame, text="Chart (s):").pack(side="left", padx=2)
        self.chart_refresh_var = tk.IntVar(value=5)
        self.chart_refresh_spin = ttk.Spinbox(settings_frame, from_=1, to=60, width=5, 
                                            textvariable=self.chart_refresh_var)
        self.chart_refresh_spin.pack(side="left", padx=5)

        self.status_lbl = ttk.Label(control_frame, text="Status: Stopped", font=("Arial", 10, "bold"))
        self.status_lbl.pack(side="right", padx=20)

        # Manual Trade Panel
        manual_frame = ttk.LabelFrame(self.root, text="Manual Trade", padding=10)
        manual_frame.pack(fill="x", padx=10, pady=5)
        
        # Volume
        ttk.Label(manual_frame, text="Vol:").pack(side="left", padx=2)
        self.vol_var = tk.DoubleVar(value=CONFIG['MANUAL_PARAMS']['volume'])
        self.vol_spin = ttk.Spinbox(manual_frame, from_=0.01, to=10.0, increment=0.01, width=5, textvariable=self.vol_var)
        self.vol_spin.pack(side="left", padx=5)
        
        # TP Points
        ttk.Label(manual_frame, text="TP (pts):").pack(side="left", padx=2)
        self.tp_var = tk.IntVar(value=CONFIG['MANUAL_PARAMS']['tp_points'])
        self.tp_entry = ttk.Entry(manual_frame, textvariable=self.tp_var, width=6)
        self.tp_entry.pack(side="left", padx=5)
        
        # SL Points
        ttk.Label(manual_frame, text="SL (pts):").pack(side="left", padx=2)
        self.sl_var = tk.IntVar(value=CONFIG['MANUAL_PARAMS']['sl_points'])
        self.sl_entry = ttk.Entry(manual_frame, textvariable=self.sl_var, width=6)
        self.sl_entry.pack(side="left", padx=5)
        
        # Buttons
        self.buy_btn = tk.Button(manual_frame, text="BUY", bg="green", fg="white", font=("Arial", 9, "bold"),
                               command=lambda: self.manual_trade_action(1))
        self.buy_btn.pack(side="left", padx=10)
        
        self.sell_btn = tk.Button(manual_frame, text="SELL", bg="red", fg="white", font=("Arial", 9, "bold"),
                                command=lambda: self.manual_trade_action(2))
        self.sell_btn.pack(side="left", padx=5)
        
        # Info Panel
        info_frame = ttk.LabelFrame(self.root, text="Market Info", padding=10)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        self.symbol_lbl = ttk.Label(info_frame, text=f"Symbol: {CONFIG['SYMBOL']}")
        self.symbol_lbl.pack(side="left", padx=10)
        
        self.price_lbl = ttk.Label(info_frame, text="Price: ---")
        self.price_lbl.pack(side="left", padx=10)
        
        self.signal_lbl = ttk.Label(info_frame, text="Last Signal: ---")
        self.signal_lbl.pack(side="left", padx=10)

        self.pattern_lbl = ttk.Label(info_frame, text="Patterns: ---", foreground="blue")
        self.pattern_lbl.pack(side="left", padx=10)
        
        # Chart Area
        chart_frame = ttk.LabelFrame(self.root, text="Price Chart", padding=10)
        chart_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.fig, self.ax = plt.subplots(figsize=(8, 4), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Log Area
        log_frame = ttk.LabelFrame(self.root, text="Logs", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state="disabled")
        self.log_text.pack(fill="both", expand=True)
        
    def log(self, message):
        self.log_queue.put(message)
        
    def update_bot_config(self):
        try:
            new_interval = self.bot_interval_var.get()
            if self.bot:
                self.bot.config['POLL_INTERVAL'] = new_interval
                # self.log(f"Updated bot poll interval to {new_interval}s") 
        except Exception:
            pass

    def update_log_from_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
                self.log_text.see("end")
                self.log_text.config(state="disabled")
                
                # Parse status messages to update labels
                if "Status:" in msg:
                    try:
                        # Extract dict string from log message
                        dict_str = msg.split("Status: ", 1)[1]
                        status = ast.literal_eval(dict_str)
                        self.price_lbl.config(text=f"Price: {status.get('price', '---')}")
                        self.signal_lbl.config(text=f"Signal: {status.get('signal', '---')} ({status.get('confidence', '0')}%)")
                        self.pattern_lbl.config(text=f"Patterns: {status.get('patterns', 'None')}")
                    except Exception as e:
                        print(f"Error parsing status: {e}")
                        pass
                        
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.update_log_from_queue)
            
    def update_chart_loop(self):
        refresh_rate = 5000 # Default
        try:
            refresh_rate = max(1000, self.chart_refresh_var.get() * 1000)
        except:
            pass

        if self.bot and self.bot.latest_data is not None:
            try:
                df = self.bot.latest_data
                
                # Optimization: Only redraw if data has changed
                current_shape = df.shape
                if self.last_data_shape != current_shape:
                    self.last_data_shape = current_shape
                    
                    self.ax.clear()
                    self.ax.plot(df.index, df['close'], label='Close Price', color='blue')
                    
                    # Format chart
                    self.ax.set_title(f"{CONFIG['SYMBOL']} Price History")
                    self.ax.set_xlabel("Time")
                    self.ax.set_ylabel("Price")
                    self.ax.legend()
                    self.ax.grid(True, alpha=0.3)
                    
                    # Format x-axis dates
                    self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                    self.fig.autofmt_xdate()
                    
                    self.canvas.draw()
            except Exception as e:
                print(f"Chart update error: {e}")
                
        self.root.after(refresh_rate, self.update_chart_loop)
        
    def toggle_controls(self, state):
        self.symbol_combo.config(state=state)
        self.tf_combo.config(state=state)
        
    def start_bot(self):
        if self.bot_thread and self.bot_thread.is_alive():
            return
            
        # Update config from UI before starting
        CONFIG['POLL_INTERVAL'] = self.bot_interval_var.get()
        CONFIG['SYMBOL'] = self.symbol_var.get()
        
        tf_str = self.tf_var.get()
        if tf_str in self.timeframe_map:
            CONFIG['TIMEFRAME'] = self.timeframe_map[tf_str]
            
        self.symbol_lbl.config(text=f"Symbol: {CONFIG['SYMBOL']}")
            
        self.bot = SuperpointTradingBot(CONFIG, log_callback=self.log)
        self.bot_thread = threading.Thread(target=self.bot.run, daemon=True)
        self.bot_thread.start()
        
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.toggle_controls("disabled")
        self.status_lbl.config(text="Status: Running", foreground="green")
        self.log(f"Bot started: {CONFIG['SYMBOL']} ({tf_str})")
        
    def manual_trade_action(self, signal):
        if not self.bot:
            self.log("Error: Bot is not running. Start bot first.")
            return
            
        try:
            vol = float(self.vol_var.get())
            tp = int(self.tp_var.get())
            sl = int(self.sl_var.get())
            
            # Run in thread to not block UI
            threading.Thread(target=self.bot.manual_trade, args=(signal, vol, sl, tp)).start()
            
        except ValueError:
            self.log("Error: Invalid manual trade parameters")

    def stop_bot(self):
        if self.bot:
            self.bot.stop()
            self.log("Stopping bot (waiting for loop to finish)...")
            
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.toggle_controls("readonly")
        self.status_lbl.config(text="Status: Stopped", foreground="red")

if __name__ == "__main__":
    root = tk.Tk()
    app = TradingBotGUI(root)
    root.mainloop()
