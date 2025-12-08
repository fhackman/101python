import MetaTrader5 as mt5
import pandas as pd
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue

# Display settings
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

class PAPatternScanner:
    def __init__(self, symbol="XAUUSD.m", timeframe=mt5.TIMEFRAME_H1):
        self.symbol = symbol
        self.timeframe = timeframe
        self.connected = False
        
    def connect(self):
        if not mt5.initialize():
            return False
        self.connected = True
        return True

    def disconnect(self):
        mt5.shutdown()
        self.connected = False

    def fetch_candles(self, n=100):
        if not self.connected:
            return None
            
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, n)
        if rates is None:
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s') + pd.Timedelta(hours=7)
        
        # Calculate basic candle properties
        df['body_top'] = df[['open', 'close']].max(axis=1)
        df['body_bottom'] = df[['open', 'close']].min(axis=1)
        df['body_size'] = df['body_top'] - df['body_bottom']
        df['upper_wick'] = df['high'] - df['body_top']
        df['lower_wick'] = df['body_bottom'] - df['low']
        df['is_bullish'] = df['close'] > df['open']
        df['is_bearish'] = df['close'] < df['open']
        
        return df

    # ==========================================
    # PATTERN DETECTION LOGIC
    # ==========================================

    def check_pat1_rejection(self, row):
        """
        PAT 1: Rejection (Hammer / Shooting Star)
        """
        # Buy (Hammer): Long lower wick, small upper wick
        if row['lower_wick'] > (2 * row['body_size']) and row['upper_wick'] < row['body_size']:
            return "BUY (Hammer)", "BUY", row['close']
            
        # Sell (Shooting Star): Long upper wick, small lower wick
        if row['upper_wick'] > (2 * row['body_size']) and row['lower_wick'] < row['body_size']:
            return "SELL (Shooting Star)", "SELL", row['close']
            
        return None, None, None

    def check_pat2_engulfing(self, curr, prev):
        """
        PAT 2: Engulfing
        """
        # Buy: Prev Bearish, Curr Bullish, Engulfs
        if prev['is_bearish'] and curr['is_bullish']:
            if curr['close'] > prev['open'] and curr['open'] < prev['close']:
                return "BUY (Engulfing)", "BUY", curr['close']
                
        # Sell: Prev Bullish, Curr Bearish, Engulfs
        if prev['is_bullish'] and curr['is_bearish']:
            if curr['close'] < prev['open'] and curr['open'] > prev['close']:
                return "SELL (Engulfing)", "SELL", curr['close']
                
        return None, None, None

    def check_pat3_1_piercing(self, curr, prev):
        """
        PAT 3-1: Piercing Line / Dark Cloud Cover
        """
        prev_midpoint = (prev['open'] + prev['close']) / 2
        
        # Buy (Piercing): Prev Bearish, Curr Bullish, opens low, closes above midpoint
        if prev['is_bearish'] and curr['is_bullish']:
            if curr['open'] < prev['close'] and curr['close'] > prev_midpoint:
                return "BUY (Piercing)", "BUY", curr['close']
                
        # Sell (Dark Cloud): Prev Bullish, Curr Bearish, opens high, closes below midpoint
        if prev['is_bullish'] and curr['is_bearish']:
            if curr['open'] > prev['close'] and curr['close'] < prev_midpoint:
                return "SELL (Dark Cloud)", "SELL", curr['close']
                
        return None, None, None

    def check_pat3_2_star(self, curr, prev, prev2):
        """
        PAT 3-2: Morning Star / Evening Star (3 candles)
        """
        # Buy (Morning Star): Bearish -> Small -> Bullish
        if prev2['is_bearish'] and prev2['body_size'] > prev['body_size'] * 2: 
            if prev['body_size'] < prev2['body_size'] * 0.3: 
                if curr['is_bullish'] and curr['close'] > (prev2['open'] + prev2['close'])/2: 
                    return "BUY (Morning Star)", "BUY", curr['close']
                    
        # Sell (Evening Star): Bullish -> Small -> Bearish
        if prev2['is_bullish'] and prev2['body_size'] > prev['body_size'] * 2: 
            if prev['body_size'] < prev2['body_size'] * 0.3: 
                if curr['is_bearish'] and curr['close'] < (prev2['open'] + prev2['close'])/2: 
                    return "SELL (Evening Star)", "SELL", curr['close']
                    
        return None, None, None

    def check_pat3_3_inside_breakout(self, curr, prev, prev2):
        """
        PAT 3-3: Inside Bar Breakout (Three Inside Up/Down)
        """
        is_inside = (prev['high'] < prev2['high']) and (prev['low'] > prev2['low'])
        
        if not is_inside:
            return None, None, None
            
        # Buy: Breakout above Mother High
        if curr['close'] > prev2['high']:
            return "BUY (Inside Bar Breakout)", "BUY", curr['close']
            
        # Sell: Breakout below Mother Low
        if curr['close'] < prev2['low']:
            return "SELL (Inside Bar Breakout)", "SELL", curr['close']
            
        return None, None, None

    def scan_once(self):
        """
        Performs a single scan and returns a list of found patterns.
        """
        df = self.fetch_candles()
        if df is None:
            return []

        found_patterns = []

        # Iterate through candles (need at least 3 for some patterns)
        # We scan the last few candles to be efficient, but enough to catch recent patterns
        # Let's scan the last 5 closed candles + current open candle
        start_idx = max(2, len(df) - 10) 
        
        for i in range(start_idx, len(df)):
            curr = df.iloc[i]
            prev = df.iloc[i-1]
            prev2 = df.iloc[i-2]
            
            timestamp = curr['time']
            
            # Check PAT 1
            pat_name, pat_type, price = self.check_pat1_rejection(curr)
            if pat_name: found_patterns.append((timestamp, pat_name, pat_type, price))
                
            # Check PAT 2
            pat_name, pat_type, price = self.check_pat2_engulfing(curr, prev)
            if pat_name: found_patterns.append((timestamp, pat_name, pat_type, price))
                
            # Check PAT 3-1
            pat_name, pat_type, price = self.check_pat3_1_piercing(curr, prev)
            if pat_name: found_patterns.append((timestamp, pat_name, pat_type, price))
                
            # Check PAT 3-2
            pat_name, pat_type, price = self.check_pat3_2_star(curr, prev, prev2)
            if pat_name: found_patterns.append((timestamp, pat_name, pat_type, price))
                
            # Check PAT 3-3
            pat_name, pat_type, price = self.check_pat3_3_inside_breakout(curr, prev, prev2)
            if pat_name: found_patterns.append((timestamp, pat_name, pat_type, price))

        return found_patterns

class ScannerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Price Action Scanner")
        self.root.geometry("900x600")
        
        self.scanner = PAPatternScanner()
        self.is_scanning = False
        self.scan_queue = queue.Queue()
        
        self._setup_ui()
        
    def _setup_ui(self):
        # Top Control Panel
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        ttk.Label(control_frame, text="Symbol:").pack(side=tk.LEFT, padx=5)
        self.symbol_var = tk.StringVar(value="XAUUSD.m")
        self.symbol_entry = ttk.Entry(control_frame, textvariable=self.symbol_var, width=15)
        self.symbol_entry.pack(side=tk.LEFT, padx=5)
        
        # Timeframe Selection
        ttk.Label(control_frame, text="TF:").pack(side=tk.LEFT, padx=5)
        self.tf_var = tk.StringVar(value="H1")
        self.tf_combo = ttk.Combobox(control_frame, textvariable=self.tf_var, width=5, state="readonly")
        self.tf_combo['values'] = ("M1", "M5", "M15", "M30", "H1", "H4", "D1")
        self.tf_combo.pack(side=tk.LEFT, padx=5)
        
        # Refresh Interval
        ttk.Label(control_frame, text="Refresh (s):").pack(side=tk.LEFT, padx=5)
        self.refresh_var = tk.StringVar(value="60")
        self.refresh_entry = ttk.Entry(control_frame, textvariable=self.refresh_var, width=5)
        self.refresh_entry.pack(side=tk.LEFT, padx=5)
        
        self.btn_start = ttk.Button(control_frame, text="Start Scanning", command=self.start_scanning)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = ttk.Button(control_frame, text="Stop", command=self.stop_scanning, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar(value="Status: Idle")
        self.lbl_status = ttk.Label(control_frame, textvariable=self.status_var)
        self.lbl_status.pack(side=tk.RIGHT, padx=10)

        # Results Table
        table_frame = ttk.Frame(self.root, padding="10")
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("time", "symbol", "pattern", "type", "price")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        self.tree.heading("time", text="Time")
        self.tree.heading("symbol", text="Symbol")
        self.tree.heading("pattern", text="Pattern")
        self.tree.heading("type", text="Type")
        self.tree.heading("price", text="Price")
        
        self.tree.column("time", width=150)
        self.tree.column("symbol", width=100)
        self.tree.column("pattern", width=250)
        self.tree.column("type", width=100)
        self.tree.column("price", width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tags for coloring
        self.tree.tag_configure("BUY", background="#e6ffe6") # Light Green
        self.tree.tag_configure("SELL", background="#ffe6e6") # Light Red

    def start_scanning(self):
        symbol = self.symbol_var.get()
        tf_str = self.tf_var.get()
        
        # Map string to MT5 constant
        tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }
        
        self.scanner.symbol = symbol
        self.scanner.timeframe = tf_map.get(tf_str, mt5.TIMEFRAME_H1)
        
        if not self.scanner.connect():
            messagebox.showerror("Error", "Could not connect to MT5")
            return
            
        self.is_scanning = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.symbol_entry.config(state=tk.DISABLED)
        self.tf_combo.config(state=tk.DISABLED)
        self.refresh_entry.config(state=tk.DISABLED)
        self.status_var.set(f"Status: Scanning {symbol} ({tf_str})...")
        
        # Start background thread
        threading.Thread(target=self._scan_loop, daemon=True).start()
        
        # Start checking queue
        self.root.after(100, self._process_queue)

    def stop_scanning(self):
        self.is_scanning = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.symbol_entry.config(state=tk.NORMAL)
        self.tf_combo.config(state=tk.NORMAL)
        self.refresh_entry.config(state=tk.NORMAL)
        self.status_var.set("Status: Stopped")
        self.scanner.disconnect()

    def _scan_loop(self):
        while self.is_scanning:
            try:
                patterns = self.scanner.scan_once()
                if patterns:
                    self.scan_queue.put(patterns)
            except Exception as e:
                print(f"Scan error: {e}")
            
            # Get refresh interval
            try:
                interval = int(self.refresh_var.get())
                if interval < 1: interval = 1
            except ValueError:
                interval = 60
            
            # Wait before next scan
            for _ in range(interval): # Check stop flag every second
                if not self.is_scanning: break
                time.sleep(1)

    def _process_queue(self):
        try:
            while True:
                patterns = self.scan_queue.get_nowait()
                for timestamp, pat_name, pat_type, price in patterns:
                    # Check if already exists to avoid duplicates (simple check based on time+pattern)
                    # In a real app, might want a more robust ID system
                    exists = False
                    for item in self.tree.get_children():
                        vals = self.tree.item(item)['values']
                        # vals[0] is string representation of time, need to be careful
                        if str(timestamp) == str(vals[0]) and vals[2] == pat_name:
                            exists = True
                            break
                    
                    if not exists:
                        self.tree.insert("", 0, values=(timestamp, self.scanner.symbol, pat_name, pat_type, price), tags=(pat_type,))
        except queue.Empty:
            pass
        
        if self.is_scanning:
            self.root.after(1000, self._process_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = ScannerGUI(root)
    root.mainloop()
