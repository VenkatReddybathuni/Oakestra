import requests
import json
import time


credentials = {"username":"Admin", "password":"Admin"}

# IP here must be replaced with the root orchestrator's IP. Same applies to line 21
auth_response = requests.post("http://128.110.223.18:10000/api/auth/login", json=credentials) 

auth_data = auth_response.json()
token = auth_data['token']

data = []
start = time.time()
i = 0

auth = {'Authorization': 'Bearer {}'.format(token)}

while time.time() - start < 120:
    services_response = requests.get("http://128.110.223.18:10000/api/services/", headers=auth).text
    num_node_sched = services_response.count("NODE_SCHEDULED")
    num_running = services_response.count("RUNNING")
    data.append({
        "time":(time.time()-start),
        "running": services_response.count("RUNNING"),
        "node_scheduled": services_response.count("NODE_SCHEDULED"),
        "failed": services_response.count("FAILED"),
        "dead":services_response.count("DEAD"),
        "created":services_response.count("CREATED")
    })
    i += 1
    print(i)

with open('8_outputfile1', 'w') as fout:
    json.dump(data, fout)
