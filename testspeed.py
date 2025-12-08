import datetime
import threading
import time
from contextlib import contextmanager
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from bs4 import BeautifulSoup

# --- Backend / Speed Test Logic ---

@contextmanager
def get_driver(headless=True):
    """Context manager for Microsoft Edge WebDriver"""
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Edge(options=options)
    try:
        yield driver
    finally:
        driver.quit()

def extract_speed_info(soup):
    """Extract download and upload speed from BeautifulSoup parsed HTML"""
    try:
        dl_speed = soup.select_one('#speed-value').text
        dl_unit = soup.select_one('#speed-units').text
        upload_speed = soup.select_one('#upload-value').text
        upload_unit = soup.select_one('#upload-units').text
        return {
            'download': f'{dl_speed} {dl_unit}',
            'upload': f'{upload_speed} {upload_unit}',
            'success': True
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def run_speed_test_logic(stop_event, headless=True):
    try:
        print("DEBUG: Initializing driver...")
        with get_driver(headless=headless) as driver:
            if stop_event.is_set(): 
                return {'success': False, 'error': 'Stopped by user'}
            
            print("DEBUG: Driver started. Navigating to fast.com...")
            driver.get('https://fast.com')
            print("DEBUG: Page loaded. Waiting for test to complete...")
            
            # Wait for upload test to complete (ensures full results)
            # Fast.com flow: Download -> (wait) -> Upload -> Done
            upload_done_selector = '#upload-value.succeeded'
            
            # Custom wait loop to allow checking stop_event
            end_time = time.time() + 90
            while time.time() < end_time:
                if stop_event.is_set():
                    return {'success': False, 'error': 'Stopped by user'}
                try:
                    if driver.find_elements(By.CSS_SELECTOR, upload_done_selector):
                        print("DEBUG: Upload complete selector found.")
                        break
                except:
                    pass
                time.sleep(0.5)
            else:
                print("DEBUG: Timeout waiting for upload to complete.")
                raise TimeoutError("Timed out waiting for speed test to complete")

            if stop_event.is_set(): 
                return {'success': False, 'error': 'Stopped by user'}
            
            # Extract results HTML
            print("DEBUG: Extracting results...")
            results_selector = '.speed-container'
            results_el = driver.find_element(By.CSS_SELECTOR, results_selector)
            results_html = results_el.get_attribute('outerHTML')
        
        soup = BeautifulSoup(results_html, 'html.parser')
        return extract_speed_info(soup)
    except Exception as e:
        print(f"DEBUG: Exception occurred: {e}")
        return {'success': False, 'error': str(e)}

# --- GUI / Frontend ---

class SpeedTestApp(ttk.Window):
    def __init__(self):
        super().__init__(themename="cyborg")
        self.title("Fast.com Speed Test")
        self.geometry("500x600")
        self.resizable(False, False)
        
        self.is_running = False
        self.stop_event = threading.Event()
        self.auto_run_enabled = tk.BooleanVar(value=False)
        self.next_run_id = None
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main Container
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)
        
        # Header
        header_lbl = ttk.Label(
            main_frame, 
            text="SPEED TEST", 
            font=("Helvetica", 24, "bold"),
            bootstyle="inverse-primary"
        )
        header_lbl.pack(pady=(0, 20), fill=X)
        
        # Speed Display Frame
        self.speed_frame = ttk.Labelframe(main_frame, text="Current Results", padding=15, bootstyle="info")
        self.speed_frame.pack(fill=X, pady=10)
        
        # Download
        ttk.Label(self.speed_frame, text="DOWNLOAD", font=("Helvetica", 10), bootstyle="secondary").pack(anchor=W)
        self.dl_var = tk.StringVar(value="-- Mbps")
        ttk.Label(self.speed_frame, textvariable=self.dl_var, font=("Helvetica", 32, "bold"), bootstyle="success").pack(anchor=W, pady=(0, 10))
        
        # Upload
        ttk.Label(self.speed_frame, text="UPLOAD", font=("Helvetica", 10), bootstyle="secondary").pack(anchor=W)
        self.ul_var = tk.StringVar(value="-- Mbps")
        ttk.Label(self.speed_frame, textvariable=self.ul_var, font=("Helvetica", 32, "bold"), bootstyle="warning").pack(anchor=W)
        
        # Controls
        controls_frame = ttk.Frame(main_frame, padding=10)
        controls_frame.pack(fill=X, pady=20)
        
        self.start_btn = ttk.Button(
            controls_frame, 
            text="START TEST", 
            command=self.start_test_thread,
            bootstyle="primary-outline",
            width=15
        )
        self.start_btn.pack(side=LEFT, padx=5)

        self.stop_btn = ttk.Button(
            controls_frame, 
            text="STOP", 
            command=self.stop_test,
            bootstyle="danger-outline",
            width=10,
            state=DISABLED
        )
        self.stop_btn.pack(side=LEFT, padx=5)
        
        self.auto_check = ttk.Checkbutton(
            controls_frame, 
            text="Auto-run (5m)", 
            variable=self.auto_run_enabled,
            command=self.toggle_auto_run,
            bootstyle="round-toggle"
        )
        self.auto_check.pack(side=RIGHT, padx=5)
        
        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            main_frame, 
            textvariable=self.status_var, 
            font=("Consolas", 9), 
            bootstyle="secondary"
        )
        status_bar.pack(side=BOTTOM, fill=X, pady=5)
        
        # History Log (Simple Listbox)
        history_header_frame = ttk.Frame(main_frame)
        history_header_frame.pack(fill=X, pady=(10, 0))
        
        ttk.Label(history_header_frame, text="History", font=("Helvetica", 12, "bold"), bootstyle="secondary").pack(side=LEFT)
        ttk.Button(history_header_frame, text="Clear", command=self.clear_history, bootstyle="link-secondary", padding=0).pack(side=RIGHT)

        history_frame = ttk.Frame(main_frame)
        history_frame.pack(fill=BOTH, expand=YES, pady=5)
        
        self.history_list = tk.Listbox(
            history_frame, 
            height=6, 
            bg="#2e2e2e", 
            fg="#ffffff", 
            borderwidth=0, 
            highlightthickness=0,
            font=("Consolas", 9)
        )
        self.history_list.pack(fill=BOTH, expand=YES)
        
        # Scrollbar for history
        scrollbar = ttk.Scrollbar(self.history_list, orient=VERTICAL, command=self.history_list.yview)
        self.history_list.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)

    def start_test_thread(self):
        if self.is_running:
            return
        
        self.is_running = True
        self.stop_event.clear()
        self.start_btn.configure(state=DISABLED)
        self.stop_btn.configure(state=NORMAL)
        self.status_var.set("Initializing Speed Test...")
        self.dl_var.set("Testing...")
        self.ul_var.set("Testing...")
        
        # Run in separate thread
        thread = threading.Thread(target=self.run_test, daemon=True)
        thread.start()

    def run_test(self):
        try:
            self.update_status("Running Edge (Headless)...")
            results = run_speed_test_logic(self.stop_event, headless=True)
            
            # Schedule UI update on main thread
            self.after(0, lambda: self.on_test_complete(results))
        except Exception as e:
            self.after(0, lambda: self.on_test_error(str(e)))

    def on_test_complete(self, results):
        self.is_running = False
        self.start_btn.configure(state=NORMAL)
        self.stop_btn.configure(state=DISABLED)
        
        if results.get('success'):
            dl = results['download']
            ul = results['upload']
            self.dl_var.set(dl)
            self.ul_var.set(ul)
            
            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
            log_entry = f"[{timestamp}] DL: {dl} | UL: {ul}"
            self.history_list.insert(0, log_entry)
            self.status_var.set(f"Last run: {timestamp}")
        else:
            self.on_test_error(results.get('error', 'Unknown error'))
            
        # Schedule next run if auto is enabled
        if self.auto_run_enabled.get():
            self.schedule_next_run()

    def on_test_error(self, error_msg):
        self.is_running = False
        self.start_btn.configure(state=NORMAL)
        self.stop_btn.configure(state=DISABLED)
        self.status_var.set("Error occurred" if error_msg != 'Stopped by user' else "Stopped")
        if error_msg == 'Stopped by user':
             self.dl_var.set("Stopped")
             self.ul_var.set("Stopped")
             return

        self.dl_var.set("Error")
        self.ul_var.set("Error")
        messagebox.showerror("Speed Test Error", error_msg)

    def toggle_auto_run(self):
        if self.auto_run_enabled.get():
            self.status_var.set("Auto-run enabled. Next run in 5 mins.")
            self.schedule_next_run()
        else:
            if self.next_run_id:
                self.after_cancel(self.next_run_id)
                self.next_run_id = None
            self.status_var.set("Auto-run disabled.")

    def schedule_next_run(self):
        if self.next_run_id:
            self.after_cancel(self.next_run_id)
        # 5 minutes = 300,000 ms
        self.next_run_id = self.after(300000, self.start_test_thread)
        self.update_status("Next test in 5 minutes...")

    def update_status(self, text):
        self.after(0, lambda: self.status_var.set(text))

    def stop_test(self):
        if self.is_running:
            self.status_var.set("Stopping...")
            self.stop_event.set()
    
    def clear_history(self):
        self.history_list.delete(0, END)

if __name__ == '__main__':
    app = SpeedTestApp()
    app.mainloop()