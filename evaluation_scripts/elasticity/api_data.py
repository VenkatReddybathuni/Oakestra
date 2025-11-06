import requests
import time
import pandas as pd
import pickle
import json
from datetime import datetime
import threading

API_URL = "http://128.105.145.65:10100/api/node/get_workers"

def send_request(data):
    timestamp = datetime.now().isoformat()
    try:
        response = requests.post(API_URL, timeout=5)
        status = response.text
    except requests.RequestException:
        status = None  # Mark failure
    
    data.append((timestamp, status))
    print(f"[{timestamp}] Status: {status}")

def ping_endpoint(interval, output_file):
    data = []  # To store timestamp and response status
    print(f"Starting to ping {API_URL} every {interval} seconds. Press Ctrl+C to stop.")
    
    try:
        while True:
            thread = threading.Thread(target=send_request, args=(data,))
            thread.start()
            thread.join()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Stopping recording...")
        
        # Save data to DataFrame and serialize
        df = pd.DataFrame(data, columns=['timestamp', 'status'])
        with open(output_file, 'wb') as f:
            pickle.dump(df, f)
        
        print(f"Data saved to {output_file}")

if __name__ == "__main__":
    ping_interval = 0.5
    output_filename = "data/elastic.pkl"
    
    ping_endpoint(ping_interval, output_filename)
