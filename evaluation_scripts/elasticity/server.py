from flask import Flask, request
import subprocess
import signal
import datetime

app = Flask(__name__)

processes = {}  # Dictionary to store processes by PID

@app.route('/run-command', methods=['POST'])
def run_command():
    data = request.json
    if not data or 'command' not in data:
        return {"error": "Invalid request format. Must include 'command' key."}, 400
    
    command = ["sudo", "NodeEngine", "-n", "6000", "-p", "10000", "-r"] + [data["cluster_ip"]]

    try:
        # Start the command without waiting for it to complete
        process = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes[process.pid] = process  # Store the process by its PID
        return {
            "success": True,
            "message": f"Command '{command}' started successfully.",
            "time": datetime.datetime.now(datetime.timezone.utc),
            "pid": process.pid
        }
    except Exception as e:
        print(e)
        return {
            "success": False,
            "error": str(e)
        }, 500

@app.route('/kill-process', methods=['POST'])
def kill_process():
    data = request.json
    if not data or 'pid' not in data:
        return {"error": "Invalid request format. Must include 'pid' key."}, 400

    pid = data['pid']

    try:
        if pid in processes:
            command = ["sudo", "kill", "-15", f"{pid + 1}"]
            subprocess.call(command)

            return {
                "success": True,
                "time": datetime.datetime.now(datetime.timezone.utc),
                "message": f"Process with PID {pid} terminated successfully."
            }
        else:
            return {
                "success": False,
                "error": f"No process found with PID {pid}."
            }, 404
    except Exception as e:
        print(e)
        return {
            "success": False,
            "error": str(e)
        }, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
