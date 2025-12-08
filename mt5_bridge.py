import MetaTrader5 as mt5
import pandas as pd
import time
import os
import sys

# Constants
REQUEST_FILE = "request.txt"
DATA_FILE = "candles.csv"

def connect_mt5():
    if not mt5.initialize():
        print("initialize() failed")
        mt5.shutdown()
        return False
    return True

def get_timeframe(tf_str):
    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1
    }
    return tf_map.get(tf_str, mt5.TIMEFRAME_H1)

def main():
    if not connect_mt5():
        return

    print("MT5 Bridge Started. Waiting for requests...")
    
    last_modified = 0
    
    while True:
        try:
            # Check if request file exists
            if os.path.exists(REQUEST_FILE):
                # Check if file has been modified
                current_modified = os.path.getmtime(REQUEST_FILE)
                if current_modified > last_modified:
                    last_modified = current_modified
                    
                    # Read request
                    with open(REQUEST_FILE, "r") as f:
                        content = f.read().strip().split(",")
                        if len(content) >= 2:
                            symbol = content[0].strip()
                            tf_str = content[1].strip()
                            
                            print(f"Fetching {symbol} {tf_str}...")
                            
                            # Fetch candles
                            rates = mt5.copy_rates_from_pos(symbol, get_timeframe(tf_str), 0, 100)
                            
                            if rates is not None and len(rates) > 0:
                                df = pd.DataFrame(rates)
                                df['time'] = pd.to_datetime(df['time'], unit='s') + pd.Timedelta(hours=7) # Bangkok Time
                                
                                # Select columns matching VFP cursor: time, symbol, open, high, low, close
                                # Note: VFP APPEND FROM CSV expects specific order or matching types. 
                                # We will write: time, symbol, open, high, low, close
                                
                                # Format time for VFP (YYYY-MM-DD hh:mm:ss) usually works with CSV
                                # But VFP APPEND FROM CSV might be tricky with dates. 
                                # Let's try standard string format.
                                
                                output_data = []
                                for index, row in df.iterrows():
                                    t_str = row['time'].strftime("%Y-%m-%d %H:%M:%S")
                                    output_data.append(f"{t_str},{symbol},{row['open']},{row['high']},{row['low']},{row['close']}")
                                
                                with open(DATA_FILE + ".tmp", "w") as f:
                                    f.write("\n".join(output_data))
                                
                                # Atomic rename
                                if os.path.exists(DATA_FILE):
                                    os.remove(DATA_FILE)
                                os.rename(DATA_FILE + ".tmp", DATA_FILE)
                                    
                                print(f"Written {len(rates)} candles to {DATA_FILE}")
                            else:
                                print("No data found")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        mt5.shutdown()
