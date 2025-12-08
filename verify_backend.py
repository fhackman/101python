import threading
from testspeed import run_speed_test_logic

def test_backend():
    print("Starting backend test...")
    stop_event = threading.Event()
    try:
        # Run with headless=False to see what's happening
        result = run_speed_test_logic(stop_event, headless=False)
        print("Test Result:", result)
    except Exception as e:
        print("Test Failed with exception:", e)

if __name__ == "__main__":
    test_backend()
