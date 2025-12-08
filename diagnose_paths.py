import os
import shutil

edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
print(f"Checking Edge binary at: {edge_path}")
if os.path.exists(edge_path):
    print("Edge binary FOUND.")
else:
    print("Edge binary NOT FOUND.")

driver_name = "msedgedriver.exe"
driver_path = shutil.which(driver_name)
print(f"Checking for {driver_name} in PATH...")
if driver_path:
    print(f"Driver found in PATH at: {driver_path}")
else:
    print("Driver NOT found in PATH.")
