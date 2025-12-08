import tkinter as tk
from tkinter import ttk, messagebox

class RiskCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("Sniper Risk Management Tool (For Hack)")
        self.root.geometry("450x600")
        self.root.configure(bg="#121212") # Dark theme for traders

        self.assets = {
            "EURUSD (Forex Major)": {"contract_size": 100000, "type": "FX"},
            "XAUUSD (Gold)": {"contract_size": 100, "type": "CFD"},
            "USOIL (WTI Crude)": {"contract_size": 1000, "type": "CFD"}, # Standard lot for oil
            "BTCUSD (Crypto)": {"contract_size": 1, "type": "CRYPTO"},
        }
        
        self._init_ui()

    def _init_ui(self):
        # Styles
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", background="#121212", foreground="#e0e0e0", font=("Consolas", 11))
        style.configure("TButton", font=("Segoe UI", 11, "bold"), background="#007acc", foreground="white")
        style.configure("TRadiobutton", background="#121212", foreground="#e0e0e0", font=("Consolas", 10))
        
        main_frame = tk.Frame(self.root, bg="#121212", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        tk.Label(main_frame, text="RISK CALCULATOR", font=("Impact", 20), bg="#121212", fg="#00ff88").pack(pady=(0, 20))

        # 1. Account Settings
        self._create_input(main_frame, "Account Balance ($):", "balance", "10000")
        self._create_input(main_frame, "Risk per Trade (%):", "risk_pct", "1.0")

        tk.Frame(main_frame, height=2, bg="#333").pack(fill=tk.X, pady=15)

        # 2. Trade Setup
        tk.Label(main_frame, text="Select Asset Class:", bg="#121212", fg="#00aaff", font=("Consolas", 12, "bold")).pack(anchor="w")
        
        self.asset_var = tk.StringVar(value="XAUUSD (Gold)")
        asset_menu = ttk.OptionMenu(main_frame, self.asset_var, "XAUUSD (Gold)", *self.assets.keys())
        asset_menu.config(width=25)
        asset_menu.pack(pady=5)

        self._create_input(main_frame, "Entry Price:", "entry", "")
        self._create_input(main_frame, "Stop Loss Price:", "sl", "")
        self._create_input(main_frame, "Take Profit Price (Optional):", "tp", "")

        # Calculate Button
        tk.Button(main_frame, text="CALCULATE SIZE", command=self.calculate, 
                  bg="#d32f2f", fg="white", font=("Segoe UI", 12, "bold"), relief=tk.FLAT, pady=5).pack(fill=tk.X, pady=20)

        # Result Area
        self.result_frame = tk.Frame(main_frame, bg="#1e1e1e", bd=1, relief=tk.SOLID)
        self.result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.result_label = tk.Label(self.result_frame, text="Waiting for input...", 
                                     bg="#1e1e1e", fg="#888", font=("Consolas", 11), justify=tk.LEFT, padx=10, pady=10)
        self.result_label.pack(fill=tk.BOTH, expand=True)

        self.entries = {}

    def _create_input(self, parent, label_text, key, default_val):
        frame = tk.Frame(parent, bg="#121212")
        frame.pack(fill=tk.X, pady=5)
        tk.Label(frame, text=label_text, width=20, anchor="w", bg="#121212", fg="#ccc").pack(side=tk.LEFT)
        entry = tk.Entry(frame, bg="#2d2d2d", fg="white", insertbackground="white", font=("Consolas", 11))
        entry.insert(0, default_val)
        entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        
        # Store entry reference dynamically
        if not hasattr(self, 'input_widgets'):
            self.input_widgets = {}
        self.input_widgets[key] = entry

    def calculate(self):
        try:
            # Get Inputs
            balance = float(self.input_widgets['balance'].get())
            risk_pct = float(self.input_widgets['risk_pct'].get())
            entry = float(self.input_widgets['entry'].get())
            sl = float(self.input_widgets['sl'].get())
            tp_input = self.input_widgets['tp'].get()
            
            asset_name = self.asset_var.get()
            asset_info = self.assets[asset_name]
            contract_size = asset_info['contract_size']

            # 1. Calculate Risk Amount ($)
            risk_amount = balance * (risk_pct / 100)

            # 2. Calculate Distance
            distance = abs(entry - sl)
            if distance == 0: raise ValueError("Entry and SL cannot be the same!")

            # 3. Calculate Position Size
            # Formula: Size = Risk / (Distance * Contract_Size)
            # Note: For crypto (BTC), contract size is usually 1 (calculating raw units)
            position_size = risk_amount / (distance * contract_size)

            # 4. Format Output
            if asset_info['type'] == 'FX':
                size_fmt = f"{position_size:.2f} Lots"
                point_val = distance * 100000 # for 5 decimal broker
                pips = point_val / 10 # approx
                dist_str = f"{pips:.1f} Pips"
            elif asset_info['type'] == 'CFD': # Gold/Oil
                size_fmt = f"{position_size:.2f} Lots"
                dist_str = f"{distance:.2f} Points ($)"
            else: # Crypto
                size_fmt = f"{position_size:.4f} BTC"
                dist_str = f"${distance:.2f}"

            # 5. Reward:Risk Calculation (if TP provided)
            rr_str = "N/A"
            if tp_input:
                tp = float(tp_input)
                reward_dist = abs(tp - entry)
                rr_ratio = reward_dist / distance
                rr_str = f"1 : {rr_ratio:.2f}"
                
                # Color coding for RR
                rr_color = "#00ff88" if rr_ratio >= 2 else "#ff9900"
            else:
                rr_color = "#cccccc"

            # Display Result
            result_text = (
                f"⚠️ RISK AMOUNT:   ${risk_amount:.2f} ({risk_pct}%)\n"
                f"📉 STOP LOSS DIST: {dist_str}\n"
                f"----------------------------------\n"
                f"🎯 POSITION SIZE:  [{size_fmt}]\n"
                f"----------------------------------\n"
                f"⚖️ REWARD:RISK:    {rr_str}\n"
            )
            
            self.result_label.config(text=result_text, fg="#ffffff", font=("Consolas", 12, "bold"))
            
        except ValueError:
            self.result_label.config(text="Error: Please check your numbers!", fg="#ff4444")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = RiskCalculator(root)
    root.mainloop()