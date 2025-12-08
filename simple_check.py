from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import os

print("Starting simple driver check...")
try:
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--disable-gpu')
    opts.add_argument("--log-level=3")
    
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if os.path.exists(edge_path):
        print(f"Found Edge binary at {edge_path}")
        opts.binary_location = edge_path
    else:
        print("Edge binary not found at default location.")

    print("Installing driver...")
    driver_path = EdgeChromiumDriverManager().install()
    print(f"Driver installed at {driver_path}")
    
    service = Service(driver_path)
    print("Initializing WebDriver...")
    driver = webdriver.Edge(service=service, options=opts)
    print("WebDriver initialized successfully.")
    driver.quit()
    print("Driver quit.")
except Exception as e:
    print(f"Error: {e}")
