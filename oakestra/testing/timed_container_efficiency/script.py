import time
import numpy as np
import requests

def send_ping(ip, event):
    timestamp = time.time()
    try:
        requests.post(f"http://{ip}:5000/ping", json={"event": event, "timestamp": timestamp})
        print(f"Sent {event} ping to {ip} at {timestamp}")
    except Exception as e:
        print(f"Failed to send ping: {e}")

def cpu_intensive_task(duration):
    """Perform dummy NumPy CPU operations to simulate work."""
    start_time = time.time()
    while time.time() - start_time < duration:
        _ = np.random.rand(100, 100).dot(np.random.rand(100, 100))  # Simulate work

if __name__ == "__main__":
    TARGET_IP = "XXXXX"
    COMPUTE_DURATION = 5 # Could be 3, 5, 8, 13, 20 depending on specific test. 

    send_ping(TARGET_IP, "start")
    cpu_intensive_task(COMPUTE_DURATION)
    send_ping(TARGET_IP, "end")