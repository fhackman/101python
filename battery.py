import tkinter as tk
from tkinter import ttk

class SmartBatteryGUI(tk.Tk):
    """
    GUI application to simulate a battery with specific charge/discharge logic:
    Charges only below 60%. Discharges only at 100%.
    """
    
    CHARGE_RATE = 5
    DISCHARGE_RATE = 10
    
    def __init__(self, initial_level=55):
        super().__init__()
        self.title("Smart Battery Controller")
        self.geometry("380x280")
        self.resizable(False, False)

        # State variable for the battery level, constrained [0, 100]
        self.battery_level = max(0, min(100, initial_level))
        
        # Tkinter variables
        self.progress_var = tk.DoubleVar(value=self.battery_level)
        self.status_var = tk.StringVar(value="System Initialized.")
        
        # 1. Setup TTK Styles for colored progress bars
        self._setup_styles()
        
        # --- UI Elements Setup ---
        
        # 2. Level Label
        self.level_label = ttk.Label(self, text="", font=('Helvetica', 16, 'bold'))
        self.level_label.pack(pady=(20, 5))
        
        # 3. Progress Bar
        self.progress_bar = ttk.Progressbar(
            self, 
            orient='horizontal', 
            length=300, 
            mode='determinate', 
            variable=self.progress_var,
            style='Yellow.Horizontal.TProgressbar' # Start with a default style
        )
        self.progress_bar.pack(pady=10, padx=20)
        
        # 4. Status Message
        self.status_label = ttk.Label(self, textvariable=self.status_var, font=('Helvetica', 10, 'italic'))
        self.status_label.pack(pady=5)
        
        # 5. Buttons Frame
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=20)
        
        # Charge Button
        self.charge_btn = ttk.Button(
            button_frame, 
            text=f"🔌 Charge (+{self.CHARGE_RATE}%)", 
            command=self.attempt_charge
        )
        self.charge_btn.pack(side=tk.LEFT, padx=10)
        
        # Discharge Button
        self.discharge_btn = ttk.Button(
            button_frame, 
            text=f"⚡ Discharge (-{self.DISCHARGE_RATE}%)", 
            command=self.attempt_discharge
        )
        self.discharge_btn.pack(side=tk.LEFT, padx=10)
        
        # Initial display update
        self._update_display("Ready to monitor.")

    def _setup_styles(self):
        """Configures custom styles for the Progressbar."""
        s = ttk.Style()
        s.theme_use('clam') # Use a theme that allows background customization

        # Define custom styles for different battery levels
        s.configure("Red.Horizontal.TProgressbar", background='red')
        s.configure("Yellow.Horizontal.TProgressbar", background='gold')
        s.configure("Green.Horizontal.TProgressbar", background='green')

    def _update_display(self, message):
        """Updates the progress bar, label text, status message, and bar color."""
        self.progress_var.set(self.battery_level)
        self.level_label.config(text=f"Level: {self.battery_level}%")
        self.status_var.set(message)
        
        # Set progress bar style based on battery level
        if self.battery_level <= 20:
            style = 'Red.Horizontal.TProgressbar'
        elif self.battery_level <= 80: # Covers 21% to 80%
            style = 'Yellow.Horizontal.TProgressbar'
        else: # Covers 81% to 100%
            style = 'Green.Horizontal.TProgressbar'

        self.progress_bar.config(style=style)

    def attempt_charge(self):
        """Attempts to charge based on the < 60% rule."""
        rate = self.CHARGE_RATE
        
        if self.battery_level < 60:
            # Safely increment, ensuring it doesn't exceed 100
            self.battery_level = min(100, self.battery_level + rate)
            
            # Use f-strings for clear logging
            message = f"⚡ CHARGING: Level increased to {self.battery_level}%."
        else:
            message = f"🛑 CHARGE Halted: Level is {self.battery_level}%, which is $\\ge 60\\%$. (No change)"

        self._update_display(message)

    def attempt_discharge(self):
        """Attempts to discharge based on the 100% rule."""
        rate = self.DISCHARGE_RATE

        if self.battery_level == 100:
            # Safely decrement, ensuring it doesn't drop below 0
            self.battery_level = max(0, self.battery_level - rate)
            message = f"⬇️ DISCHARGING: Level decreased to {self.battery_level}%."
        else:
            message = f"🛑 DISCHARGE Halted: Level is {self.battery_level}%, not $100\\%$. (No change)"

        self._update_display(message)

# -------------------------------------------------------------
# --- EXECUTION BLOCK: NOW STARTS AT 100% ---
# -------------------------------------------------------------
if __name__ == "__main__":
    app = SmartBatteryGUI(initial_level=100) # <-- THE CHANGE IS HERE
    app.mainloop()