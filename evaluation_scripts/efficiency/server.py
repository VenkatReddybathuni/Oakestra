from flask import Flask, request, jsonify
import time

app = Flask(__name__)

LOG_FILE = "timestamps"

def log_event(ip, event, timestamp):
    with open(LOG_FILE, "a") as file:
        file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}, {ip}, {event}, {timestamp}\n")

@app.route('/ping', methods=['POST'])
def receive_ping():
    """Handles pings from finished workers and logs the start/end time (productive work time)"""
    data = request.json
    ip = request.remote_addr  # Get sender's IP
    event = data.get("event")
    timestamp = data.get("timestamp", time.time())  # Use received timestamp or default to now

    if event not in ["start", "end"]:
        return jsonify({"status": "error", "message": "Invalid event type"}), 400

    log_event(ip, event, timestamp)
    return jsonify({"status": "success", "event": event, "timestamp": timestamp})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)