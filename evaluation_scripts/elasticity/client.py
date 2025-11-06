import requests
import json
import time
import threading



### NOTE: THESE IPs ARE NOT STATIC, THEY SHOULD BE THE ONES USED BY THE 
###     ACTUAL WORKERS IN A PARTICULAR TEST INSTANCE
WORKER_URLS = [
    ("http://128.105.146.166:5000", "10.10.4"),
    ("http://128.105.146.169:5000", "10.10.3"),
    ("http://128.105.146.167:5000", "10.10.2"),
    ("http://128.105.146.170:5000", "10.10.1"),
    ("http://128.105.146.168:5000", "10.10.5"),
    ("http://128.105.146.173:5000", "10.10.6"),
    ("http://128.105.146.171:5000", "10.10.7"),
    ("http://128.105.146.172:5000", "10.10.8")
    ]
API_URL = "http://128.105.145.65:10100/api/node/get_workers"

command_start_node = "sudo NodeEngine -n 6000 -p 10000 -r 128.105.145.65"
command_exit_node = ""

def send_command(command, http_url, node_ip, tracking):
    try:
        # Send the POST request with the command as JSON data
        response = requests.post(f"{http_url}/run-command", json={"command": command, "cluster_ip": f"{node_ip}.2"})
        print("RESPONSE: ", response.text)
        print("CODE", response.status_code)
        # Check if the response is successful
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                tracking[http_url] = data.get("pid")
                print(data)
                return data.get("pid")
            else:
                print(f"Error: {data.get('error', 'Unknown error')}")
        else:
            print(f"Failed to execute command. HTTP Status Code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def kill_process(pid, http_url):
    try:
        # Send the POST request with the PID to kill the process
        response = requests.post(f"{http_url}/kill-process", json={"pid": pid})

        # Check if the response is successful
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"Process with PID {pid} terminated successfully.")
            else:
                print(f"Error: {data.get('error', 'Unknown error')}")
        else:
            print(f"Failed to kill process. HTTP Status Code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    data = {}
    interval = 10

    time.sleep(interval)

    threads = []
    for worker in WORKER_URLS[0:4]:
        thread = threading.Thread(target=send_command, args=(command_start_node, worker[0], worker[1], data))
        threads.append(thread)
        thread.start()
    time.sleep(interval)

    for worker in WORKER_URLS[2:4]:
        if data.get(worker[0]):
            thread = threading.Thread(target=kill_process, args=(data[worker[0]], worker[0]))
            threads.append(thread)
            thread.start()
    time.sleep(interval)

    for worker in WORKER_URLS[2:6]:
        thread = threading.Thread(target=send_command, args=(command_start_node, worker[0], worker[1], data))
        threads.append(thread)
        thread.start()
    time.sleep(interval)

    for worker in WORKER_URLS[4:6]:
        if data.get(worker[0]):
            thread = threading.Thread(target=kill_process, args=(data[worker[0]], worker[0]))
            threads.append(thread)
            thread.start()
    time.sleep(interval)

    for worker in WORKER_URLS[4:8]:
        thread = threading.Thread(target=send_command, args=(command_start_node, worker[0], worker[1], data))
        threads.append(thread)
        thread.start()
    time.sleep(interval*3)

    for worker in WORKER_URLS[4:8]:
        if data.get(worker[0]):
            thread = threading.Thread(target=kill_process, args=(data[worker[0]], worker[0]))
            threads.append(thread)
            thread.start()
    time.sleep(interval)

    for worker in WORKER_URLS[4:6]:
        thread = threading.Thread(target=send_command, args=(command_start_node, worker[0], worker[1], data))
        threads.append(thread)
        thread.start()
    time.sleep(interval)

    for worker in WORKER_URLS[2:6]:
        if data.get(worker[0]):
            thread = threading.Thread(target=kill_process, args=(data[worker[0]], worker[0]))
            threads.append(thread)
            thread.start()
    time.sleep(interval)

    for worker in WORKER_URLS[2:4]:
        thread = threading.Thread(target=send_command, args=(command_start_node, worker[0], worker[1], data))
        threads.append(thread)
        thread.start()
    time.sleep(interval)

    for worker in WORKER_URLS[0:4]:
        if data.get(worker[0]):
            thread = threading.Thread(target=kill_process, args=(data[worker[0]], worker[0]))
            threads.append(thread)
            thread.start()
    time.sleep(interval)

    print("HELLO")
    for thread in threads:
        thread.join()
    time.sleep(interval)
