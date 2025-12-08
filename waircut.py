class WirelessAirCut20:
    """
    A Python simulation of a Wireless Air Cut 2.0 tool
    with battery management, pressure control, and cutting functionality.
    """
    
    def __init__(self, max_battery=100, max_pressure=150):
        # Initial setup
        self.max_battery = max_battery
        self.battery_level = max_battery
        self.max_pressure = max_pressure  # PSI
        self.current_pressure = 0
        self.is_powered_on = False
        self.is_connected = False
        self.cut_mode = "standard"
        self.cut_speed = 1  # 1-5 scale
        self.cut_modes = ["standard", "precision", "heavy-duty"]
        self.material_settings = {
            "sheet_metal": {"pressure": 120, "speed": 2},
            "aluminum": {"pressure": 90, "speed": 3},
            "steel": {"pressure": 140, "speed": 1},
            "plastic": {"pressure": 60, "speed": 4}
        }
        print("Wireless Air Cut 2.0 initialized and ready!")
    
    def power_on(self):
        """Power on the device"""
        if self.battery_level > 0:
            self.is_powered_on = True
            print("Powering on Wireless Air Cut 2.0...")
            print("System check: OK")
            print(f"Battery level: {self.battery_level}%")
            return True
        else:
            print("Unable to power on: Battery depleted. Please recharge.")
            return False
    
    def power_off(self):
        """Power off the device"""
        self.is_powered_on = False
        self.release_pressure()
        print("Powering off Wireless Air Cut 2.0...")
        return True
    
    def build_pressure(self, target_pressure=None):
        """Build air pressure in the system"""
        if not self.is_powered_on:
            print("Device is not powered on.")
            return False
            
        if target_pressure is None:
            target_pressure = self.max_pressure
        
        if target_pressure > self.max_pressure:
            print(f"Warning: Target pressure exceeds maximum. Setting to {self.max_pressure} PSI.")
            target_pressure = self.max_pressure
        
        print(f"Building pressure to {target_pressure} PSI...")
        
        # Simulate pressure building
        while self.current_pressure < target_pressure:
            if self.battery_level <= 0:
                print("Battery depleted during pressure build.")
                return False
                
            self.current_pressure += 10
            if self.current_pressure > target_pressure:
                self.current_pressure = target_pressure
                
            self.battery_level -= 2  # Building pressure uses battery
            if self.battery_level < 0:
                self.battery_level = 0
                
            print(f"Current pressure: {self.current_pressure} PSI | Battery: {self.battery_level}%")
        
        print(f"Pressure built successfully: {self.current_pressure} PSI")
        return True
    
    def release_pressure(self):
        """Release all pressure from the system"""
        print("Releasing pressure...")
        self.current_pressure = 0
        print("Pressure released. Current pressure: 0 PSI")
        return True
    
    def set_cut_mode(self, mode):
        """Set the cutting mode"""
        if mode not in self.cut_modes:
            print(f"Invalid mode. Available modes: {', '.join(self.cut_modes)}")
            return False
        
        self.cut_mode = mode
        print(f"Cut mode set to: {mode}")
        
        # Adjust pressure based on mode
        if mode == "precision":
            self.build_pressure(self.max_pressure * 0.6)
        elif mode == "heavy-duty":
            self.build_pressure(self.max_pressure * 0.9)
        else:  # standard
            self.build_pressure(self.max_pressure * 0.75)
        
        return True
    
    def set_cut_speed(self, speed):
        """Set the cutting speed (1-5)"""
        if not 1 <= speed <= 5:
            print("Speed must be between 1 (slowest) and 5 (fastest)")
            return False
        
        self.cut_speed = speed
        print(f"Cut speed set to: {speed}")
        return True
    
    def select_material(self, material):
        """Set optimal settings for a specific material"""
        if material not in self.material_settings:
            print(f"Material not in database. Available materials: {', '.join(self.material_settings.keys())}")
            return False
        
        settings = self.material_settings[material]
        print(f"Optimizing for {material}...")
        self.build_pressure(settings["pressure"])
        self.set_cut_speed(settings["speed"])
        print(f"Settings applied for {material}")
        return True
    
    def cut(self, duration=5):
        """Perform a cutting operation for the specified duration"""
        if not self.is_powered_on:
            print("Device is not powered on.")
            return False
        
        if self.current_pressure < 30:
            print("Pressure too low for cutting. Please build pressure.")
            return False
        
        if self.battery_level < 10:
            print("Warning: Low battery. Cutting performance may be affected.")
        
        print(f"Cutting with mode: {self.cut_mode}, speed: {self.cut_speed}, pressure: {self.current_pressure} PSI")
        
        # Simulate cutting operation
        for second in range(1, duration + 1):
            if self.battery_level <= 0:
                print("Battery depleted during cutting operation.")
                return False
            
            # Battery consumption based on speed and pressure
            battery_use = (self.cut_speed * 0.5) + (self.current_pressure / self.max_pressure * 2)
            self.battery_level -= battery_use
            if self.battery_level < 0:
                self.battery_level = 0
            
            # Pressure loss during cutting
            self.current_pressure -= 2
            if self.current_pressure < 0:
                self.current_pressure = 0
            
            print(f"Cutting: {second}/{duration}s | Pressure: {self.current_pressure} PSI | Battery: {int(self.battery_level)}%")
        
        print("Cutting operation completed successfully!")
        return True
    
    def recharge_battery(self):
        """Recharge the battery to maximum capacity"""
        print("Recharging battery...")
        self.battery_level = self.max_battery
        print(f"Battery recharged to {self.battery_level}%")
        return True
    
    def perform_diagnostics(self):
        """Run a diagnostic check on the system"""
        print("Running diagnostics...")
        print(f"Power Status: {'ON' if self.is_powered_on else 'OFF'}")
        print(f"Battery Level: {self.battery_level}%")
        print(f"Current Pressure: {self.current_pressure} PSI")
        print(f"Maximum Pressure: {self.max_pressure} PSI")
        print(f"Current Cut Mode: {self.cut_mode}")
        print(f"Current Cut Speed: {self.cut_speed}")
        print("All systems normal.")
        return True


# Example usage
def demonstration():
    # Create a new Wireless Air Cut 2.0 device
    tool = WirelessAirCut20()
    
    # Power on the device
    tool.power_on()
    
    # Set up for cutting aluminum
    tool.select_material("aluminum")
    
    # Perform a cutting operation
    tool.cut(duration=3)
    
    # Switch to precision mode for detailed work
    tool.set_cut_mode("precision")
    
    # Perform another cutting operation
    tool.cut(duration=2)
    
    # Check the device status
    tool.perform_diagnostics()
    
    # Power off the device
    tool.power_off()

# Run the demonstration
if __name__ == "__main__":
    demonstration()