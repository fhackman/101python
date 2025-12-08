import time
import csv
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. SMART BATTERY SIMULATION CLASS
# ==============================================================================

class SmartBattery:
    """
    Simulates a battery based on specific management logic.
    """
    def __init__(self, initial_level: int = 55, charge_rate: int = 5, discharge_rate: int = 10):
        # Constrain level between 0 and 100
        self.level = max(0, min(100, initial_level))
        self.charge_rate = charge_rate
        self.discharge_rate = discharge_rate
        logger.info(f"🔋 SmartBattery Initialized: {self.level}%")

    def attempt_charge(self) -> str:
        """Increases battery level if current level is less than 60%."""
        if self.level < 60:
            old_level = self.level
            self.level = min(100, self.level + self.charge_rate)
            msg = f"⚡ Charging... ({old_level}% -> {self.level}%)"
            logger.info(msg)
            return msg
        else:
            msg = f"🛑 Charge Halted: {self.level}%. (Must be < 60%)"
            logger.warning(msg)
            return msg

    def attempt_discharge(self) -> str:
        """Decreases battery level if there is charge remaining."""
        if self.level > 0:
            old_level = self.level
            self.level = max(0, self.level - self.discharge_rate)
            msg = f"⬇️ Discharging... ({old_level}% -> {self.level}%)"
            logger.info(msg)
            return msg
        else:
            msg = f"🛑 Discharge Halted: {self.level}%. (Battery Empty)"
            logger.warning(msg)
            return msg

    def get_status(self) -> int:
        return self.level

# ==============================================================================
# 2. FILE HANDLING CLASS
# ==============================================================================

class FileHandler:
    """
    Utility class for basic file operations using pathlib.
    """
    @staticmethod
    def write_csv(filename: str, header: List[str], data: List[List[Any]]):
        """Writes data to a CSV file."""
        file_path = Path(filename)
        try:
            with file_path.open('w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(data)
            logger.info(f"✅ Data successfully written to {file_path.absolute()}")
        except IOError as e:
            logger.error(f"❌ Error writing file {filename}: {e}")

    @staticmethod
    def read_csv(filename: str) -> List[Dict[str, Any]]:
        """Reads data from a CSV file and returns a list of dictionaries."""
        file_path = Path(filename)
        data = []
        try:
            if not file_path.exists():
                logger.error(f"❌ Error: File not found at {file_path.absolute()}")
                return []
                
            with file_path.open('r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(dict(row))
            logger.info(f"✅ Data successfully read from {filename}")
            return data
        except IOError as e:
            logger.error(f"❌ Error reading file {filename}: {e}")
            return []

# ==============================================================================
# 3. WEB DATA FETCHING FUNCTION
# ==============================================================================

def fetch_public_api_data(url: str) -> Optional[Dict[str, Any]]:
    """
    Fetches JSON data from a given URL.
    """
    logger.info(f"📡 Attempting to fetch data from: {url}")
    try:
        with requests.Session() as session:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.info("✅ Data fetched successfully")
            return data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ HTTP/Network Error: {e}")
        return None
    except json.JSONDecodeError:
        logger.error("❌ Error: Received non-JSON response.")
        return None

# ==============================================================================
# --- EXECUTION DEMONSTRATION ---
# ==============================================================================

if __name__ == "__main__":
    
    # DEMO 1: SmartBattery Simulation
    print("\n" + "="*40)
    print("      DEMO 1: SMART BATTERY LOGIC")
    print("="*40)
    
    battery = SmartBattery(initial_level=59)
    battery.attempt_charge()
    battery.attempt_charge() # Should fail
    
    battery.level = 100
    logger.info(f"Manually set level to {battery.level}%")
    battery.attempt_discharge()
    
    # DEMO 2: File Handling
    print("\n" + "="*40)
    print("      DEMO 2: FILE HANDLING (CSV)")
    print("="*40)
    
    filename = "battery_log.csv"
    csv_header = ["time", "level", "action"]
    csv_data = [
        [time.strftime("%H:%M:%S"), 100, "START"],
        [time.strftime("%H:%M:%S"), 90, "DISCHARGE"],
        [time.strftime("%H:%M:%S"), 60, "HALTED_CHARGE"]
    ]
    
    FileHandler.write_csv(filename, csv_header, csv_data)
    loaded_data = FileHandler.read_csv(filename)
    if loaded_data:
        print(f"Loaded {len(loaded_data)} rows.")

    # DEMO 3: Web Data Fetching
    print("\n" + "="*40)
    print("      DEMO 3: WEB DATA FETCHING")
    print("="*40)
    
    api_url = "https://jsonplaceholder.typicode.com/posts/1" 
    fetched_data = fetch_public_api_data(api_url)
    
    if fetched_data:
        print(f"Title: {fetched_data.get('title')}")